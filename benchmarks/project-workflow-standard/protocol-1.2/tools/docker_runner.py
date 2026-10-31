"""Fail-closed Docker execution. There is deliberately no host or bwrap fallback."""
from __future__ import annotations
import json, os, shutil, stat, subprocess, threading, uuid
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

def _inspect_absent(name: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(["docker", "container", "inspect", name],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=10, env={"PATH": "/usr/bin:/bin"})
        detail = (result.stdout + result.stderr).strip()[-1000:]
        return (result.returncode != 0 and
                ("No such object" in detail or "No such container" in detail)), detail
    except (OSError, subprocess.SubprocessError) as exc:
        return False, repr(exc)


def _cleanup(name: str) -> tuple[bool, list[str]]:
    notes = []
    absent, detail = _inspect_absent(name)
    if absent:
        return True, notes
    try:
        removed = subprocess.run(["docker", "rm", "-f", name], stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=10,
                                 env={"PATH": "/usr/bin:/bin"})
        if removed.returncode:
            notes.append(f"docker rm -f failed ({removed.returncode}): {(removed.stdout + removed.stderr)[-1000:]}")
    except (OSError, subprocess.SubprocessError) as exc:
        notes.append(f"docker rm -f error: {exc!r}")
    absent, detail = _inspect_absent(name)
    if not absent:
        notes.append(f"container absence not confirmed: {detail}")
    return absent, notes


def run_python(workspace: Path, args: list[str], image: str, harness: Path | None = None,
               payload: Path | None = None, timeout: int = 30, writable: bool = False) -> dict:
    """Fail-closed Docker execution, including container cleanup confirmation."""
    if not shutil.which("docker"):
        return {"ok": False, "status": "sandbox_unavailable", "exit_code": None,
                "output": "docker is required; host execution is forbidden", "container_removed": False}
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
    if payload is not None:
        payload = Path(payload)
        entry = payload.lstat()
        if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
            raise SandboxUnavailable("probe payload must be a real regular file; symlinks forbidden")
        if entry.st_size > 1024 * 1024:
            raise SandboxUnavailable("probe payload exceeds 1 MiB")
        payload = payload.resolve(strict=True)
        command += ["--mount", f"type=bind,source={payload},target=/probe.json,readonly"]
    command += [image, "python3", "-I", *args]
    sink: list[str] = []
    proc = None
    reader = None
    code = None
    status = "sandbox_error"
    error = ""
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env={"PATH": "/usr/bin:/bin"})
        reader = threading.Thread(target=_consume, args=(proc.stdout, sink), daemon=True)
        reader.start()
        try:
            code = proc.wait(timeout=timeout)
            status = "executed"
        except subprocess.TimeoutExpired:
            status = "timeout"
            error = f"docker run exceeded {timeout}s"
    except (OSError, subprocess.SubprocessError) as exc:
        error = f"docker run error: {exc!r}"
    finally:
        removed, notes = _cleanup(name)
        if proc is not None and proc.poll() is None:
            try:
                code = proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    notes.append("docker CLI did not terminate after kill")
        if reader is not None:
            reader.join(timeout=5)
    if not removed:
        status = "cleanup_failed"
    output = "".join(sink)
    if error or notes:
        output += "\n" + "\n".join([s for s in [error, *notes] if s])
    return {"ok": code == 0 and status == "executed" and removed,
            "status": status, "exit_code": code, "output": output,
            "backend": "docker-cgroup-network-none-readonly", "image": image,
            "container_removed": removed}
