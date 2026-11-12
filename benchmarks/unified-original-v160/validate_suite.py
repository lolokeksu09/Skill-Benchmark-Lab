#!/usr/bin/env python3
"""Offline suite integrity check; never runs model agents or scores outcomes."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent

def validate(data):
    issues=[]
    if not isinstance(data,dict) or data.get('schema_version')!=1:
        return ['Expected suite schema_version=1']
    rows=data.get('tasks')
    if not isinstance(rows,list) or len(rows)!=10:
        return ['Expected exactly ten task specifications']
    ids=set()
    domains=set()
    for row in rows:
        if not isinstance(row,dict):
            issues.append('Malformed task item')
            continue
        name=row.get('id')
        if not isinstance(name,str) or not re.fullmatch(r'U160-[0-9]{2}',name):
            issues.append('Invalid task ID')
            continue
        if name in ids:
            issues.append('Duplicate task ID: '+name)
        ids.add(name)
        domain=row.get('domain')
        if not isinstance(domain,str) or not domain:
            issues.append('No domain: '+name)
        else:
            domains.add(domain)
        prompt=row.get('prompt')
        if not isinstance(prompt,str) or len(prompt)<100:
            issues.append('Insufficient task prompt: '+name)
        acceptance=row.get('acceptance')
        if not isinstance(acceptance,list) or len(acceptance)!=3 or any(not isinstance(x,str) or len(x)<25 for x in acceptance):
            issues.append('Expected three concrete acceptance criteria: '+name)
        negative=row.get('negative_controls')
        if not isinstance(negative,list) or len(negative)!=2 or any(not isinstance(x,str) or len(x)<20 for x in negative):
            issues.append('Expected two independent negative controls: '+name)
    if len(domains)!=10:
        issues.append('Expected ten distinct domains')
    return issues

def selftest(data):
    assert not validate(data), validate(data)
    copy1=copy.deepcopy(data);copy1['tasks'][1]['negative_controls']=[]
    assert validate(copy1), 'Negative control omission went undetected'
    copy2=copy.deepcopy(data);copy2['tasks'][1]['id']=copy2['tasks'][0]['id']
    assert validate(copy2), 'Duplicate task ID went undetected'
    copy3=copy.deepcopy(data);copy3['tasks'][1]['prompt']='test'
    assert validate(copy3), 'Empty/short prompt went undetected'
    return {'selftest_negative_controls':3,'passed':3}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--suite',type=Path,default=ROOT/'TASKS.json')
    p.add_argument('--selftest',action='store_true')
    args=p.parse_args()
    data=json.loads(args.suite.read_text(encoding='utf-8'))
    issues=validate(data)
    result={'schema_version':1,'tasks':len(data.get('tasks',[])),'valid':not issues,
            'issues':issues,'agent_runs':0,'efficacy_measured':False}
    if args.selftest and not issues:
        result['selftest']=selftest(data)
    print(json.dumps(result,indent=2))
    return 2 if issues else 0

if __name__=='__main__':
    sys.exit(main())
