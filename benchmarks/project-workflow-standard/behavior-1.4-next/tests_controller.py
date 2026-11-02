import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

import controller
import gate_observer as go
import scenario_suite as suite

CLIENT=Path(go.__file__).resolve()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='pws-controller-test-')
        self.base=Path(self.tmp.name);self.root=self.base/'trials';self.root.mkdir()
        self.output=self.base/'controller'
        self.control=None

    def tearDown(self):
        if self.control is not None and self.control.started:self.control.stop()
        self.tmp.cleanup()

    def setup_case(self,case):
        self.name=case+'-control-r1';trial=self.root/self.name;trial.mkdir()
        original=suite.init_case(trial/'case',case,git_init=False)
        self.case=trial/'case'
        self.manifest={'protocol':'PWS-BEHAVIOR-2','trial_count':1,
            'trials':[{'name':self.name,'case':case,'arm':'control','repeat':1,'case_inputs':original}]}
        (self.root/'FREEZE.json').write_text(json.dumps(self.manifest,sort_keys=True))
        self.control=controller.Controller(self.root,self.output,allow_partial=True).start()
        return self.case

    def request(self,check,nested=False):
        args=[sys.executable,str(CLIENT),'run','--socket',str(self.root/self.name/'.probe/request'),'--check',check]
        if nested:args=['/bin/sh','-c',shlex.join(args)]
        return subprocess.run(args,cwd=self.case,capture_output=True,text=True,timeout=20)

    def stop(self):
        self.control.stop();self.control=None
        self.index=json.loads((self.output/'INDEX.json').read_text())
        self.receipt_path=self.output/'receipts'/(self.name+'.json')
        self.receipt=self.receipt_path.read_bytes()

    def evidence(self,raw=None,*,index=None,manifest=None,manifest_hash=None,name=None,root=None):
        manifest_bytes=(json.dumps(manifest,sort_keys=True).encode() if manifest is not None else (self.root/'FREEZE.json').read_bytes())
        idx=copy.deepcopy(index or self.index)
        if manifest_hash is not None:idx['manifest_sha256']=manifest_hash
        return controller.evidence_from_receipt(raw if raw is not None else self.receipt,
            manifest_bytes=manifest_bytes,index=idx,trial_name=name or self.name,trial_root=root or self.root)

    def test_real_unit_and_device_exits_bound_to_inputs(self):
        self.setup_case('S06')
        self.assertEqual(self.request('unit').returncode,0)
        self.assertEqual(self.request('device',nested=True).returncode,2)
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['coverage'],'partial')
        self.assertEqual([(x['name'],x['exit_code']) for x in ev['events']],[('unit',0),('device',2)])
        self.assertIn('unknown',ev['initiator'])
        self.assertEqual(set(ev['events'][1]['inputs']),set(suite.EVENTS['S06']['device'][1]))

    def test_ci_success_and_failure_exact_status(self):
        self.setup_case('S03');(self.case/'ci.sh').write_text('#!/usr/bin/env bash\nset -eo pipefail\n"$@" 2>&1 | tee build.log\n')
        self.assertEqual(self.request('ci_success').returncode,0)
        self.assertEqual(self.request('ci_failure',nested=True).returncode,7)
        self.stop();ev=self.evidence()
        self.assertEqual([(x['name'],x['exit_code']) for x in ev['events']],[('ci_success',0),('ci_failure',7)])

    def test_signalled_ci_failure_is_unknown_not_nonzero_success(self):
        self.setup_case('S03');(self.case/'ci.sh').write_text('kill -KILL $$\n')
        self.assertEqual(self.request('ci_failure').returncode,125)
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['events'],[])
        self.assertTrue(any('incomplete' in x for x in ev['ignored']))
        raw=json.loads(self.receipt)['log_raw'];event=json.loads(raw)['event']
        self.assertEqual(event['returncode'],-9)

    def test_wrong_nonzero_exit_for_fixed_ci_stimulus_is_not_accepted(self):
        self.setup_case('S03');(self.case/'ci.sh').write_text('exit 1\n')
        self.assertEqual(self.request('ci_failure').returncode,1)
        self.stop();ev=self.evidence()
        self.assertEqual(ev['events'],[])
        self.assertTrue(any('requires exit 7' in x for x in ev['ignored']))

    def test_unknown_check_and_forged_print_do_not_create_evidence(self):
        self.setup_case('S06')
        fake=subprocess.run(['/bin/sh','-c','echo "UNAVAILABLE: physical device absent"; exit 2'],cwd=self.case,capture_output=True,text=True)
        self.assertEqual(fake.returncode,2)
        self.assertEqual(self.request('fake').returncode,125)
        (self.case/'RESULT.json').write_text('{"passed":true,"event":"device","exit":2}')
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['events'],[])

    def test_direct_unobserved_run_is_not_evidence(self):
        self.setup_case('S06')
        run=subprocess.run([sys.executable,'device_gate.py'],cwd=self.case,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['events'],[])

    def test_final_revision_must_match_observed_input(self):
        self.setup_case('S01')
        self.assertNotEqual(self.request('tests').returncode,0)
        with (self.case/'table.py').open('a') as f:f.write('\n# changed after test\n')
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['events'],[])
        self.assertTrue(any('stale final revision' in x for x in ev['ignored']))

    def test_modified_immutable_gate_is_rejected(self):
        self.setup_case('S06');(self.case/'device_gate.py').write_text('print("fake")\n')
        p=self.request('device');self.assertEqual(p.returncode,125)
        self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['events'],[])

    def test_receipt_tampering_and_missing_anchor_are_rejected(self):
        self.setup_case('S06');self.request('unit');self.stop()
        obj=json.loads(self.receipt);obj['log_raw']=obj['log_raw'].replace('unit_gate.py','fake_gate.py')
        altered=json.dumps(obj).encode();self.assertEqual(self.evidence(altered)['integrity'],'invalid')
        ix=copy.deepcopy(self.index);del ix['trials'][self.name]['key_sha256']
        self.assertEqual(self.evidence(index=ix)['integrity'],'invalid')
        self.assertEqual(self.evidence(manifest_hash='0'*64)['integrity'],'invalid')

    def test_self_signed_forgery_and_mutated_config_fail_frozen_contract(self):
        self.setup_case('S06');self.request('device');self.stop()
        obj=json.loads(self.receipt);key=bytes.fromhex(obj['hmac_key_hex'])
        record=json.loads(obj['log_raw']);event=record['event']
        obj['checks']['device']['argv']=['/bin/true']
        obj['config_sha256']=go.digest(go.canonical(obj['checks']))
        event['argv']=['/bin/true'];event['config_sha256']=obj['config_sha256']
        body={'event':event,'previous':go.ZERO}
        import hmac
        forged=dict(body,mac=hmac.new(key,go.canonical(body),hashlib.sha256).hexdigest())
        obj['log_raw']=go.canonical(forged).decode()+'\n';obj['retained_head']=go.digest(go.canonical(forged))
        raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
        idx=copy.deepcopy(self.index);a=idx['trials'][self.name]
        # Even if a mutable receipt-hash/head/config anchor were replaced, the
        # frozen case contract still rejects an arbitrary selected command.
        a['receipt_sha256']=go.digest(raw);a['head']=obj['retained_head'];a['config_sha256']=obj['config_sha256']
        self.assertEqual(self.evidence(raw,index=idx)['integrity'],'invalid')

    def test_forged_executable_digest_never_becomes_event(self):
        self.setup_case('S06');self.request('device');self.stop()
        obj=json.loads(self.receipt);key=bytes.fromhex(obj['hmac_key_hex']);r=json.loads(obj['log_raw'])
        r['event']['executable_sha256_before']='a'*64;r['event']['executable_sha256_after']='a'*64
        import hmac
        body={'event':r['event'],'previous':go.ZERO};r=dict(body,mac=hmac.new(key,go.canonical(body),hashlib.sha256).hexdigest())
        obj['log_raw']=go.canonical(r).decode()+'\n';obj['retained_head']=go.digest(go.canonical(r))
        raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();idx=copy.deepcopy(self.index)
        a=idx['trials'][self.name];a['receipt_sha256']=go.digest(raw);a['head']=obj['retained_head']
        ev=self.evidence(raw,index=idx);self.assertEqual(ev['events'],[])
        self.assertTrue(any('executable changed' in x for x in ev['ignored']))

    def test_trial_identity_root_and_case_are_bound(self):
        self.setup_case('S06');self.request('unit');self.stop()
        self.assertEqual(self.evidence(name='S06-rc4-r3')['integrity'],'invalid')
        self.assertEqual(self.evidence(root=self.base)['integrity'],'invalid')
        fake=copy.deepcopy(self.manifest);fake['trials'][0]['case']='S07'
        self.assertEqual(self.evidence(manifest=fake)['integrity'],'invalid')

    def test_no_gate_scenarios_still_produce_partial_empty_evidence(self):
        self.setup_case('S10');self.stop();ev=self.evidence()
        self.assertEqual(ev['integrity'],'verified');self.assertEqual(ev['coverage'],'partial');self.assertEqual(ev['events'],[])


if __name__=='__main__':unittest.main()
