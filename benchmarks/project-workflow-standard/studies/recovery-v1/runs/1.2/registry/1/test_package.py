import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from package import build_manifest


class ManifestTests(unittest.TestCase):
    def test_normalizes_sorts_sums_and_omits_extra_fields(self):
        records = [
            {"name": " z.js ", "bytes": 7, "private": "omit"},
            {"name": "B.js", "bytes": 0},
            {"name": "app.css", "bytes": 11},
        ]
        self.assertEqual(build_manifest(records), {
            "version": 2,
            "items": [
                {"name": "app.css", "bytes": 11},
                {"name": "B.js", "bytes": 0},
                {"name": "z.js", "bytes": 7},
            ],
            "total_bytes": 18,
        })
        self.assertEqual(records[0]["name"], " z.js ")

    def test_empty(self):
        self.assertEqual(build_manifest([]), {
            "version": 2, "items": [], "total_bytes": 0,
        })

    def test_invalid_name(self):
        for name in ["", " \t\n", None, 7, True]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "name"):
                build_manifest([{"name": name, "bytes": 0}])

    def test_case_insensitive_duplicates_after_trimming(self):
        for first, second in [("app.js", " APP.JS "), ("Straße", "STRASSE")]:
            with self.subTest(first=first), self.assertRaisesRegex(ValueError, "duplicate"):
                build_manifest([
                    {"name": first, "bytes": 1},
                    {"name": second, "bytes": 2},
                ])

    def test_invalid_bytes(self):
        for size in [-1, 1.0, 1.5, True, False, "7", None]:
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, "bytes"):
                build_manifest([{"name": "app.js", "bytes": size}])

    def test_invalid_structure(self):
        for records in [None, {}, "text", [None], [7], [{}], [{"name": "a"}]]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                build_manifest(records)


class CliTests(unittest.TestCase):
    script = Path(__file__).with_name("package.py").resolve()

    def run_cli(self, source, output):
        return subprocess.run(
            [sys.executable, str(self.script), str(source), "--output", str(output)],
            capture_output=True, text=True, check=False,
        )

    def test_writes_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            source, output = Path(directory) / "input.json", Path(directory) / "manifest.json"
            source.write_text('[{"name":" a ","bytes":3}]', encoding="utf-8")
            result = self.run_cli(source, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
                "version": 2, "items": [{"name": "a", "bytes": 3}], "total_bytes": 3,
            })

    def test_invalid_input_preserves_existing_output(self):
        inputs = [
            ("{broken", "JSON"),
            ('[{"name":" ","bytes":1}]', "name"),
            ('[{"name":"a","bytes":true}]', "bytes"),
            ('[{"name":"a","bytes":1},{"name":" A ","bytes":2}]', "duplicate"),
            ("{}", "list"),
        ]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            source, output = Path(directory) / "input.json", Path(directory) / "manifest.json"
            for content, message in inputs:
                with self.subTest(content=content):
                    source.write_text(content, encoding="utf-8")
                    output.write_bytes(b"existing output\n")
                    result = self.run_cli(source, output)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message.lower(), result.stderr.lower())
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(output.read_bytes(), b"existing output\n")

    def test_missing_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            output = Path(directory) / "manifest.json"
            output.write_bytes(b"existing output\n")
            result = self.run_cli(Path(directory) / "missing.json", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output.read_bytes(), b"existing output\n")

    def test_invalid_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            source, output = Path(directory) / "input.json", Path(directory) / "manifest.json"
            source.write_text('[{"name":"a","bytes":-1}]', encoding="utf-8")
            result = self.run_cli(source, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
