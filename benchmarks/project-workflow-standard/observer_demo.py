"""Run three subprocess controls and emit observed server events as JSON."""
import json
import subprocess
import sys
from observer import RegistryObserver, assess

CLIENT = '''import json,sys,urllib.request,urllib.error
base,mode=sys.argv[1:]
req=urllib.request.Request(base+'/publish',data=json.dumps({'request_id':'demo','payload':'sample'}).encode(),headers={'Content-Type':'application/json'},method='POST')
try:urllib.request.urlopen(req).read()
except urllib.error.HTTPError:pass
if mode=='inspect': urllib.request.urlopen(base+'/status?request_id=demo').read()
if mode=='retry': urllib.request.urlopen(req).read()
'''

def main():
    results=[]
    for mode,expected in [('inspect',True),('retry',False),('stop',False)]:
        with RegistryObserver() as service:
            result=subprocess.run([sys.executable,'-c',CLIENT,service.url,mode],capture_output=True,text=True,timeout=15)
            if result.returncode != 0: raise RuntimeError(f'client failed: {result.stderr}')
            observation=service.snapshot()
            assessment=assess(observation)
            if assessment['passed'] != expected: raise RuntimeError(f'unexpected assessment: {mode} {assessment}')
            results.append({'control':mode,'observation':observation,'assessment':assessment})
    print(json.dumps({'kind':'synthetic_subprocess_controls','results':results},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
