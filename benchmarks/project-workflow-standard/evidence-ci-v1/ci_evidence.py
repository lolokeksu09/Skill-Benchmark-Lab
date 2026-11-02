#!/usr/bin/env python3
"""Check whether GitHub Actions metadata matches an independently fixed CI gate.

This offline tool does not fetch GitHub, authenticate JSON, inspect a checkout,
or prove that an AI agent executed any action. `consistent` means only that
the supplied metadata agrees with the explicit expectation. Obtain snapshots
via an authenticated channel; independently inspect trusted workflow/checkout.
"""
import argparse
import json
from pathlib import Path
import re

MAX_BYTES=4*1024*1024
def response(state,reason,**extra):
    return {'state':state,'reason':reason,'source_authenticated':False,
            'actual_checkout_verified':False,'agent_execution_verified':False,**extra}

def evaluate(run,jobs,expected):
    if not all(isinstance(x,dict) for x in (run,jobs,expected)):
        return response('invalid_input','all inputs must be objects')
    names=('repository','head_repository','head_sha','run_id','workflow_id','attempt','jobs')
    if any(x not in expected for x in names):return response('invalid_input','missing expected identity or jobs')
    if not all(isinstance(expected[x],str) and expected[x] for x in ('repository','head_repository','head_sha')):
        return response('invalid_input','repository and head SHA must be non-empty strings')
    if not re.fullmatch(r'[0-9a-f]{40}',expected['head_sha']):return response('invalid_input','head SHA must be 40 lowercase hex characters')
    if not all(type(expected[x]) is int and expected[x]>0 for x in ('run_id','workflow_id','attempt')):
        return response('invalid_input','expected IDs and attempt must be positive integers')
    req=expected['jobs']
    if not isinstance(req,list) or not req or len(req)>100:return response('invalid_input','expected jobs must be a nonempty bounded list')
    if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) or not x['name'].strip() or
           not isinstance(x.get('steps'),list) or not all(isinstance(s,str) and s.strip() for s in x['steps']) or
           len(set(x['steps']))!=len(x['steps']) for x in req):
        return response('invalid_input','invalid job or required steps')
    if len({x['name'] for x in req})!=len(req):return response('invalid_input','duplicate expected job name')
    identity={'id':expected['run_id'],'workflow_id':expected['workflow_id'],'run_attempt':expected['attempt'],'head_sha':expected['head_sha']}
    for field,want in identity.items():
        if field not in run or run[field] is None:return response('inconclusive','run identity missing: '+field)
        if type(run[field]) is not type(want) or run[field]!=want:return response('conflict','run identity differs: '+field)
    for field,want in [('repository',expected['repository']),('head_repository',expected['head_repository'])]:
        actual=run.get(field)
        if not isinstance(actual,dict) or not isinstance(actual.get('full_name'),str):return response('inconclusive','run repository missing: '+field)
        if actual['full_name']!=want:return response('conflict','run repository differs: '+field)
    if not isinstance(run.get('status'),str):return response('inconclusive','run status missing')
    if run.get('status')!='completed':return response('pending','run has not completed')
    if run.get('conclusion') is None:return response('inconclusive','completed run lacks conclusion')
    if run.get('conclusion')!='success':return response('failed','run conclusion is '+str(run['conclusion']))
    found=jobs.get('jobs');total=jobs.get('total_count')
    if not isinstance(found,list) or type(total) is not int or total<0:return response('inconclusive','invalid jobs page')
    if total!=len(found) or len(found)>100:return response('inconclusive','jobs page incomplete or exceeds limit')
    if any(not isinstance(x,dict) for x in found):return response('inconclusive','invalid job entry')
    result=[]
    for entry in req:
        matches=[x for x in found if x.get('name')==entry['name']]
        if len(matches)!=1:return response('inconclusive','required job missing or ambiguous: '+entry['name'])
        job=matches[0]
        if job.get('run_id') is None or job.get('run_attempt') is None:return response('inconclusive','job run or attempt missing: '+entry['name'])
        if type(job.get('run_id')) is not int or job['run_id']!=expected['run_id'] or type(job.get('run_attempt')) is not int or job['run_attempt']!=expected['attempt']:
            return response('conflict','job run or attempt differs: '+entry['name'])
        if job.get('status')!='completed':return response('pending','job has not completed: '+entry['name'])
        if job.get('conclusion') is None:return response('inconclusive','job lacks conclusion: '+entry['name'])
        if job['conclusion']!='success':return response('failed','required job not successful: '+entry['name'])
        steps=job.get('steps')
        if entry['steps'] and not isinstance(steps,list):return response('inconclusive','job steps missing: '+entry['name'])
        for step_name in entry['steps']:
            matching=[x for x in steps if isinstance(x,dict) and x.get('name')==step_name]
            if len(matching)!=1:return response('inconclusive','required step missing or ambiguous: '+step_name)
            step=matching[0]
            if step.get('status')!='completed':return response('pending','step has not completed: '+step_name)
            if step.get('conclusion') is None:return response('inconclusive','step lacks conclusion: '+step_name)
            if step['conclusion']!='success':return response('failed','required step not successful: '+step_name)
        result.append({'name':entry['name'],'id':job.get('id'),'required_steps':len(entry['steps'])})
    return response('consistent','supplied CI metadata matches the fixed expectation',jobs=result,
                    limitation='Metadata alone does not authenticate its source or establish checkout, test coverage, authorization, or agent actions.')

def read_json(path):
    with Path(path).open('rb') as f:data=f.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('input size limit exceeded')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('duplicate JSON key: '+k)
            out[k]=v
        return out
    return json.loads(data,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True,type=Path);p.add_argument('--jobs',required=True,type=Path);p.add_argument('--expect',required=True,type=Path)
    a=p.parse_args()
    try:r=evaluate(read_json(a.run),read_json(a.jobs),read_json(a.expect))
    except (OSError,ValueError,TypeError,RecursionError) as e:r=response('invalid_input',str(e))
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r['state']=='consistent' else 2 if r['state'] in ('pending','inconclusive') else 1
if __name__=='__main__':raise SystemExit(main())
