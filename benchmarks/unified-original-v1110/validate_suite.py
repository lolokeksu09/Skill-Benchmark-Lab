#!/usr/bin/env python3
"""Validate frozen benchmark specifications only; never invokes or scores an AI."""
import copy
import json
from pathlib import Path
import re

def reject_duplicate_fields(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate field: '+key)
        result[key] = value
    return result

def issues(data):
    errors = []
    if not isinstance(data,dict) or data.get('schema_version') != 1:
        return ['Expected schema_version=1']
    tasks = data.get('tasks')
    if not isinstance(tasks,list) or len(tasks) != 5:
        return ['Expected five frozen tasks']
    if data.get('actual_agent_trials') != 0 or data.get('trial_status') != 'not-run':
        errors.append('Agent runs have not been verified')
    digest = data.get('candidate_zip_sha256')
    if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):
        errors.append('Invalid candidate ZIP SHA-256')
    seen = set()
    for task in tasks:
        if not isinstance(task,dict):
            errors.append('Malformed task');continue
        id = task.get('id')
        if not isinstance(id,str) or not re.fullmatch(r'U1110-0[1-5]',id):
            errors.append('Invalid task ID');continue
        if id in seen:errors.append('Duplicate task ID')
        seen.add(id)
        if not isinstance(task.get('prompt'),str) or len(task['prompt']) < 140:
            errors.append('Task prompt too short: '+id)
        for key,size in (('acceptance',3),('negative_controls',2)):
            records = task.get(key)
            if not isinstance(records,list) or len(records) != size or any(
                not isinstance(record,str) or len(record) < 20 for record in records
            ):
                errors.append('Invalid '+key+': '+id)
    return errors

def main():
    root = Path(__file__).resolve().parent
    data = json.loads((root/'TASKS.json').read_text(encoding='utf-8'),
                      object_pairs_hook=reject_duplicate_fields)
    failures = issues(data)
    mutation_cases = [
        lambda x: x['tasks'][0].update(negative_controls=[]),
        lambda x: x['tasks'][1].update(id=x['tasks'][0]['id']),
        lambda x: x.update(actual_agent_trials=1),
        lambda x: x['tasks'][0].update(prompt='short'),
    ]
    for index, mutation in enumerate(mutation_cases):
        candidate = copy.deepcopy(data)
        mutation(candidate)
        if not issues(candidate):failures.append('Mutation not rejected: '+str(index))
    print(json.dumps({'valid':not failures,'task_count':len(data.get('tasks',[])),
          'negative_selftests':4,'agent_trials':0,'efficacy_measured':False,
          'issues':failures},indent=2))
    return 2 if failures else 0

if __name__=='__main__':
    raise SystemExit(main())
