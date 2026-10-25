import tempfile
import unittest
from pathlib import Path
from evaluator.benchmark import evaluate, load_records, validate_scenarios

CASE = {"id": "android-ui", "category": "android", "task": "Improve UI",
        "acceptance_criteria": ["Preserve behavior"]}

class BenchmarkTests(unittest.TestCase):
    def test_reject_duplicate_scenarios(self):
        with self.assertRaisesRegex(ValueError, "Duplicate scenario"):
            validate_scenarios([CASE, CASE])

    def test_unknown_variant(self):
        with self.assertRaisesRegex(ValueError, "Unknown variant"):
            evaluate([{"scenario_id": "android-ui", "variant": "unknown",
                       "run_id": "r1", "duration_seconds": 2}], [CASE])

    def test_missing_data_remains_null(self):
        report = evaluate([{"scenario_id": "android-ui", "variant": "p2p-improved",
                            "run_id": "r1", "duration_seconds": 4.2}], [CASE])
        result = report["results"][0]
        self.assertIsNone(result["median_tokens"])
        self.assertIsNone(result["quality_score_90"])
        self.assertEqual(result["repeats"], 1)

    def test_review_and_median(self):
        records = [
            {"scenario_id": "android-ui", "variant": "p2p-improved", "run_id": "r1",
             "duration_seconds": 2.0, "total_tokens": 100,
             "review": {"quality": 5, "correctness": 4, "constraints": 5}},
            {"scenario_id": "android-ui", "variant": "p2p-improved", "run_id": "r2",
             "duration_seconds": 6.0, "total_tokens": 300,
             "review": {"quality": 3, "correctness": 4, "constraints": 3}},
        ]
        result = evaluate(records, [CASE])["results"][0]
        self.assertEqual(result["median_seconds"], 4)
        self.assertEqual(result["median_tokens"], 200)
        self.assertAlmostEqual(result["quality_score_90"], 72)

    def test_duplicate_runs(self):
        r = {"scenario_id": "android-ui", "variant": "control", "run_id": "r1", "duration_seconds": 1}
        with self.assertRaisesRegex(ValueError, "Duplicate run"):
            evaluate([r, r], [CASE])

    def test_invalid_review(self):
        r = {"scenario_id": "android-ui", "variant": "control", "run_id": "r1",
             "review": {"quality": 6, "correctness": 4, "constraints": 5}}
        with self.assertRaisesRegex(ValueError, "review"):
            evaluate([r], [CASE])

    def test_invalid_json_line(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "runs.jsonl"
            p.write_text("{bad json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                load_records(p)

if __name__ == "__main__":
    unittest.main()
