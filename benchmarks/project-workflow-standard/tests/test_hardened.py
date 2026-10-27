import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TRACK = Path(__file__).resolve().parents[1]
ENTRY = TRACK / 'hardened.py'

class HardenedTests(unittest.TestCase):
    def test_optimized_invocations_refused(self):
        for mode in ('flag', 'environment'):
            env = dict(os.environ)
            env.pop('PYTHONOPTIMIZE', None)
            args = [sys.executable]
            if mode == 'flag': args.append('-O')
            else: env['PYTHONOPTIMIZE'] = '1'
            result = subprocess.run(args + [str(ENTRY), 'replay'], env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('optimized Python', result.stderr)

    def test_original_verifiers_refuse_optimization(self):
        for entry in (TRACK / 'verify.py', TRACK / 'studies' / 'recovery-v1' / 'verify.py'):
            result = subprocess.run([sys.executable, '-O', str(entry)], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('optimized Python', result.stderr)

    def test_tampered_saved_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            track = Path(tmp) / 'track'
            shutil.copytree(TRACK, track, ignore=shutil.ignore_patterns('__pycache__'))
            study = track / 'studies' / 'recovery-v1'
            (study / 'runs' / '1.1' / 'registry' / '1' / 'manifest.json').write_text('{}')
            result = subprocess.run([sys.executable, str(study / 'verify.py')], capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('recorded evidence changed', result.stderr)
            self.assertNotIn('PASS:', result.stdout)

    def test_unexpected_status_is_a_failure(self):
        spec = importlib.util.spec_from_file_location('hardened', ENTRY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.exit_for_checks([{'status': 'unexpected'}]), 1)
        self.assertEqual(module.exit_for_checks([{'status': 'pass'}, {'status': 'unavailable'}]), 2)
        self.assertEqual(module.exit_for_checks([{'status': 'pass'}]), 0)
        self.assertEqual(module.exit_for_checks([]), 1)

    def test_evaluation_distinguishes_unavailable_from_unexpected(self):
        study = TRACK / 'studies' / 'recovery-v1'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'runs' / '1.1' / 'restore' / '1'
            run.parent.mkdir(parents=True)
            shutil.copytree(study / 'runs' / '1.1' / 'restore' / '1', run)
            (root / 'manifests').mkdir()
            manifest = root / 'manifests' / '1.1-restore-1.json'
            shutil.copyfile(study / 'manifests' / '1.1-restore-1.json', manifest)
            args = [sys.executable, str(ENTRY), 'evaluate', '--work-root', str(root), '1.1', 'restore', '1']
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)['overall_status'], 'partial_unavailable')
            # Model a provider that unexpectedly reports success; preserve the
            # fixture's infrastructure checksum so only the status changes.
            script = run / 'provider_check.py'
            script.write_text('print("unexpected provider success")\n')
            meta = json.loads(manifest.read_text())
            meta['initial_hashes']['provider_check.py'] = hashlib.sha256(script.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(meta))
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['overall_status'], 'failed_or_unexpected')
            self.assertTrue(any(c['check'] == 'real_provider_integration' and c['status'] == 'unexpected' for c in report['checks']))
            self.assertFalse((root / 'results').exists(), 'evaluation must not mutate the input root')

if __name__ == '__main__': unittest.main()
