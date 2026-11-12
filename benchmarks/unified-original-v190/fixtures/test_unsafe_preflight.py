"""Public negative control: unsafe preflight must fail exactly one test."""
import unittest
from unsafe_preflight import can_install

VALID={
    'plugin.json':b'{"version":"1.9.0"}',
    '.codex-plugin/plugin.json':b'{"version":"1.9.0"}',
    'scripts/skill_hashes.json':b'{"version":"1.9.0"}'
}

class MetadataGuards(unittest.TestCase):
    def test_valid_metadata_passes(self):
        self.assertTrue(can_install(VALID))
    def test_one_missing_marker_rejected(self):
        partial=dict(VALID)
        partial.pop('plugin.json')
        self.assertFalse(can_install(partial))
    def test_all_missing_markers_rejected(self):
        self.assertFalse(can_install({}))

if __name__=='__main__':unittest.main()
