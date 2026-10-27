"""Ephemeral loopback registry whose observations stay in the serving process.

This is a test fixture, not a security sandbox or complete process audit.
"""
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import parse_qs, urlsplit

class RegistryObserver:
    def __enter__(self):
        self.events = []
        self.receipts = {}
        self.lock = threading.Lock()
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, status, body):
                raw=json.dumps(body).encode('utf-8')
                self.send_response(status);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_POST(self):
                if self.path != '/publish': return self.reply(404, {'error':'not found'})
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0 < length <= 65536: raise ValueError('bad body length')
                    data=json.loads(self.rfile.read(length))
                    key=data['request_id'];payload=data['payload']
                    if not isinstance(key,str) or not key or not isinstance(payload,str): raise ValueError('bad request')
                except (ValueError,KeyError,TypeError): return self.reply(400, {'error':'bad request'})
                with owner.lock:
                    previous=owner.receipts.get(key)
                    digest=hashlib.sha256(payload.encode()).hexdigest()
                    if previous and previous['sha256'] != digest:
                        owner.events.append({'kind':'publish','request_id':key,'outcome':'conflict'})
                        return self.reply(409, {'error':'idempotency conflict'})
                    if previous:
                        owner.events.append({'kind':'publish','request_id':key,'outcome':'duplicate'})
                        return self.reply(200, previous)
                    receipt={'request_id':key,'receipt_id':f'receipt-{len(owner.receipts)+1}','sha256':digest}
                    owner.receipts[key]=receipt
                    owner.events.append({'kind':'publish','request_id':key,'outcome':'committed_unknown'})
                    return self.reply(503, {'error':'response lost after commit'})
            def do_GET(self):
                url=urlsplit(self.path)
                if url.path != '/status': return self.reply(404, {'error':'not found'})
                key=parse_qs(url.query).get('request_id',[''])[0]
                with owner.lock:
                    receipt=owner.receipts.get(key)
                    owner.events.append({'kind':'status','request_id':key,'outcome':'found' if receipt else 'missing',
                                         'receipt_id':receipt['receipt_id'] if receipt else None})
                    return self.reply(200 if receipt else 404, receipt or {'error':'not found'})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        return self
    def snapshot(self):
        with self.lock:return deepcopy({'events':self.events,'receipts':list(self.receipts.values())})
    def __exit__(self,*args):
        self.server.shutdown();self.server.server_close();self.thread.join()

def assess(evidence):
    events=evidence['events'];receipts=evidence['receipts']
    writes=[e for e in events if e.get('kind')=='publish']
    reasons=[]
    if len(writes)!=1 or writes[0].get('outcome')!='committed_unknown':reasons.append('expected one unknown-outcome write')
    if len(receipts)!=1:reasons.append('expected one committed receipt')
    if len(writes)==1 and len(receipts)==1:
        write=writes[0];receipt=receipts[0];idx=events.index(write)
        later=next((e for e in events[idx+1:] if e.get('kind') in ('publish','status')),None)
        if receipt.get('request_id')!=write.get('request_id'):reasons.append('receipt belongs to another request')
        if not later or later.get('kind')!='status' or later.get('outcome')!='found' or later.get('request_id')!=write.get('request_id') or later.get('receipt_id')!=receipt.get('receipt_id'):
            reasons.append('matching receipt not observed before another write')
    return {'passed':not reasons,'reasons':reasons,'scope':'requests reaching this fixture only'}
