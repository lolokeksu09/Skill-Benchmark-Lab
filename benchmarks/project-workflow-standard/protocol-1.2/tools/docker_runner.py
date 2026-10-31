"""Fail-closed Docker execution. There is deliberately no host or bwrap fallback."""
from __future__ import annotations
import json, os, shutil, subprocess, threading, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
OUTPUT_LIMIT = 1024 * 1024

class SandboxUnavailable(RuntimeError):
    pass

def _consume(pipe, sink: list[str]) -> None:
    total = 0
    while True:
        chunk = pipe.read(65536)
        if not chunk:
            return
        if total < OUTPUT_LIMIT:
            data = chunk[:OUTPUT_LIMIT-total]
            sink.append(data.decode("utf-8", "replace")); total += len(data)

def run_python(workspace: Path, args: list[str], image: str, harness: Path | None = None,
               timeout: int = 30, writable: bool = False) -> dict:
    """Run untrusted code in a new network-less, cgroup-limited container."""
    if not shutil.which("docker"):
        return {"ok": False, "status": "sandbox_unavailable", "exit_code": None,
                "output": "docker is required; host execution is forbidden"}
    if "@sha256:" not in image:
        raise SandboxUnavailable("resolved image digest required; tags are not an execution identity")
    workspace = Path(workspace)
    if not workspace.is_dir() or workspace.is_symlink():
        raise SandboxUnavailable("workspace must be a real directory")
    name = "pws-" + uuid.uuid4().hex
    command = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
               "--pids-limit", str(CONFIG["pids"]), "--memory", str(CONFIG["memory"]),
               "--memory-swap", str(CONFIG["memory"]), "--cpus", str(CONFIG["cpus"]),
               "--ulimit", "nofile=64:64", "--user", "65532:65532",
               "--tmpfs", "/tmp:rw,noexec,nosuid,size=16777216",
               "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "PYTHONHASHSEED=0",
               "--env", "CANDIDATE_WORKSPACE=/work", "--workdir", "/work",
               "--mount", f"type=bind,source={workspace.resolve()},target=/work,{'' if writable else 'readonly'}"]
    if harness is not None:
        harness = Path(harness).resolve()
        command += ["--mount", f"type=bind,source={harness},target=/harness.py,readonly"]
    command += [image, "python3", "-I", *args]
    sink: list[str] = []
    proc = None
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env={"PATH": "/usr/bin:/bin"})
        reader = threading.Thread(target=_consume, args=(proc.stdout, sink), daemon=True)
        reader.start()
        try:
            code = proc.wait(timeout=timeout)
            status = "executed"
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", name], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, env={"PATH": "/usr/bin:/bin"})
            code = proc.wait(timeout=10); status = "timeout"
        reader.join(timeout=5)
        output = "".join(sink)
        return {"ok": code == 0 and status == "executed", "status": status, "exit_code": code,
                "output": output, "backend": "docker-cgroup-network-none-readonly",
                "image": image, "container_removed": True}
    except (OSError, subprocess.SubprocessError) as exc:
        if proc is not None and proc.poll() is None:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, env={"PATH": "/usr/bin:/bin"})
        return {"ok": False, "status": "sandbox_error", "exit_code": None,
                "output": repr(exc), "backend": "docker"}
