import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmarks/diagnostics/p2p-dds-integration-v213-cases.json"


class P2PDDSIntegrationCases(unittest.TestCase):
    def test_case_contract(self):
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 4)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            self.assertIn("[P2P_INTAKE]", case["prompt"])
            self.assertIn("[/P2P_INTAKE]", case["prompt"])
            self.assertTrue(case["required"])
            self.assertIsInstance(case["forbidden"], list)
            self.assertIsInstance(case["expected_stack"], list)
            self.assertIsInstance(case["forbidden_stack"], list)


if __name__ == "__main__":
    unittest.main()
