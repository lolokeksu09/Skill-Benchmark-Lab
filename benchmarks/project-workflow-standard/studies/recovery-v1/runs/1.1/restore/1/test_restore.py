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

    def test_classifies_and_sorts_new_changed_and_unchanged_paths(self):
        current = {
            "old.txt": "old",
            "z-change.txt": "before",
            "a-change.txt": "before",
            "keep.txt": "same",
        }
        backup = {
            "z-new.txt": "new",
            "a-new.txt": "new",
            "z-change.txt": "after",
            "keep.txt": "same",
            "a-change.txt": "after",
        }
        self.assertEqual(
            build_plan(current, backup),
            {
                "create": ["a-new.txt", "z-new.txt"],
                "update": ["a-change.txt", "z-change.txt"],
                "delete": [],
            },
        )

    def test_prune_lists_only_missing_paths_in_sorted_order(self):
        self.assertEqual(
            build_plan(
                {"z-old": "old", "a-old": "old", "change": "before", "keep": "same"},
                {"new": "new", "change": "after", "keep": "same"},
                prune=True,
            ),
            {"create": ["new"], "update": ["change"], "delete": ["a-old", "z-old"]},
        )

    def test_identical_snapshots_have_no_changes_even_with_prune(self):
        for prune in (False, True):
            with self.subTest(prune=prune):
                self.assertEqual(
                    build_plan({"same": "content"}, {"same": "content"}, prune),
                    {"create": [], "update": [], "delete": []},
                )

    def test_empty_backup_preserves_current_unless_pruning(self):
        current = {"b": "", "a": "value"}
        self.assertEqual(
            build_plan(current, {}), {"create": [], "update": [], "delete": []}
        )
        self.assertEqual(
            build_plan(current, {}, prune=True),
            {"create": [], "update": [], "delete": ["a", "b"]},
        )

    def test_empty_current_creates_every_backup_path(self):
        self.assertEqual(
            build_plan({}, {"b": "", "a": "value"}),
            {"create": ["a", "b"], "update": [], "delete": []},
        )

    def test_inputs_are_unchanged(self):
        current = {"keep": "same", "change": "before", "old": "old"}
        backup = {"keep": "same", "change": "after", "new": "new"}
        original_current = current.copy()
        original_backup = backup.copy()
        build_plan(current, backup, prune=True)
        self.assertEqual(current, original_current)
        self.assertEqual(backup, original_backup)


class CLITests(unittest.TestCase):
    def run_cli(self, current, backup, *arguments):
        # All isolated fixtures stay inside the project directory.
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory = Path(directory)
            current_path = directory / "current.json"
            backup_path = directory / "backup.json"
            current_path.write_bytes(current)
            backup_path.write_bytes(backup)
            result = subprocess.run(
                [sys.executable, str(ROOT / "restore.py"), str(current_path),
                 str(backup_path), *arguments],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(current_path.read_bytes(), current)
            self.assertEqual(backup_path.read_bytes(), backup)
            return result

    def assert_input_error(self, result, filename, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(filename, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_preview_outputs_json_without_prune(self):
        result = self.run_cli(
            b'{"keep":"same","change":"before","old":"old"}',
            b'{"keep":"same","change":"after","new":"new"}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            json.loads(result.stdout),
            {"create": ["new"], "update": ["change"], "delete": []},
        )

    def test_prune_outputs_deletion_preview(self):
        result = self.run_cli(b'{"old":"old"}', b'{}', "--prune")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout), {"create": [], "update": [], "delete": ["old"]}
        )

    def test_unicode_paths_and_content(self):
        result = self.run_cli(
            '{"файл.txt":"до"}'.encode("utf-8"),
            '{"файл.txt":"после","новый.txt":""}'.encode("utf-8"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"create": ["новый.txt"], "update": ["файл.txt"], "delete": []},
        )

    def test_malformed_json_in_either_input(self):
        for index, name in enumerate(("current.json", "backup.json")):
            with self.subTest(input=name):
                inputs = [b'{}', b'{}']
                inputs[index] = b'{broken'
                self.assert_input_error(self.run_cli(*inputs), name, "invalid JSON")

    def test_non_object_in_either_input(self):
        for index, name in enumerate(("current.json", "backup.json")):
            for value in ([], None, True, 42, "text"):
                with self.subTest(input=name, value=value):
                    inputs = [b'{}', b'{}']
                    inputs[index] = json.dumps(value).encode("utf-8")
                    self.assert_input_error(self.run_cli(*inputs), name, "JSON object")

    def test_non_string_content_in_either_input(self):
        for index, name in enumerate(("current.json", "backup.json")):
            for value in (None, True, 42, [], {}):
                with self.subTest(input=name, value=value):
                    inputs = [b'{}', b'{}']
                    inputs[index] = json.dumps({"bad.txt": value}).encode("utf-8")
                    result = self.run_cli(*inputs)
                    self.assert_input_error(result, name, "string")
                    self.assertIn("bad.txt", result.stderr)

    def test_invalid_utf8_has_clear_error(self):
        self.assert_input_error(self.run_cli(b'\xff', b'{}'), "current.json", "UTF-8")

    def test_missing_file_has_clear_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            missing = Path(directory) / "missing.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "restore.py"), str(missing), str(missing)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assert_input_error(result, "missing.json", "cannot read")


if __name__ == "__main__":
    unittest.main()
