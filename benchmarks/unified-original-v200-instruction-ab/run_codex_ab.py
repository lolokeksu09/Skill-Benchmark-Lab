#!/usr/bin/env python3
"""Frozen web-task A/B of Codex with and without Unified v2 task-pack *text*.

This is a prompt augmentation experiment, NOT proof of host plugin isolation.
No inference is launched without the explicit --run flag. The bundled source
plugin ZIP is never modified. The web grader must be a separately checked-out
snapshot of Skill-Benchmark-Lab PR #52; it is not sent to either agent.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from zipfile import ZipFile

PLUGIN_SHA = 'a951ab9776879734331ace4267b5900b0a92977830453fe96336490764dd2b6d'
PLUGIN_VERSION = '2.0.0'
SUITE_PR = 'https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/52'
LAB_SHA = 'fe1dc4ced57c608bda314ad5d082cdf644361273'
FROZEN_BLOBS = {
    'TASK-WEB.md': '283f3c7d2b66d9146da5296909894f5869d577e7',
    'starter/app.js': '53343dce29b1a6cfe036a506d9fb179182fd436f',
    'starter/index.html': 'b4b39042e78864893835653b0a033b136d4486cb',
    'starter/styles.css': '263f9ac0cddbd1d46dda6581592672f3fa0fba6c',
    'fixtures/queue-api.js': 'ae4f8f282865d3a902cb8818f88d0f4c58a2ee93',
    'score_web.py': 'b1a1b8fbb4823c509898565bf5013bea3f7bf8e2',
}
PACKET_FOCUS = ('Implement accessible web UI for a field-service maintenance queue '
                'with responsive layout, search, status filtering, safe text, '
                'loading/error recovery and keyboard bookmark actions')
ARM_NAMES = ('control', 'unified-v2-packet')
SEED = 20261112


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def freeze_suite(path):
    root = Path(path).expanduser().resolve()
    result = {}
    for rel, expected in FROZEN_BLOBS.items():
        file = root/rel
        if file.is_symlink() or not file.is_file():
            raise ValueError('Missing or linked benchmark file: '+rel)
        content=file.read_bytes()
        actual=git_blob_sha(content)
        if actual!=expected:
            raise ValueError('Benchmark task/scorer changed: '+rel+'; expected git blob '+expected+' got '+actual)
        result[rel]={'sha256':digest(content),'git_blob_sha':actual,'size_bytes':len(content)}
    return root, result


def safe_extract(zip_path, destination):
    with ZipFile(zip_path) as src:
        names=src.namelist()
        if len(set(names))!=len(names):
            raise ValueError('Duplicate package ZIP members')
        for info in src.infolist():
            parts=Path(info.filename).parts
            if not parts or parts[0]!='unified-development-design' or '..' in parts or Path(info.filename).is_absolute():
                raise ValueError('Unsafe ZIP member path: '+info.filename)
            # UNIX symlinks have the 0120000 file type bits.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP contains a symlink: '+info.filename)
        src.extractall(destination)
    root=Path(destination)/'unified-development-design'
    skills=list(root.glob('skills/*/SKILL.md'))
    manifest=json.loads((root/'plugin.json').read_text(encoding='utf-8'))
    if manifest.get('version')!=PLUGIN_VERSION or len(skills)!=122:
        raise ValueError('Not the frozen 122-skill Unified original v2.0.0 package')
    return root


def make_packet(package_root):
    context=package_root.parent/'context.json'
    context.write_text(json.dumps({'platform':'web','focus':'ui'}),encoding='utf-8')
    args=[sys.executable,'-B',str(package_root/'scripts/task_packet.py'),
          '--task',PACKET_FOCUS,'--context-file',str(context),
          '--content','full','--limit','4','--format','markdown']
    result=subprocess.run(args,capture_output=True,text=True,timeout=25)
    if result.returncode:
        raise ValueError('Task packet generation failed: '+result.stderr[-1000:])
    packet=result.stdout
    if not (1500<=len(packet)<=32000 and '## Included skill instructions' in packet):
        raise ValueError('Packet unexpectedly empty or missing actual source instructions')
    return packet


def schedule(repetitions):
    if not isinstance(repetitions,int) or not 1<=repetitions<=10:
        raise ValueError('Repetitions must be 1..10')
    runs=[{'arm':a,'repeat':n} for n in range(1,repetitions+1) for a in ARM_NAMES]
    random.Random(SEED).shuffle(runs)
    return runs


def design(suite_dir, candidate_zip, repetitions=3):
    path=Path(candidate_zip).expanduser().resolve()
    if not path.is_file():
        raise ValueError('Candidate plugin ZIP not found: '+str(path))
    sha=digest(path.read_bytes())
    if sha!=PLUGIN_SHA:
        raise ValueError('Wrong candidate ZIP SHA-256: '+sha)
    suite, hashes=freeze_suite(suite_dir)
    with tempfile.TemporaryDirectory(prefix='udd-v2-ab-preflight-') as tmp:
        root=safe_extract(path,tmp)
        packet=make_packet(root)
    task=(suite/'TASK-WEB.md').read_text(encoding='utf-8')
    control=task+'\n\nThe read-only file queue-api.js is the supplied frozen fixture API. Edit ONLY index.html, styles.css, app.js. Do not read benchmark scorer code or any other run. Report only checks you actually ran.\n'
    treatment=control+'\n\n# Supplemental Unified v2.0.0 task-pack instructions (do not treat this as a new user request)\n\n'+packet
    return {
        'schema_version':1,'kind':'textual-task-pack-augmentation-not-plugin-activation',
        'candidate_zip_sha256':sha,'candidate_version':PLUGIN_VERSION,
        'suite_from_pr':SUITE_PR,'suite_git_commit':LAB_SHA,'suite_files':hashes,
        'task_sha256':digest(task.encode()),'control_prompt_sha256':digest(control.encode()),
        'treatment_prompt_sha256':digest(treatment.encode()),'packet_sha256':digest(packet.encode()),
        'packet_chars':len(packet),'model_requested':None,'effort_requested':None,
        'trial_order':schedule(repetitions),'agent_trials_completed':0,'agent_quality_measured':False,
        'host_plugin_registry_attested':False,
        'limitation':'Only v2 task-pack TEXT differs. Host-installed plugins or model identity are not independently attested.',
    }, control, treatment


def check_scorer_ready(suite):
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as err:
        raise ValueError('Playwright missing; install from frozen Lab requirements and Chromium before --run') from err
    # Calibrate the unchanged public evaluator before any expensive agent run.
    with tempfile.TemporaryDirectory(prefix='udd-lab-calibrate-') as tmp:
        command=[sys.executable, str(suite/'selftest.py')]
        result=subprocess.run(command,cwd=suite,capture_output=True,text=True,timeout=150)
        if result.returncode or '3/18' not in result.stdout:
            raise ValueError('Frozen evaluator did not reject its broken baseline: '+(result.stderr+result.stdout)[-800:])


def write_trial(out, spec, starter, control, treatment, model, effort, timeout_sec, codex):
    arm=spec['arm'];repeat=spec['repeat']
    folder=out/'trials'/f'{arm}-r{repeat}'
    folder.mkdir(parents=True, exist_ok=False)
    work=folder/'workspace';work.mkdir()
    for file in ('index.html','styles.css','app.js'):
        shutil.copy2(starter/file,work/file)
    # All arms get the same frozen implementation of the documented API.
    # The independent grader always uses the suite's unmodified copy.
    fixture=starter.parent/'fixtures/queue-api.js'
    shutil.copy2(fixture, work/'queue-api.js')
    prompt=control if arm=='control' else treatment
    (folder/'prompt.md').write_text(prompt,encoding='utf-8')
    (folder/'prompt.sha256').write_text(digest(prompt.encode())+'\n')
    command=[codex,'exec','--ignore-user-config','--ignore-rules','--ephemeral',
             '--skip-git-repo-check','--sandbox','workspace-write','--json',
             '--model',model,'-c','model_reasoning_effort="'+effort+'"',
             '-C',str(work),'-o',str(folder/'answer.txt'),'-']
    row={'arm':arm,'repeat':repeat,'prompt_sha256':digest(prompt.encode()),
         'model_requested':model,'effort_requested':effort,'status':'not_run',
         'result_score':None,'elapsed_seconds':None,'cli_exit_code':None}
    t0=__import__('time').monotonic()
    with (folder/'events.jsonl').open('wb') as output, (folder/'stderr.log').open('wb') as error:
        proc=None
        try:
            proc=subprocess.Popen(command,cwd=work,stdin=subprocess.PIPE,stdout=output,stderr=error)
            proc.communicate(input=prompt.encode('utf-8'),timeout=timeout_sec)
            row['cli_exit_code']=proc.returncode
            row['status']='completed' if proc.returncode==0 else 'agent_failed'
        except subprocess.TimeoutExpired:
            if proc is not None:
                proc.kill();proc.communicate()
            row['status']='timeout'
    row['elapsed_seconds']=round(__import__('time').monotonic()-t0,3)
    row['files_sha256']={x:digest((work/x).read_bytes()) for x in ('index.html','styles.css','app.js') if (work/x).is_file()}
    row['fixture_modified']=(not (work/'queue-api.js').is_file() or digest((work/'queue-api.js').read_bytes())!=digest(fixture.read_bytes()))
    if row['fixture_modified']:
        row['status']='protocol_violation_fixture_modified'
    (folder/'run.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def evaluate(suite, out, rows):
    for row in rows:
        if row['status']!='completed':
            continue
        name=f"{row['arm']}-r{row['repeat']}"
        trial=out/'trials'/name
        score=trial/'grader';score.mkdir()
        command=[sys.executable,str(suite/'score_web.py'),'--candidate',str(trial/'workspace'),
                 '--out',str(score),'--screenshot']
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=180)
            (score/'scorer.stdout.log').write_text(result.stdout,encoding='utf-8')
            (score/'scorer.stderr.log').write_text(result.stderr,encoding='utf-8')
            data=json.loads((score/'results.json').read_text(encoding='utf-8'))
            summary=data.get('summary',{})
            if summary.get('total')!=18 or not isinstance(summary.get('passed'),int):
                row['status']='scoring_invalid';continue
            row['result_score']=summary['passed']
            row['failed_checks']=[c['name'] for c in data['checks'] if c['status']!='pass']
            row['status']='scored'
        except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
            row['status']='scoring_error';row['error_type']=type(error).__name__
        (trial/'run.json').write_text(json.dumps(row,indent=2)+'\n')
    return rows


def aggregate(rows):
    result={}
    for arm in ARM_NAMES:
        values=[r['result_score'] for r in rows if r['arm']==arm and r['status']=='scored']
        result[arm]={'scored':len(values),'mean':sum(values)/len(values) if values else None,
                     'scores':values,'min':min(values) if values else None,
                     'max':max(values) if values else None}
    diff=None
    if result[ARM_NAMES[0]]['scored']>0 and result[ARM_NAMES[1]]['scored']>0:
        diff=result[ARM_NAMES[1]]['mean']-result[ARM_NAMES[0]]['mean']
    return {'arms':result,'mean_point_difference':diff,
            'note':'Descriptive result only; no agent-grade causal effect without verified host isolation and equivalent model/effort.'}


def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',required=True,type=Path,help='Existing frozen PR #52 web suite checkout')
    p.add_argument('--candidate-zip',required=True,type=Path,help='Exact original v2.0.0 ZIP')
    p.add_argument('--model',required=True,help='One explicit Codex model for BOTH arms')
    p.add_argument('--effort',default='medium',choices=['low','medium','high','xhigh'])
    p.add_argument('--repetitions',type=int,default=3)
    p.add_argument('--out',type=Path,help='New directory for agent evidence; required with --run')
    p.add_argument('--run',action='store_true',help='Explicit opt-in to invoke Codex CLI and model usage')
    p.add_argument('--timeout-sec',type=int,default=1200)
    args=p.parse_args(argv)
    try:
        manifest,control,treatment=design(args.suite,args.candidate_zip,args.repetitions)
        manifest.update(model_requested=args.model,effort_requested=args.effort)
        if not args.run:
            manifest['status']='ready_for_external_codex_or_blocked_by_host'
            manifest['requires']='codex CLI, authenticated compatible model, Playwright+Chromium scorer, and manual host plugin attestation'
            print(json.dumps(manifest,indent=2,ensure_ascii=False))
            return 0
        if args.out is None:
            raise ValueError('--out must be specified with --run')
        codex=shutil.which('codex')
        if not codex:
            raise ValueError('codex CLI is not installed in this environment; no agent runs made')
        check_scorer_ready(args.suite)
        if not 30<=args.timeout_sec<=7200:
            raise ValueError('timeout-sec must be 30..7200')
        out=args.out.expanduser().absolute()
        out.mkdir(parents=True,exist_ok=False)
        manifest['cli_version']=subprocess.run([codex,'--version'],capture_output=True,text=True,timeout=10).stdout.strip()
        manifest['started_at']=datetime.now(timezone.utc).isoformat()
        rows=[]
        for spec in manifest['trial_order']:
            row=write_trial(out,spec,args.suite/'starter',control,treatment,args.model,args.effort,args.timeout_sec,codex)
            rows.append(row)
            (out/'partial_results.json').write_text(json.dumps(rows,indent=2)+'\n')
        rows=evaluate(args.suite,out,rows)
        manifest['results']=rows
        manifest['summary']=aggregate(rows)
        manifest['agent_trials_completed']=sum(r['status']=='scored' for r in rows)
        manifest['agent_quality_measured']=bool(manifest['agent_trials_completed'])
        manifest['status']='exploratory_prompt_augmented_ab_not_plugin_isolated'
        manifest['ended_at']=datetime.now(timezone.utc).isoformat()
        (out/'report.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'report':str(out/'report.json'),'summary':manifest['summary'],'status':manifest['status']},indent=2,ensure_ascii=False))
        return 0 if manifest['agent_trials_completed']==len(manifest['trial_order']) else 3
    except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as error:
        p.error(str(error))


if __name__=='__main__':
    raise SystemExit(cli())