#!/usr/bin/env python3
"""PWS-ARCHIVE-1: fixed, deterministic archive-validator regression corpus."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import warnings
import zipfile

ROOT = Path(__file__).resolve().parent
CASES = [
    ("valid_zip", True), ("valid_directory", True), ("fenced_example", True),
    ("missing_original", False), ("missing_extra", False), ("unexpected_payload", False),
    ("invalid_utf8", False), ("broken_local_link", False), ("broken_anchor", False),
    ("broken_image", False), ("broken_reference", False), ("missing_safety_marker", False),
    ("empty_readme", False), ("wrong_version", False), ("zip_symlink", False),
    ("directory_symlink", False), ("directory_fifo", False), ("zip_traversal", False),
    ("zip_absolute", False), ("zip_backslash", False), ("zip_drive", False),
    ("zip_alias", False), ("zip_double_separator", False), ("zip_duplicate", False),
    ("oversized_source", False), ("oversized_zip", False), ("python_syntax", False),
    ("optimized_missing_rule", False), ("crc_corrupt", False),
]


def digest(b):
    return hashlib.sha256(b).hexdigest()


def inventory(root):
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        mode = p.lstat().st_mode
        if stat.S_ISLNK(mode): out[rel] = {"type": "symlink", "target": os.readlink(p)}
        elif stat.S_ISFIFO(mode): out[rel] = {"type": "fifo"}
        elif p.is_file(): out[rel] = digest(p.read_bytes())
    return out


def prepare(source, parent, case):
    kit = parent / "kit"; shutil.copytree(source, kit)
    extra = []
    if case in ("missing_original", "missing_extra"):
        (kit / ("PROJECT.md" if case == "missing_original" else "examples/README.md")).unlink()
    elif case == "unexpected_payload": (kit / "payload.bin").write_bytes(b"unreviewed")
    elif case == "invalid_utf8": (kit / "PROJECT.md").write_bytes(b"\xff")
    elif case in ("broken_local_link", "broken_anchor", "broken_image", "broken_reference", "fenced_example"):
        addition = {"broken_local_link": "[bad](missing.md)", "broken_anchor": "[bad](AGENTS.md#missing)",
                    "broken_image": "![bad](missing.png)", "broken_reference": "[bad][undefined]",
                    "fenced_example": "```md\n[example](missing.md)\n```"}[case]
        with (kit / "README.md").open("a") as f: f.write("\n" + addition + "\n")
    elif case in ("missing_safety_marker", "optimized_missing_rule"):
        p = kit / "TESTING-LEVELS.md"; p.write_text(p.read_text().replace("не переносится автоматически", "переносится"))
    elif case == "empty_readme": (kit / "README.md").write_bytes(b"")
    elif case == "wrong_version":
        p = kit / "README.md"; p.write_text(p.read_text().replace("# Project Workflow Standard — 1.4-", "# Project Workflow Standard — 9.9-", 1))
    elif case == "directory_symlink":
        target = parent / "outside.md"; target.write_bytes((kit / "PROJECT.md").read_bytes())
        (kit / "PROJECT.md").unlink(); (kit / "PROJECT.md").symlink_to("../outside.md")
    elif case == "directory_fifo":
        (kit / "PROJECT.md").unlink(); os.mkfifo(kit / "PROJECT.md")
    elif case in ("oversized_source", "oversized_zip"): (kit / "PROJECT.md").write_bytes(b"x" * (256 * 1024 + 1))
    elif case == "python_syntax":
        with (kit / "tools/check_standard.py").open("a") as f: f.write("\ndef broken(:\n")
    extras = {"zip_traversal": "../payload.bin", "zip_absolute": "/payload.bin", "zip_backslash": "a\\payload.bin",
              "zip_drive": "C:/payload.bin", "zip_alias": "./payload.bin", "zip_double_separator": "a//payload.bin"}
    if case in extras: extra.append((extras[case], b"x"))
    if case not in ("valid_zip", "valid_directory", "crc_corrupt"):
        if inventory(kit) == inventory(source) and not extra and case not in ("zip_duplicate", "zip_symlink"):
            raise RuntimeError("mutation did not change input: " + case)
    if case in ("valid_directory", "directory_symlink", "directory_fifo", "oversized_source", "optimized_missing_rule"):
        return kit, inventory(kit)
    path = parent / "input.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
            for f in sorted(kit.rglob("*")):
                if f.is_file():
                    info = zipfile.ZipInfo(f.relative_to(kit).as_posix(), (2026, 11, 1, 0, 0, 0))
                    info.create_system = 3; info.external_attr = (stat.S_IFREG | 0o644) << 16
                    z.writestr(info, f.read_bytes())
            for name, data in extra: z.writestr(name, data)
            if case == "zip_symlink":
                i = zipfile.ZipInfo("payload"); i.create_system = 3; i.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(i, "../outside")
            if case == "zip_duplicate": z.writestr("PROJECT.md", (kit / "PROJECT.md").read_bytes())
    if case == "crc_corrupt":
        data = bytearray(path.read_bytes()); name_len, extra_len = struct.unpack_from("<HH", data, 26)
        data[30 + name_len + extra_len] ^= 1; path.write_bytes(data)
    return path, {"zip_sha256": digest(path.read_bytes())}


def run(output):
    variants = {"rc3": ROOT / "original-v1.4-rc3", "rc4": ROOT / "candidate-v1.4-rc4"}
    rows = []
    for case, expected in CASES:
        for repeat in range(1, 4):
            for version, source in variants.items():
                with tempfile.TemporaryDirectory() as temp:
                    target, inputs = prepare(source, Path(temp), case)
                    start = time.perf_counter()
                    command = [sys.executable] + (["-O"] if case == "optimized_missing_rule" else []) + [str(source / "tools/check_standard.py"), str(target)]
                    try:
                        p = subprocess.run(command, capture_output=True, text=True, timeout=10)
                        elapsed = time.perf_counter() - start
                        error = p.returncode not in (0, 1) or "Traceback" in p.stderr
                        rows.append({"case": case, "repeat": repeat, "variant": version, "expected_accept": expected,
                                     "accepted": p.returncode == 0, "tool_error": error, "exit": p.returncode,
                                     "elapsed_s": elapsed, "input": inputs,
                                     "stdout": p.stdout.replace(temp, "<tmp>"), "stderr": p.stderr.replace(temp, "<tmp>")})
                    except subprocess.TimeoutExpired:
                        rows.append({"case": case, "repeat": repeat, "variant": version, "expected_accept": expected,
                                     "accepted": False, "tool_error": True, "exit": None, "input": inputs,
                                     "elapsed_s": time.perf_counter() - start, "stderr": "timeout"})
                    if version == "rc3" and target.is_file():
                        start = time.perf_counter()
                        try:
                            with zipfile.ZipFile(target) as z: accepted = z.testzip() is None
                        except (zipfile.BadZipFile, RuntimeError): accepted = False
                        rows.append({"case": case, "repeat": repeat, "variant": "crc_only", "expected_accept": expected,
                                     "accepted": accepted, "tool_error": False, "exit": 0 if accepted else 1,
                                     "elapsed_s": time.perf_counter()-start, "input": inputs})
    summary = {}
    for version in ("crc_only", "rc3", "rc4"):
        subset = [r for r in rows if r["variant"] == version]
        summary[version] = {"runs": len(subset), "cases": len({r["case"] for r in subset}),
            "correct": sum(r["accepted"] == r["expected_accept"] and not r["tool_error"] for r in subset),
            "false_accept": sum(r["accepted"] and not r["expected_accept"] for r in subset),
            "false_reject": sum(not r["accepted"] and r["expected_accept"] for r in subset),
            "tool_error": sum(r["tool_error"] for r in subset),
            "elapsed_total_s": sum(r["elapsed_s"] for r in subset)}
    result = {"protocol": "PWS-ARCHIVE-1", "scope": "archive validators, not AI agents", "agent_runs": 0,
              "python": sys.version, "platform": platform.platform(),
              "evaluator_sha256": digest(Path(__file__).read_bytes()),
              "protocol_sha256": digest((ROOT / "PROTOCOL.md").read_bytes()),
              "sources": {k: inventory(v) for k, v in variants.items()}, "summary": summary, "runs": rows,
              "tokens": None, "cost": None, "ai_model": None}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["rc4"]["correct"] == summary["rc4"]["runs"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    sys.exit(run(parser.parse_args().output))
