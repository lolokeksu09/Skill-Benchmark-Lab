import importlib.util
import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

RUNNER = Path(__file__).with_name('run_codex_ab.py')
ZIP = Path(os.environ.get('UNIFIED_V2_ZIP', str(Path(__file__).with_name('candidate-v2.zip'))))
spec = importlib.util.spec_from_file_location('ab', RUNNER)
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)

class BenchmarkHarnessTests(unittest.TestCase):
    def test_fixed_balance_and_interleaving(self):
        x=ab.schedule(3)
        self.assertEqual(x,ab.schedule(3))
        self.assertEqual(len(x),6)
        self.assertEqual(sum(row['arm']=='control' for row in x),3)
        self.assertEqual(sum(row['arm']=='unified-v2-packet' for row in x),3)
        self.assertEqual({r['repeat'] for r in x},{1,2,3})

    def test_reject_invalid_repetitions(self):
        for n in (0,11,-1):
            with self.assertRaises(ValueError):ab.schedule(n)

    def test_git_blob_matches_empty(self):
        self.assertEqual(ab.git_blob_sha(b''),'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')

    def test_frozen_source_checks_both_task_and_grader(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for name in ab.FROZEN_BLOBS:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text('sample '+name,encoding='utf-8')
            frozen={name:ab.git_blob_sha((root/name).read_bytes()) for name in ab.FROZEN_BLOBS}
            with patch.object(ab,'FROZEN_BLOBS',frozen):
                _, hashes=ab.freeze_suite(root)
                self.assertEqual(len(hashes),6)
                (root/'score_web.py').write_text('tampered')
                with self.assertRaisesRegex(ValueError,'changed'):
                    ab.freeze_suite(root)

    @unittest.skipUnless(ZIP.is_file(), 'Frozen candidate ZIP not present in CI; test locally with UNIFIED_V2_ZIP')
    def test_embedded_v2_skill_instruction_packet(self):
        with tempfile.TemporaryDirectory() as t:
            root=ab.safe_extract(ZIP,t)
            packet=ab.make_packet(root)
            self.assertIn('## Included skill instructions',packet)
            self.assertIn('skills/web-ui/SKILL.md',packet)
            self.assertIn('skills/responsive-layout/SKILL.md',packet)
            self.assertIn('Workflow: web-feature',packet)

    def test_wrong_zip_digest_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            suite=Path(t)
            with self.assertRaisesRegex(ValueError,'Wrong candidate ZIP'):
                ab.design(suite,RUNNER)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.zip'
            with ZipFile(p,'w') as z:z.writestr('unified-development-design/../../escape','no')
            with self.assertRaisesRegex(ValueError,'Unsafe ZIP'):
                ab.safe_extract(p,Path(t)/'output')

    def test_score_accounting_requires_actual_scored(self):
        rows=[{'arm':'control','status':'scored','result_score':3},
              {'arm':'control','status':'timeout','result_score':None},
              {'arm':'unified-v2-packet','status':'scored','result_score':10}]
        result=ab.aggregate(rows)
        self.assertEqual(result['mean_point_difference'],7)
        self.assertEqual(result['arms']['control']['scored'],1)
        self.assertEqual(result['arms']['unified-v2-packet']['scored'],1)
        self.assertNotEqual(result['arms']['control']['scores'],[3,0])

    def test_no_score_for_empty_trials(self):
        result=ab.aggregate([])
        self.assertIsNone(result['mean_point_difference'])
        self.assertIsNone(result['arms']['control']['mean'])

if __name__=='__main__':unittest.main()