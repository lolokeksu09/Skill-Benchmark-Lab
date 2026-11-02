#!/usr/bin/env python3
"""Package already-captured model results and observer receipts without scoring."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

def sha(value):return hashlib.sha256(value).hexdigest()
def enc(value):return base64.b64encode(value).decode()
def build(root,observers,checkpoints,output):
    root=Path(root);observers=Path(observers);checkpoints=Path(checkpoints)
    index=json.loads((observers/'INDEX.json').read_text());mb=(root/'FREEZE.json').read_bytes();manifest=json.loads(mb)
    if sha(mb)!=index['manifest_sha256'] or len(manifest['trials'])!=84:raise ValueError('freeze mismatch')
    trials={}
    for item in manifest['trials']:
        name=item['name'];candidate=(checkpoints/(name+'.json.gz')).read_bytes();receipt=(observers/'receipts'/(name+'.json')).read_bytes()
        if sha(receipt)!=index['trials'][name]['receipt_sha256']:raise ValueError('observer receipt hash mismatch: '+name)
        if json.loads(gzip.decompress(candidate))['name']!=name:raise ValueError('candidate identity mismatch')
        trials[name]={'candidate_sha256':sha(candidate),'candidate_gzip_b64':enc(candidate),'observer_receipt_b64':enc(receipt)}
    body={'protocol':'PWS-BEHAVIOR-2-RAW','freeze_b64':enc(mb),'observer_index':index,'trials':trials}
    value=gzip.compress(json.dumps(body,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode(),mtime=0)
    with Path(output).open('xb') as f:f.write(value)
    return {'trials':len(trials),'bytes':len(value),'sha256':sha(value)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--observers',required=True);p.add_argument('--checkpoints',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(build(a.root,a.observers,a.checkpoints,a.output)))
