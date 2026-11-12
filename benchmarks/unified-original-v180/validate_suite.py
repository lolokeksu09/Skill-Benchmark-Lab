#!/usr/bin/env python3
"""Offline v1.8.0 benchmark task metadata validator; no LLM calls or scoring."""
import copy
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parent

def pairs_no_dupes(items):
    result={}
    for key,val in items:
        if key in result:raise ValueError('Duplicate JSON field: '+key)
        result[key]=val
    return result

def invalid(data):
    errors=[]
    if not isinstance(data,dict) or data.get('schema_version')!=1:
        return ['Expected schema_version=1']
    tasks=data.get('tasks')
    if not isinstance(tasks,list) or len(tasks)!=5:
        return ['Expected five task records']
    seen=set()
    for task in tasks:
        if not isinstance(task,dict):
            errors.append('Nonobject task');continue
        id=task.get('id')
        if not isinstance(id,str) or not re.fullmatch('U180-0[1-5]',id):
            errors.append('Invalid ID');continue
        if id in seen:errors.append('Duplicate ID '+id)
        seen.add(id)
        prompt=task.get('prompt')
        if not isinstance(prompt,str) or len(prompt)<120:errors.append('Missing realistic prompt for '+id)
        if not isinstance(task.get('domain'),str) or len(task['domain'])<5:
            errors.append('Missing domain for '+id)
        for field,count in [('acceptance',3),('negative_controls',2)]:
            values=task.get(field)
            if not isinstance(values,list) or len(values)!=count or any(not isinstance(x,str) or len(x)<25 for x in values):
                errors.append('Bad '+field+' for '+id)
    if not isinstance(data.get('candidate_zip_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',data['candidate_zip_sha256']):
        errors.append('Invalid candidate ZIP digest')
    if data.get('agent_runs')!=0:errors.append('This frozen preflight has no agent runs')
    return errors

def main():
    data=json.loads((ROOT/'TASKS.json').read_text(encoding='utf-8'),object_pairs_hook=pairs_no_dupes)
    problems=invalid(data)
    negative=[]
    for name,change in [
        ('empty_negative', lambda d:d['tasks'][0].update(negative_controls=[])),
        ('duplicate_id',lambda d:d['tasks'][1].update(id=d['tasks'][0]['id'])),
        ('short_prompt',lambda d:d['tasks'][1].update(prompt='x')),
        ('wrong_digest',lambda d:d.update(candidate_zip_sha256='not-a-hash'))
    ]:
        altered=copy.deepcopy(data);change(altered)
        if not invalid(altered):negative.append(name)
    output={'schema_version':1,'tasks':len(data.get('tasks',[])),'metadata_passed':not problems,
            'negative_selftests_passed':4-len(negative),'negative_selftests_expected':4,
            'issues':problems+negative,'agent_runs':0,'agent_effectiveness_measured':False}
    print(json.dumps(output,indent=2))
    return 0 if not output['issues'] else 2

if __name__=='__main__':sys.exit(main())
