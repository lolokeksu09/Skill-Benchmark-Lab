import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from restore import build_plan


ROOT = Path(__file__).resolve().parent


class BuildPlanTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(
            build_plan({}, {}), {"create": [], "update": [], "delete": []}
        )

    def test_default_preview_creates_updates_and_preserves_extra_files(self):
        current = {"keep.txt": "same", "old.txt": "old", "change.txt": "before"}
        backup = {"keep.txt": "same", "new.txt": "new", "change.txt": "after"}
        expected = {"create": ["new.txt"], "update": ["change.txt"], "delete": []}
        self.assertEqual(build_plan(current, backup), expected)
        self.assertEqual(build_plan(current, backup, prune=False), expected)

    def test_prune_and_all_lists_are_sorted(self):
        current = {
            "z-old": "old", "z-change": "before", "a-old": "old",
            "a-change": "before", "unchanged": "same",
        }
        backup = {
            "z-new": "new", "z-change": "after", "a-new": "new",
            "a-change": "after", "unchanged": "same",
        }
        self.assertEqual(
            build_plan(current, backup, prune=True),
            {
                "create": ["a-new", "z-new"],
                "update": ["a-change", "z-change"],
                "delete": ["a-old", "z-old"],
            },
        )

    def test_identical_files_are_unchanged_with_or_without_prune(self):
        files = {"empty": "", "кириллица.txt": "текст\n", "same": "same"}
        for prune in (False, True):
            with self.subTest(prune=prune):
                self.assertEqual(
                    build_plan(files, files, prune=prune),
                    {"create": [], "update": [], "delete": []},
                )

    def test_empty_backup_only_deletes_with_prune(self):
        current = {"z": "", "a": "text"}
        self.assertEqual(build_plan(current, {}), {"create": [], "update": [], "delete": []})
        self.assertEqual(
            build_plan(current, {}, prune=True),
            {"create": [], "update": [], "delete": ["a", "z"]},
        )

    def test_empty_current_only_creates(self):
        self.assertEqual(
            build_plan({}, {"z": "", "a": "text"}, prune=True),
            {"create": ["a", "z"], "update": [], "delete": []},
        )

    def test_content_is_compared_exactly(self):
        self.assertEqual(
            build_plan({"empty": "text", "newline": "text"}, {"empty": "", "newline": "text\n"}),
            {"create": [], "update": ["empty", "newline"], "delete": []},
        )

    def test_inputs_are_not_mutated(self):
        current = {"old": "old", "change": "before"}
        backup = {"new": "new", "change": "after"}
        before_current, before_backup = current.copy(), backup.copy()
        build_plan(current, backup, prune=True)
        self.assertEqual(current, before_current)
        self.assertEqual(backup, before_backup)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="restore-test-", dir=ROOT)
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)
        self.current_path = self.directory / "current.json"
        self.backup_path = self.directory / "backup.json"

    def run_raw(self, current_text, backup_text, *flags):
        self.current_path.write_text(current_text, encoding="utf-8")
        self.backup_path.write_text(backup_text, encoding="utf-8")
        return self.invoke(*flags)

    def run_cli(self, current, backup, *flags):
        return self.run_raw(json.dumps(current), json.dumps(backup), *flags)

    def invoke(self, *flags):
        return subprocess.run(
            [sys.executable, str(ROOT / "restore.py"), str(self.current_path), str(self.backup_path), *flags],
            cwd=self.directory, capture_output=True, text=True, encoding="utf-8",
        )

    def assert_rejected(self, result, filename, error_text):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(filename, result.stderr)
        self.assertIn(error_text, result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_outputs_json_preview_and_supports_prune(self):
        current = {"old": "old", "change": "before", "same": "same"}
        backup = {"новый.txt": "новый", "change": "after", "same": "same"}
        for flags, deleted in (((), []), (("--prune",), ["old"])):
            with self.subTest(flags=flags):
                result = self.run_cli(current, backup, *flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(
                    json.loads(result.stdout),
                    {"create": ["новый.txt"], "update": ["change"], "delete": deleted},
                )

    def test_invalid_json_is_rejected_in_either_input(self):
        for filename in ("current.json", "backup.json"):
            with self.subTest(filename=filename):
                values = {"current.json": "{}", "backup.json": "{}"}
                values[filename] = '{"broken":'
                result = self.run_raw(values["current.json"], values["backup.json"])
                self.assert_rejected(result, filename, "invalid json")

    def test_non_objects_are_rejected_in_either_input(self):
        for filename in ("current.json", "backup.json"):
            for value in ([], ["file"], None, "text", 42, True):
                with self.subTest(filename=filename, value=value):
                    values = {"current.json": {}, "backup.json": {}}
                    values[filename] = value
                    result = self.run_cli(values["current.json"], values["backup.json"])
                    self.assert_rejected(result, filename, "json object")

    def test_non_string_contents_are_rejected_in_either_input(self):
        for filename in ("current.json", "backup.json"):
            for value in (None, False, 0, 1.5, [], {}):
                with self.subTest(filename=filename, value=value):
                    values = {"current.json": {}, "backup.json": {}}
                    values[filename] = {"bad.txt": value}
                    result = self.run_cli(values["current.json"], values["backup.json"])
                    self.assert_rejected(result, filename, "string")
                    self.assertIn("bad.txt", result.stderr)

    def test_missing_input_is_reported_without_traceback(self):
        self.backup_path.write_text("{}", encoding="utf-8")
        self.assert_rejected(self.invoke(), "current.json", "cannot read")

    def test_invalid_utf8_is_reported_without_traceback(self):
        self.backup_path.write_text("{}", encoding="utf-8")
        self.current_path.write_bytes(b"\xff")
        self.assert_rejected(self.invoke(), "current.json", "utf-8")

    def test_preview_does_not_change_input_files(self):
        current, backup = {"old": "old"}, {"new": "new"}
        result = self.run_cli(current, backup, "--prune")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.current_path.read_text(encoding="utf-8"), json.dumps(current))
        self.assertEqual(self.backup_path.read_text(encoding="utf-8"), json.dumps(backup))
        self.assertEqual(
            sorted(path.name for path in self.directory.iterdir()),
            ["backup.json", "current.json"],
        )


if __name__ == "__main__":
    unittest.main()
