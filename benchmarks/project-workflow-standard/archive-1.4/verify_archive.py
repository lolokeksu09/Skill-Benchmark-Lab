#!/usr/bin/env python3
"""Run the archive acceptance gates and create a checked ZIP. Never deploys."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(output, expected_revision=None):
    output.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if expected_revision is not None and revision != expected_revision:
        raise RuntimeError("checkout differs from expected revision: " + revision)
    source = json.loads((ROOT / "SOURCE.json").read_text())
    for folder, key in [("original-v1.4-rc3", "original_files"), ("reference-v1.3", "v1.3_files")]:
        actual = {p.relative_to(ROOT / folder).as_posix(): sha(p.read_bytes()) for p in (ROOT / folder).rglob("*") if p.is_file()}
        if actual != source[key]: raise RuntimeError("frozen source differs: " + folder)
    candidate = ROOT / "candidate-v1.4-rc4"
    checker = candidate / "tools/check_standard.py"
    commands = []

    def run(args, name, optimized=False):
        env = os.environ.copy()
        env.pop("PYTHONOPTIMIZE", None)
        if optimized: env["PYTHONOPTIMIZE"] = "1"
        proc = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
        log = output / (name + ".log")
        log.write_text(proc.stdout + proc.stderr)
        commands.append({"command": args, "optimized": optimized, "exit": proc.returncode,
                         "log": log.name, "sha256": sha(log.read_bytes())})
        if proc.returncode: raise RuntimeError(name + " failed; see " + str(log))
        print("PASS", name)

    run([sys.executable, str(checker), str(candidate), "--json"], "package")
    for opt in [False, True]:
        run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT), "-p", "test_checker.py"],
            "tests-optimized" if opt else "tests-normal", optimized=opt)
    run([sys.executable, str(ROOT / "compare_archives.py"), "--output", str(output / "RESULTS.json")], "comparison")
    path = output / "Project-Workflow-Standard-v1.4-rc4.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(candidate.rglob("*")):
            if f.is_file():
                info = zipfile.ZipInfo(f.relative_to(candidate).as_posix(), (2026, 11, 1, 0, 0, 0))
                info.create_system = 3; info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, f.read_bytes())
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None: raise RuntimeError("artifact CRC failed")
        archived = {n: sha(z.read(n)) for n in z.namelist()}
    tree = {p.relative_to(candidate).as_posix(): sha(p.read_bytes()) for p in candidate.rglob("*") if p.is_file()}
    if len(archived) != 16 or archived != tree: raise RuntimeError("artifact tree mismatch")
    run([sys.executable, str(checker), str(path), "--json"], "zip")
    run([sys.executable, "-O", str(checker), str(path), "--json"], "zip-optimized")
    build = {"git_head": revision, "working_diff": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
             "python": sys.version, "platform": platform.platform(), "artifact": path.name,
             "artifact_sha256": sha(path.read_bytes()), "artifact_bytes": path.stat().st_size,
             "candidate_files": tree, "commands": commands, "agent_runs": 0}
    (output / "BUILD.json").write_text(json.dumps(build, ensure_ascii=False, indent=2) + "\n")
    (output / "SHA256SUMS.txt").write_text(sha(path.read_bytes()) + "  " + path.name + "\n")
    print("PASS ZIP CRC, 16-file equality, original integrity; " + build["artifact_sha256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-revision", help="optional exact CI head gate")
    args = parser.parse_args()
    main(args.output.resolve(), args.expected_revision)
