#!/usr/bin/env python3
"""Deterministic saved-artifact replay; never launches models."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import receipts
import suite
import evaluate_v2

HERE=Path(__file__).resolve().parent
def main():
    frozen=json.loads((HERE/'receipts/FREEZE.json').read_text())
    for name in ['suite.py','PROTOCOL.md']:
        if suite.digest(HERE/name)!=frozen['files'][name]:raise ValueError('premeasurement source changed: '+name)
    for arm,files in frozen['instructions'].items():
        if suite.ARMS[arm] and suite.inventory(suite.SOURCES/suite.ARMS[arm])!=files:raise ValueError('instruction arm changed: '+arm)
    suite.selfcheck()
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_*.py','-v'])
    if r.returncode:raise SystemExit(r.returncode)
    index=json.loads((HERE/'receipts/INDEX.json').read_text())
    if len(index)!=12:raise ValueError('expected twelve actual saved trajectories')
    failures={k:v['integrity_failures'] for k,v in index.items() if not v['integrity_passed']}
    for name,meta in index.items():
        saved=receipts.read_gzip(HERE/'receipts'/(name+'.json.gz'))
        computed=receipts.recompute_integrity(saved,frozen['runs'][name])
        if computed!=saved['integrity']:raise ValueError('integrity audit differs: '+name)
        if [k for k,v in computed.items() if not v]!=meta['integrity_failures']:raise ValueError('integrity index differs: '+name)
        if all(computed.values())!=meta['integrity_passed']:raise ValueError('integrity summary differs: '+name)
    result=receipts.replay(HERE/'receipts')
    expected=json.loads((HERE/'RESULTS.json').read_text())
    if result!=expected:raise ValueError('saved results differ from frozen scorer replay')
    diagnostic=evaluate_v2.evaluate()
    if diagnostic!=json.loads((HERE/'DIAGNOSTIC-V2.json').read_text()):raise ValueError('diagnostic v2 replay differs')
    print(json.dumps({'protocol':result['protocol'],'trajectories':len(result['trajectories']),'applications':sum(v['total'] for v in result['trajectories'].values()),'primary_passed_tasks':sum(v['passed'] for v in result['trajectories'].values()),'integrity_audit':'reproduced, including recorded gaps','trajectories_with_recorded_gaps':len(failures),'agent_runs_started_by_this_replay':0},ensure_ascii=False))
if __name__=='__main__':main()
