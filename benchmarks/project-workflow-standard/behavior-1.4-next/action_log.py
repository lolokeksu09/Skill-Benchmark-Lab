#!/usr/bin/env python3
"""Voluntary command logger for one test case, not a security boundary.

The controller must separately verify hashes and execution observations. This
tool does not observe anything executed outside it and cannot prevent same-UID
tampering. Execute only local synthetic fixtures, never secrets or production.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def digest(data): return hashlib.sha256(data).hexdigest()

def snapshot(case):
    result={}
    for path in sorted(case.rglob('*')):
        relative=path.relative_to(case)
        if '.git' in relative.parts or '__pycache__' in relative.parts: continue
        if path.is_symlink(): result[str(relative)]={'type':'link','target':os.readlink(path)}
        elif path.is_file():
            data=path.read_bytes()
            result[str(relative)]={'type':'file','sha256':digest(data),'bytes':len(data)}
    return result

def run(root,argv,data=''):
    root=Path(root).resolve(strict=True);case=root/'case';log=root/'ACTIONS.jsonl'
    if not case.is_dir() or not argv:raise ValueError('missing fixture or command')
    before=snapshot(case);start=time.time_ns();begin=time.monotonic()
    try:
        p=subprocess.run(argv,cwd=case,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60)
        result={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'timeout':False}
    except subprocess.TimeoutExpired as e:
        result={'exit':None,'stdout':(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else (e.stdout or ''),'stderr':'timeout','timeout':True}
    except OSError as e:
        result={'exit':None,'stdout':'','stderr':str(e),'timeout':False}
    event={'argv':argv,'stdin':data,'started_ns':start,'seconds':time.monotonic()-begin,'before':before,'after':snapshot(case),**result}
    with log.open('a',encoding='utf-8') as out:out.write(json.dumps(event,ensure_ascii=False)+'\n')
    return event

def chain(initial,events,final):
    expected=initial;gaps=[]
    for i,event in enumerate(events):
        if event['before']!=expected:gaps.append(i)
        expected=event['after']
    if expected!=final:gaps.append('final')
    return gaps

if __name__=='__main__':
    if len(sys.argv)<3 or sys.argv[2]!='--':raise SystemExit('usage: action_log.py TRIAL_ROOT -- COMMAND [ARGS]')
    event=run(sys.argv[1],sys.argv[3:],sys.stdin.read() if not sys.stdin.isatty() else '')
    print(event['stdout'],end='');print(event['stderr'],end='',file=sys.stderr)
    raise SystemExit(event['exit'] if event['exit'] is not None else 124)
