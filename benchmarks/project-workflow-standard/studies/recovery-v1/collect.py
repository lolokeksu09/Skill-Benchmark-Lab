"""Parent-side evidence collection after applications finish; never modifies a run."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent

def collect(work):
    spec=importlib.util.spec_from_file_location('study_grader',ROOT/'evaluate.py')
    grader=importlib.util.module_from_spec(spec);spec.loader.exec_module(grader)
    dest_runs=ROOT/'runs';dest_runs.mkdir(exist_ok=False)
    rows=[]
    for version in ['1.1','1.2']:
        for case in ['registry','restore']:
            for repeat in [1,2]:
                run=work/'runs'/version/case/str(repeat)
                assert (run/'FINAL.md').is_file(),('application unfinished',run)
                label=f'{version}-{case}-{repeat}'
                existing=work/'results'/f'{label}.json'
                row=json.loads(existing.read_text()) if existing.is_file() else grader.evaluate(work,version,case,repeat)
                rows.append({k:v for k,v in row.items() if k!='checks'})
                target=dest_runs/version/case/str(repeat);target.mkdir(parents=True)
                for path in run.rglob('*'):
                    name=path.relative_to(run)
                    if not path.is_file() or any(part in ['.git','__pycache__','templates'] for part in name.parts):continue
                    if str(name) in ['AGENTS.md','TESTING-LEVELS.md','PROJECT.md','TASK.txt']:continue
                    dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
                resultdir=ROOT/'results';resultdir.mkdir(exist_ok=True)
                shutil.copyfile(work/'results'/f'{label}.json',resultdir/f'{label}.json')
                diff=subprocess.run(['git','-C',str(run),'diff','--no-ext-diff'],capture_output=True,text=True,check=True)
                (resultdir/f'{label}.diff').write_text(diff.stdout)
                env=dict(os.environ);env.pop('WFS_RESTORE_PROVIDER_RECEIPT',None)
                with tempfile.TemporaryDirectory(prefix='recovery-units-') as tmp:
                    copied=Path(tmp)/'project'
                    shutil.copytree(run,copied,ignore=shutil.ignore_patterns('.git','__pycache__'))
                    result=subprocess.run([sys.executable,'-m','unittest','discover','-v'],cwd=copied,env=env,capture_output=True,text=True,timeout=45)
                (resultdir/f'{label}-unittest.log').write_text(result.stdout+result.stderr)
                (resultdir/f'{label}-unittest.json').write_text(json.dumps({'command':'python3 -m unittest discover -v','exit_code':result.returncode,'python':sys.version.split()[0],'provider_receipt_env':'unset'},indent=2))
    (ROOT/'summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    files={}
    for folder in ['runs','results','manifests']:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file():files[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT/'outputs-frozen.json').write_text(json.dumps({'files':files},indent=2))
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',type=Path,required=True);a=p.parse_args();collect(a.work_root.resolve())
