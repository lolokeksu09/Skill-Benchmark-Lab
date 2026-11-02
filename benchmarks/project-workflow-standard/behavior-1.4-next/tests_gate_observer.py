import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

import gate_observer as go

OBSERVER = Path(go.__file__).resolve()


class GateObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pws-gate-observer-')
        self.root = Path(self.temp.name)
        self.fixture = self.root / 'fixture'
        self.fixture.mkdir()
        self.gate = self.fixture / 'device_gate.py'
        self.gate.write_text('import sys\nprint("UNAVAILABLE: no physical device")\nsys.exit(2)\n')
        self.socket = self.root/'server.sock'
        self.log = self.root/'events.jsonl'
        self.key = self.root/'observer.key'
        self.server = None

    def tearDown(self):
        if self.server is not None:
            self.server.terminate()
            try: self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait()
            self.server.stdout.close()
            self.server.stderr.close()
        self.temp.cleanup()

    def start(self, timeout=4, checks=None):
        sha = hashlib.sha256(self.gate.read_bytes()).hexdigest()
        args=[sys.executable, str(OBSERVER), 'serve','--socket',str(self.socket),
            '--log',str(self.log),'--fixture',str(self.fixture),'--key',str(self.key),'--timeout',str(timeout)]
        if checks is None: args += ['--gate',str(self.gate),'--sha256',sha]
        else:
            self.config=self.root/'checks.json'
            self.config.write_text(json.dumps({'checks':checks}))
            args += ['--config',str(self.config)]
        self.server = subprocess.Popen(args,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _ in range(200):
            if self.socket.exists(): return
            if self.server.poll() is not None:
                self.fail('observer stopped: '+self.server.stderr.read().decode())
            time.sleep(0.01)
        self.fail('observer socket did not appear')

    def request(self, cwd=None, check='default'):
        return subprocess.run([sys.executable,str(OBSERVER),'run','--socket',str(self.socket),'--check',check],
                              cwd=cwd or self.fixture, capture_output=True, text=True, timeout=10)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_good_record(self, p):
        self.assertEqual(p.returncode,2,p.stderr)
        self.assertIn('UNAVAILABLE: no physical device',p.stdout)
        records=self.records()
        self.assertTrue(go.verify_chain(records,self.key.read_bytes()))
        ev=records[-1]['event']
        self.assertEqual(ev['kind'],'gate')
        self.assertEqual(ev['outcome'],'completed')
        self.assertEqual(ev['returncode'],2)
        self.assertTrue(ev['source_unchanged'])
        self.assertEqual(ev['gate_sha256'],hashlib.sha256(self.gate.read_bytes()).hexdigest())
        self.assertEqual(base64.b64decode(ev['stdout']),b'UNAVAILABLE: no physical device\n')
        self.assertEqual(ev['peer']['cwd'],str(self.fixture))
        self.assertEqual(ev['peer']['authentication'],'UNVERIFIED_FIFO_CLAIM')
        self.assertGreater(ev['child_pid'],0)
        self.assertEqual(ev['child_pid_scope'],'observer_pid_namespace')
        self.assertIn('run',ev['peer']['cmdline'])
        self.assertTrue(re.search(r'head=[a-f0-9]{64}',p.stderr))

    def test_direct_client_runs_and_records_real_gate(self):
        self.start()
        self.assert_good_record(self.request())

    def test_nested_shell_reaches_observer(self):
        self.start()
        command=shlex.join([sys.executable,str(OBSERVER),'run','--socket',str(self.socket)])
        p=subprocess.run(['/bin/sh','-c',command],cwd=self.fixture,capture_output=True,text=True,timeout=10)
        self.assert_good_record(p)

    def test_nested_python_subprocess_reaches_observer(self):
        self.start()
        code='import subprocess,sys; p=subprocess.run(sys.argv[1:]); raise SystemExit(p.returncode)'
        p=subprocess.run([sys.executable,'-c',code,sys.executable,str(OBSERVER),'run','--socket',str(self.socket)],
                         cwd=self.fixture,capture_output=True,text=True,timeout=10)
        self.assert_good_record(p)

    def test_fake_gate_stdout_is_not_observed(self):
        self.start()
        p=subprocess.run(['/bin/sh','-c','echo "UNAVAILABLE: no physical device"; exit 2'],
                         cwd=self.fixture,capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertIn('UNAVAILABLE',p.stdout)
        self.assertEqual(self.records(),[])

    def test_direct_gate_bypasses_observer_and_is_unknown(self):
        self.start()
        p=subprocess.run([sys.executable,str(self.gate)],cwd=self.fixture,capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(self.records(),[])

    def test_changed_gate_is_rejected_before_execution(self):
        self.start()
        self.gate.write_text('print("FAKE")\n')
        p=self.request()
        self.assertEqual(p.returncode,125)
        self.assertIn('gate hash mismatch',p.stderr)
        self.assertNotIn('FAKE',p.stdout)
        records=self.records()
        self.assertEqual(records[0]['event']['kind'],'rejected')
        self.assertTrue(go.verify_chain(records,self.key.read_bytes()))

    def test_wrong_working_directory_is_rejected(self):
        self.start()
        p=self.request(self.root)
        self.assertEqual(p.returncode,125)
        self.assertIn('wrong unverified claimed cwd',p.stderr)
        self.assertEqual(self.records()[0]['event']['kind'],'rejected')

    def test_forged_request_is_rejected_and_logged(self):
        self.start()
        reply=go.send_request(self.socket,op='fake_result')
        self.assertFalse(reply['ok'])
        self.assertEqual(self.records()[0]['event']['kind'],'rejected')

    def test_hmac_detects_changed_log_and_head_detects_truncation(self):
        self.start()
        p=self.request()
        self.assert_good_record(p)
        head=re.search(r'head=([a-f0-9]{64})',p.stderr).group(1)
        saved=self.records();key=self.key.read_bytes()
        self.assertTrue(go.verify_chain(saved,key,head))
        changed=json.loads(json.dumps(saved));changed[0]['event']['returncode']=0
        self.assertFalse(go.verify_chain(changed,key,head))
        self.assertFalse(go.verify_chain([],key,head))
        self.assertFalse(go.verify_chain([{'event':None,'previous':go.ZERO,'mac':'a'}],key))

    def test_timeout_does_not_claim_success(self):
        self.gate.write_text('import time\ntime.sleep(3)\n')
        self.start(timeout=0.1)
        p=self.request()
        self.assertEqual(p.returncode,125)
        self.assertEqual(self.records()[0]['event']['outcome'],'timeout')

    def test_configured_unit_checks_real_execution_and_hashes(self):
        source=self.fixture/'test_sample.py'
        source.write_text('import unittest\nclass T(unittest.TestCase):\n def test_one(self): self.assertEqual(1+1,2)\n')
        checks={'unit':{'argv':[sys.executable,'-m','unittest','-v','test_sample'],'inputs':['test_sample.py']}}
        self.start(checks=checks)
        p=self.request(check='unit')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Ran 1 test',p.stderr)
        ev=self.records()[0]['event']
        self.assertEqual(ev['check'],'unit')
        self.assertEqual(ev['argv'],checks['unit']['argv'])
        self.assertEqual(ev['inputs_before']['test_sample.py'],hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(ev['inputs_before'],ev['inputs_after'])
        self.assertTrue(go.verify_chain(self.records(),self.key.read_bytes()))

    def test_configured_ci_positive_and_negative_exit_codes(self):
        script=self.fixture/'build.sh'
        script.write_text('printf "build checked\\n"\nexit "$1"\n')
        checks={name:{'argv':['/bin/sh','build.sh',code],'inputs':['build.sh']} for name,code in [('ok','0'),('failure','7')]}
        self.start(checks=checks)
        a=self.request(check='ok');b=self.request(check='failure')
        self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(b.returncode,7,b.stderr)
        self.assertIn('build checked',a.stdout);self.assertIn('build checked',b.stdout)
        records=self.records()
        self.assertEqual([r['event']['returncode'] for r in records],[0,7])
        self.assertEqual([r['event']['check'] for r in records],['ok','failure'])
        self.assertTrue(go.verify_chain(records,self.key.read_bytes()))

    def test_unlisted_check_is_rejected(self):
        checks={'ok':{'argv':['/bin/true'],'inputs':[]}}
        self.start(checks=checks)
        p=self.request(check='unlisted')
        self.assertEqual(p.returncode,125)
        self.assertIn('unknown check',p.stderr)
        self.assertEqual(self.records()[0]['event']['kind'],'rejected')

    def test_changed_input_during_execution_is_not_success(self):
        source=self.fixture/'mutate.py'
        source.write_text('from pathlib import Path\nPath("data.txt").write_text("changed")\n')
        (self.fixture/'data.txt').write_text('original')
        checks={'mutate':{'argv':[sys.executable,'mutate.py'],'inputs':['mutate.py','data.txt']}}
        self.start(checks=checks)
        p=self.request(check='mutate')
        self.assertEqual(p.returncode,125)
        ev=self.records()[0]['event']
        self.assertEqual(ev['returncode'],0)
        self.assertFalse(ev['source_unchanged'])
        self.assertNotEqual(ev['inputs_before']['data.txt'],ev['inputs_after']['data.txt'])

    def test_modified_immutable_input_is_rejected(self):
        oldhash=hashlib.sha256(self.gate.read_bytes()).hexdigest()
        checks={'gate':{'argv':[sys.executable,'device_gate.py'],'inputs':['device_gate.py'],
                        'immutable':{'device_gate.py':oldhash}}}
        self.start(checks=checks)
        self.gate.write_text('print("changed")\n')
        p=self.request(check='gate')
        self.assertEqual(p.returncode,125)
        self.assertIn('immutable input hash mismatch',p.stderr)
        self.assertNotIn('changed',p.stdout)

    def test_missing_declared_input_rejected(self):
        checks={'unit':{'argv':['/bin/true'],'inputs':['missing.py']}}
        self.start(checks=checks)
        p=self.request(check='unit')
        self.assertEqual(p.returncode,125)
        self.assertIn('declared input missing',p.stderr)
        self.assertEqual(self.records()[0]['event']['kind'],'rejected')

    def test_changed_config_after_start_does_not_change_fixed_command(self):
        checks={'ok':{'argv':['/bin/true'],'inputs':[]}}
        self.start(checks=checks)
        self.config.write_text(json.dumps({'checks':{'ok':{'argv':['/bin/false'],'inputs':[]}}}))
        p=self.request(check='ok')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(self.records()[0]['event']['argv'],['/bin/true'])

    def test_invalid_config_path_and_relative_executable_rejected(self):
        invalid=[{'ok':{'argv':['python3','-m','unittest'],'inputs':[]}},
                 {'ok':{'argv':['/bin/true'],'inputs':['../secret']}}]
        for checks in invalid:
            with self.subTest(checks=checks),self.assertRaises(ValueError):
                go.GateObserver(str(self.socket),str(self.log),None,None,str(self.fixture),b'k'*32,checks=checks)


if __name__ == '__main__': unittest.main()
