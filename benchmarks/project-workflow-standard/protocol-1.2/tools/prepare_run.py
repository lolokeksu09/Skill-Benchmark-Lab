#!/usr/bin/env python3
"""Prepare an immutable-input run bundle; this does not launch an agent."""
import argparse, hashlib, importlib.util, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {"S05": "S05-unreproducible", "S06": "S06-release-exception"}
STANDARDS = {"v1.3", "v1.4-rc3"}
spec = importlib.util.spec_from_file_location("safe_io", ROOT / "tools/safe_io.py")
safe = importlib.util.module_from_spec(spec); spec.loader.exec_module(safe)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--standard", required=True, choices=sorted(STANDARDS))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeat < 1: parser.error("--repeat must be positive")
    bundle = args.output.resolve()
    if bundle.exists(): parser.error(f"target exists; refusing to overwrite: {bundle}")
    scenario_dir = ROOT / "scenarios" / SCENARIOS[args.scenario]
    fixture, standard = scenario_dir / "fixture", ROOT / "standards" / args.standard
    workspace = bundle / "workspace"
    bundle.mkdir(parents=True)
    shutil.copytree(fixture, workspace)
    shutil.copytree(standard, workspace / "_standard")
    shutil.copy2(scenario_dir / "task.md", workspace / "TASK.md")
    metadata = {"run_id": f"{args.scenario}-{args.standard}-r{args.repeat}",
                "protocol": "PWS-BENCH-PROTOCOL-1.2", "scenario": args.scenario,
                "standard": args.standard, "repeat": args.repeat,
                "status": "prepared_not_executed", "fixture_sha256": safe.tree_hash(fixture),
                "standard_tree_sha256": safe.tree_hash(standard),
                "prepared_utc": datetime.now(timezone.utc).isoformat(),
                "agent": {"model": None, "provider": None, "tokens": "not_measured", "cost": "not_measured"}}
    (bundle / "RUN.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    environment = {"status": "unverified_prepared_bundle",
                   "note": "JSON flags are not evidence. Acceptance requires a signed runner attestation bound to this run."}
    (bundle / "environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (bundle / "tool-log.jsonl").write_text("", encoding="utf-8")
    print(f"Prepared only: {bundle}\nAgent-visible root: {workspace}\nNo agent was launched.")
    return 0
if __name__ == "__main__": sys.exit(main())
