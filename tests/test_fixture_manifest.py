import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class FixtureManifestTests(unittest.TestCase):
    def test_all_scenario_variants_are_declared(self):
        from evaluator.benchmark import VARIANTS
        data = json.loads((ROOT / "benchmarks/versions.json").read_text(encoding="utf8"))
        self.assertEqual({x["id"] for x in data["entries"]}, VARIANTS)

    def test_pinned_files_have_sha256(self):
        import re
        data = json.loads((ROOT / "benchmarks/versions.json").read_text(encoding="utf8"))
        for entry in data["entries"]:
            if entry["status"] == "pinned_not_imported":
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_fixture_files_present(self):
        expected = [
            "benchmarks/fixtures/web/tests/feed.test.mjs",
            "benchmarks/fixtures/web/baseline/feed.mjs",
            "benchmarks/fixtures/web/reference/feed.mjs",
            "benchmarks/fixtures/web/baseline/feed.css",
            "benchmarks/fixtures/web/reference/feed.css",
            "benchmarks/fixtures/android/shared/FixtureCheck.kt",
            "benchmarks/fixtures/android/baseline/FeedState.kt",
            "benchmarks/fixtures/android/reference/FeedState.kt",
            "benchmarks/fixtures/android/build.gradle.kts",
            ".github/workflows/fixture-checks.yml",
        ]
        for path in expected:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

if __name__ == "__main__":
    unittest.main()
