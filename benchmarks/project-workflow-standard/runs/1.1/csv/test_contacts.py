import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from contacts import read_contacts


PROJECT_DIR = Path(__file__).resolve().parent


class ContactsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=PROJECT_DIR)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "contacts.csv"

    def write_csv(self, contents):
        self.path.write_text(contents, encoding="utf-8")

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(PROJECT_DIR / "contacts.py"), str(self.path), *arguments],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )

    def test_basic(self):
        self.write_csv("name,email\nAnna,anna@example.invalid\n")
        self.assertEqual(
            read_contacts(self.path),
            [{"name": "Anna", "email": "anna@example.invalid"}],
        )

    def test_bom_spaces_blank_rows_and_order(self):
        self.write_csv(
            "\ufeff\n  ,  \n name , email \r\n"
            " Борис , Boris@example.invalid \r\n"
            "\r\n  , \t \r\n"
            " Анна , anna@example.invalid \r\n"
        )
        self.assertEqual(
            read_contacts(self.path),
            [
                {"name": "Борис", "email": "Boris@example.invalid"},
                {"name": "Анна", "email": "anna@example.invalid"},
            ],
        )

    def test_empty_input(self):
        for contents in ("", "\ufeff\n  \n , \n", "name,email\n\n , \n"):
            with self.subTest(contents=contents):
                self.write_csv(contents)
                self.assertEqual(read_contacts(self.path), [])

    def test_quoted_values(self):
        self.write_csv('name,email\n" Anna, Maria ", anna@example.invalid \n')
        self.assertEqual(read_contacts(self.path)[0]["name"], "Anna, Maria")

    def test_empty_email_rejected(self):
        for record in ("Anna,", "Anna, \t ", "Anna"):
            with self.subTest(record=record):
                self.write_csv(f"name,email\n{record}\n")
                with self.assertRaisesRegex(ValueError, r"[Ee]mail.*пуст"):
                    read_contacts(self.path)

    def test_missing_email_column_rejected(self):
        self.write_csv("name\nAnna\n")
        with self.assertRaisesRegex(ValueError, r"[Ee]mail.*пуст"):
            read_contacts(self.path)

    def test_duplicate_email_rejected(self):
        for repeated in ("anna@example.invalid", " ANNA@EXAMPLE.INVALID "):
            with self.subTest(repeated=repeated):
                self.write_csv(
                    f"name,email\nAnna,anna@example.invalid\nOther,{repeated}\n"
                )
                with self.assertRaisesRegex(ValueError, r"[Пп]овтор.*anna@example.invalid"):
                    read_contacts(self.path)

    def test_cli_limits(self):
        self.write_csv(
            "name,email\nАнна,anna@example.invalid\nБорис,boris@example.invalid\n"
        )
        for arguments, names in (
            ((), ["Анна", "Борис"]),
            (("--limit", "0"), []),
            (("--limit", "1"), ["Анна"]),
            (("--limit", "2"), ["Анна", "Борис"]),
            (("--limit", "10"), ["Анна", "Борис"]),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([row["name"] for row in json.loads(result.stdout)], names)
                self.assertEqual(result.stderr, "")

    def test_cli_rejects_invalid_limit(self):
        self.write_csv("name,email\nAnna,anna@example.invalid\n")
        for limit in ("-1", "1.5", "abc"):
            with self.subTest(limit=limit):
                result = self.run_cli("--limit", limit)
                self.assertEqual(result.returncode, 2)
                self.assertIn("--limit", result.stderr)
                self.assertIn("целым неотрицательным", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_cli_reports_invalid_email(self):
        self.write_csv("name,email\nAnna,\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Email", result.stderr)
        self.assertIn("пуст", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
