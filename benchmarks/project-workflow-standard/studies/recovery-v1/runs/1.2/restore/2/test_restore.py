import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from restore import build_plan


SCRIPT = Path(__file__).with_name("restore.py").resolve()


class BuildPlanTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(
            build_plan({}, {}), {"create": [], "update": [], "delete": []}
        )

    def test_only_new_and_changed_paths_are_included(self):
        current = {"same": "equal", "change": "before", "old": "removed"}
        backup = {"same": "equal", "change": "after", "new": "added"}
        self.assertEqual(
            build_plan(current, backup),
            {"create": ["new"], "update": ["change"], "delete": []},
        )

    def test_prune_is_explicit_and_results_are_sorted(self):
        current = {"z-old": "x", "b-change": "x", "a-old": "x", "a-change": "x"}
        backup = {"z-new": "y", "b-change": "y", "a-new": "y", "a-change": "y"}
        self.assertEqual(
            build_plan(current, backup, prune=True),
            {
                "create": ["a-new", "z-new"],
                "update": ["a-change", "b-change"],
                "delete": ["a-old", "z-old"],
            },
        )

    def test_empty_backup_does_not_delete_without_prune(self):
        current = {"b": "", "a": "data"}
        self.assertEqual(
            build_plan(current, {}), {"create": [], "update": [], "delete": []}
        )
        self.assertEqual(
            build_plan(current, {}, prune=True),
            {"create": [], "update": [], "delete": ["a", "b"]},
        )

    def test_empty_current_creates_all_backup_paths(self):
        self.assertEqual(
            build_plan({}, {"b": "", "a": "text"}),
            {"create": ["a", "b"], "update": [], "delete": []},
        )

    def test_identical_and_empty_contents_are_unchanged(self):
        self.assertEqual(
            build_plan({"empty": "", "same": "x"}, {"same": "x", "empty": ""}, True),
            {"create": [], "update": [], "delete": []},
        )

    def test_inputs_are_not_mutated(self):
        current = {"old": "x", "change": "before"}
        backup = {"new": "y", "change": "after"}
        originals = current.copy(), backup.copy()
        build_plan(current, backup, True)
        self.assertEqual((current, backup), originals)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=SCRIPT.parent)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.current = self.root / "current.json"
        self.backup = self.root / "backup.json"
        self.current.write_text(
            json.dumps({"same": "", "old": "old", "change": "before"}), encoding="utf-8"
        )
        self.backup.write_text(
            json.dumps({"same": "", "new": "new", "change": "after"}), encoding="utf-8"
        )

    def run_cli(self, *flags):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.current), str(self.backup), *flags],
            capture_output=True,
            text=True,
            cwd=self.root,
        )

    def test_json_output_in_both_modes_and_no_file_writes(self):
        originals = {path.name: path.read_bytes() for path in self.root.iterdir()}
        for flags, deletes in [((), []), (("--prune",), ["old"])]:
            with self.subTest(flags=flags):
                result = self.run_cli(*flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(
                    json.loads(result.stdout),
                    {"create": ["new"], "update": ["change"], "delete": deletes},
                )
                self.assertEqual(
                    {path.name: path.read_bytes() for path in self.root.iterdir()}, originals
                )

    def test_invalid_input_has_clear_error_and_no_stdout(self):
        invalid_inputs = [
            ("{", "invalid JSON"),
            ("[]", "JSON object"),
            ("null", "JSON object"),
            ('"text"', "JSON object"),
            ("42", "JSON object"),
            ('{"file": null}', "string"),
            ('{"file": false}', "string"),
            ('{"file": 42}', "string"),
            ('{"file": []}', "string"),
            ('{"file": {}}', "string"),
        ]
        for target in (self.current, self.backup):
            original = target.read_bytes()
            for contents, message in invalid_inputs:
                with self.subTest(input=target.name, contents=contents):
                    target.write_text(contents, encoding="utf-8")
                    result = self.run_cli()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
            target.write_bytes(original)

    def test_missing_file_has_clear_error(self):
        self.current.unlink()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("current.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_encoding_has_clear_error(self):
        self.backup.write_bytes(b"\xff")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_argument_has_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=self.root
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
