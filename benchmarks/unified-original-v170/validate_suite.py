#!/usr/bin/env python3
"""Offline schema guard only; does not score model output."""
import copy
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
def object_no_dupes(items):
    result={}
    for key,value in items:
        if key in result: raise ValueError('Duplicate JSON field: '+key)
        result[key]=value
    return result

def issues(data):
    errors=[]
    if not isinstance(data,dict) or data.get('schema_version')!=1:
        return ['Invalid schema']
    tasks=data.get('tasks')
    if not isinstance(tasks,list) or len(tasks)!=4:
        return ['Expected four tasks']
    ids=[]
    for task in tasks:
        if not isinstance(task,dict):
            errors.append('Task is not an object');continue
        slug=task.get('id')
        if not isinstance(slug,str) or not re.fullmatch('U170-0[1-4]',slug):
            errors.append('Invalid task ID');continue
        ids.append(slug)
        if not isinstance(task.get('prompt'),str) or len(task['prompt'])<120:
            errors.append('Prompt too short: '+slug)
        for field,count in [('acceptance',3),('negative_controls',2)]:
            items=task.get(field)
            if not isinstance(items,list) or len(items)!=count or any(not isinstance(x,str) or len(x)<25 for x in items):
                errors.append('Invalid '+field+': '+slug)
    if len(set(ids))!=4:errors.append('Duplicate or missing IDs')
    return errors

def main():
    data=json.loads((HERE/'TASKS.json').read_text(encoding='utf-8'),object_pairs_hook=object_no_dupes)
    errors=issues(data)
    if errors:print(json.dumps({'valid':False,'errors':errors}));return 2
    mutations=[]
    m=copy.deepcopy(data);m['tasks'][0]['negative_controls']=[];mutations.append(m)
    m=copy.deepcopy(data);m['tasks'][0]['id']=m['tasks'][1]['id'];mutations.append(m)
    m=copy.deepcopy(data);m['tasks'][0]['prompt']='oops';mutations.append(m)
    if any(not issues(item) for item in mutations):
        raise RuntimeError('Validator did not reject corrupted test specification')
    print(json.dumps({'valid':True,'tasks':4,'negative_selftests':3,'agent_runs':0,
                      'effectiveness_measured':False},indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
