import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from contacts import read_contacts


class ContactsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "contacts.csv"

    def write_csv(self, contents):
        self.path.write_text(contents, encoding="utf-8")
        return self.path

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("contacts.py")),
             str(self.path), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_basic(self):
        self.write_csv("name,email\nAnna,anna@example.invalid\n")
        self.assertEqual(read_contacts(self.path), [
            {"name": "Anna", "email": "anna@example.invalid"},
        ])

    def test_bom_whitespace_blank_rows_and_order(self):
        self.write_csv(
            "\ufeff\n  \n name , email \n"
            " Анна , Anna@example.invalid \n"
            "\n , \n \t \n"
            " Boris , boris@example.invalid \n"
        )
        self.assertEqual(read_contacts(self.path), [
            {"name": "Анна", "email": "Anna@example.invalid"},
            {"name": "Boris", "email": "boris@example.invalid"},
        ])

    def test_empty_inputs(self):
        for contents in ("", "\ufeff\n  \n,\n", "name,email\n\n,\n"):
            with self.subTest(contents=contents):
                self.assertEqual(read_contacts(self.write_csv(contents)), [])

    def test_empty_email_is_rejected(self):
        for row in ("Anna,", "Anna,   ", "Anna"):
            with self.subTest(row=row):
                self.write_csv(f"name,email\n{row}\n")
                with self.assertRaisesRegex(ValueError, r"[Ee]mail.*line 2"):
                    read_contacts(self.path)

    def test_duplicate_email_is_rejected_ignoring_case_and_whitespace(self):
        self.write_csv(
            "name,email\nAnna,anna@example.invalid\n"
            "Other, ANNA@EXAMPLE.INVALID \n"
        )
        with self.assertRaisesRegex(ValueError, r"[Dd]uplicate email.*line 3"):
            read_contacts(self.path)

    def test_csv_quoted_values(self):
        self.write_csv('name,email\n" Anna, Jr. ",anna@example.invalid\n')
        self.assertEqual(read_contacts(self.path)[0]["name"], "Anna, Jr.")

    def test_cli_limits(self):
        self.write_csv(
            "name,email\nAnna,anna@example.invalid\n"
            "Boris,boris@example.invalid\n"
        )
        expected = read_contacts(self.path)
        for arguments, contacts in (
            ((), expected),
            (("--limit", "0"), []),
            (("--limit", "1"), expected[:1]),
            (("--limit", "20"), expected),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), contacts)

    def test_cli_rejects_invalid_limits(self):
        self.write_csv("name,email\nAnna,anna@example.invalid\n")
        for limit in ("-1", "1.5", "abc"):
            with self.subTest(limit=limit):
                result = self.run_cli("--limit", limit)
                self.assertEqual(result.returncode, 2)
                self.assertIn("--limit", result.stderr)
                self.assertIn("non-negative integer", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_cli_reports_invalid_email_even_with_zero_limit(self):
        for contents, message in (
            ("name,email\nAnna,\n", "Missing email"),
            ("name,email\nAnna,a@example.invalid\nOther,A@example.invalid\n",
             "Duplicate email"),
        ):
            with self.subTest(message=message):
                self.write_csv(contents)
                result = self.run_cli("--limit", "0")
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
