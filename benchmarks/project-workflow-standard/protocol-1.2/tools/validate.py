#!/usr/bin/env python3
"""Validate Protocol 1.2. --static-only never claims sandbox or agent validation."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS={"S05":"S05-unreproducible","S06":"S06-release-exception"}
STANDARDS=["v1.3","v1.4-rc3"]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
safe=load("safe_io",ROOT/"tools/safe_io.py");attest=load("attestations",ROOT/"tools/attestations.py");factory=load("control_factory",ROOT/"tools/control_factory.py")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(cmd,timeout=120):return subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=timeout)
def report_from(proc):
    try:return json.JSONDecoder().raw_decode(proc.stdout.lstrip())[0]
    except Exception:raise AssertionError(f"no JSON report: {proc.stdout[-800:]} {proc.stderr[-800:]}")
def keypair(path:Path):
    proc=run(["ssh-keygen","-t","ed25519","-N","","-f",path]);assert proc.returncode==0,proc.stderr
    return path.read_text() if False else path.with_suffix(".pub").read_text().split()[:2]
def sign(key:Path,payload:Path,namespace:str):
    proc=run(["ssh-keygen","-Y","sign","-f",key,"-n",namespace,payload]);assert proc.returncode==0,proc.stderr
    return Path(str(payload)+".sig")

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--static-only",action="store_true");ap.add_argument("--preflight",type=Path);args=ap.parse_args()
    failures=0;completed=0
    def check(name,fn):
        nonlocal failures,completed
        try:
            note=fn();completed+=1;print(f"PASS {name}"+(f": {note}" if note else ""))
        except Exception as exc:failures+=1;print(f"FAIL {name}: {exc}")
    def required():
        for rel in ["README.md","PROTOCOL.md","MANIFEST.json","config.json","tools/preflight.py","tools/docker_runner.py","tools/safe_io.py"]:
            assert (ROOT/rel).is_file(),rel
        assert "PWS-BENCH-PROTOCOL-1.2" in (ROOT/"PROTOCOL.md").read_text()
    def manifest():
        m=json.loads((ROOT/"MANIFEST.json").read_text())
        for rel,digest in m["files"].items():assert (ROOT/rel).is_file() and sha(ROOT/rel)==digest,rel
        return f"{len(m['files'])} tracked file hashes"
    def origins():
        m=json.loads((ROOT/"standards/manifest.json").read_text())
        for version in STANDARDS:assert safe.snapshot(ROOT/"standards"/version)==m["files"][version],version
    def safe_files():
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"root";root.mkdir();outside=Path(tmp)/"outside";outside.write_text("secret")
            (root/"ok").write_text("fine");assert safe.read_text(root,"ok")=="fine"
            (root/"link").symlink_to(outside)
            try:safe.read_bytes(root,"link");raise AssertionError("symlink followed")
            except (safe.UnsafeFile,OSError):pass
            try:safe.snapshot(root);raise AssertionError("symlink snapshot accepted")
            except (safe.UnsafeFile,OSError):pass
            (root/"link").unlink();os.mkfifo(root/"fifo")
            try:safe.snapshot(root);raise AssertionError("FIFO accepted")
            except (safe.UnsafeFile,OSError):pass
    def bundles_and_pairs():
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);bundles={}
            invalid=tmp/"rejected-s06-fail-cli"
            try:
                factory.materialize("S06","fail-cli",invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("S06 fail-cli must raise ValueError")
            assert not invalid.exists(),"invalid control modified files before rejection"
            for scenario in SCENARIOS:
                for version in STANDARDS:
                    target=tmp/f"{scenario}-{version}";p=run([sys.executable,ROOT/"tools/prepare_run.py","--scenario",scenario,"--standard",version,"--output",target]);assert p.returncode==0,p.stderr
                    assert not (target/"workspace/RUN.json").exists();bundles[(scenario,version)]=target
                pair=run([sys.executable,ROOT/"tools/compare_pair.py",bundles[(scenario,"v1.3")],bundles[(scenario,"v1.4-rc3")]]);assert pair.returncode==0,pair.stdout
            same=run([sys.executable,ROOT/"tools/compare_pair.py",bundles[("S05","v1.3")],bundles[("S06","v1.3")]]);assert same.returncode!=0,"same standards accepted"
            for version in STANDARDS:
                (bundles[("S05",version)]/"workspace/cli.py").write_text("both-pairs-tampered\n")
            tampered = run([sys.executable,ROOT/"tools/compare_pair.py",bundles[("S05","v1.3")],bundles[("S05","v1.4-rc3")]])
            assert tampered.returncode != 0, "jointly tampered inputs accepted"
            shutil.rmtree(bundles[("S05","v1.4-rc3")]/"workspace/_standard")
            missing=run([sys.executable,ROOT/"tools/compare_pair.py",bundles[("S05","v1.3")],bundles[("S05","v1.4-rc3")]]);assert missing.returncode!=0,"missing standard accepted"
        return "both versions and exact non-standard equality enforced"
    def fail_closed_acceptance():
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);bundle=tmp/"run";p=run([sys.executable,ROOT/"tools/prepare_run.py","--scenario","S06","--standard","v1.3","--output",bundle]);assert p.returncode==0
            pass_tree=tmp/"pass";factory.materialize("S06","pass",pass_tree)
            for name in ["decision.json","DECISION.md"]:shutil.copy2(pass_tree/name,bundle/"workspace"/name)
            meta=safe.read_json(bundle,"RUN.json");meta["status"]="executed";(bundle/"RUN.json").write_text(json.dumps(meta))
            env={"status":"verified_by_runner","network_disabled":True,"resource_limits_enforced":True};(bundle/"environment.json").write_text(json.dumps(env))
            pending=run([sys.executable,ROOT/"tools/evaluate.py",bundle]);assert pending.returncode==2 and not report_from(pending)["accepted"],"forged JSON flags accepted"
            runner_key=tmp/"runner";review_key=tmp/"reviewer";rpub=keypair(runner_key);vpub=keypair(review_key)
            allowed=tmp/"allowed_signers";allowed.write_text(f"runner@pws {rpub[0]} {rpub[1]}\nreviewer@pws {vpub[0]} {vpub[1]}\n")
            image="python@sha256:"+"0"*64
            preflight=tmp/"preflight.json";preflight.write_text(json.dumps({"protocol":meta["protocol"],"status":"READY","image":image}))
            eval_path=ROOT/"scenarios/S06-release-exception/evaluator.py"
            runner={"kind":"runner","status":"executed","run_id":meta["run_id"],"protocol":meta["protocol"],
                    "workspace_sha256":safe.tree_hash(bundle/"workspace"),"tool_log_sha256":attest.file_hash(bundle/"tool-log.jsonl"),
                    "scenario_evaluator_sha256":attest.file_hash(eval_path),"preflight_sha256":attest.file_hash(preflight),"image":image,
                    "environment":{k:True for k in ["workspace_root_only","network_disabled","external_credentials_absent","publication_tools_absent","resource_limits_enforced","tool_log_complete"]}}
            rp=tmp/"runner.json";rp.write_text(json.dumps(runner));rs=sign(runner_key,rp,"pws-runner-v1")
            command=[sys.executable,ROOT/"tools/evaluate.py",bundle,"--image",image,"--preflight",preflight,"--runner-attestation",rp,"--runner-signature",rs,"--allowed-signers",allowed]
            no_review=run(command);assert no_review.returncode==2 and not report_from(no_review)["accepted"],"runner-only accepted"
            core=report_from(no_review)
            review={"kind":"review","reviewer":"reviewer@pws","run_id":meta["run_id"],"protocol":meta["protocol"],"blinded_to_standard":True,"approved":True,
                    "workspace_sha256":runner["workspace_sha256"],"automated_report_sha256":core["automated_report_sha256"],"runner_attestation_sha256":attest.file_hash(rp)}
            vp=tmp/"review.json";vp.write_text(json.dumps(review));vs=sign(review_key,vp,"pws-review-v1")
            accepted=run(command+["--review-attestation",vp,"--review-signature",vs]);assert accepted.returncode==0 and report_from(accepted)["accepted"],report_from(accepted)
            wrong=dict(review);wrong["run_id"]="other";wp=tmp/"wrong.json";wp.write_text(json.dumps(wrong));ws=sign(review_key,wp,"pws-review-v1")
            rejected=run(command+["--review-attestation",wp,"--review-signature",ws]);assert rejected.returncode!=0 and not report_from(rejected)["accepted"],"wrong binding accepted"
            return "forged flags, missing review and wrong bindings rejected; synthetic signature path only"
    tests=[required,manifest,origins,safe_files,bundles_and_pairs,fail_closed_acceptance]
    if not args.static_only:
        assert args.preflight,"--preflight required unless --static-only"
        pre=json.loads(args.preflight.read_text());assert pre["status"]=="READY" and pre["protocol"]=="PWS-BENCH-PROTOCOL-1.2","runner NOT_READY"
        image=pre["image"];assert "@sha256:" in image
        def positive():
            for scenario,name in SCENARIOS.items():
                base=ROOT/"scenarios"/name
                with tempfile.TemporaryDirectory() as tmp:
                    work=Path(tmp)/"pass";factory.materialize(scenario,"pass",work)
                    cmd=[sys.executable,base/"evaluator.py",work]+(["--image",image] if scenario=="S05" else [])
                    proc=run(cmd);assert proc.returncode==0 and report_from(proc)["automated_pass"],f"positive rejected {name}: {proc.stdout[-800:]}"
        def negative():
            for scenario,name in SCENARIOS.items():
                base=ROOT/"scenarios"/name
                with tempfile.TemporaryDirectory() as tmp:
                    work=Path(tmp)/"fail";factory.materialize(scenario,"fail",work)
                    cmd=[sys.executable,base/"evaluator.py",work]+(["--image",image] if scenario=="S05" else [])
                    proc=run(cmd);assert proc.returncode!=0 and not report_from(proc)["automated_pass"],name
        def mutations():
            total=0
            for scenario,name in SCENARIOS.items():
                base=ROOT/"scenarios"/name;expect=json.loads((base/"mutation-expectations.json").read_text())
                for control,item in expect.items():
                    with tempfile.TemporaryDirectory() as tmp:
                        work=Path(tmp)/control;factory.materialize(scenario,control,work)
                        if scenario=="S05" and control=="fail-cli":
                            positive=Path(tmp)/"positive";factory.materialize("S05","pass",positive)
                            mutated=(work/"cli.py").read_bytes()
                            assert b"broken CLI mutation" in mutated,"fail-cli mutation marker missing"
                            assert mutated!=(positive/"cli.py").read_bytes(),"fail-cli equals positive control"
                        cmd=[sys.executable,base/"evaluator.py",work]+(["--image",image] if scenario=="S05" else [])
                        proc=run(cmd);report=report_from(proc);actual={c["name"] for c in report["checks"] if not c["ok"]};expected=set(item["failed_exactly"])
                        if proc.returncode==0 or actual!=expected:
                            raise AssertionError(
                                f"{control}: expected exactly {sorted(expected)}, got {sorted(actual)}\n"
                                f"evaluator_exit_code={proc.returncode}\n"
                                f"evaluator_stderr={proc.stderr}\n"
                                f"full_report={json.dumps(report,ensure_ascii=False,indent=2)}"
                            )
                        total+=1
            return f"{total} exact mutation sets"
        tests += [positive,negative,mutations]
    for fn in tests:check(fn.__name__,fn)
    print(f"Result: {completed}/{len(tests)} passed; failures={failures}; agent_runs=0; mode={'static' if args.static_only else 'docker-controls'}")
    return 1 if failures else 0
if __name__=="__main__":sys.exit(main())
