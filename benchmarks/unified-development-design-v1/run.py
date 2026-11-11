#!/usr/bin/env python3
"""Self-contained reproducible offline plugin smoke test using Skill-Benchmark-Lab V4 task signals.

No network, AI, Git changes, workspace service, browser or emulator. This is NOT
Lab V4's 44-point behavioral benchmark; it checks plugin structure/routing.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures.json'


def run_command(argv, cwd, timeout=90):
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'seconds': round(time.monotonic()-start, 3)}
    except subprocess.TimeoutExpired:
        return {'exit_code': -999, 'stdout': '', 'stderr': 'timeout',
                'seconds': round(time.monotonic()-start, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--expected-version', default='1.0.0', help='Manifest version, default preserves original Lab v1.0.0 run')
    args = ap.parse_args()
    archive = args.archive.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    fixture = json.loads(FIXTURES.read_text(encoding='utf-8'))
    report = {'source': fixture['benchmark_repo'], 'protocol': fixture['source_protocol'],
              'task': fixture['source_task'], 'fixture_version': fixture['fixture_version'],
              'fixture_sha256': hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
              'archive': {'name': archive.name,
                          'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                          'bytes': archive.stat().st_size},
              'python': sys.version.split()[0], 'no_ai_agent_executed': True,
              'host_repo_clone': False,
              'checks': {}, 'scenarios': []}
    with tempfile.TemporaryDirectory(prefix='unified-lab-smoke-') as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            invalid = []
            for info in z.infolist():
                name = PurePosixPath(info.filename)
                is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
                if name.is_absolute() or '..' in name.parts or '\\' in info.filename or is_symlink:
                    invalid.append(info.filename)
            report['checks']['archive'] = {'passed': not invalid and z.testzip() is None,
                                           'entries': len(names), 'unsafe_paths': invalid}
            if invalid: raise RuntimeError(f'unsafe archive: {invalid[:10]}')
            z.extractall(tmp_path)
        roots = [p for p in tmp_path.iterdir() if p.is_dir()]
        if len(roots) != 1: raise RuntimeError(f'expected 1 plugin root, got {len(roots)}')
        root = roots[0]
        manifest = json.loads((root/'plugin.json').read_text(encoding='utf-8'))
        skills = list((root/'skills').glob('*/SKILL.md'))
        names = [p.parent.name for p in skills]
        report['checks']['plugin'] = {
            'passed': manifest.get('version')==args.expected_version and len(skills)==122 and len(names)==len(set(names))
                and (root/'skills/impeccable/SKILL.md').exists()
                and (root/'skills/anti-ai-slop/SKILL.md').exists(),
            'version': manifest.get('version'), 'skills': len(skills),
            'unique_names': len(set(names)),
            'impeccable_files': sum(1 for p in (root/'skills/impeccable').rglob('*') if p.is_file()),
            'ui_ux_pro_max_count': sum(name=='ui-ux-pro-max' for name in names),
        }
        router = root/'skills/skill-router/scripts/route.py'
        regression = run_command([sys.executable,str(root/'skills/skill-router/scripts/test_router_context.py')],cwd=root)
        try:
            regression_data=json.loads(regression['stdout'])
            regression_result={'passed': regression['exit_code']==0 and regression_data['passed']==regression_data['total'],
                               'passed_count':regression_data['passed'], 'total': regression_data['total']}
        except (ValueError, KeyError):
            regression_result={'passed':False,'error':regression['stderr'][-500:]}
        report['checks']['p2p_regression']=regression_result
        for case in fixture['cases']:
            cmd=run_command([sys.executable,str(router),'--task',case['task'],'--stack',case['stack']],cwd=root)
            try:
                o=json.loads(cmd['stdout']);initial=[s['skill'] for s in o.get('initial',[])];
                missing=sorted(set(case['must_include'])-set(initial));forbidden=sorted(set(case['must_exclude'])&set(initial))
                result={'id':case['id'],'passed':cmd['exit_code']==0 and not missing and not forbidden,
                        'missing':missing,'forbidden':forbidden,'selected':initial,
                        'mode':o.get('mode'),'risk':o.get('risk')}
            except (ValueError,KeyError,TypeError):
                result={'id':case['id'],'passed':False,'error':cmd['stderr'][-500:] or cmd['stdout'][-500:]}
            report['scenarios'].append(result)
        ui_tests = run_command([sys.executable,'-m','unittest','discover','-s',str(root/'skills/ui-ux-pro-max/scripts/tests'),'-p','test_*.py','-q'],cwd=root,timeout=120)
        combined = ui_tests['stdout'] + '\n' + ui_tests['stderr']
        found = re.search(r'Ran (\d+) tests',combined)
        errors = re.search(r'FAILED \(errors=(\d+)\)',combined)
        failed = re.search(r'FAILED \(failures=(\d+)',combined)
        report['checks']['ui_ux_unittest'] = {
            'passed': ui_tests['exit_code']==0,
            'return_code':ui_tests['exit_code'],
            'discovered_tests':int(found.group(1)) if found else None,
            'module_errors':int(errors.group(1)) if errors else 0,
            'assertion_failures':int(failed.group(1)) if failed else 0,
            'missing_external_development_scripts': all(x in combined for x in ['test_catalog_refresh','test_relevance_evaluator','test_skill_script_paths']),
        }
        (out/'ui-ux-unittest.log').write_text(combined,encoding='utf-8')
        verify_paths=[root/'references/ANTI-AI-SLOP.md',root/'references/DESIGN-PROFILE.template.md',root/'references/DESIGN-REVIEW.template.md',root/'skills/impeccable/reference/critique.md',root/'skills/impeccable/reference/android.md']
        report['checks']['design_docs']={'passed':all(p.exists() for p in verify_paths),
                                        'files_present':sum(p.exists() for p in verify_paths),
                                        'files_required':len(verify_paths)}
    report['summary']={
        'scenarios_passed':sum(x['passed'] for x in report['scenarios']),
        'scenarios_total':len(report['scenarios']),
        'check_groups_passed':sum(v['passed'] for v in report['checks'].values()),
        'check_groups_total':len(report['checks'])}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False))
    print('results:',out/'results.json')
    return 0 if all(x['passed'] for x in report['scenarios']) and all(v['passed'] for v in report['checks'].values()) else 1

if __name__=='__main__': raise SystemExit(main())
