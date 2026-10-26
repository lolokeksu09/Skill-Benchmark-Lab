#!/usr/bin/env python3
"""Run P2P intake cases against an extracted DDS skill-router package."""
import argparse
import importlib.util
import json
from pathlib import Path


def load_router(root):
    target = Path(root) / "skills/skill-router/scripts/route.py"
    if not target.is_file():
        raise ValueError(f"Missing router at: {target}")
    spec = importlib.util.spec_from_file_location("p2p_dds_router", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(router, cases):
    rows = []
    for case in cases:
        result = router.route(case["prompt"])
        names = {item["skill"] for item in result["initial"] + result["deferred"]}
        stack = set(result["stack"])
        issues = {
            "missing_required": sorted(set(case["required"]) - names),
            "selected_forbidden": sorted(set(case["forbidden"]) & names),
            "missing_stack": sorted(set(case["expected_stack"]) - stack),
            "forbidden_stack": sorted(set(case["forbidden_stack"]) & stack),
        }
        rows.append({
            "id": case["id"],
            "passed": not any(issues.values()),
            "issues": issues,
            "selected": sorted(names),
            "stack": sorted(stack),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, help="Extracted development-design-skills root")
    parser.add_argument(
        "--cases",
        default="benchmarks/diagnostics/p2p-dds-integration-v213-cases.json",
    )
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if len({row["id"] for row in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    rows = evaluate(load_router(args.candidate), cases)
    output = {
        "total": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": [row for row in rows if not row["passed"]],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    raise SystemExit(0 if not output["failed"] else 1)


if __name__ == "__main__":
    main()
