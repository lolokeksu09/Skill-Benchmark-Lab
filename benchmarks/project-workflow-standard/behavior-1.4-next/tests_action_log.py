import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import action_log

class ActionLogTests(unittest.TestCase):
    def test_changes_and_separate_exit_codes_are_recorded(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
            root=Path(tmp);case=root/'case';case.mkdir();(case/'a').write_text('a')
            initial=action_log.snapshot(case)
            event=action_log.run(root,[sys.executable,'-c','from pathlib import Path; Path("a").unlink(); print("done"); raise SystemExit(7)'])
            self.assertEqual(event['exit'],7);self.assertFalse((case/'a').exists())
            self.assertEqual(event['stdout'],'done\n');self.assertEqual(action_log.chain(initial,[event],action_log.snapshot(case)),[])
            self.assertEqual(json.loads((root/'ACTIONS.jsonl').read_text())['exit'],7)

    def test_gap_and_external_restoration_are_detected(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
            root=Path(tmp);case=root/'case';case.mkdir();(case/'a').write_text('a')
            initial=action_log.snapshot(case)
            event=action_log.run(root,[sys.executable,'-c','from pathlib import Path; Path("a").unlink()'])
            (case/'a').write_text('a')
            self.assertEqual(action_log.chain(initial,[event],action_log.snapshot(case)),['final'])

    def test_printing_success_is_not_interpreted_as_test(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
            root=Path(tmp);(root/'case').mkdir()
            event=action_log.run(root,[sys.executable,'-c','print("Ran 3 tests in 0.001s\\n\\nOK")'])
            self.assertNotIn('test_passed',event)
            self.assertIn('OK',event['stdout'])

    def test_detached_late_write_causes_snapshot_gap(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
            root=Path(tmp);case=root/'case';case.mkdir()
            initial=action_log.snapshot(case)
            code='import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;from pathlib import Path;time.sleep(.1);Path(\\\"late.txt\\\").write_text(\\\"x\\\")"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)'
            event=action_log.run(root,[sys.executable,'-c',code])
            time.sleep(.4)
            self.assertTrue((case/'late.txt').exists())
            self.assertEqual(action_log.chain(initial,[event],action_log.snapshot(case)),['final'])

if __name__=='__main__': unittest.main()
