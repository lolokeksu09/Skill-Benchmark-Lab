#!/usr/bin/env python3
"""Experimental FIFO gate observer. Not a sandbox or a full process trace.

The observer is a separate local process. A client sends a request via a FIFO;
the observer executes a preconfigured check in its own child process and
records actual wait status, output hashes, executable hash and declared input
file hashes before/after. The controller fixes an argv list for each check;
the client selects only the name. No shell interpolation is performed by this
service. A shell can appear as an explicit controller-chosen executable. A
nested shell or Python subprocess can call the client. Echoing an output does
not create a record. A direct execution bypassing the client remains unknown.
This does not trace arbitrary commands performed by an agent.

FIFO requests carry a CLAIMED PID and cwd, not authenticated peer credentials.
/proc/PID may reveal the claimed process's cmdline, cwd and UID, but does not
prove that process wrote the request; cross-namespace reads may be denied and
are recorded as unknown. Claimed cwd is never labelled verified. All parties share UID/filesystem: they
can potentially spoof requests, alter service/key/log and interfere with /proc.
HMAC chaining detects ordinary record mutation if its key and final head are
retained separately; it is not a security boundary or independent attestation.

Requires Linux /proc and FIFO. Named checks run the fixed argv directly with a
minimal environment, without a sealed snapshot. Hashes describe pre/post file
state and cannot detect in-between modifications or prove what bytes the OS
actually read. Optional legacy `--gate` mode requires memfd_create and file
seals; its pinned script has `__file__` /proc/self/fd/N and Python runs with -I.
Scripts depending on location, environment or sibling imports may differ.
Only use explicitly compatible fixtures. STDOUT/STDERR are captured in memory;
the configured fixtures must be bounded and trusted not to exhaust memory.
Use private absolute 0700 directories, and keep key/log outside agent fixtures.
This prototype must not execute secrets or production code.
"""
from __future__ import annotations
import argparse
import base64
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import select
import signal
import stat
import subprocess
import sys
import threading
import time

MAX_MESSAGE=2048
MAX_OUTPUT=65536
ZERO='0'*64
# Linux UAPI values: F_ADD_SEALS=1033; F_SEAL_SEAL/SHRINK/GROW/WRITE=1/2/4/8.
# Some CPython builds lack their fcntl module constants despite kernel support.
F_ADD_SEALS=getattr(fcntl,'F_ADD_SEALS',1033)
SEALS=15


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def digest(data): return hashlib.sha256(data).hexdigest()


def verify_chain(records,key,expected_head=None):
    """Validate chain + HMAC; only an independently retained head detects truncation."""
    if not records:return expected_head==ZERO
    previous=ZERO
    for index,record in enumerate(records):
        if not isinstance(record,dict) or set(record)!={'event','previous','mac'}: return False
        if not isinstance(record['event'],dict) or not isinstance(record['mac'],str):return False
        if record['previous']!=previous or record['event'].get('sequence')!=index:return False
        body={'event':record['event'],'previous':previous}
        signature=hmac.new(key,canonical(body),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(record['mac'],signature):return False
        previous=digest(canonical(record))
    return expected_head is None or hmac.compare_digest(previous,expected_head)


def claimed_process(pid,claimed_cwd):
    if not isinstance(pid,int) or pid<=0: raise ValueError('invalid claimed pid')
    if not isinstance(claimed_cwd,str) or not os.path.isabs(claimed_cwd):raise ValueError('invalid claimed cwd')
    proc=Path('/proc')/str(pid)
    peer={'claimed_pid':pid,'authentication':'UNVERIFIED_FIFO_CLAIM',
          'claimed_cwd':claimed_cwd,'cwd':None,'exe':None,'cmdline':None,
          'uid':None,'gid':None,'unavailable':{}}
    for name in ('cmdline','cwd','exe','uid_gid'):
        try:
            if name=='cmdline':
                raw=(proc/'cmdline').read_bytes();peer[name]=[os.fsdecode(x) for x in raw.split(b'\0') if x]
            elif name in ('cwd','exe'):peer[name]=os.readlink(proc/name)
            else:
                info=proc.stat();peer['uid']=info.st_uid;peer['gid']=info.st_gid
        except OSError as exc:peer['unavailable'][name]=type(exc).__name__
    return peer


def _write_all(fd,payload,deadline):
    view=memoryview(payload)
    while view:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('FIFO response timed out')
        if not select.select([], [fd], [], remaining)[1]: raise TimeoutError('FIFO response timed out')
        try: n=os.write(fd,view)
        except BlockingIOError:continue
        if not n: raise OSError('FIFO write failed')
        view=view[n:]


class GateObserver:
    def __init__(self,socket_path,log_path,gate_path,gate_sha256,fixture_root,key,timeout=10,checks=None):
        # socket_path is retained as an API/CLI name for compatibility; it is a FIFO.
        self.socket_path=Path(socket_path);self.log_path=Path(log_path)
        self.gate_path=Path(gate_path) if gate_path is not None else None
        self.fixture_root=Path(fixture_root).resolve(strict=True)
        if not all(p.is_absolute() for p in (self.socket_path,self.log_path)):
            raise ValueError('FIFO, log and gate paths must be absolute')
        if not self.fixture_root.is_dir() or len(key)<32:raise ValueError('invalid fixture or key')
        if checks is None:
            if self.gate_path is None or not self.gate_path.is_absolute() or not self.gate_path.parent.resolve(strict=True).is_relative_to(self.fixture_root):raise ValueError('gate must be in fixture root')
            if not isinstance(gate_sha256,str) or not re.fullmatch('[a-f0-9]{64}',gate_sha256):raise ValueError('invalid gate hash')
        else:
            if self.gate_path is not None or gate_sha256 is not None:raise ValueError('choose gate or configured checks')
            self._validate_checks(checks)
        self.expected_hash=gate_sha256;self.key=key;self.timeout=timeout
        # Freeze controller-provided command/inputs configuration in memory.
        self.checks=json.loads(json.dumps(checks)) if checks is not None else None
        self.config_sha256=digest(canonical(self.checks)) if self.checks is not None else None
        self.records=[];self.head=ZERO;self._fd=None;self._thread=None;self._stop=threading.Event()

    @staticmethod
    def _validate_checks(checks):
        if not isinstance(checks,dict) or not checks:raise ValueError('checks must be a nonempty object')
        for name,spec in checks.items():
            if not re.fullmatch('[A-Za-z0-9_.-]{1,64}',name):raise ValueError('invalid check name')
            if not isinstance(spec,dict) or set(spec)-{'argv','inputs','immutable'}:raise ValueError('invalid check fields')
            argv=spec.get('argv');inputs=spec.get('inputs');immutable=spec.get('immutable',{})
            if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x and '\x00' not in x for x in argv) or not os.path.isabs(argv[0]):raise ValueError('argv must start with an absolute executable')
            if not isinstance(inputs,list) or not all(isinstance(x,str) and x for x in inputs) or len(set(inputs))!=len(inputs):raise ValueError('invalid inputs')
            if not isinstance(immutable,dict) or not set(immutable).issubset(inputs):raise ValueError('immutable files must be inputs')
            for rel in inputs:
                p=Path(rel)
                if p.is_absolute() or '..' in p.parts or rel in ('.',''):raise ValueError('invalid input path')
            if not all(isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) for v in immutable.values()):raise ValueError('invalid immutable hash')

    def _input_hashes(self,paths):
        result={}
        for rel in paths:
            p=self.fixture_root/rel
            try:
                resolved=p.resolve(strict=True)
                if not resolved.is_relative_to(self.fixture_root) or p.is_symlink():raise ValueError('input escapes fixture or is symlink')
                if not resolved.is_file():raise ValueError('input is not a file')
                result[rel]=digest(resolved.read_bytes())
            except FileNotFoundError:
                result[rel]=None
        return result

    def _run_configured(self,check):
        if check not in self.checks:raise ValueError('unknown check')
        spec=self.checks[check];before=self._input_hashes(spec['inputs'])
        if any(value is None for value in before.values()):raise ValueError('declared input missing')
        if any(before[name]!=want for name,want in spec.get('immutable',{}).items()):raise ValueError('immutable input hash mismatch')
        argv=spec['argv'];exe=Path(argv[0]).resolve(strict=True)
        if not exe.is_file():raise ValueError('executable is not a file')
        executable_before=digest(exe.read_bytes())
        proc=subprocess.Popen(argv,cwd=self.fixture_root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            start_new_session=True,env={'PATH':os.defpath,'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','PYTHONUTF8':'1'})
        try:out,err=proc.communicate(timeout=self.timeout);outcome='completed'
        except subprocess.TimeoutExpired:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            out,err=proc.communicate();outcome='timeout'
        after=self._input_hashes(spec['inputs'])
        try:executable_after=digest(exe.read_bytes())
        except OSError:executable_after=None
        return {'outcome':outcome,'child_pid':proc.pid,'child_pid_scope':'observer_pid_namespace',
            'returncode':proc.returncode,'argv':argv,'config_sha256':self.config_sha256,
            'inputs_before':before,'inputs_after':after,'executable_sha256_before':executable_before,
            'executable_sha256_after':executable_after,'source_unchanged':before==after and executable_before==executable_after,
            'stdout':base64.b64encode(out[:MAX_OUTPUT]).decode('ascii'),'stderr':base64.b64encode(err[:MAX_OUTPUT]).decode('ascii'),
            'stdout_sha256':digest(out),'stderr_sha256':digest(err),'stdout_bytes':len(out),'stderr_bytes':len(err),
            'truncated':len(out)>MAX_OUTPUT or len(err)>MAX_OUTPUT}

    def _append(self,event):
        event=dict(event,sequence=len(self.records),recorded_ns=time.time_ns())
        body={'event':event,'previous':self.head}
        record=dict(body,mac=hmac.new(self.key,canonical(body),hashlib.sha256).hexdigest())
        with self.log_path.open('ab') as out:
            out.write(canonical(record)+b'\n');out.flush();os.fsync(out.fileno())
        self.records.append(record);self.head=digest(canonical(record))
        return record

    def _gate_bytes(self):
        fd=os.open(self.gate_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            with os.fdopen(fd,'rb',closefd=False) as src:payload=src.read(1048577)
            if len(payload)>1048576:raise ValueError('gate too large')
            if digest(payload)!=self.expected_hash:raise ValueError('gate hash mismatch')
            return payload
        finally:os.close(fd)

    def _run_gate(self):
        payload=self._gate_bytes();fd=os.memfd_create('pws-observer-gate',os.MFD_ALLOW_SEALING)
        try:
            view=memoryview(payload)
            while view:
                n=os.write(fd,view)
                if not n:raise OSError('memfd write failed')
                view=view[n:]
            fcntl.fcntl(fd,F_ADD_SEALS,SEALS)
            proc=subprocess.Popen([sys.executable,'-I','/proc/self/fd/'+str(fd)],cwd=self.fixture_root,
                pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            try:out,err=proc.communicate(timeout=self.timeout);outcome='completed'
            except subprocess.TimeoutExpired:
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                out,err=proc.communicate();outcome='timeout'
            try:source_after=digest(self.gate_path.read_bytes())
            except OSError:source_after=None
            return {'outcome':outcome,'child_pid':proc.pid,'child_pid_scope':'observer_pid_namespace','returncode':proc.returncode,
                    'gate_sha256':digest(payload),'gate_source_sha256_after':source_after,
                    'source_unchanged':source_after==self.expected_hash,
                    'stdout':base64.b64encode(out[:MAX_OUTPUT]).decode('ascii'),
                    'stderr':base64.b64encode(err[:MAX_OUTPUT]).decode('ascii'),
                    'stdout_sha256':digest(out),'stderr_sha256':digest(err),
                    'stdout_bytes':len(out),'stderr_bytes':len(err),
                    'truncated':len(out)>MAX_OUTPUT or len(err)>MAX_OUTPUT}
        finally:os.close(fd)

    def _respond(self,nonce,response):
        path=self.socket_path.parent/('reply-'+nonce)
        if not stat.S_ISFIFO(os.lstat(path).st_mode): raise ValueError('response is not FIFO')
        fd=os.open(path,os.O_WRONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:_write_all(fd,canonical(response)+b'\n',time.monotonic()+5)
        finally:os.close(fd)

    def _handle(self,line):
        request=None;peer=None;nonce=None
        try:
            request=json.loads(line.decode('utf-8'))
            if not isinstance(request,dict):raise ValueError('invalid request')
            nonce=request.get('nonce')
            if not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{32}',nonce):
                raise ValueError('invalid nonce')
            if set(request)!={'op','pid','nonce','check','claimed_cwd'} or request['op']!='run':raise ValueError('unsupported request')
            check=request['check']
            if not isinstance(check,str) or not re.fullmatch('[A-Za-z0-9_.-]{1,64}',check):raise ValueError('invalid check name')
            peer=claimed_process(request['pid'],request['claimed_cwd'])
            if Path(peer['claimed_cwd']).resolve(strict=False)!=self.fixture_root:
                raise ValueError('wrong unverified claimed cwd')
            if peer['cwd'] is not None and Path(peer['cwd']).resolve(strict=False)!=self.fixture_root:
                raise ValueError('observed claimed-pid cwd differs')
            if self.checks is None:
                if check!='default':raise ValueError('unknown check')
                run=self._run_gate()
            else:run=self._run_configured(check)
            record=self._append({'kind':'gate','check':check,'peer':peer,**run})
            response={'ok':True,'record':record,'head':self.head}
        except (ValueError,OSError,json.JSONDecodeError) as exc:
            record=self._append({'kind':'rejected','peer':peer,'error':str(exc)})
            response={'ok':False,'error':str(exc),'record':record,'head':self.head}
        if isinstance(nonce,str) and re.fullmatch('[a-f0-9]{32}',nonce):
            try:self._respond(nonce,response)
            except (OSError,ValueError,TimeoutError):pass

    def start(self):
        if self.socket_path.exists() or self.socket_path.is_symlink() or self.log_path.exists():
            raise FileExistsError('observer never overwrites FIFO or log')
        os.mkfifo(self.socket_path,0o600)
        self._fd=os.open(self.socket_path,os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
        def serve():
            buffer=bytearray()
            while not self._stop.is_set():
                try:
                    if not select.select([self._fd],[],[],0.1)[0]:continue
                    part=os.read(self._fd,4096)
                except OSError:break
                buffer.extend(part)
                if len(buffer)>MAX_MESSAGE and b'\n' not in buffer:
                    self._append({'kind':'rejected','peer':None,'error':'oversized request'});buffer.clear();continue
                while b'\n' in buffer:
                    line,_,tail=buffer.partition(b'\n');buffer=bytearray(tail)
                    if len(line)>MAX_MESSAGE:self._append({'kind':'rejected','peer':None,'error':'oversized request'})
                    else:self._handle(bytes(line))
        self._thread=threading.Thread(target=serve,daemon=True);self._thread.start();return self

    def close(self):
        self._stop.set()
        if self._thread:self._thread.join(timeout=self.timeout+6)
        if self._fd is not None:os.close(self._fd)
        if self.socket_path.exists():self.socket_path.unlink()


def send_request(socket_path,op='run',timeout=20,check='default'):
    fifo=Path(socket_path)
    if not fifo.is_absolute():raise ValueError('absolute FIFO path required')
    nonce=secrets.token_hex(16);reply=fifo.parent/('reply-'+nonce)
    os.mkfifo(reply,0o600)
    fd=os.open(reply,os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        # This host may mount /proc from an ancestor PID namespace. os.getpid()
        # then cannot be looked up as /proc/<pid>; /proc/self resolves there.
        proc_visible_pid=int(os.readlink('/proc/self').rsplit('/',1)[-1])
        request=canonical({'op':op,'pid':proc_visible_pid,'nonce':nonce,'check':check,'claimed_cwd':os.getcwd()})+b'\n'
        out=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            # Request fits PIPE_BUF and is therefore atomic under POSIX.
            if len(request)>MAX_MESSAGE:raise ValueError('oversized request')
            if os.write(out,request)!=len(request):raise OSError('short FIFO request write')
        finally:os.close(out)
        deadline=time.monotonic()+timeout;chunks=bytearray()
        while b'\n' not in chunks:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([fd],[],[],remaining)[0]:raise TimeoutError('observer response timeout')
            try:chunks.extend(os.read(fd,8192))
            except BlockingIOError:continue
            if len(chunks)>200000:raise ValueError('oversized response')
        return json.loads(bytes(chunks).split(b'\n',1)[0])
    finally:os.close(fd);reply.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    server=sub.add_parser('serve')
    for flag in ('socket','log','fixture','key'):server.add_argument('--'+flag,required=True)
    for flag in ('gate','sha256','config'):server.add_argument('--'+flag)
    server.add_argument('--timeout',type=float,default=10)
    client=sub.add_parser('run');client.add_argument('--socket',required=True);client.add_argument('--check',default='default')
    args=parser.parse_args()
    if args.command=='run':
        response=send_request(args.socket,check=args.check)
        if not response['ok']:
            print(response['error'],file=sys.stderr);return 125
        event=response['record']['event']
        sys.stdout.buffer.write(base64.b64decode(event['stdout']));sys.stderr.buffer.write(base64.b64decode(event['stderr']))
        print('\n[observer sequence=%d head=%s]'%(event['sequence'],response['head']),file=sys.stderr)
        if event['outcome']!='completed' or not event['source_unchanged']:return 125
        return event['returncode'] if 0<=event['returncode']<=255 else 125
    checks=None
    if args.config:
        if args.gate or args.sha256:parser.error('choose --config or --gate with --sha256')
        cfg_path=Path(args.config)
        if not cfg_path.is_absolute():parser.error('--config must be absolute')
        checks=json.loads(cfg_path.read_text())['checks']
    elif not args.gate or not args.sha256:parser.error('supply --config or both --gate and --sha256')
    key_path=Path(args.key)
    if not key_path.is_absolute():parser.error('--key must be absolute')
    fd=os.open(key_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:os.write(fd,secrets.token_bytes(32))
    finally:os.close(fd)
    observer=GateObserver(args.socket,args.log,args.gate,args.sha256,args.fixture,key_path.read_bytes(),args.timeout,checks=checks).start()
    try:
        while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:observer.close()
    return 0

if __name__=='__main__':raise SystemExit(main())
