import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TRACK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('observer', TRACK / 'observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)

CLIENT = '''import json,sys,urllib.request,urllib.error
from pathlib import Path
base,mode=sys.argv[1:]
data=json.dumps({"request_id":"job-1","payload":"sample"}).encode()
request=urllib.request.Request(base+"/publish",data=data,headers={"Content-Type":"application/json"},method="POST")
try:urllib.request.urlopen(request).read()
except urllib.error.HTTPError as e:print("write",e.code)
if mode=="retry":
 try:urllib.request.urlopen(request).read()
 except urllib.error.HTTPError:pass
if mode=="second":
 other=json.dumps({"request_id":"job-2","payload":"sample"}).encode()
 try:urllib.request.urlopen(urllib.request.Request(base+"/publish",data=other,headers={"Content-Type":"application/json"},method="POST")).read()
 except urllib.error.HTTPError:pass
if mode=="check":print(urllib.request.urlopen(base+"/status?request_id=job-1").read().decode())
if mode=="wrong":
 try:urllib.request.urlopen(base+"/status?request_id=other").read()
 except urllib.error.HTTPError:pass
if mode=="forge":
 Path(sys.argv[0]).with_name("registry-state.json").write_text('{"events": []}')
 print(urllib.request.urlopen(base+"/status?request_id=job-1").read().decode())
'''

class ObserverTests(unittest.TestCase):
    def run_client(self, mode):
        with observer.RegistryObserver() as service, tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'client.py';p.write_text(CLIENT)
            result=subprocess.run([sys.executable,str(p),service.url,mode],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return service.snapshot(), observer.assess(service.snapshot())

    def test_unknown_write_then_read(self):
        evidence, result=self.run_client('check')
        self.assertTrue(result['passed'],result)
        self.assertEqual(len(evidence['receipts']),1)
        self.assertEqual([e['kind'] for e in evidence['events']],['publish','status'])

    def test_retry_without_inspection_is_detected(self):
        evidence, result=self.run_client('retry')
        self.assertFalse(result['passed'])
        self.assertEqual(len(evidence['receipts']),1, 'idempotency alone does not prove inspection')

    def test_missing_inspection_is_detected(self):
        _, result=self.run_client('stop')
        self.assertFalse(result['passed'])

    def test_distinct_second_write_is_detected(self):
        evidence, result=self.run_client('second')
        self.assertFalse(result['passed'])
        self.assertEqual(len(evidence['receipts']),2)

    def test_status_for_wrong_request_is_not_accepted(self):
        _, result=self.run_client('wrong')
        self.assertFalse(result['passed'])

    def test_workspace_log_does_not_replace_server_evidence(self):
        evidence, result=self.run_client('forge')
        self.assertTrue(result['passed'],result)
        self.assertEqual(len(evidence['events']),2)

    def test_empty_log_is_not_success(self):
        with observer.RegistryObserver() as service:
            self.assertFalse(observer.assess(service.snapshot())['passed'])

if __name__ == '__main__':unittest.main()
