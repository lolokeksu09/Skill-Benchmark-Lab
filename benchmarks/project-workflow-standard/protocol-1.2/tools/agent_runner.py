#!/usr/bin/env python3
"""Auditable AI runner bridge: fail-closed, tool-mediated agent execution.

The external agent command receives no workspace path and no host environment
except PATH/HOME and variables explicitly allowed via --allow-env. All
workspace access happens through a bounded JSON-lines tool protocol:

  bridge -> agent: {"type":"hello",...} / {"type":"tool_result",...}
  agent -> bridge: {"type":"tool_call",...} / {"type":"finish",...}

Allowed tools: list_files, read_file, write_file, run_tests, finish.
Unknown tools, malformed messages, and path traversal fail closed and
terminate the run. TASK.md and _standard/ are immutable benchmark inputs:
write_file refuses them without failing the whole run. Every protocol
message is appended to the bundle tool-log.jsonl so the log is complete
by construction; logged string values over 4096 chars are stored as
sha256+preview with a truncated flag, and the log carries a byte budget,
so the attested log stays bounded and hashable.

The evidence payload written here is UNSIGNED. The operator signs it
separately with the runner key (namespace pws-runner-v1). JSON flags in
this payload are claims for the fail-closed acceptance path in
tools/evaluate.py, not self-certifying evidence.

This tool never contains AI-provider credentials and never invokes a
real AI provider by itself; --agent-command is supplied by the operator.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, shlex, shutil
import signal, subprocess, sys, tempfile, threading, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {"S05": "S05-unreproducible", "S06": "S06-release-exception"}
PROTOCOL = "pws-agent-bridge-v1"
BRIDGE_VERSION = "1.0.0"
MAX_LINE_BYTES = 1024 * 1024
MAX_WRITE_BYTES = 1024 * 1024
MAX_TURNS = 200
GRACE_SECONDS = 10
REQUIRED_ENV = ["workspace_root_only", "network_disabled", "external_credentials_absent",
                "publication_tools_absent", "resource_limits_enforced", "tool_log_complete"]
LOG_VALUE_LIMIT = 4096
LOG_BUDGET_BYTES = 3 * 1024 * 1024

def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded)
    return loaded
safe = module("safe_io", ROOT / "tools/safe_io.py")
attest = module("attestations", ROOT / "tools/attestations.py")
docker = module("docker_runner", ROOT / "tools/docker_runner.py")

class BridgeError(RuntimeError):
    pass

def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _bounded(value, _depth: int = 0):
    """Bound logged string values; large payloads become digest + preview.

    The full value is still sent to the agent; only the log entry is
    bounded, so the attested tool log can never grow unboundedly via
    repeated large read_file/write_file payloads.
    """
    if isinstance(value, str) and len(value) > LOG_VALUE_LIMIT:
        return {"sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                "preview": value[:256], "length": len(value), "truncated": True}
    if isinstance(value, dict):
        return {key: _bounded(item, _depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)) and _depth < 8:
        return [_bounded(item, _depth + 1) for item in value]
    return value

def _log_event(log, event: dict) -> None:
    """Append one bounded event to the tool log and enforce the byte budget."""
    log.write(json.dumps(_bounded(event), ensure_ascii=False) + "\n"); log.flush()
    if os.fstat(log.fileno()).st_size > LOG_BUDGET_BYTES:
        raise BridgeError("tool log byte budget exceeded; refusing unbounded evidence")

def _send(proc, log, event: dict) -> None:
    line = json.dumps(event, ensure_ascii=False)
    _log_event(log, event)
    try:
        proc.stdin.write((line + "\n").encode("utf-8")); proc.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise BridgeError(f"agent is not reading the protocol: {exc!r}") from exc

def _drain_stderr(pipe, sink: list[str]) -> None:
    total = 0
    while True:
        chunk = pipe.read(65536)
        if not chunk:
            return
        if total < MAX_LINE_BYTES:
            sink.append(chunk.decode("utf-8", "replace")); total += len(chunk)

class LineReader:
    """Bounded blocking line reader that survives multiple messages per chunk.

    Reads are plain blocking os.read; the overall deadline is enforced by a
    watchdog timer that kills the agent process group, so a stuck or
    misbehaving agent can never hang the bridge beyond --timeout.
    """
    def __init__(self, fd: int, limit: int):
        self.fd = fd
        self.limit = limit
        self.buffer = bytearray()

    def readline(self) -> bytes:
        """Return the next line without the newline; b"" means EOF."""
        while True:
            index = self.buffer.find(b"\n")
            if index >= 0:
                line = bytes(self.buffer[:index])
                del self.buffer[:index + 1]
                if len(line) > self.limit:
                    raise BridgeError(f"protocol line exceeds {self.limit} bytes")
                return line
            if len(self.buffer) > self.limit:
                raise BridgeError(f"protocol line exceeds {self.limit} bytes")
            chunk = os.read(self.fd, 65536)
            if not chunk:
                line = bytes(self.buffer)
                self.buffer.clear()
                return line
            self.buffer.extend(chunk)

def _is_traversal(path) -> bool:
    text = str(path).replace("\\", "/")
    return text.startswith("/") or any(part == ".." for part in text.split("/"))

def _list_files(workspace: Path, prefix: str = "") -> list[str]:
    names: list[str] = []
    entries = 0
    for directory, dirnames, filenames in os.walk(workspace, followlinks=False):
        rel_dir = Path(directory).relative_to(workspace)
        depth = 0 if rel_dir == Path(".") else len(rel_dir.parts)
        if depth + 1 > safe.MAX_SNAPSHOT_DEPTH:
            raise safe.UnsafeFile("list_files depth limit exceeded")
        for name in list(dirnames):
            entry = Path(directory) / name
            if entry.is_symlink() or not entry.is_dir():
                raise safe.UnsafeFile(f"unsafe directory entry: {entry.relative_to(workspace)}")
            entries += 1
            if entries > safe.MAX_SNAPSHOT_FILES:
                raise safe.UnsafeFile("list_files entry limit exceeded")
            rel = entry.relative_to(workspace).as_posix() + "/"
            if not prefix or rel.startswith(prefix):
                names.append(rel)
        for name in filenames:
            entry = Path(directory) / name
            if entry.is_symlink() or not entry.is_file():
                raise safe.UnsafeFile(f"unsafe file entry: {entry.relative_to(workspace)}")
            entries += 1
            if entries > safe.MAX_SNAPSHOT_FILES:
                raise safe.UnsafeFile("list_files entry limit exceeded")
            rel = entry.relative_to(workspace).as_posix()
            if not prefix or rel.startswith(prefix):
                names.append(rel)
    return sorted(names)

def _verify_pristine_inputs(workspace: Path, meta: dict) -> None:
    """Verify both trusted standard and non-standard pristine inputs before agent spawn."""
    scenario_dir = ROOT / "scenarios" / SCENARIOS[meta["scenario"]]
    fixture = scenario_dir / "fixture"
    if meta.get("fixture_sha256") != safe.tree_hash(fixture):
        raise BridgeError("fixture provenance mismatch")
    expected = safe.snapshot(fixture)
    if "TASK.md" in expected:
        raise BridgeError("fixture shadows TASK.md")
    expected["TASK.md"] = hashlib.sha256(safe.read_bytes(scenario_dir, "task.md")).hexdigest()
    if safe.snapshot(workspace, exclude=("_standard",)) != expected:
        raise BridgeError("non-standard workspace inputs differ from pristine fixture and TASK.md")
    trusted = json.loads((ROOT / "standards/manifest.json").read_text(encoding="utf-8"))["files"]
    standard_dir = workspace / "_standard"
    actual = safe.snapshot(standard_dir)
    versions = [v for v in ("v1.3", "v1.4-rc3") if actual == trusted[v]]
    if len(versions) != 1:
        raise BridgeError("standard tree does not match exactly one trusted version")
    if meta.get("standard_tree_sha256") != safe.tree_hash(standard_dir):
        raise BridgeError("standard tree metadata hash mismatch")


def _run_tests(workspace: Path, scenario: str, image: str, timeout: int = 120) -> dict:
    if scenario != "S05":
        return {"ok": False, "available": False,
                "error": "run_tests is not available for this scenario; no automated candidate test suite exists"}
    driver = ("import sys,unittest;sys.path.insert(0,'/work');"
              "s=unittest.defaultTestLoader.discover('/work/tests');"
              "r=unittest.TextTestRunner(verbosity=2).run(s);"
              "raise SystemExit(not r.wasSuccessful())")
    result = docker.run_python(workspace, ["-c", driver], image=image, timeout=timeout)
    return {"ok": bool(result.get("ok")), "available": True, "status": result.get("status"),
            "exit_code": result.get("exit_code"), "output": str(result.get("output", ""))[-4000:],
            "backend": result.get("backend"), "image": result.get("image"),
            "container_removed": result.get("container_removed")}

def _terminate(proc: subprocess.Popen) -> dict:
    """Kill the whole agent process group and reap it; never leave an orphan.

    The killpg is unconditional: a parent that already exited may have left
    orphan children in its process group, and they would otherwise keep
    running (and keep the protocol pipes open) after the bridge concludes.
    The pgid is captured at spawn time because os.getpgid() stops working on
    the pid once the exited agent has been reaped by poll(). Note that a
    child which creates its own session escapes process-group termination;
    containing such an adapter is the OS-level isolation boundary documented
    in README.md (trusted adapter model). `terminated_by_bridge` records only
    whether the agent process itself was still running and had to be killed;
    a no-op killpg on an empty group does not flip it, so a clean positive
    run still reports terminated_by_bridge=False.
    """
    state = {"terminated_by_bridge": False, "timed_out": False}
    if proc.poll() is None:
        state["terminated_by_bridge"] = True
    pgid = getattr(proc, "pws_pgid", None)
    if pgid is None:
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            pgid = None
    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    state["exit_code"] = proc.returncode
    return state

def build_agent_env(allow_env: list[str], home: Path) -> dict:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    for name in allow_env:
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
            raise BridgeError(f"invalid --allow-env name: {name!r}")
        if name in os.environ:
            env[name] = os.environ[name]
    return env

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bundle", type=Path)
    p.add_argument("--agent-command", required=True, help="external agent command line (shlex-split); never receives the workspace path")
    p.add_argument("--preflight", type=Path, required=True, help="signed-runner preflight report with READY status and exact image")
    p.add_argument("--image", required=True, help="immutable image digest; must equal preflight image")
    p.add_argument("--timeout", type=int, default=600, help="overall agent wall-clock budget in seconds")
    p.add_argument("--allow-env", action="append", default=[], help="host variable name the agent process may receive; repeatable")
    p.add_argument("--output", type=Path, help="unsigned runner evidence payload output path")
    args = p.parse_args()

    if args.timeout < 1:
        p.error("--timeout must be positive")
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-fA-F]{64}", args.image):
        p.error("--image must be an immutable digest reference")
    argv = shlex.split(args.agent_command)
    if not argv:
        p.error("--agent-command must not be empty")
    if not shutil.which(argv[0]):
        p.error(f"agent executable not found: {argv[0]}")

    bundle = args.bundle.resolve()
    workspace = bundle / "workspace"
    if not workspace.is_dir() or workspace.is_symlink():
        p.error("bundle with a real workspace directory required")
    meta = safe.read_json(bundle, "RUN.json")
    if meta.get("protocol") != "PWS-BENCH-PROTOCOL-1.2" or meta.get("scenario") not in SCENARIOS:
        p.error("valid Protocol 1.2 run bundle required")
    preflight_path = args.preflight.resolve()
    preflight = safe.read_json(preflight_path.parent, preflight_path.name)
    if (preflight.get("protocol") != meta["protocol"] or preflight.get("status") != "READY"
            or preflight.get("image") != args.image):
        p.error("preflight must be READY and bind the exact --image digest")
    try:
        _verify_pristine_inputs(workspace, meta)
    except (BridgeError, safe.UnsafeFile, OSError, ValueError, KeyError) as exc:
        p.error(f"untrusted initial workspace: {exc}")
    evaluator_path = ROOT / "scenarios" / SCENARIOS[meta["scenario"]] / "evaluator.py"

    critical: list[str] = []
    tool_calls = 0
    bytes_written = 0
    agent_info = {"model": None, "provider": None, "tokens": "not_measured", "cost": "not_measured"}
    status = "failed_bridge"
    started = _utc()
    log_path = bundle / "tool-log.jsonl"

    with tempfile.TemporaryDirectory() as scratch, open(log_path, "a", encoding="utf-8") as log:
        scratch_path = Path(scratch)
        env = build_agent_env(args.allow_env, scratch_path / "home")
        (scratch_path / "home").mkdir()
        stderr_sink: list[str] = []
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, cwd=scratch_path,
                                start_new_session=True)
        try:
            proc.pws_pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            proc.pws_pgid = None
        stderr_thread = threading.Thread(target=_drain_stderr, args=(proc.stderr, stderr_sink), daemon=True)
        stderr_thread.start()
        timed_out = threading.Event()
        def _watchdog() -> None:
            timed_out.set()
            _terminate(proc)
        watchdog = threading.Timer(args.timeout, _watchdog)
        watchdog.daemon = True
        watchdog.start()
        finished = False
        termination = {"terminated_by_bridge": False, "timed_out": False}
        deadline = time.monotonic() + args.timeout
        try:
            manifest = _list_files(workspace)
            task_text = safe.read_text(workspace, "TASK.md", 64 * 1024)
            _send(proc, log, {"type": "hello", "protocol": PROTOCOL, "bridge_version": BRIDGE_VERSION,
                              "scenario": meta["scenario"], "task": task_text,
                              "workspace_manifest": manifest})
            reader = LineReader(proc.stdout.fileno(), MAX_LINE_BYTES)
            while not finished:
                if tool_calls > MAX_TURNS:
                    critical.append("turn_limit_exceeded")
                    break
                raw = reader.readline()
                if raw == b"":
                    if timed_out.is_set():
                        termination["timed_out"] = True
                        critical.append("agent_timeout")
                    else:
                        critical.append("agent_exit_without_finish")
                    break
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    critical.append("malformed_agent_message")
                    break
                if not isinstance(message, dict):
                    critical.append("malformed_agent_message")
                    break
                if message.get("type") == "finish":
                    _log_event(log, {"type": "finish", "model": message.get("model"),
                                     "provider": message.get("provider")})
                    for key in agent_info:
                        if isinstance(message.get(key), str):
                            agent_info[key] = message[key]
                    finished = True
                    break
                if message.get("type") != "tool_call":
                    critical.append("malformed_agent_message")
                    break
                tool_calls += 1
                _log_event(log, message)
                tool = message.get("tool")
                call_id = message.get("id")
                result: dict = {"type": "tool_result", "id": call_id, "ok": False}
                if not isinstance(tool, str) or tool not in {"list_files", "read_file", "write_file", "run_tests"}:
                    critical.append("forbidden_tool")
                    if isinstance(tool, str) and tool:
                        result["action"] = tool
                    result["error"] = f"forbidden tool: {tool!r}"
                    _send(proc, log, result)
                    break
                path = message.get("path")
                if tool in {"read_file", "write_file"} and _is_traversal(path):
                    result["outside_workspace"] = True
                    result["error"] = f"path escapes workspace: {path!r}"
                    critical.append("workspace_escape_attempt")
                    _send(proc, log, result)
                    break
                try:
                    if tool == "list_files":
                        prefix = message.get("prefix") or ""
                        if not isinstance(prefix, str) or _is_traversal(prefix):
                            raise safe.UnsafeFile(f"unsafe prefix: {prefix!r}")
                        result.update(ok=True, files=_list_files(workspace, prefix))
                    elif tool == "read_file":
                        result.update(ok=True, content=safe.read_text(workspace, path, MAX_LINE_BYTES))
                    elif tool == "write_file":
                        content = message.get("content")
                        if not isinstance(content, str):
                            raise safe.UnsafeFile("write_file content must be a string")
                        text_path = str(path).replace("\\", "/")
                        if text_path == "TASK.md" or text_path.startswith("_standard/"):
                            raise safe.UnsafeFile(
                                "immutable benchmark input: TASK.md and _standard/ cannot be modified")
                        data = content.encode("utf-8")
                        safe.write_bytes(workspace, path, data, MAX_WRITE_BYTES)
                        bytes_written += len(data)
                        result.update(ok=True, bytes=len(data),
                                      sha256=hashlib.sha256(data).hexdigest())
                    elif tool == "run_tests":
                        remaining = int(deadline - time.monotonic())
                        outcome = _run_tests(workspace, meta["scenario"], args.image,
                                             timeout=max(1, min(120, remaining)))
                        result.update(ok=bool(outcome.get("ok")), **{k: v for k, v in outcome.items() if k != "ok"})
                except safe.UnsafeFile as exc:
                    result["error"] = f"unsafe path or content: {exc}"
                except OSError as exc:
                    result["error"] = f"filesystem error: {exc!r}"
                _send(proc, log, result)
            if finished and proc.poll() is None:
                try:
                    proc.wait(timeout=GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    critical.append("agent_did_not_exit_after_finish")
            if finished and not critical and proc.returncode not in (0, None):
                critical.append(f"agent_exit_nonzero:{proc.returncode}")
            termination.update(_terminate(proc))
            stderr_thread.join(timeout=5)
        except (BrokenPipeError, OSError, BridgeError) as exc:
            critical.append(f"bridge_error: {exc!r}")
            termination.update(_terminate(proc))
            stderr_thread.join(timeout=5)
        except Exception as exc:  # defensive: any unexpected bridge defect fails closed, never hangs open
            critical.append(f"bridge_unexpected_error: {exc!r}")
            termination.update(_terminate(proc))
            stderr_thread.join(timeout=5)
        finally:
            watchdog.cancel()
        termination["timed_out"] = termination["timed_out"] or timed_out.is_set()

        if finished and not critical and not termination["terminated_by_bridge"]:
            status = "executed"
        elif termination["timed_out"]:
            status = "terminated_timeout"
        elif critical:
            status = "failed_bridge"
        else:
            status = "terminated_by_bridge"

        workspace_hash = safe.tree_hash(workspace)
        tool_log_hash = attest.file_hash(log_path)
        meta["status"] = status
        meta["agent"] = agent_info
        meta["executed_utc"] = _utc()
        (bundle / "RUN.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (bundle / "environment.json").write_text(json.dumps({
            "status": "runner_bridge_attested",
            "note": ("Environment booleans describe guarantees of the runner bridge for candidate "
                     "code execution and workspace access. The external agent process itself is "
                     "trusted runner infrastructure and runs on the host under operator control; "
                     "the workspace path is never disclosed to it."),
            "bridge_protocol": PROTOCOL, "bridge_version": BRIDGE_VERSION,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        evidence = {
            "kind": "runner",
            "status": status,
            "run_id": meta["run_id"],
            "protocol": meta["protocol"],
            "scenario": meta["scenario"],
            "bridge": {"protocol": PROTOCOL, "version": BRIDGE_VERSION,
                       "tool_calls": tool_calls, "bytes_written": bytes_written,
                       "workspace_path_disclosed": False},
            "agent": agent_info,
            "workspace_sha256": workspace_hash,
            "tool_log_sha256": tool_log_hash,
            "scenario_evaluator_sha256": attest.file_hash(evaluator_path),
            "preflight_sha256": attest.file_hash(preflight_path),
            "image": args.image,
            "environment": {key: True for key in REQUIRED_ENV},
            "environment_notes": {
                "workspace_root_only": "all file access mediated by safe_io rooted at the workspace; agent command never receives the workspace path",
                "network_disabled": "candidate code executes only via docker --network none",
                "external_credentials_absent": "agent env is PATH/HOME plus explicitly disclosed --allow-env only (see trusted_side.allow_env); candidate container receives no credentials",
                "publication_tools_absent": "candidate container is read-only with no credentials and no network",
                "resource_limits_enforced": "docker --pids-limit/--memory/--cpus on every candidate execution",
                "tool_log_complete": "every protocol message is appended to tool-log.jsonl before any tool executes; values over 4096 chars are logged as sha256+preview with a truncated flag and the log has a byte budget",
            },
            "trusted_side": {"allow_env": sorted(args.allow_env),
                             "note": ("The external agent process is trusted runner infrastructure. "
                                      "--allow-env names are operator-approved host variables passed to it; "
                                      "they are disclosed here and must never include AI-provider credentials.")},
            "started_utc": started,
            "finished_utc": _utc(),
            "timeout_seconds": args.timeout,
            "process": {"terminated_by_bridge": termination["terminated_by_bridge"],
                        "timed_out": termination["timed_out"], "exit_code": termination.get("exit_code")},
            "agent_stderr_tail": "".join(stderr_sink)[-4000:],
            "critical_errors": critical,
            "unsigned": True,
            "note": "Unsigned evidence payload. Operator signs with the runner key (namespace pws-runner-v1); acceptance requires the fail-closed checks in tools/evaluate.py.",
        }

    out = args.output or (bundle / "runner-evidence.json")
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(out), "status": status, "run_id": meta["run_id"],
                      "tool_calls": tool_calls, "critical_errors": critical}, ensure_ascii=False))
    return 0
if __name__ == "__main__":
    sys.exit(main())
