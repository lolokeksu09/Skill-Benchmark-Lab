"""Schema and repeatability checks for the standalone router comparison corpus."""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "benchmarks" / "diagnostics"


class RouterCasesTests(unittest.TestCase):
    def test_cases_have_unique_ids_and_explicit_expectations(self):
        rows = json.loads((FIXTURE_DIR / "router-independent-cases-v202.json").read_text(encoding="utf8"))
        self.assertEqual(len(rows), 18)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        for row in rows:
            self.assertTrue(row["prompt"].strip())
            for field in ("required", "forbidden", "expected_stack", "forbidden_stack"):
                self.assertIsInstance(row[field], list)
                self.assertEqual(len(row[field]), len(set(row[field])))

    def test_result_ledger_matches_documented_counts(self):
        records = json.loads((FIXTURE_DIR / "router-independent-results-v202.json").read_text(encoding="utf8"))
        self.assertEqual(len(records), 18)
        self.assertEqual(sum(x["2.0.1"] == "pass" for x in records), 6)
        self.assertEqual(sum(x["2.0.2"] == "pass" for x in records), 17)
        self.assertEqual([x["id"] for x in records if x["2.0.2"] == "fail"], ["en_without_rn"])

    def test_comparison_runner_is_python_syntax_valid(self):
        source = (FIXTURE_DIR / "check_router_variants.py").read_text(encoding="utf8")
        ast.parse(source)

if __name__ == "__main__":
    unittest.main()
