import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from package import build_manifest


ROOT = Path(__file__).resolve().parent


class ManifestTests(unittest.TestCase):
    def test_normalizes_sorts_and_sums_without_mutating_input(self):
        records = [
            {"name": " z.js ", "bytes": 7, "extra": "discard"},
            {"name": "Beta", "bytes": 0},
            {"name": "app.css", "bytes": 11},
        ]
        original = copy.deepcopy(records)
        self.assertEqual(build_manifest(records), {
            "version": 2,
            "items": [
                {"name": "app.css", "bytes": 11},
                {"name": "Beta", "bytes": 0},
                {"name": "z.js", "bytes": 7},
            ],
            "total_bytes": 18,
        })
        self.assertEqual(records, original)

    def test_empty(self):
        self.assertEqual(build_manifest([]), {
            "version": 2, "items": [], "total_bytes": 0,
        })

    def test_names_are_compared_using_unicode_casefold(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_manifest([
                {"name": "Straße", "bytes": 1},
                {"name": " STRASSE ", "bytes": 2},
            ])

    def test_invalid_records_are_rejected(self):
        cases = [
            (None, "list"),
            ({}, "list"),
            ([None], "object"),
            ([{}], "name"),
            ([{"name": None, "bytes": 1}], "name"),
            ([{"name": 3, "bytes": 1}], "name"),
            ([{"name": "", "bytes": 1}], "empty"),
            ([{"name": " \t\n", "bytes": 1}], "empty"),
            ([{"name": "x"}], "bytes"),
            ([{"name": "x", "bytes": -1}], "non-negative"),
            ([{"name": "x", "bytes": 1.0}], "integer"),
            ([{"name": "x", "bytes": "1"}], "integer"),
            ([{"name": "x", "bytes": None}], "integer"),
            ([{"name": "x", "bytes": True}], "integer"),
            ([{"name": "x", "bytes": False}], "integer"),
            ([{"name": "file", "bytes": 1},
              {"name": " FILE ", "bytes": 2}], "duplicate"),
        ]
        for records, message in cases:
            with self.subTest(records=records):
                with self.assertRaisesRegex(ValueError, message):
                    build_manifest(records)


class CliTests(unittest.TestCase):
    def run_cli(self, input_path, output_path):
        return subprocess.run(
            [sys.executable, str(ROOT / "package.py"), str(input_path),
             "--output", str(output_path)],
            capture_output=True, text=True, cwd=ROOT,
        )

    def test_sample_cli(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "manifest.json"
            output.write_text("previous output", encoding="utf-8")
            result = self.run_cli(ROOT / "sample.json", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
                "version": 2,
                "items": [{"name": "app.css", "bytes": 11},
                          {"name": "z.js", "bytes": 7}],
                "total_bytes": 18,
            })

    def test_invalid_input_preserves_existing_output(self):
        inputs = [
            ("{", "JSON"),
            ('[{"name": "  ", "bytes": 1}]', "empty"),
            ('[{"name": "x", "bytes": true}]', "integer"),
            ('[{"name": "x", "bytes": -1}]', "non-negative"),
            ('[{"name": "x", "bytes": 1.5}]', "integer"),
            ('[{"name": "x", "bytes": 1}, {"name": " X ", "bytes": 2}]', "duplicate"),
            ('{}', "list"),
        ]
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            for content, message in inputs:
                with self.subTest(content=content):
                    input_path.write_text(content, encoding="utf-8")
                    output_path.write_bytes(b"existing output\x00\xff")
                    result = self.run_cli(input_path, output_path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(output_path.read_bytes(), b"existing output\x00\xff")

    def test_missing_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "output.json"
            output.write_bytes(b"previous output")
            result = self.run_cli(Path(directory) / "missing.json", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output.read_bytes(), b"previous output")

    def test_invalid_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            input_path = Path(directory) / "input.json"
            output = Path(directory) / "output.json"
            input_path.write_text('[{"name":"x","bytes":false}]', encoding="utf-8")
            result = self.run_cli(input_path, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
