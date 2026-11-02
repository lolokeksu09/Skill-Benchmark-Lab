#!/usr/bin/env python3
"""Capture completed submissions, verify trace chain, replay frozen scorer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import suite

HERE=Path(__file__).resolve().parent
def sha(data): return hashlib.sha256(data).hexdigest()
def save_gzip(path,value):
    data=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    path.write_bytes(gzip.compress(data,mtime=0))
def read_gzip(path): return json.loads(gzip.decompress(path.read_bytes()))

def capture(root,dest):
    root=Path(root); dest=Path(dest); dest.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((root/'FREEZE.json').read_text())
    shutil.copyfile(root/'FREEZE.json',dest/'FREEZE.json')
    index={}
    for name,initial in frozen['runs'].items():
        bundle=root/name
        if not all((bundle/case/'RESULT.json').is_file() for case in suite.CASES):
            raise ValueError('trajectory unfinished: '+name)
        traces=[json.loads(line) for line in (bundle/'TRACE.jsonl').read_text().splitlines()]
        files={}
        integrity={}
        for rel,expected in initial['instruction_files'].items():
            actual=suite.digest(bundle/rel)
            integrity['instruction:'+rel]=actual==expected
        for case in suite.CASES:
            cwd=bundle/case
            files[case]={str(p.relative_to(cwd)):p.read_bytes().decode('utf-8') for p in sorted(cwd.rglob('*')) if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
            expected=initial['manifest'][case]['files']
            relevant=[t for t in traces if t['case']==case]
            for n,t in enumerate(relevant):
                integrity[f'{case}:trace-chain:{n}']=t['before']==expected
                expected=t['after']
            integrity[case+':final-hashes']=suite.inventory(cwd)==expected
            integrity[case+':task-unchanged']=suite.digest(cwd/'TASK.md')==initial['manifest'][case]['files']['TASK.md']
        receipt={'name':name,'files':files,'trace':traces,'integrity':integrity,'instruction_hashes':{rel:suite.digest(bundle/rel) for rel in initial['instruction_files']}}
        path=dest/(name+'.json.gz'); save_gzip(path,receipt)
        index[name]={'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'integrity_passed':all(integrity.values()),'integrity_failures':[k for k,v in integrity.items() if not v],'trace_commands':len(traces),'first_command':traces[0]['started'] if traces else None,'last_command':traces[-1]['started'] if traces else None}
    (dest/'INDEX.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    return index

def recompute_integrity(receipt,initial):
    result={}
    for rel,expected in initial['instruction_files'].items():result['instruction:'+rel]=receipt['instruction_hashes'].get(rel)==expected
    for case in suite.CASES:
        expected=initial['manifest'][case]['files']
        for n,t in enumerate(x for x in receipt['trace'] if x['case']==case):
            result[f'{case}:trace-chain:{n}']=t['before']==expected
            expected=t['after']
        final={rel:sha(content.encode('utf-8')) for rel,content in receipt['files'][case].items()}
        result[case+':final-hashes']=final==expected
        result[case+':task-unchanged']=final['TASK.md']==initial['manifest'][case]['files']['TASK.md']
    return result

def restore(dest,root):
    dest=Path(dest); root=Path(root); index=json.loads((dest/'INDEX.json').read_text())
    for name,meta in index.items():
        path=dest/(name+'.json.gz')
        if sha(path.read_bytes())!=meta['sha256']: raise ValueError('receipt changed '+name)
        receipt=read_gzip(path)
        for case,files in receipt['files'].items():
            for rel,content in files.items():
                target=root/name/case/rel
                if not target.resolve().is_relative_to(root.resolve()): raise ValueError('receipt path escape')
                suite.write(root/name/case,rel,content)
        suite.write(root/name,'TRACE.jsonl',''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in receipt['trace']))

def replay(dest):
    with tempfile.TemporaryDirectory(prefix='pws-behavior-replay-') as tmp:
        restore(dest,Path(tmp))
        return suite.score(Path(tmp))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['capture','replay']);p.add_argument('--root',type=Path);p.add_argument('--receipts',type=Path,default=HERE/'receipts');p.add_argument('--output',type=Path);a=p.parse_args()
    result=capture(a.root,a.receipts) if a.action=='capture' else replay(a.receipts)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    else: print(text)
if __name__=='__main__':main()
