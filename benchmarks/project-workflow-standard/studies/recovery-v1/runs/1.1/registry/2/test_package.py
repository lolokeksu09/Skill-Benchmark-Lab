import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from package import build_manifest


PROJECT_DIR = Path(__file__).resolve().parent


class ManifestTests(unittest.TestCase):
    def test_normalizes_sorts_sums_and_removes_extra_fields(self):
        records = [
            {"name": " z.js ", "bytes": 7, "ignored": "value"},
            {"name": "app.css", "bytes": 11},
            {"name": " B.txt ", "bytes": 0},
        ]
        original = copy.deepcopy(records)
        self.assertEqual(
            build_manifest(records),
            {
                "version": 2,
                "items": [
                    {"name": "app.css", "bytes": 11},
                    {"name": "B.txt", "bytes": 0},
                    {"name": "z.js", "bytes": 7},
                ],
                "total_bytes": 18,
            },
        )
        self.assertEqual(records, original)

    def test_empty(self):
        self.assertEqual(
            build_manifest([]), {"version": 2, "items": [], "total_bytes": 0}
        )

    def test_invalid_records(self):
        invalid = [
            None,
            {},
            "text",
            [None],
            [[]],
            [{}],
            [{"name": "a"}],
            [{"bytes": 1}],
            [{"name": "", "bytes": 1}],
            [{"name": " \t\n ", "bytes": 1}],
            [{"name": 42, "bytes": 1}],
            [{"name": "a", "bytes": -1}],
            [{"name": "a", "bytes": 1.0}],
            [{"name": "a", "bytes": "1"}],
            [{"name": "a", "bytes": None}],
            [{"name": "a", "bytes": True}],
            [{"name": "a", "bytes": False}],
        ]
        for records in invalid:
            with self.subTest(records=records):
                with self.assertRaisesRegex(ValueError, r"records|record|name|bytes"):
                    build_manifest(records)

    def test_duplicates_are_case_insensitive_after_trimming(self):
        for names in [(" A ", "a"), ("Straße", "STRASSE")]:
            with self.subTest(names=names):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    build_manifest([{"name": n, "bytes": 1} for n in names])


class CliTests(unittest.TestCase):
    def run_cli(self, input_path, output_path):
        return subprocess.run(
            [sys.executable, str(PROJECT_DIR / "package.py"), str(input_path),
             "--output", str(output_path)],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )

    def test_successful_cli(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            input_path.write_text(
                '[{"name":" z.js ","bytes":7},{"name":"app.css","bytes":11}]',
                encoding="utf-8",
            )
            output_path.write_text("old output", encoding="utf-8")
            result = self.run_cli(input_path, output_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")),
                {"version": 2, "items": [{"name": "app.css", "bytes": 11},
                                          {"name": "z.js", "bytes": 7}],
                 "total_bytes": 18},
            )

    def test_invalid_input_preserves_existing_output(self):
        invalid_inputs = [
            "not json", "{}", "[null]",
            '[{"name":" ","bytes":1}]',
            '[{"name":"a","bytes":true}]',
            '[{"name":"a","bytes":1},{"name":" A ","bytes":2}]',
        ]
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            sentinel = b"existing output\x00\xff\n"
            for content in invalid_inputs:
                with self.subTest(content=content):
                    input_path.write_text(content, encoding="utf-8")
                    output_path.write_bytes(sentinel)
                    result = self.run_cli(input_path, output_path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("error:", result.stderr.lower())
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(output_path.read_bytes(), sentinel)

    def test_invalid_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            input_path.write_text("[false]", encoding="utf-8")
            result = self.run_cli(input_path, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output_path.exists())

    def test_missing_input_preserves_output(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR) as directory:
            input_path = Path(directory) / "missing.json"
            output_path = Path(directory) / "output.json"
            output_path.write_bytes(b"unchanged")
            result = self.run_cli(input_path, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr.lower())
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output_path.read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
