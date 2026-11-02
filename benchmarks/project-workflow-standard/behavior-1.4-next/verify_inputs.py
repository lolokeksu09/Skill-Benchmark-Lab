#!/usr/bin/env python3
"""Reject changed fixture inputs before model runs. This is not an OS sandbox."""
import argparse
import hashlib
import json
from pathlib import Path
import scenario_suite as suite

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_trial(root,item):
    path=Path(root)/item['name'];case=path/'case';errors=[]
    if not suite._tree_contained(case):errors.append('unsafe case path or symlink')
    if suite.inventory(case)!=item['case_inputs']['files']:errors.append('case inputs differ')
    try:
        if suite.git(case,'rev-parse','HEAD')!=item['case_inputs']['head']:errors.append('HEAD differs')
        if suite.git(case,'diff')!=item['case_inputs']['dirty_diff']:errors.append('dirty diff differs')
    except Exception:errors.append('Git metadata unavailable')
    for rel,key in [('RUN_TASK.md','run_task_sha256'),('AVAILABLE_CHECKS.md','available_checks_sha256')]:
        try:
            if sha(path/rel)!=item[key]:errors.append(rel+' differs')
        except (OSError,KeyError):errors.append(rel+' missing')
    for rel,want in item.get('harness_hashes',{}).items():
        try:
            if sha(path/'_harness'/rel)!=want:errors.append('harness differs: '+rel)
        except OSError:errors.append('harness missing: '+rel)
    for rel,want in item['instruction_hashes'].items():
        try:
            p=path/rel
            if p.is_symlink() or sha(p)!=want:errors.append('instruction differs: '+rel)
        except OSError:errors.append('instruction missing: '+rel)
    return errors

def verify(root):
    root=Path(root);manifest=json.loads((root/'FREEZE.json').read_text(encoding='utf-8'))
    failures={}
    if manifest.get('trial_count')!=84 or len(manifest.get('trials',[]))!=84:failures['manifest']=['wrong trial count']
    names=[t['name'] for t in manifest['trials']]
    if len(names)!=len(set(names)):failures['duplicates']=['duplicate trial names']
    for name,want in manifest.get('premeasurement_code_sha256',{}).items():
        try:
            if sha(HERE/name)!=want:failures.setdefault('source',[]).append(name+' differs')
        except OSError:failures.setdefault('source',[]).append(name+' missing')
    for item in manifest['trials']:
        errors=verify_trial(root,item)
        if errors:failures[item['name']]=errors
    return {'pass':not failures,'trial_count':len(names),'freeze_sha256':sha(root/'FREEZE.json'),'failures':failures}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    r=verify(a.root);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
