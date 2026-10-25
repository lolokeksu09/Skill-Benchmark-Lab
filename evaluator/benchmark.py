"""Offline benchmark validator and aggregator. Never invent missing measurements."""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

VARIANTS = frozenset({"control", "p2p-original", "p2p-improved", "development", "combined"})
WEIGHTS = {"quality": 40, "correctness": 30, "constraints": 20}


def load_records(path):
    records = []
    for index, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON at line {index}: {error.msg}") from error
        if not isinstance(row, dict):
            raise ValueError(f"Expected object at line {index}")
        records.append(row)
    return records


def validate_scenarios(cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError("Scenarios must be a nonempty list")
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Scenario must be an object")
        scenario_id = case.get("id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("Scenario id required")
        if scenario_id in ids:
            raise ValueError(f"Duplicate scenario: {scenario_id}")
        ids.add(scenario_id)
        if not isinstance(case.get("category"), str) or not case["category"].strip():
            raise ValueError(f"Scenario {scenario_id}: category required")
        if not isinstance(case.get("task"), str) or not case["task"].strip():
            raise ValueError(f"Scenario {scenario_id}: task required")
        checks = case.get("acceptance_criteria")
        if not isinstance(checks, list) or not checks or not all(isinstance(x, str) and x.strip() for x in checks):
            raise ValueError(f"Scenario {scenario_id}: acceptance_criteria required")
    return ids


def is_number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and value == value and abs(value) != float("inf")


def evaluate(records, cases):
    allowed = validate_scenarios(cases)
    groups = defaultdict(list)
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Result must be an object")
        scenario, variant, run_id = row.get("scenario_id"), row.get("variant"), row.get("run_id")
        if scenario not in allowed:
            raise ValueError(f"Unknown scenario: {scenario}")
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant: {variant}")
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a nonempty string")
        key = (scenario, variant, run_id)
        if key in seen:
            raise ValueError(f"Duplicate run: {key}")
        seen.add(key)
        for field in ("duration_seconds", "total_tokens"):
            value = row.get(field)
            if value is not None and (not is_number(value) or value < 0 or (field == "total_tokens" and int(value) != value)):
                raise ValueError(f"Invalid {field} in {key}")
        review = row.get("review")
        if review is not None:
            if not isinstance(review, dict) or set(review) != set(WEIGHTS):
                raise ValueError(f"Invalid review fields in {key}")
            if any(not is_number(v) or not 0 <= v <= 5 for v in review.values()):
                raise ValueError(f"Invalid review score in {key}")
        groups[(scenario, variant)].append(row)

    output = []
    for (scenario, variant), runs in sorted(groups.items()):
        def median(field):
            values = [x[field] for x in runs if x.get(field) is not None]
            return statistics.median(values) if len(values) == len(runs) else None
        if all(x.get("review") is not None for x in runs):
            per_run = [sum(x["review"][name] * weight / 5 for name, weight in WEIGHTS.items()) for x in runs]
            quality = round(statistics.mean(per_run), 2)
        else:
            quality = None
        output.append({
            "scenario_id": scenario,
            "variant": variant,
            "repeats": len(runs),
            "median_seconds": median("duration_seconds"),
            "median_tokens": median("total_tokens"),
            "quality_score_90": quality,
            "score_basis": "human_review_only" if quality is not None else "unrated",
        })
    return {
        "schema_version": 1, "results": output,
        "note": "Offline only; missing values remain null. Quality score is human-rated 0-90, not an automatic metric."
    }


def main():
    parser = argparse.ArgumentParser(description="Validate and aggregate recorded benchmark results (offline)")
    parser.add_argument("--scenarios", default="benchmarks/scenarios.json")
    parser.add_argument("--results", help="Optional JSON Lines file")
    args = parser.parse_args()
    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    runs = load_records(args.results) if args.results else []
    print(json.dumps(evaluate(runs, scenarios), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
