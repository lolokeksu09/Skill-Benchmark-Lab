#!/usr/bin/env python3
"""Offline metadata checks for frozen tasks; never invokes a model."""
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent

def no_duplicate_keys(items):
    out={}
    for name,value in items:
        if name in out:
            raise ValueError("Duplicate field: "+name)
        out[name]=value
    return out

def invalid(data):
    issues=[]
    if not isinstance(data,dict) or data.get('schema_version')!=1:
        return ['Invalid schema']
    tasks=data.get('tasks')
    if not isinstance(tasks,list) or len(tasks)!=4:
        return ['Expected four frozen tasks']
    seen=set()
    for row in tasks:
        if not isinstance(row,dict):
            issues.append('Not an object');continue
        slug=row.get('id')
        if not isinstance(slug,str) or not re.fullmatch(r'U190-0[1-4]',slug):
            issues.append('Invalid task ID');continue
        if slug in seen:issues.append('Duplicate task ID')
        seen.add(slug)
        if not isinstance(row.get('prompt'),str) or len(row['prompt'])<120:
            issues.append('Incomplete prompt: '+slug)
        if not isinstance(row.get('domain'),str) or len(row['domain'])<5:
            issues.append('Missing domain: '+slug)
        for key,n in (('acceptance',3),('negative_controls',2)):
            value=row.get(key)
            if not isinstance(value,list) or len(value)!=n or any(not isinstance(x,str) or len(x)<25 for x in value):
                issues.append('Incomplete '+key+': '+slug)
    if data.get('agent_runs')!=0:issues.append('Unverified agent-run claim')
    if not isinstance(data.get('candidate_zip_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',data['candidate_zip_sha256']):
        issues.append('Missing candidate digest')
    return issues

def main():
    data=json.loads((ROOT/'TASKS.json').read_text(encoding='utf-8'),object_pairs_hook=no_duplicate_keys)
    problems=invalid(data)
    failed=[]
    for name,change in [
        ('duplicate ID',lambda d:d['tasks'][1].update(id=d['tasks'][0]['id'])),
        ('short prompt',lambda d:d['tasks'][1].update(prompt='short')),
        ('missing negative controls',lambda d:d['tasks'][1].update(negative_controls=[])),
        ('bad hash',lambda d:d.update(candidate_zip_sha256='unverified'))
    ]:
        variant=copy.deepcopy(data);change(variant)
        if not invalid(variant):failed.append(name)
    outcome={'tasks':len(data.get('tasks',[])),'schema_valid':not problems,
             'negative_selftests_passed':4-len(failed),'negative_selftests_expected':4,
             'issues':problems+failed,'actual_agent_runs':0,'efficacy_measured':False}
    print(json.dumps(outcome,indent=2))
    return 2 if outcome['issues'] else 0

if __name__=='__main__':
    sys.exit(main())
