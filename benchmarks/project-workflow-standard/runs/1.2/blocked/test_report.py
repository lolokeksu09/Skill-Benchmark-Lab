import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from report import summarize


class SummaryTests(unittest.TestCase):
    def test_counts_follow_statuses(self):
        checks = [
            {"mandatory": True, "status": "success"},
            {"mandatory": False, "status": "failure"},
            {"mandatory": False, "status": "skipped"},
            {"mandatory": False, "status": "success"},
        ]
        self.assertEqual(
            summarize(checks),
            {"counts": {"success": 2, "failure": 1, "skipped": 1}, "ready": True},
        )

    def test_empty_checks_are_not_ready(self):
        self.assertEqual(
            summarize([]),
            {"counts": {"success": 0, "failure": 0, "skipped": 0}, "ready": False},
        )

    def test_optional_only_checks_are_not_ready(self):
        for status in ("success", "failure", "skipped"):
            with self.subTest(status=status):
                self.assertFalse(summarize([{"mandatory": False, "status": status}])["ready"])

    def test_mandatory_status_controls_readiness(self):
        for mandatory_status in ("success", "failure", "skipped"):
            for optional_status in ("success", "failure", "skipped"):
                with self.subTest(mandatory=mandatory_status, optional=optional_status):
                    checks = [
                        {"mandatory": True, "status": mandatory_status},
                        {"mandatory": False, "status": optional_status},
                    ]
                    self.assertEqual(summarize(checks)["ready"], mandatory_status == "success")

    def test_every_mandatory_check_must_succeed(self):
        for status in ("success", "failure", "skipped"):
            with self.subTest(status=status):
                checks = [
                    {"mandatory": True, "status": "success"},
                    {"mandatory": True, "status": status},
                ]
                self.assertEqual(summarize(checks)["ready"], status == "success")


class CliTests(unittest.TestCase):
    def test_cli_prints_json_from_input_file(self):
        project = Path(__file__).resolve().parent
        checks = [
            {"mandatory": True, "status": "success"},
            {"mandatory": False, "status": "skipped"},
        ]
        with tempfile.TemporaryDirectory(dir=project) as directory:
            input_path = Path(directory) / "checks.json"
            input_path.write_text(json.dumps(checks), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(project / "report.py"), str(input_path)],
                capture_output=True,
                text=True,
                check=True,
                cwd=project,
            )
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            json.loads(result.stdout),
            {"counts": {"success": 1, "failure": 0, "skipped": 1}, "ready": True},
        )


if __name__ == "__main__":
    unittest.main()
