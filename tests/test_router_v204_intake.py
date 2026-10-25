import json
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1] / "benchmarks"

class DevelopmentV204IntakeTests(unittest.TestCase):
    def test_23_cases_have_distinct_id_and_requirements(self):
        items=json.loads((BASE/"diagnostics/router-negation-v204-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(items),23)
        self.assertEqual(len({x["id"] for x in items}),23)
        for x in items:
            self.assertTrue(x["prompt"].strip())
            for field in ("required","forbidden","expected_stack","forbidden_stack"):
                self.assertIsInstance(x[field], list)

    def test_result_counts(self):
        x=json.loads((BASE/"diagnostics/router-negation-v204-results.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(r["2.0.3"]=="pass" for r in x),9)
        self.assertEqual(sum(r["2.0.4"]=="pass" for r in x),23)

    def test_artifact_version_and_provenance(self):
        x=json.loads((BASE/"snapshots/development-design-2.0.4-2026-10-25.json").read_text(encoding="utf-8"))
        self.assertEqual(x["archive"]["version"],"2.0.4")
        self.assertEqual(len(x["archive"]["sha256"]),64)
        self.assertEqual(x["diff_vs_203"]["skill_md_preserved_byte_identical"],116)

if __name__=="__main__":
    unittest.main()
