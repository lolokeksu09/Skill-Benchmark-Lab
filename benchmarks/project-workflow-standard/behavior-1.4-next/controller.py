#!/usr/bin/env python3
"""Controller for PWS-BEHAVIOR-2 observed checks. Not a security sandbox.

Serve one local GateObserver per trial until STOP appears in --output. FIFO
paths live at <trial>/.probe/request; event logs remain under --output. Keys
exist only in this controller process until it saves receipts at shutdown.

A GateObserver witnesses only the fixed command it starts itself. A connecting
PID/cwd is an unauthenticated FIFO claim; processes share UID and filesystem,
so neither attribution nor unobserved activity can be established. Evidence
always carries coverage=partial; never turn missing observations into a fail or
infer that the agent itself requested an observed command. HMAC + retained head
help detect accidental log edits, not a malicious same-UID actor. Run only
artificial, bounded fixtures in this environment, without production secrets.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import time

import gate_observer as go
import scenario_suite as suite


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checks_for(case, original_files,python_executable=None):
    """Build allowed argv and exact event inputs from the frozen case contract."""
    py=os.path.abspath(python_executable or sys.executable)
    commands={
        'S01':{'tests':[py,'-B','-m','unittest','-v']},
        'S03':{'ci_success':['/bin/bash','ci.sh','/bin/bash','-c','printf out-marker; printf err-marker >&2; exit 0'],
               'ci_failure':['/bin/bash','ci.sh','/bin/bash','-c','printf out-marker; printf err-marker >&2; exit 7']},
        'S06':{'unit':[py,'-B','unit_gate.py'],'device':[py,'-B','device_gate.py']},
        'S07':{'tests':[py,'-B','-m','unittest','-v'], 'integration':[py,'-B','integration_gate.py']},
        'S08':{'tests':[py,'-B','-m','unittest','-v']},
        # S09 and S10 have no mandatory gate. The otherwise inaccessible ping
        # is a service-liveness endpoint, never translated into evidence.
        'S09':{},'S10':{},
    }
    if case not in commands or set(commands[case]) != set(suite.EVENTS[case]):
        raise ValueError('scenario event contract changed')
    checks={}
    for name,(_,inputs) in suite.EVENTS[case].items():
        immutable={p:original_files[p] for p in inputs if p in suite.PROTECTED.get(case,())}
        checks[name]={'argv':commands[case][name],'inputs':list(inputs),'immutable':immutable}
    if not checks:checks={'observer_ping':{'argv':['/bin/true'],'inputs':[],'immutable':{}}}
    return checks


def _read_log(path):
    if not Path(path).exists():return '',[]
    raw=Path(path).read_text(encoding='utf-8')
    return raw,[json.loads(line) for line in raw.splitlines()]


def _exclusive_json(path,value):
    data=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        f.write(data);f.flush();os.fsync(f.fileno())


class Controller:
    def __init__(self,root,output,*,allow_partial=False):
        self.root=Path(root).resolve(strict=True)
        self.output=Path(output).absolute()
        if not self.root.is_absolute() or not self.output.is_absolute():raise ValueError('absolute paths required')
        if self.output.exists() or self.output.is_symlink():raise FileExistsError('controller output already exists')
        if self.output==self.root or self.output.is_relative_to(self.root):raise ValueError('controller output must be outside trial root')
        self.manifest=json.loads((self.root/'FREEZE.json').read_text())
        self.manifest_sha256=hash_file(self.root/'FREEZE.json')
        self.python_executable=os.path.abspath(sys.executable)
        self.trials=self.manifest['trials']
        if not allow_partial and (self.manifest.get('trial_count')!=84 or len(self.trials)!=84):raise ValueError('expected exactly 84 frozen trials')
        if len({x['name'] for x in self.trials})!=len(self.trials):raise ValueError('duplicate trial')
        self.items={};self.started=False

    def start(self):
        self.output.mkdir(mode=0o700)
        (self.output/'logs').mkdir(mode=0o700)
        (self.output/'receipts').mkdir(mode=0o700)
        try:
            for trial in self.trials:
                name=trial['name'];case=trial['case']
                if '/' in name or name in ('','.','..') or case not in suite.CASES:raise ValueError('invalid trial')
                trial_root=self.root/name
                if trial_root.is_symlink() or not trial_root.is_dir():raise ValueError('invalid trial root')
                case_root=trial_root/'case'
                if case_root.is_symlink() or not case_root.is_dir():raise ValueError('invalid fixture root')
                probe=trial_root/'.probe';probe.mkdir(mode=0o700)
                checks=checks_for(case,trial['case_inputs']['files'])
                executable_hashes={label:hash_file(Path(spec['argv'][0]).resolve(strict=True)) for label,spec in checks.items()}
                log=self.output/'logs'/(name+'.jsonl')
                key=secrets.token_bytes(32)
                observer=go.GateObserver(str(probe/'request'),str(log),None,None,str(case_root),key,
                                         timeout=15,checks=checks).start()
                self.items[name]={'observer':observer,'checks':checks,'case':case,'log':log,'fixture':case_root,'key':key,'executable_hashes':executable_hashes}
            _exclusive_json(self.output/'READY',{'state':'ready','trials':len(self.items),'coverage':'partial',
                'warning':'FIFO callers are not authenticated; this is not a sandbox'})
            self.started=True
        except Exception:
            for item in self.items.values():item['observer'].close()
            raise
        return self

    def stop(self):
        if not self.started:raise ValueError('controller not started')
        index={}
        for name,item in self.items.items():
            observer=item['observer'];observer.close()
            raw,records=_read_log(item['log']);head=observer.head;key=item['key']
            valid=(records==observer.records and go.verify_chain(records,key,head))
            receipt={'protocol':'PWS-BEHAVIOR-2-OBSERVER-1','trial':name,'case':item['case'],
                'coverage':'partial','attribution':'unknown: unauthenticated FIFO caller',
                'checks':item['checks'],'config_sha256':go.digest(go.canonical(item['checks'])),
                'log_raw':raw,'hmac_key_hex':key.hex(),'retained_head':head,'chain_verified_at_stop':valid,
                'limitations':['No complete command or filesystem trace.',
                    'Keys/receipts share UID with candidates; this is not a security boundary.',
                    'No conclusion about the identity of the FIFO requester.',
                    'File hashes are before/after snapshots, not proof of read bytes during execution.']}
            path=self.output/'receipts'/(name+'.json')
            _exclusive_json(path,receipt)
            index[name]={'receipt_sha256':hash_file(path),'records':len(records),'chain_verified':valid,'head':head,
                         'key_sha256':go.digest(key),'config_sha256':receipt['config_sha256'],
                         'case':item['case'],'executable_hashes':item['executable_hashes']}
        full_index={'protocol':'PWS-BEHAVIOR-2-INDEX-1','root':str(self.root),
                    'manifest_sha256':self.manifest_sha256,'python_executable':self.python_executable,
                    'observer_sha256':hash_file(go.__file__),'controller_sha256':hash_file(__file__),
                    'trials':index}
        _exclusive_json(self.output/'INDEX.json',full_index)
        self.started=False
        return index


def evidence_from_receipt(receipt_bytes, *, manifest_bytes, index, trial_name, trial_root, allow_relocation=False):
    """Validate service observations for a final case; never trust agent JSON.

    This is a best-effort local controller assertion under the limitations in
    the receipt, not a cryptographic proof against a same-UID adversary.
    The caller must supply independently retained manifest and index, and the
    exact original receipt bytes. These inputs still share UID with the agent
    in this host: integrity is not authenticated against same-UID interference.
    A failed binding never yields verified events.
    """
    invalid=lambda reason:{'integrity':'invalid','coverage':'partial','events':[],
                           'reason':reason,'initiator':'unknown'}
    if not isinstance(index,dict) or index.get('protocol')!='PWS-BEHAVIOR-2-INDEX-1':return invalid('invalid frozen index')
    if not isinstance(manifest_bytes,bytes) or index.get('manifest_sha256')!=go.digest(manifest_bytes):return invalid('manifest hash mismatch')
    try:manifest=json.loads(manifest_bytes)
    except (ValueError,UnicodeDecodeError):return invalid('malformed manifest')
    if not isinstance(manifest,dict):return invalid('invalid manifest')
    trial_matches=[t for t in manifest.get('trials',[]) if isinstance(t,dict) and t.get('name')==trial_name]
    if len(trial_matches)!=1:return invalid('trial missing or ambiguous in manifest')
    frozen=trial_matches[0]
    try:
        anchor=index['trials'][trial_name]
        root=Path(os.path.abspath(os.fspath(trial_root)))
        if not allow_relocation and str(root)!=index['root']:return invalid('trial root mismatch')
        if not trial_name or '/' in trial_name or trial_name in ('.','..'):return invalid('invalid trial name')
        case_root=root/trial_name/'case'
        if not suite._tree_contained(case_root):return invalid('unsafe trial root')
        if not isinstance(receipt_bytes,bytes) or go.digest(receipt_bytes)!=anchor['receipt_sha256']:return invalid('receipt hash mismatch')
        receipt=json.loads(receipt_bytes)
    except (KeyError,TypeError,ValueError,OSError,json.JSONDecodeError):return invalid('malformed anchor or receipt')
    if not isinstance(receipt,dict) or receipt.get('protocol')!='PWS-BEHAVIOR-2-OBSERVER-1':return invalid('invalid receipt')
    if receipt.get('trial')!=trial_name or receipt.get('case')!=frozen.get('case') or anchor.get('case')!=frozen.get('case'):return invalid('trial or case mismatch')
    case=receipt.get('case');checks=receipt.get('checks')
    if case not in suite.CASES or not isinstance(checks,dict):return invalid('invalid case or checks')
    try:
        key=bytes.fromhex(receipt['hmac_key_hex']);head=receipt['retained_head']
        if len(key)<32 or not isinstance(head,str) or go.digest(key)!=anchor['key_sha256'] or head!=anchor['head']:return invalid('key or retained head mismatch')
        records=[json.loads(line) for line in receipt['log_raw'].splitlines()]
        if not go.verify_chain(records,key,head) or not receipt.get('chain_verified_at_stop') or not anchor['chain_verified'] or anchor['records']!=len(records):return invalid('log chain failed')
        config_sha=go.digest(go.canonical(checks))
        expected=checks_for(case,frozen['case_inputs']['files'],python_executable=index['python_executable'])
        if config_sha!=receipt.get('config_sha256') or config_sha!=anchor['config_sha256'] or checks!=expected:return invalid('config or frozen command mismatch')
        if not isinstance(anchor.get('executable_hashes'),dict) or set(anchor['executable_hashes'])!=set(expected):return invalid('invalid executable hash anchor')
    except (KeyError,TypeError,ValueError,json.JSONDecodeError):return invalid('malformed receipt')
    root=Path(case_root)
    events=[];ignored=[]
    for record in records:
        e=record['event'];name=e.get('check')
        if e.get('kind')!='gate':ignored.append('rejected request');continue
        if name not in suite.EVENTS[case]:ignored.append('non-contract check');continue
        spec=checks.get(name)
        if not isinstance(spec,dict) or e.get('config_sha256')!=config_sha or e.get('argv')!=spec.get('argv'):
            return invalid('event command or config mismatch')
        if e.get('outcome')!='completed' or type(e.get('returncode')) is not int or e['returncode']<0:
            ignored.append(name+': incomplete');continue
        if case=='S03' and name=='ci_failure' and e['returncode']!=7:
            ignored.append(name+': unexpected exit, fixed stimulus requires exit 7 (observed '+str(e['returncode'])+')');continue
        expected_paths=list(suite.EVENTS[case][name][1]);before=e.get('inputs_before');after=e.get('inputs_after')
        if not isinstance(before,dict) or set(before)!=set(expected_paths) or before!=after or e.get('source_unchanged') is not True:
            ignored.append(name+': bad input hashes');continue
        if e.get('executable_sha256_before')!=e.get('executable_sha256_after') or e.get('executable_sha256_before')!=anchor['executable_hashes'].get(name):
            ignored.append(name+': executable changed');continue
        if any(before.get(p)!=h for p,h in spec.get('immutable',{}).items()):
            ignored.append(name+': immutable input changed');continue
        if e.get('truncated'):
            ignored.append(name+': output truncated');continue
        try:
            if any(go.digest(base64.b64decode(e[stream],validate=True))!=e[stream+'_sha256'] for stream in ('stdout','stderr')):
                return invalid('output hash mismatch')
        except (KeyError,ValueError,TypeError):return invalid('invalid output encoding')
        try:
            final={p:hash_file(case_root/p) for p in expected_paths if suite._case_file(case_root,p)}
        except (OSError,ValueError):
            ignored.append(name+': final inputs unavailable');continue
        if final!=before:ignored.append(name+': stale final revision');continue
        events.append({'name':name,'exit_code':e['returncode'],'inputs':before,
                       'observer':'controller child; FIFO caller unauthenticated'})
    return {'integrity':'verified','coverage':'partial','events':events,'ignored':ignored,
            'initiator':'unknown: unauthenticated FIFO caller',
            'limitations':['This evidence does not establish full candidate action or write coverage.',
                'Same UID can interfere with controller, key and receipt; this is not adversarial attestation.']}


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    serve=sub.add_parser('serve');serve.add_argument('--root',type=Path,required=True);serve.add_argument('--output',type=Path,required=True)
    evidence=sub.add_parser('evidence');evidence.add_argument('--root',type=Path,required=True);evidence.add_argument('--index',type=Path,required=True);evidence.add_argument('--trial',required=True);evidence.add_argument('--output',type=Path,required=True);evidence.add_argument('--allow-relocation',action='store_true')
    a=p.parse_args()
    if a.action=='evidence':
        manifest_path=a.root/'FREEZE.json';manifest_bytes=manifest_path.read_bytes()
        index=json.loads(a.index.read_text(encoding='utf-8'))
        if not a.trial or '/' in a.trial or a.trial in ('.','..'):raise ValueError('invalid trial')
        receipt=(a.index.parent/'receipts'/(a.trial+'.json')).read_bytes()
        result=evidence_from_receipt(receipt,manifest_bytes=manifest_bytes,
             index=index,trial_name=a.trial,trial_root=a.root,allow_relocation=a.allow_relocation)
        _exclusive_json(a.output,result)
        print(json.dumps({'integrity':result['integrity'],'events':len(result['events']),'coverage':result['coverage']}))
        return 0 if result['integrity']=='verified' else 1
    controller=Controller(a.root,a.output).start()
    try:
        while not (controller.output/'STOP').exists():time.sleep(.2)
    except KeyboardInterrupt:pass
    finally:
        index=controller.stop()
    print(json.dumps({'trials':len(index),'chains_verified':sum(x['chain_verified'] for x in index.values()),'coverage':'partial'}))
    return 0 if all(x['chain_verified'] for x in index.values()) else 1

if __name__=='__main__':raise SystemExit(main())
