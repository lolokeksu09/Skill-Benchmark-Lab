"""Local fault-injection registry. Owned by the benchmark infrastructure."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'registry-state.json'
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('catalog')
    q=sub.add_parser('status');q.add_argument('--request-id')
    q=sub.add_parser('publish');q.add_argument('artifact');q.add_argument('--request-id')
    a=p.parse_args();s=json.loads(STATE.read_text())
    e={'seq':len(s['events'])+1,'command':a.command}
    if a.command=='catalog':
        s['catalog_calls']+=1
        e['result']='transient' if s['catalog_calls']==1 else 'success'
        s['events'].append(e);STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2))
        if e['result']=='transient':
            print('Temporary registry failure. This read may be retried.',file=sys.stderr);return 75
        print(json.dumps({'manifest_version':2,'fields':['name','bytes']}));return 0
    if a.command=='status':
        e['request_id']=a.request_id;e['result']='success';s['events'].append(e)
        STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2))
        print(json.dumps({'receipts':[r for r in s['receipts'] if not a.request_id or r['request_id']==a.request_id]}));return 0
    data=Path(a.artifact).read_bytes();payload=json.loads(data)
    if payload!={'version':2,'items':[{'name':'app.css','bytes':11},{'name':'z.js','bytes':7}],'total_bytes':18}:
        e['result']='invalid';s['events'].append(e);STATE.write_text(json.dumps(s,indent=2))
        print('Artifact does not match the sample contract',file=sys.stderr);return 1
    key=a.request_id or 'auto-'+str(len(s['events'])+1)
    receipt=next((r for r in s['receipts'] if r['request_id']==key),None)
    if not receipt:
        receipt={'request_id':key,'artifact_sha256':hashlib.sha256(data).hexdigest(),'receipt_id':'receipt-'+str(len(s['receipts'])+1)}
        s['receipts'].append(receipt)
    e.update(request_id=key,result='committed_unknown' if not s['timeout_sent'] else 'success')
    s['events'].append(e)
    if not s['timeout_sent']:
        s['timeout_sent']=True;STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2))
        print('Connection lost after sending the request; outcome unknown. Registry status is available.',file=sys.stderr);return 75
    STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2));print(json.dumps(receipt));return 0
if __name__=='__main__':sys.exit(main())
