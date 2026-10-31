#!/usr/bin/env python3
"""Verify the concrete Docker runner and emit READY or NOT_READY; never runs an agent."""
from __future__ import annotations
import argparse, importlib.util, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
spec = importlib.util.spec_from_file_location("docker_runner", ROOT / "tools/docker_runner.py")
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)

def docker(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], text=True, capture_output=True, timeout=timeout)

def resolve_image() -> str:
    pulled = docker("pull", CONFIG["image"])
    if pulled.returncode:
        raise RuntimeError("image pull failed: " + pulled.stderr[-1000:])
    inspected = docker("image", "inspect", "--format", "{{json .RepoDigests}}", CONFIG["image"])
    refs = json.loads(inspected.stdout)
    if inspected.returncode or not refs:
        raise RuntimeError("image has no immutable repository digest")
    repository = CONFIG["image"].split(":", 1)[0] + "@sha256:"
    matches = [ref for ref in refs if ref.startswith(repository)]
    if len(matches) != 1:
        raise RuntimeError(f"cannot uniquely resolve image digest: {refs}")
    return matches[0]

def probe(workspace: Path, image: str, source: str) -> tuple[bool, str]:
    result = runner.run_python(workspace, ["-c", source], image=image,
                               timeout=CONFIG["timeout_seconds"])
    return result["ok"], result["output"][-1200:]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    checks = []
    image = None
    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail else ""))
    record("python_3_12", sys.version_info >= (3, 12), sys.version.split()[0])
    record("docker_installed", bool(shutil.which("docker")))
    record("ssh_keygen_installed", bool(shutil.which("ssh-keygen")))
    if shutil.which("docker"):
        try:
            image = resolve_image(); record("image_digest_resolved", True, image)
        except Exception as exc:
            record("image_digest_resolved", False, repr(exc))
    if image:
        with tempfile.TemporaryDirectory(prefix="pws-preflight-") as tmp:
            work = Path(tmp); (work / "sentinel.txt").write_text("unchanged\n", encoding="utf-8")
            probes = {
                "baseline": "print('container-ok')",
                "network_disabled": "import socket\ns=socket.socket();s.settimeout(1)\ntry:\n s.connect(('192.0.2.1',9));raise SystemExit(1)\nexcept OSError:\n print('network-blocked')\nfinally:\n s.close()",
                "network_namespace": "import pathlib\ninterfaces = {path.name for path in pathlib.Path('/sys/class/net').iterdir()}\nassert interfaces == {'lo'}, interfaces\nv4 = pathlib.Path('/proc/net/route')\nif v4.exists():\n for row in v4.read_text().splitlines()[1:]:\n  fields = row.split()\n  assert len(fields) < 2 or fields[1] != '00000000', fields\nv6 = pathlib.Path('/proc/net/ipv6_route')\nif v6.exists():\n for row in v6.read_text().splitlines():\n  fields = row.split()\n  assert len(fields) < 2 or not (fields[0] == '0'*32 and fields[1] == '00'), fields\nprint('only-loopback-no-default-route')",
                "workspace_read_only": "from pathlib import Path\ntry:\n Path('/work/forbidden-write').write_text('x');raise SystemExit(1)\nexcept OSError:\n print('readonly-ok')",
                "cgroup_limits": "from pathlib import Path\nm=Path('/sys/fs/cgroup/memory.max').read_text().strip();p=Path('/sys/fs/cgroup/pids.max').read_text().strip();assert m!='max' and int(m)<=268435456,(m,p);assert p!='max' and int(p)<=64,(m,p);print('cgroup-ok',m,p)",
                "host_credentials_not_inherited": "import os\nassert not os.environ.get('GITHUB_TOKEN');assert not os.environ.get('OPENAI_API_KEY');assert not os.environ.get('MOONSHOT_API_KEY');print('environment-clean')",
            }
            for name, source in probes.items():
                try:
                    ok, detail = probe(work, image, source); record(name, ok, detail.strip())
                except Exception as exc:
                    record(name, False, repr(exc))
            record("workspace_input_preserved", (work / "sentinel.txt").read_text() == "unchanged\n")
            record("no_workspace_escape_artifact", not (work / "forbidden-write").exists())
    ready = bool(checks) and all(c["ok"] for c in checks)
    report = {
        "protocol": "PWS-BENCH-PROTOCOL-1.2", "status": "READY" if ready else "NOT_READY",
        "checked_utc": datetime.now(timezone.utc).isoformat(), "image": image,
        "checks": checks, "agent_execution_performed": False,
        "scope": "runner capability only; AI provider credentials and signed execution attestations are separate requirements",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8")
    print(report["status"])
    return 0 if ready else 1
if __name__ == "__main__":
    raise SystemExit(main())
