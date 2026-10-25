import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V205IntakeTests(unittest.TestCase):
    def test_cases_have_unique_ids(self):
        cases=json.loads((ROOT/"benchmarks/diagnostics/router-required-fixes-v205.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cases),12)
        self.assertEqual(len({x["id"] for x in cases}),12)
        for case in cases:
            self.assertTrue(case["prompt"].strip())
            self.assertIsInstance(case["required"],list)
    def test_recorded_artifact_and_suite(self):
        x=json.loads((ROOT/"benchmarks/snapshots/development-design-2.0.5-2026-10-25.json").read_text(encoding="utf-8"))
        self.assertEqual(x["artifact"]["version"],"2.0.5")
        self.assertEqual(len(x["artifact"]["sha256"]),64)
        self.assertEqual(x["artifact"]["skills_preserved"],116)
        self.assertEqual(x["results"]["v205_router_suite"]["passed"],112)
        self.assertEqual(x["results"]["v205_frozen_multidomain_40"]["passed"],38)
if __name__=="__main__":
    unittest.main()
