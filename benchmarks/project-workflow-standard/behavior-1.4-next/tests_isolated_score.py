import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
import isolated_score

class CaptureRestoreTests(unittest.TestCase):
    def test_restore_exact_binary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=b'fake fixture\x00\xff';entry={'type':'file','data_b64':base64.b64encode(content).decode(),'sha256':hashlib.sha256(content).hexdigest()}
            root=Path(tmp)/'case';isolated_score.restore_case(root,{'sub/file.bin':entry})
            self.assertEqual((root/'sub/file.bin').read_bytes(),content)
    def test_unsafe_paths_and_bad_hash_fail_closed(self):
        for name,checksum in [('../escape','x'),('/absolute','x'),('normal','wrong')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                entry={'type':'file','data_b64':base64.b64encode(b'x').decode(),'sha256':checksum}
                with self.assertRaises(ValueError):isolated_score.restore_case(Path(tmp)/'case',{name:entry})
    def test_agent_symlink_cannot_redirect_restore_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=b'x';entry={'type':'file','data_b64':base64.b64encode(content).decode(),'sha256':hashlib.sha256(content).hexdigest()}
            with self.assertRaises(OSError):isolated_score.restore_case(Path(tmp)/'case',{'build':{'type':'symlink','target':'/tmp'},'build/file':entry})

if __name__=='__main__':unittest.main()
