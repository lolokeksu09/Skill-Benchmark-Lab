#!/usr/bin/env python3
"""Compare two already extracted trusted router packages using fixed-case expectations.

Example:
  python benchmarks/diagnostics/check_router_variants.py \
    --baseline /path/to/extracted-v201/plugin-root \
    --candidate /path/to/extracted-v202/plugin-root
The script imports Python router code from both directories. Use only trusted ZIPs
whose SHA-256 matches the pinned snapshot. No network or paid model calls.
"""
import argparse
import importlib.util
import json
from pathlib import Path


def load_router(root, label):
    target = Path(root) / "skills/skill-router/scripts/route.py"
    if not target.is_file():
        raise ValueError(f"Missing router at: {target}")
    spec = importlib.util.spec_from_file_location(label, target)
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
        rows.append({"id": case["id"], "passed": not any(issues.values()),
                     "issues": issues, "selected": sorted(names), "stack": sorted(stack)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="Extracted V2.0.1 plugin root")
    parser.add_argument("--candidate", required=True, help="Extracted V2.0.2 plugin root")
    parser.add_argument("--cases", default="benchmarks/diagnostics/router-independent-cases-v202.json")
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if len({row["id"] for row in cases}) != len(cases):
        raise ValueError("Duplicate IDs in independent cases")
    baseline = evaluate(load_router(args.baseline, "baseline_router"), cases)
    candidate = evaluate(load_router(args.candidate, "candidate_router"), cases)
    output = {
        "total": len(cases),
        "baseline_passed": sum(row["passed"] for row in baseline),
        "candidate_passed": sum(row["passed"] for row in candidate),
        "candidate_failures": [row for row in candidate if not row["passed"]],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    raise SystemExit(0 if len(output["candidate_failures"]) == 0 else 1)


if __name__ == "__main__":
    main()
