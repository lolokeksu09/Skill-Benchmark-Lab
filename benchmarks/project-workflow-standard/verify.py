"""Replay frozen outputs and verify the grader; never invokes an AI service."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12+ required')
    for version in ['1.1','1.2']:
        instruction_root=ROOT/'instructions'/version
        docs=list(instruction_root.rglob('*.md'))
        assert len(docs)==9,(version,len(docs))
        for path in docs:
            for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
                if not link.startswith(('http:','https:','#')):
                    assert (path.parent/link.split('#')[0]).is_file(),(path,link)
        for case in ['csv','blocked']:
            manifest=json.loads((ROOT/'manifests'/f'{version}-{case}.json').read_text())
            for name in ['AGENTS.md','TESTING-LEVELS.md']:
                assert hashlib.sha256((instruction_root/name).read_bytes()).hexdigest()==manifest['initial_hashes'][name],(version,case,name)
    frozen=json.loads((ROOT/'candidate-frozen.json').read_text())
    for name,digest in frozen.items():
        assert hashlib.sha256((ROOT/'instructions/1.2'/name).read_bytes()).hexdigest()==digest,name
    for case in ['csv','blocked']:
        a=json.loads((ROOT/'manifests'/f'1.1-{case}.json').read_text())
        b=json.loads((ROOT/'manifests'/f'1.2-{case}.json').read_text())
        assert a['task']==b['task'],case
        for name,digest in a['initial_hashes'].items():
            if name not in {'AGENTS.md','TESTING-LEVELS.md'} and not name.startswith('templates/'):
                assert digest==b['initial_hashes'][name],(case,name)
    grader=load('workflow_grader',ROOT/'evaluate.py')
    generator=load('workflow_generator',ROOT/'setup.py')
    with tempfile.TemporaryDirectory(prefix='workflow-replay-') as tmp:
        work=Path(tmp)
        shutil.copytree(ROOT/'runs',work/'runs')
        shutil.copytree(ROOT/'manifests',work/'manifests')
        grader.ROOT=work
        summary=[]
        for version in ['1.1','1.2']:
            for case,expected in [('csv',12),('blocked',13)]:
                row=grader.evaluate(version,case)
                assert row['fail']==0 and row['pass']==expected,row
                report=json.loads((work/'results'/f'{version}-{case}.json').read_text())
                if case=='blocked':
                    integrations=[x for x in report['checks'] if x['check']=='external_integration']
                    assert len(integrations)==1 and integrations[0]['status']=='unavailable',integrations
                summary.append(row)
        # Known-broken inputs must be rejected, not silently accepted by the evaluator.
        pristine=work/'pristine';pristine.mkdir()
        generator.ROOT=pristine
        grader.ROOT=pristine
        for case,minimum_failures in [('csv',8),('blocked',9)]:
            generator.setup('1.1',case)
            row=grader.evaluate('1.1',case)
            assert row['fail']>=minimum_failures,('grader accepted broken input',row)
            print('Known-broken fixture correctly rejected:',json.dumps(row))
        print('Frozen outputs:',json.dumps(summary))
    print('PASS: instruction integrity, equal inputs, 4 output replays and 2 known-broken controls. No AI executed.')

if __name__=='__main__':main()
