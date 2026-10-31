#!/usr/bin/env python3
"""Require equal non-standard inputs and exactly v1.3 versus v1.4-rc3 trusted trees."""
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("safe_io", ROOT / "tools/safe_io.py")
safe = importlib.util.module_from_spec(spec); spec.loader.exec_module(safe)

def checked_bundle(path: Path):
    meta = safe.read_json(path, "RUN.json")
    if meta.get("protocol") != "PWS-BENCH-PROTOCOL-1.2":
        raise ValueError("wrong protocol")
    expected_standard = json.loads((ROOT / "standards/manifest.json").read_text())["files"][meta["standard"]]
    actual_standard = safe.snapshot(path / "workspace/_standard")
    if actual_standard != expected_standard:
        raise ValueError(f"untrusted or modified standard tree: {meta['standard']}")
    fixture = safe.tree_hash(ROOT / "scenarios" / {"S05":"S05-unreproducible","S06":"S06-release-exception"}[meta["scenario"]] / "fixture")
    if meta.get("fixture_sha256") != fixture:
        raise ValueError("fixture provenance mismatch")
    return meta, safe.snapshot(path / "workspace", exclude=("_standard",))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path); parser.add_argument("right", type=Path)
    args = parser.parse_args()
    try:
        a, a_files = checked_bundle(args.left.resolve()); b, b_files = checked_bundle(args.right.resolve())
        assert {a["standard"], b["standard"]} == {"v1.3", "v1.4-rc3"}, "pair must contain both standards"
        assert a["standard"] != b["standard"], "identical standards are not a comparison"
        assert a["scenario"] == b["scenario"] and a["repeat"] == b["repeat"], "scenario/repeat mismatch"
        if a_files != b_files:
            for key in sorted(set(a_files) | set(b_files)):
                if a_files.get(key) != b_files.get(key): print(f"DIFF {key}")
            return 1
    except (AssertionError, ValueError, KeyError, OSError) as exc:
        print(f"PAIR REJECTED: {exc}"); return 1
    print(f"PAIR OK: {a['scenario']} repeat {a['repeat']}; {a['standard']} vs {b['standard']}; {len(a_files)} equal non-standard files")
    return 0
if __name__ == "__main__": sys.exit(main())
