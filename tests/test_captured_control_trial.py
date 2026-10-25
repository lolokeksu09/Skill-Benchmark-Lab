"""Provenance checks for the *single* real local model candidate, not an LLM quality ranking."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "benchmarks/measurements/qwen3-control-trial-001.json"

class CapturedControlTrialTests(unittest.TestCase):
    def test_candidate_files_match_the_recorded_fingerprints(self):
        record = json.loads(REPORT.read_text(encoding="utf-8"))
        root = ROOT / record["candidate"]["path_prefix"]
        self.assertEqual(record["scenario_id"], "web-fixture-repair")
        self.assertEqual(record["variant"], "control")
        self.assertEqual(record["run_id"], "trial-001")
        for file_name, descriptor in record["candidate"]["files"].items():
            with self.subTest(file_name=file_name):
                self.assertEqual(
                    hashlib.sha256((root / file_name).read_bytes()).hexdigest(),
                    descriptor["sha256"]
                )
        self.assertEqual(record["inference"]["total_tokens"], 365)
        self.assertEqual(record["validation"]["runtime"]["passed"], 1)
        self.assertEqual(record["validation"]["runtime"]["failed"], 2)
        self.assertEqual(record["validation"]["runtime"]["tests_executed"], 3)

if __name__ == "__main__":
    unittest.main()
