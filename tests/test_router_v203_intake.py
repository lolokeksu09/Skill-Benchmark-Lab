import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DIAG = BASE / "benchmarks" / "diagnostics"


class DevelopmentV203IntakeTests(unittest.TestCase):
    def test_new_negation_cases_are_unique_and_labeled(self):
        cases = json.loads((DIAG / "router-negation-extended-v203.json").read_text(encoding="utf8"))
        self.assertEqual(len(cases), 11)
        self.assertEqual(len({x["id"] for x in cases}), 11)
        for row in cases:
            self.assertTrue(row["prompt"])
            self.assertEqual(len(row["required"]), 1)
            self.assertEqual(len(row["forbidden"]), 1)

    def test_recorded_comparison_counts(self):
        records = json.loads((DIAG / "router-negation-extended-results-v203.json").read_text(encoding="utf8"))
        self.assertEqual(len(records), 11)
        self.assertEqual(sum(x["2.0.2"] == "pass" for x in records), 2)
        self.assertEqual(sum(x["2.0.3"] == "pass" for x in records), 4)

    def test_intake_checksum_and_skill_count(self):
        snapshot = json.loads((BASE / "benchmarks/snapshots/development-design-2.0.3-2026-10-25.json").read_text(encoding="utf8"))
        self.assertEqual(snapshot["candidate"]["skills"], 116)
        self.assertEqual(len(snapshot["candidate"]["sha256"]), 64)
        self.assertEqual(snapshot["local_verification"]["previous_independent_18"]["v203_passed"], 18)


if __name__ == "__main__":
    unittest.main()
