"""Replay recorded applications and controls. Never invokes an AI service."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
TRACK=ROOT.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def signature(report):
    return {'checks':[(r['check'],r['status']) for r in report['checks']],
            **{k:report[k] for k in ['pass','fail','unavailable']}}

def main():
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12+ required')
    frozen=json.loads((ROOT/'frozen.json').read_text())
    for name,sha in frozen['files'].items():
        assert digest(ROOT/name)==sha,('frozen protocol/instructions changed',name)
    saved=json.loads((ROOT/'outputs-frozen.json').read_text())
    for name,sha in saved['files'].items():
        assert digest(ROOT/name)==sha,('recorded evidence changed',name)
    for case in ['registry','restore']:
        refs=[]
        for version in ['1.1','1.2']:
            for repeat in [1,2]:
                meta=json.loads((ROOT/'manifests'/f'{version}-{case}-{repeat}.json').read_text())
                refs.append(meta)
                instructions=TRACK/'instructions'/version
                for name,sha in meta['initial_hashes'].items():
                    if name in ['AGENTS.md','TESTING-LEVELS.md'] or name.startswith('templates/'):
                        assert digest(instructions/name)==sha,(version,name)
        for ref in refs[1:]:
            assert ref['task']==refs[0]['task'],case
            for name,sha in refs[0]['initial_hashes'].items():
                if name not in ['AGENTS.md','TESTING-LEVELS.md'] and not name.startswith('templates/'):
                    assert ref['initial_hashes'][name]==sha,(case,name)
    grader=load('recovery_grader',ROOT/'evaluate.py')
    generator=load('recovery_generator',ROOT/'setup.py')
    with tempfile.TemporaryDirectory(prefix='recovery-replay-') as tmp:
        replay=Path(tmp)/'applications';replay.mkdir()
        shutil.copytree(ROOT/'runs',replay/'runs');shutil.copytree(ROOT/'manifests',replay/'manifests')
        for version in ['1.1','1.2']:
            for case in ['registry','restore']:
                for repeat in [1,2]:
                    label=f'{version}-{case}-{repeat}'
                    expected=json.loads((ROOT/'results'/f'{label}.json').read_text())
                    actual=grader.evaluate(replay,version,case,repeat)
                    assert signature(actual)==signature(expected),(label,actual,expected)
                    env=dict(os.environ);env.pop('WFS_RESTORE_PROVIDER_RECEIPT',None)
                    result=subprocess.run([sys.executable,'-m','unittest','discover','-v'],cwd=replay/'runs'/version/case/str(repeat),env=env,capture_output=True,text=True,timeout=45)
                    unit=json.loads((ROOT/'results'/f'{label}-unittest.json').read_text())
                    assert result.returncode==unit['exit_code'],(label,'unit result changed',result.stdout,result.stderr)
                    print(label,json.dumps({k:actual[k] for k in ['pass','fail','unavailable']}),'unit exit',result.returncode)
        controls=Path(tmp)/'controls';controls.mkdir()
        for case,minimum in [('registry',10),('restore',8)]:
            generator.setup(controls,'1.1',case,1)
            actual=grader.evaluate(controls,'1.1',case,1)
            assert actual['fail']>=minimum,('known-broken control accepted',actual)
            print('Known-broken control rejected:',case,'failures',actual['fail'])
    print('PASS: frozen protocol, equal inputs, eight recorded applications, unit suites and broken controls. No AI executed.')

if __name__=='__main__':main()
