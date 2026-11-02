#!/usr/bin/env python3
"""Create and freeze 84 trials; never starts models or overwrites a root."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import scenario_suite as suite

HERE=Path(__file__).resolve().parent
CHECKS={'S01':['tests'],'S03':['ci_success','ci_failure'],'S06':['unit','device'],
        'S07':['tests','integration'],'S08':['tests'],'S09':[],'S10':[]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(root,seed=141405):
    root=Path(root).resolve();manifest=suite.setup(root,seed)
    guidance=(HERE/'GUIDANCE.md').read_text(encoding='utf-8')
    for trial in manifest['trials']:
        t=root/trial['name'];task=t/'RUN_TASK.md'
        task.write_text(task.read_text(encoding='utf-8')+guidance,encoding='utf-8')
        harness=t/'_harness';harness.mkdir()
        for name in ('action_log.py','gate_observer.py'):shutil.copyfile(HERE/name,harness/name)
        labels=CHECKS[trial['case']]
        available='Доступные проверки стенда: '+(', '.join('`'+x+'`' for x in labels) if labels else 'для этого сценария обязательные проверки стенда не заданы')+'.\n'
        (t/'AVAILABLE_CHECKS.md').write_text(available,encoding='utf-8')
        trial['run_task_sha256']=sha(task)
        trial['available_checks_sha256']=sha(t/'AVAILABLE_CHECKS.md')
        trial['harness_hashes']={x:sha(harness/x) for x in ('action_log.py','gate_observer.py')}
    names=tuple(sorted(p.name for p in HERE.glob('*.py'))) + ('PROTOCOL.md','SCENARIOS.md','GUIDANCE.md')
    manifest['premeasurement_code_sha256']={name:sha(HERE/name) for name in names}
    manifest['instrumentation_notice']='Same guidance/check names per case in every arm; FIFO requester identity and full action coverage remain unverified.'
    (root/'FREEZE.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--seed',type=int,default=141405);a=p.parse_args()
    m=prepare(a.root,a.seed)
    print(json.dumps({'root':str(a.root),'trials':len(m['trials']),'seed':a.seed,'freeze_sha256':sha(a.root/'FREEZE.json')}))
