"""Process-separated local fixture using a FIFO. Not a security sandbox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import sys
import tempfile
import time
from observer import assess

def serve(pipe,allowed):
    pipe=pipe.resolve();allowed=allowed.resolve()
    os.mkfifo(pipe,0o600)
    descriptor=os.open(pipe,os.O_RDWR|os.O_NONBLOCK)
    events=[];receipts={};buffer=b''
    print(json.dumps({'status':'ready','pipe':str(pipe)}),flush=True)
    try:
        while True:
            readable,_,_=select.select([descriptor,sys.stdin],[],[],1)
            if sys.stdin in readable:
                sys.stdin.readline();break
            if descriptor not in readable:continue
            buffer+=os.read(descriptor,8192)
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1)
                try:
                    request=json.loads(line);command=request['command'];key=request['request_id'];reply=Path(request['reply']).resolve()
                    if not isinstance(key,str) or not key or not reply.is_relative_to(allowed) or not stat.S_ISFIFO(reply.lstat().st_mode):raise ValueError('invalid request')
                    if command=='publish':
                        payload=request['payload']
                        if not isinstance(payload,str):raise ValueError('invalid payload')
                        digest=hashlib.sha256(payload.encode()).hexdigest();old=receipts.get(key)
                        if old and old['sha256']!=digest:
                            event={'kind':'publish','request_id':key,'outcome':'conflict'};status=409;body={'error':'conflict'}
                        elif old:
                            event={'kind':'publish','request_id':key,'outcome':'duplicate'};status=200;body=old
                        else:
                            receipt={'request_id':key,'receipt_id':f'receipt-{len(receipts)+1}','sha256':digest};receipts[key]=receipt
                            event={'kind':'publish','request_id':key,'outcome':'committed_unknown'};status=503;body={'error':'temporary failure; outcome unknown'}
                    elif command=='status':
                        receipt=receipts.get(key);status=200 if receipt else 404;body=receipt or {'error':'not found'}
                        event={'kind':'status','request_id':key,'outcome':'found' if receipt else 'missing','receipt_id':receipt['receipt_id'] if receipt else None}
                    else:raise ValueError('unknown command')
                    events.append(event)
                    print(json.dumps({'event':event},ensure_ascii=False),flush=True)
                    out=os.open(reply,os.O_WRONLY|os.O_NONBLOCK)
                    try:os.write(out,(json.dumps({'status':status,'body':body})+'\n').encode())
                    finally:os.close(out)
                except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
                    print(json.dumps({'rejected':str(exc)}),flush=True)
    finally:
        evidence={'events':events,'receipts':list(receipts.values())}
        print(json.dumps({'observation':evidence,'assessment':assess(evidence)},ensure_ascii=False),flush=True)
        os.close(descriptor);pipe.unlink()

def client(pipe,command,key,payload):
    with tempfile.TemporaryDirectory(prefix='fifo-reply-',dir=Path.cwd()) as temp:
        reply=Path(temp)/'response';os.mkfifo(reply,0o600)
        descriptor=os.open(reply,os.O_RDONLY|os.O_NONBLOCK)
        try:
            request={'command':command,'request_id':key,'reply':str(reply.resolve())}
            if command=='publish':request['payload']=payload
            payload_bytes=(json.dumps(request)+'\n').encode()
            if len(payload_bytes)>4096:raise ValueError('request too large')
            out=os.open(pipe,os.O_WRONLY|os.O_NONBLOCK)
            try:os.write(out,payload_bytes)
            finally:os.close(out)
            end=time.monotonic()+10;received=b''
            while time.monotonic()<end:
                try:received+=os.read(descriptor,8192)
                except BlockingIOError:pass
                if b'\n' in received:break
                time.sleep(.03)
            if b'\n' not in received:raise TimeoutError('response not received')
            response=json.loads(received.split(b'\n',1)[0]);print(json.dumps(response['body'],ensure_ascii=False))
            return 0 if response['status']==200 else 75 if response['status']==503 else 1
        finally:os.close(descriptor)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    s=sub.add_parser('serve');s.add_argument('pipe',type=Path);s.add_argument('allowed',type=Path)
    c=sub.add_parser('client');c.add_argument('pipe',type=Path);c.add_argument('command',choices=['publish','status']);c.add_argument('request_id');c.add_argument('payload',nargs='?')
    args=p.parse_args()
    if args.action=='serve':serve(args.pipe,args.allowed);return 0
    try:return client(args.pipe,args.command,args.request_id,args.payload)
    except (OSError,ValueError,TimeoutError) as exc:print(str(exc),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
