"""Offline evaluator with deliberately failing unauthorized-extra-file test."""
import hashlib
import unittest
from unsafe_release_check import verify_release

class DigestNegativeControls(unittest.TestCase):
    def setUp(self):
        self.files={'skills/a/SKILL.md':b'valid'}
        self.ledger={'skills/a/SKILL.md':hashlib.sha256(b'valid').hexdigest()}
    def test_matching_files_pass(self):
        self.assertTrue(verify_release(self.files,self.ledger))
    def test_changed_listed_file_fails(self):
        self.files['skills/a/SKILL.md']=b'corrupted'
        self.assertFalse(verify_release(self.files,self.ledger))
    def test_unlisted_extra_file_fails(self):
        self.files['scripts/install.sh']=b'echo unexpected'
        self.assertFalse(verify_release(self.files,self.ledger))

if __name__=='__main__':unittest.main()
