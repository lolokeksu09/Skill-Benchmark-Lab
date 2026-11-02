#!/usr/bin/env python3
"""Copy candidate submissions and observational traces. Does not score them.

Added during the run for checkpointing; the oracle/protocol remain frozen.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import action_log
import scenario_suite as suite

def digest(data):return hashlib.sha256(data).hexdigest()
def run_git(root,*args):
    try:
        p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,timeout=5)
        return {'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except (OSError,subprocess.TimeoutExpired) as e:return {'exit':None,'stdout':'','stderr':str(e)}

def collect(root,name,out):
    root=Path(root);out=Path(out);manifest=json.loads((root/'FREEZE.json').read_text());item=next(x for x in manifest['trials'] if x['name']==name)
    trial=root/name;case=trial/'case';final=trial/'FINAL.md';log=trial/'ACTIONS.jsonl'
    if not final.is_file():raise ValueError('FINAL.md missing; require completed agent')
    files={}
    for p in sorted(case.rglob('*')):
        rel=p.relative_to(case)
        if '.git' in rel.parts or '__pycache__' in rel.parts:continue
        if p.is_symlink():files[str(rel)]={'type':'symlink','target':os.readlink(p)}
        elif p.is_file():
            data=p.read_bytes()
            if len(data)>4_000_000:raise ValueError('case file exceeds capture limit')
            files[str(rel)]={'type':'file','data_b64':base64.b64encode(data).decode(),'sha256':digest(data)}
    actions=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    initial=item['case_inputs']['files'];gaps=[]
    if not actions:gaps.append('no_actions_log')
    else:
        first={k:v.get('sha256') for k,v in actions[0]['before'].items() if v.get('type')=='file'}
        if first!=initial:gaps.append('initial')
        for i in range(1,len(actions)):
            if actions[i-1]['after']!=actions[i]['before']:gaps.append(str(i))
        if actions[-1]['after']!=action_log.snapshot(case):gaps.append('final')
    root_hashes={}
    for rel in ['RUN_TASK.md','AVAILABLE_CHECKS.md','_harness/action_log.py','_harness/gate_observer.py']:
        p=trial/rel;root_hashes[rel]=digest(p.read_bytes()) if p.is_file() else None
    package={'protocol':'PWS-BEHAVIOR-2-CANDIDATE-1','name':name,'captured_ns':time.time_ns(),
             'final_answer':final.read_text(encoding='utf-8'), 'case_files':files,'actions':actions,
             'chain_gaps':gaps,'root_hashes':root_hashes,'head':run_git(case,'rev-parse','HEAD'),
             'status':run_git(case,'status','--short'),'diff':run_git(case,'diff'),
             'staged_diff':run_git(case,'diff','--cached')}
    raw=json.dumps(package,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
    return {'name':name,'sha256':digest(out.read_bytes()),'bytes':out.stat().st_size,'action_count':len(actions),'chain_gaps':gaps}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(collect(a.root,a.name,a.output),ensure_ascii=False))
