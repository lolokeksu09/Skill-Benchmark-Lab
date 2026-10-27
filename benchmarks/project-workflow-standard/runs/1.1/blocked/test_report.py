import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from report import summarize


class Basic(unittest.TestCase):
    def test_success(self):
        self.assertTrue(summarize([{"mandatory":True,"status":"success"}])["ready"])

    def test_counts_all_statuses(self):
        checks = [
            {"mandatory": True, "status": "success"},
            {"mandatory": False, "status": "success"},
            {"mandatory": True, "status": "failure"},
            {"mandatory": False, "status": "failure"},
            {"mandatory": False, "status": "skipped"},
        ]
        self.assertEqual(
            summarize(checks)["counts"],
            {"success": 2, "failure": 2, "skipped": 1},
        )

    def test_empty_report_is_not_ready(self):
        self.assertEqual(
            summarize([]),
            {"counts": {"success": 0, "failure": 0, "skipped": 0}, "ready": False},
        )

    def test_optional_only_is_not_ready(self):
        for status in ("success", "failure", "skipped"):
            with self.subTest(status=status):
                self.assertFalse(
                    summarize([{"mandatory": False, "status": status}])["ready"]
                )

    def test_every_mandatory_check_must_succeed(self):
        for status in ("failure", "skipped"):
            with self.subTest(status=status):
                checks = [
                    {"mandatory": True, "status": "success"},
                    {"mandatory": True, "status": status},
                ]
                self.assertFalse(summarize(checks)["ready"])

    def test_optional_failure_and_skipped_do_not_block_ready(self):
        checks = [
            {"mandatory": True, "status": "success"},
            {"mandatory": True, "status": "success"},
            {"mandatory": False, "status": "failure"},
            {"mandatory": False, "status": "skipped"},
        ]
        self.assertEqual(
            summarize(checks),
            {"counts": {"success": 2, "failure": 1, "skipped": 1}, "ready": True},
        )

    def test_cli_outputs_json_for_input_file(self):
        project_dir = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=project_dir) as temporary_dir:
            input_path = Path(temporary_dir) / "checks.json"
            input_path.write_text(
                json.dumps([
                    {"mandatory": True, "status": "success"},
                    {"mandatory": False, "status": "failure"},
                    {"mandatory": False, "status": "skipped"},
                ]),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(project_dir / "report.py"), str(input_path)],
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            json.loads(result.stdout),
            {"counts": {"success": 1, "failure": 1, "skipped": 1}, "ready": True},
        )


if __name__ == "__main__":
    unittest.main()
