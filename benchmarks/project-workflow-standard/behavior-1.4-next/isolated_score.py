#!/usr/bin/env python3
"""Replay frozen per-criterion oracle on captured trials in an OS sandbox.

This post-collection adapter packages files and calls the premeasurement scorer
without changing its rules. It never launches an AI. Do not run candidate
product code without isolating this whole process and its subprocesses.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

import controller
import scenario_suite as suite

def digest(data):return hashlib.sha256(data).hexdigest()
def decoded(value):return base64.b64decode(value,validate=True)

def restore_case(target,entries):
    target.mkdir(parents=True)
    links=[]
    for name,entry in entries.items():
        p=Path(name)
        if p.is_absolute() or not p.parts or '..' in p.parts:raise ValueError('unsafe case file path')
        dest=target/p
        if entry['type']=='symlink':links.append((dest,entry['target']));continue
        if entry['type']!='file':raise ValueError('unsupported case entry')
        data=decoded(entry['data_b64'])
        if digest(data)!=entry['sha256']:raise ValueError('case entry digest mismatch')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    for dest,linktarget in links:
        dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(linktarget)

def evaluate(path):
    data=json.loads(gzip.decompress(Path(path).read_bytes()))
    manifest_bytes=decoded(data['freeze_b64']);manifest=json.loads(manifest_bytes)
    index=data['observer_index']
    if digest(manifest_bytes)!=index['manifest_sha256']:raise ValueError('frozen manifest does not match observer index')
    if len(manifest['trials'])!=84:raise ValueError('expected 84 trials')
    scores={}
    with tempfile.TemporaryDirectory(prefix='pws2-isolated-') as td:
        root=Path(td)
        for item in manifest['trials']:
            name=item['name'];captured=data['trials'][name]
            raw=decoded(captured['candidate_gzip_b64'])
            if digest(raw)!=captured['candidate_sha256']:raise ValueError('candidate receipt hash differs '+name)
            submission=json.loads(gzip.decompress(raw))
            if submission['name']!=name:raise ValueError('candidate identity differs')
            trial=root/name;case=trial/'case';restore_case(case,submission['case_files'])
            observer=decoded(captured['observer_receipt_b64'])
            evidence=controller.evidence_from_receipt(observer,manifest_bytes=manifest_bytes,index=index,
                        trial_name=name,trial_root=root,allow_relocation=True)
            # Claims need independent language review; no agent prose is automatically
            # treated as execution evidence or as a proven false statement.
            score=suite.score(item['case'],case,evidence=evidence,claims=None,execute=True)
            scores[name]={'case':item['case'],'arm':item['arm'],'repeat':item['repeat'],
                          'score':score,'observation':evidence,'chain_gaps':submission['chain_gaps'],
                          'action_count':len(submission['actions'])}
    return {'protocol':'PWS-BEHAVIOR-2','claims':'not reviewed','dynamic_oracle':'containerized execution required',
            'trials':scores,'limitations':['Seven tasks were known from an earlier pilot.',
            'No OS isolation or full trace of candidate agents; FIFO requester attribution is unknown.',
            'Each product test ran in a separate temporary copy inside the caller-provided sandbox.',
            'Any chain gap requires case-level caution; absence of an event is not proof of no execution.']}

def summary(result):
    arms={}
    for name,t in result['trials'].items():
        a=arms.setdefault(t['arm'],{'total':0,'product':{'pass':0,'fail':0,'inconclusive':0},
            'protected_fail':0,'observed_expected':0,'observed_unexpected':0,'observed_inconclusive':0,
            'chain_gaps':0,'action_count':0,'overall':{'pass':0,'fail':0,'inconclusive':0}})
        a['total']+=1;a['action_count']+=t['action_count'];a['chain_gaps']+=bool(t['chain_gaps'])
        checks=t['score']['checks'];a['product'][checks['product']['status']]+=1
        a['protected_fail']+=int(any(k.startswith('preserve:') and v['status']=='fail' for k,v in checks.items()))
        a['overall'][t['score']['outcome']]+=1
        for k,v in checks.items():
            if k.startswith('observed:'):
                dest={'pass':'observed_expected','fail':'observed_unexpected','inconclusive':'observed_inconclusive'}[v['status']]
                a[dest]+=1
    return {'protocol':result['protocol'],'trials':len(result['trials']),'arms':arms,'limitations':result['limitations']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=evaluate(a.archive);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (a.output/'summary.json').write_text(json.dumps(summary(result),ensure_ascii=False,indent=2)+'\n')
    print('PWS2_SUMMARY='+json.dumps(summary(result),ensure_ascii=False,separators=(',',':')))
