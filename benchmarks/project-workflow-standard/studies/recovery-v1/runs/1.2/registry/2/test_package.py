import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from package import build_manifest


ROOT = Path(__file__).resolve().parent


class BuildManifestTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(
            build_manifest([]), {"version": 2, "items": [], "total_bytes": 0}
        )

    def test_normalizes_sorts_sums_and_discards_extra_fields(self):
        records = [
            {"name": " z.js ", "bytes": 7, "extra": "ignored"},
            {"name": "Beta.js", "bytes": 0},
            {"name": " app.css\t", "bytes": 11},
        ]
        self.assertEqual(
            build_manifest(records),
            {
                "version": 2,
                "items": [
                    {"name": "app.css", "bytes": 11},
                    {"name": "Beta.js", "bytes": 0},
                    {"name": "z.js", "bytes": 7},
                ],
                "total_bytes": 18,
            },
        )
        self.assertEqual(records[0]["name"], " z.js ")

    def test_rejects_empty_and_non_string_names(self):
        for name in ("", " \t\n", None, 123, True):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "name"):
                build_manifest([{"name": name, "bytes": 1}])

    def test_rejects_duplicate_names_after_trimming_and_casefold(self):
        for names in ((" app.js ", "APP.JS"), ("Straße", "STRASSE")):
            with self.subTest(names=names), self.assertRaisesRegex(
                ValueError, "duplicate"
            ):
                build_manifest([{"name": name, "bytes": 1} for name in names])

    def test_rejects_invalid_sizes(self):
        for size in (-1, 1.0, 1.5, True, False, "7", None):
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, "bytes"):
                build_manifest([{"name": "app.js", "bytes": size}])

    def test_rejects_wrong_structure_and_missing_fields(self):
        for records in ({}, None, "text", [None], [{}], [{"name": "app.js"}], [{"bytes": 1}]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                build_manifest(records)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="package-test-", dir=ROOT)
        self.addCleanup(self.directory.cleanup)
        self.input_path = Path(self.directory.name) / "input.json"
        self.output_path = Path(self.directory.name) / "manifest.json"

    def run_cli(self):
        return subprocess.run(
            [sys.executable, str(ROOT / "package.py"), str(self.input_path),
             "--output", str(self.output_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_input(self):
        records = [{"name": " z.js ", "bytes": 7}, {"name": "app.css", "bytes": 11}]
        self.input_path.write_text(json.dumps(records), encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(self.output_path.read_text()),
            {"version": 2, "items": [
                {"name": "app.css", "bytes": 11}, {"name": "z.js", "bytes": 7}
            ], "total_bytes": 18},
        )

    def test_invalid_input_keeps_existing_output(self):
        original = b"existing output\x00\xff\n"
        invalid_inputs = [
            "{broken", "{}", "null", '[{"name":" ","bytes":1}]',
            '[{"name":"app","bytes":true}]',
            '[{"name":"app","bytes":-1}]',
            '[{"name":"app","bytes":1.0}]',
            '[{"name":"app","bytes":1},{"name":" APP ","bytes":2}]',
        ]
        for invalid in invalid_inputs:
            with self.subTest(input=invalid):
                self.input_path.write_text(invalid, encoding="utf-8")
                self.output_path.write_bytes(original)
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.output_path.read_bytes(), original)

    def test_invalid_input_does_not_create_output(self):
        self.input_path.write_text("{broken", encoding="utf-8")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output_path.exists())

    def test_missing_input_keeps_existing_output(self):
        self.output_path.write_bytes(b"existing output")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.output_path.read_bytes(), b"existing output")


if __name__ == "__main__":
    unittest.main()
