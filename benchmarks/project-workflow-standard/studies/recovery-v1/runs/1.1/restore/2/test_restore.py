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
        self.assertEqual(build_plan({}, {}), {
            "create": [], "update": [], "delete": [],
        })

    def test_new_changed_and_unchanged_files(self):
        current = {"keep.txt": "same", "old.txt": "old", "change.txt": "before"}
        backup = {"keep.txt": "same", "new.txt": "new", "change.txt": "after"}
        self.assertEqual(build_plan(current, backup), {
            "create": ["new.txt"], "update": ["change.txt"], "delete": [],
        })
        self.assertEqual(build_plan(current, backup, prune=True), {
            "create": ["new.txt"], "update": ["change.txt"], "delete": ["old.txt"],
        })

    def test_identical_files_are_unchanged_with_or_without_prune(self):
        snapshot = {"file.txt": "same", "empty.txt": ""}
        for prune in (False, True):
            with self.subTest(prune=prune):
                self.assertEqual(build_plan(snapshot, snapshot, prune), {
                    "create": [], "update": [], "delete": [],
                })

    def test_all_lists_are_sorted_and_inputs_are_preserved(self):
        current = {"z-old": "", "z-change": "old", "a-old": "", "a-change": "old"}
        backup = {"z-new": "", "z-change": "new", "a-new": "", "a-change": "new"}
        current_before, backup_before = current.copy(), backup.copy()
        self.assertEqual(build_plan(current, backup, prune=True), {
            "create": ["a-new", "z-new"],
            "update": ["a-change", "z-change"],
            "delete": ["a-old", "z-old"],
        })
        self.assertEqual(current, current_before)
        self.assertEqual(backup, backup_before)

    def test_empty_backup_requires_prune_for_deletion(self):
        self.assertEqual(build_plan({"file": "data"}, {}), {
            "create": [], "update": [], "delete": [],
        })
        self.assertEqual(build_plan({"file": "data"}, {}, True), {
            "create": [], "update": [], "delete": ["file"],
        })

    def test_empty_current_creates_every_backup_path(self):
        self.assertEqual(build_plan({}, {"z": "", "a": "text"}), {
            "create": ["a", "z"], "update": [], "delete": [],
        })

    def test_empty_contents_and_unicode_paths(self):
        self.assertEqual(build_plan({"файл": ""}, {"файл": "текст", "新": ""}), {
            "create": ["新"], "update": ["файл"], "delete": [],
        })


class CLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.directory.cleanup)
        self.current = Path(self.directory.name) / "current.json"
        self.backup = Path(self.directory.name) / "backup.json"

    def write_snapshots(self, current, backup):
        self.current.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        self.backup.write_text(json.dumps(backup, ensure_ascii=False), encoding="utf-8")

    def run_cli(self, *options):
        return subprocess.run(
            [sys.executable, str(ROOT / "restore.py"),
             str(self.current), str(self.backup), *options],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def assert_input_error(self, result, message, path):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertIn(str(path), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_json_preview_with_and_without_prune_preserves_inputs(self):
        self.write_snapshots(
            {"old": "x", "файл": "before", "keep": "same"},
            {"new": "", "файл": "after", "keep": "same"},
        )
        before = (self.current.read_bytes(), self.backup.read_bytes())
        for options, deleted in (((), []), (("--prune",), ["old"])):
            with self.subTest(options=options):
                result = self.run_cli(*options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), {
                    "create": ["new"], "update": ["файл"], "delete": deleted,
                })
                self.assertEqual(
                    (self.current.read_bytes(), self.backup.read_bytes()), before,
                )

    def test_invalid_json_in_either_input(self):
        for target in (self.current, self.backup):
            with self.subTest(target=target.name):
                self.write_snapshots({}, {})
                target.write_text('{"broken":', encoding="utf-8")
                self.assert_input_error(self.run_cli(), "invalid JSON", target)

    def test_non_object_in_either_input(self):
        for value in ([], "text", None, 42, True):
            for target in (self.current, self.backup):
                with self.subTest(value=value, target=target.name):
                    self.write_snapshots({}, {})
                    target.write_text(json.dumps(value), encoding="utf-8")
                    self.assert_input_error(self.run_cli(), "expected a JSON object", target)

    def test_non_string_contents_in_either_input(self):
        for value in (None, 42, True, [], {}):
            for target in (self.current, self.backup):
                with self.subTest(value=value, target=target.name):
                    self.write_snapshots({}, {})
                    target.write_text(json.dumps({"bad.txt": value}), encoding="utf-8")
                    self.assert_input_error(self.run_cli(), "content for 'bad.txt' must be a string", target)

    def test_missing_input(self):
        self.write_snapshots({}, {})
        self.current.unlink()
        self.assert_input_error(self.run_cli(), "No such file", self.current)

    def test_invalid_utf8_input(self):
        self.write_snapshots({}, {})
        self.backup.write_bytes(b"\xff")
        self.assert_input_error(self.run_cli(), "valid UTF-8", self.backup)


if __name__ == "__main__":
    unittest.main()
