"""Reproducible provenance assertions; this repository does not ship the ZIP binaries."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks" / "versions.json"
SNAPSHOT = ROOT / "benchmarks" / "snapshots" / "development-design-2.0.5-full-patched-2026-10-25.json"
SHA = re.compile(r"^[0-9a-f]{64}$")


class FrozenProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        cls.entries = {row["id"]: row for row in cls.manifest["entries"]}

    def test_all_five_variants_have_unique_ids(self):
        ids = [row["id"] for row in self.manifest["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {"control", "p2p-original", "p2p-improved", "development", "combined"})

    def test_binary_inputs_are_sha256_pinned(self):
        for name in ("p2p-original", "p2p-improved", "development"):
            with self.subTest(name=name):
                entry = self.entries[name]
                self.assertEqual(entry["status"], "pinned_not_imported")
                self.assertRegex(entry["sha256"], SHA)

    def test_final_development_archive_matches_snapshot(self):
        dev = self.entries["development"]
        artifact = self.snapshot["artifact"]
        self.assertEqual(dev["sha256"], artifact["sha256"])
        self.assertEqual(dev["source"], "conversation_artifact:" + artifact["archive_filename"])
        self.assertEqual(dev["plugin_version"], artifact["plugin_version"])
        self.assertEqual(dev["skill_count"], artifact["skill_files"])
        self.assertEqual(artifact["zip_entries"], 1215)
        verified = self.snapshot["locally_reproduced"]
        self.assertTrue(verified["zip_crc_valid"])
        self.assertEqual(verified["router_tests_passed"], verified["router_tests_total"])
        self.assertEqual(verified["router_tests_total"], 153)

    def test_combined_is_a_composition_not_an_archive(self):
        combined = self.entries["combined"]
        self.assertEqual(combined["components"], ["p2p-improved", "development"])
        self.assertEqual(combined["status"], "pinned_components_not_executed")
        self.assertIsNone(combined["sha256"])
        for name in combined["components"]:
            self.assertRegex(self.entries[name]["sha256"], SHA)

    def test_original_p2p_source_has_no_unverified_release_archive_url(self):
        self.assertEqual(self.entries["p2p-original"]["source"], "https://github.com/sanic732/P2P")


if __name__ == "__main__":
    unittest.main()
