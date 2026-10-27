"""Safe entry point for frozen benchmark tools; no AI is invoked."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TRACK = Path(__file__).resolve().parent
STUDY = TRACK / 'studies' / 'recovery-v1'

def exit_for_checks(checks):
    if not checks or any(row.get('status') not in ('pass', 'unavailable') for row in checks):
        return 1
    return 2 if any(row['status'] == 'unavailable' for row in checks) else 0

def main():
    if sys.flags.optimize:
        print('Refusing optimized Python: frozen verifiers require assertions to be enabled.', file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('replay')
    score = commands.add_parser('evaluate')
    score.add_argument('--work-root', type=Path, required=True)
    score.add_argument('version', choices=['1.1', '1.2'])
    score.add_argument('case', choices=['registry', 'restore'])
    score.add_argument('repeat', type=int, choices=[1, 2])
    args = parser.parse_args()
    if args.command == 'replay':
        for path in (TRACK / 'verify.py', STUDY / 'verify.py'):
            result = subprocess.run([sys.executable, str(path)], check=False)
            if result.returncode != 0:
                return result.returncode or 1
        print('Replay passed. Document meaning and agent-controlled logs still require independent review.')
        return 0
    spec = importlib.util.spec_from_file_location('frozen_recovery_evaluator', STUDY / 'evaluate.py')
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    with tempfile.TemporaryDirectory(prefix='workflow-evaluate-') as temp:
        dest = Path(temp)
        for name in ('runs', 'manifests'):
            shutil.copytree(args.work_root.resolve() / name, dest / name)
        report = grader.evaluate(dest, args.version, args.case, args.repeat)
        report['manual_review_required'] = [
            'Assess document meaning, accuracy and completeness separately.',
            'Agent-controlled simulator logs are not independent proof of all actions.'
        ]
        report['overall_status'] = {0: 'automated_checks_passed', 1: 'failed_or_unexpected', 2: 'partial_unavailable'}[exit_for_checks(report['checks'])]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return exit_for_checks(report['checks'])

if __name__ == '__main__':
    sys.exit(main())
