#!/usr/bin/env python3
"""Verify frozen source/input and compare isolated replay to saved CI result."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(value):return hashlib.sha256(value).hexdigest()
def verify(replay):
    raw=(HERE/'FREEZE.json').read_bytes();manifest=json.loads(raw)
    for name,expected in manifest['premeasurement_code_sha256'].items():
        if Path(name).name!=name or sha((HERE/name).read_bytes())!=expected:raise ValueError('premeasurement source changed: '+name)
    data=json.loads(gzip.decompress((HERE/'cohort.json.gz').read_bytes()))
    if base64.b64decode(data['freeze_b64'],validate=True)!=raw:raise ValueError('frozen input differs')
    if data['observer_index']['manifest_sha256']!=sha(raw):raise ValueError('observer index bound to different inputs')
    if len(data['trials'])!=84:raise ValueError('missing trial')
    for generated,saved in [('scores.json','CI-SCORES.JSON'),('summary.json','CI-SUMMARY.JSON')]:
        if json.loads((Path(replay)/generated).read_bytes())!=json.loads((HERE/saved).read_bytes()):raise ValueError('replay mismatch: '+generated)
    return {'trials':84,'frozen_sha256':sha(raw),'premeasurement_sources':len(manifest['premeasurement_code_sha256']),'saved_ci_replay':'match'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.replay)))
