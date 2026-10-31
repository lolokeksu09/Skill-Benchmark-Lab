#!/usr/bin/env python3
"""Validate Protocol 1.2. --static-only never claims sandbox or agent validation."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, threading
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
        for rel in ["README.md","PROTOCOL.md","MANIFEST.json","config.json","tools/preflight.py","tools/docker_runner.py","tools/safe_io.py","tools/agent_runner.py"]:
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
            (root/"sub").mkdir()
            safe.write_bytes(root,"sub/new.txt",b"created")
            assert safe.read_bytes(root,"sub/new.txt")==b"created"
            try:safe.write_bytes(root,"../escape.txt",b"x");raise AssertionError("traversal write accepted")
            except (safe.UnsafeFile,OSError):pass
            try:safe.write_bytes(root,"missing-parent/x.txt",b"x");raise AssertionError("missing parent accepted")
            except (safe.UnsafeFile,OSError):pass
            (root/"wlink").symlink_to(outside)
            try:safe.write_bytes(root,"wlink",b"x");raise AssertionError("symlink write accepted")
            except (safe.UnsafeFile,OSError):pass
            os.mkfifo(root/"wfifo")
            fifo_error=[]
            def _fifo_write():
                try:safe.write_bytes(root,"wfifo",b"x")
                except Exception as exc:fifo_error.append(exc)
            fifo_thread=threading.Thread(target=_fifo_write,daemon=True);fifo_thread.start();fifo_thread.join(5)
            assert not fifo_thread.is_alive(),"write_bytes blocked on FIFO"
            assert fifo_error and isinstance(fifo_error[0],(safe.UnsafeFile,OSError)),fifo_error
            (root/"wfifo").unlink()
            os.link(outside,root/"hard")
            try:safe.write_bytes(root,"hard",b"changed");raise AssertionError("hardlink write accepted")
            except (safe.UnsafeFile,OSError):pass
            assert outside.read_text()=="secret"
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
    def agent_bridge():
        """Deterministic fake-agent controls for the tool-mediated runner bridge.

        No AI provider is contacted; the fake agents are inline scripts speaking
        the pws-agent-bridge-v1 JSON-lines protocol.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            image="python@sha256:"+"0"*64
            preflight=tmp/"preflight.json"
            preflight.write_text(json.dumps({"protocol":"PWS-BENCH-PROTOCOL-1.2","status":"READY","image":image}))
            def write_agent(name,code):
                path=tmp/name;path.write_text(code);return path
            def run_bridge(agent,expect,scenario="S05",timeout_s=60,allow_env=None):
                bundle=tmp/("bundle-"+agent.stem)
                p=run([sys.executable,ROOT/"tools/prepare_run.py","--scenario",scenario,
                       "--standard","v1.3","--output",bundle]);assert p.returncode==0,p.stderr
                out=tmp/("evidence-"+agent.stem+".json")
                command=[sys.executable,ROOT/"tools/agent_runner.py",bundle,
                         "--agent-command",f"{sys.executable} {agent}",
                         "--preflight",preflight,"--image",image,
                         "--timeout",str(timeout_s),"--output",out]
                for name in allow_env or []:command+=["--allow-env",name]
                proc=run(command,timeout=timeout_s+90)
                assert proc.returncode==0,proc.stderr[-600:]
                evidence=json.loads(out.read_text())
                assert evidence["status"]==expect,(expect,evidence["status"],evidence["critical_errors"])
                return evidence,bundle
            positive=write_agent("agent_positive.py",'''
import json, sys
hello = json.loads(sys.stdin.readline())
assert hello["type"] == "hello" and hello["protocol"] == "pws-agent-bridge-v1", hello
assert hello["scenario"] == "S05" and "TASK.md" in hello["workspace_manifest"], hello
def call(cid, tool, **kw):
    print(json.dumps({"type": "tool_call", "id": cid, "tool": tool, **kw}), flush=True)
    return json.loads(sys.stdin.readline())
res = call("1", "list_files")
assert res["ok"] and "TASK.md" in res["files"], res
res = call("2", "read_file", path="TASK.md")
assert res["ok"] and len(res["content"]) > 0, res
res = call("3", "write_file", path="AGENT-NOTES.txt", content="deterministic control")
assert res["ok"] and res["bytes"] == 21 and len(res["sha256"]) == 64, res
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.exit(0)
''')
            evidence,bundle=run_bridge(positive,"executed")
            assert evidence["workspace_sha256"]==safe.tree_hash(bundle/"workspace")
            assert evidence["tool_log_sha256"]==attest.file_hash(bundle/"tool-log.jsonl")
            assert evidence["scenario_evaluator_sha256"]==attest.file_hash(ROOT/"scenarios/S05-unreproducible/evaluator.py")
            assert evidence["preflight_sha256"]==attest.file_hash(preflight)
            assert evidence["image"]==image
            assert evidence["run_id"]==safe.read_json(bundle,"RUN.json")["run_id"]
            assert all(evidence["environment"].values())
            assert evidence["process"]=={"terminated_by_bridge": False, "timed_out": False, "exit_code": 0}
            assert safe.read_text(bundle/"workspace","AGENT-NOTES.txt")=="deterministic control"
            lines=[json.loads(l) for l in (bundle/"tool-log.jsonl").read_text().splitlines()]
            kinds=[e.get("type") for e in lines]
            assert kinds[0]=="hello" and kinds[-1]=="finish" and kinds.count("tool_call")==3,kinds
            forbidden=write_agent("agent_forbidden.py",'''
import json, sys
sys.stdin.readline()
print(json.dumps({"type": "tool_call", "id": "1", "tool": "delete_file", "path": "TASK.md"}), flush=True)
sys.stdin.readline()
''')
            run_bridge(forbidden,"failed_bridge")
            traversal=write_agent("agent_traversal.py",'''
import json, sys
sys.stdin.readline()
print(json.dumps({"type": "tool_call", "id": "1", "tool": "read_file", "path": "../../RUN.json"}), flush=True)
sys.stdin.readline()
''')
            evidence,bundle=run_bridge(traversal,"failed_bridge")
            log_lines=(bundle/"tool-log.jsonl").read_text().splitlines()
            assert any(json.loads(l).get("outside_workspace") is True for l in log_lines),"escape attempt not flagged"
            assert all("prepared_not_executed" not in l for l in log_lines),"outside content exfiltrated"
            sleeping=write_agent("agent_sleep.py",'''
import sys, time
sys.stdin.readline()
time.sleep(60)
''')
            evidence,_=run_bridge(sleeping,"terminated_timeout",timeout_s=3)
            assert evidence["process"]["timed_out"] is True
            env_agent=write_agent("agent_env.py",'''
import json, os, sys
sys.stdin.readline()
leaked = sorted(k for k in os.environ if k.startswith("PWS_BRIDGE"))
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.stderr.write("LEAKED=" + json.dumps(leaked) + "\\n"); sys.stderr.flush()
sys.exit(0)
''')
            os.environ["PWS_BRIDGE_SECRET"]="bridge-secret-marker"
            try:
                evidence,bundle=run_bridge(env_agent,"executed")
            finally:
                os.environ.pop("PWS_BRIDGE_SECRET",None)
            assert evidence["agent_stderr_tail"].strip().endswith("LEAKED=[]"),evidence["agent_stderr_tail"]
            assert "bridge-secret-marker" not in json.dumps(evidence)
            assert "bridge-secret-marker" not in (bundle/"tool-log.jsonl").read_text()
            s06_agent=write_agent("agent_s06.py",'''
import json, sys
hello = json.loads(sys.stdin.readline())
assert hello["scenario"] == "S06", hello
print(json.dumps({"type": "tool_call", "id": "1", "tool": "run_tests"}), flush=True)
res = json.loads(sys.stdin.readline())
assert res["type"] == "tool_result" and res.get("available") is False, res
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.exit(0)
''')
            run_bridge(s06_agent,"executed",scenario="S06")
            orphan_marker=tmp/"orphan-child.pid"
            orphan=write_agent("agent_orphan.py",'''
import json, os, subprocess, sys
sys.stdin.readline()
subprocess.Popen([sys.executable, "-c",
 "import os,time,pathlib;pathlib.Path(r'" + repr("ORPHAN_MARKER") + "').write_text(str(os.getpid()));time.sleep(300)"])
os._exit(0)
'''.replace("ORPHAN_MARKER",str(orphan_marker)))
            evidence,_=run_bridge(orphan,"terminated_timeout",timeout_s=5)
            assert evidence["process"]["timed_out"] is True
            orphan_pid=int(orphan_marker.read_text())
            try:os.kill(orphan_pid,0);raise AssertionError(f"orphan child {orphan_pid} survived bridge termination")
            except ProcessLookupError:pass
            malformed=write_agent("agent_malformed.py",'''
import json, sys
sys.stdin.readline()
print(json.dumps({"type": "tool_call", "id": "1", "tool": []}), flush=True)
sys.stdin.readline()
''')
            evidence,_=run_bridge(malformed,"failed_bridge")
            assert "forbidden_tool" in evidence["critical_errors"],evidence["critical_errors"]
            exit_nonzero=write_agent("agent_exit_nonzero.py",'''
import json, sys
sys.stdin.readline()
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.exit(1)
''')
            evidence,_=run_bridge(exit_nonzero,"failed_bridge")
            assert any(c.startswith("agent_exit_nonzero") for c in evidence["critical_errors"]),evidence["critical_errors"]
            assert evidence["process"]["exit_code"]==1,evidence["process"]
            immutable=write_agent("agent_immutable.py",'''
import json, sys
sys.stdin.readline()
def call(cid, tool, **kw):
    print(json.dumps({"type": "tool_call", "id": cid, "tool": tool, **kw}), flush=True)
    return json.loads(sys.stdin.readline())
task_before=call("0", "read_file", path="TASK.md")["content"]
std_before=call("0b", "read_file", path="_standard/AGENTS.md")["content"]
r1=call("1", "write_file", path="TASK.md", content="tampered task")
r2=call("2", "write_file", path="_standard/AGENTS.md", content="tampered standard")
assert r1["ok"] is False and "immutable" in r1["error"], r1
assert r2["ok"] is False and "immutable" in r2["error"], r2
r3=call("3", "write_file", path="notes.txt", content="allowed write")
assert r3["ok"] is True, r3
assert call("4", "read_file", path="TASK.md")["content"]==task_before, "TASK.md was modified"
assert call("5", "read_file", path="_standard/AGENTS.md")["content"]==std_before, "_standard was modified"
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.exit(0)
''')
            evidence,bundle=run_bridge(immutable,"executed")
            assert safe.read_text(bundle/"workspace","notes.txt")=="allowed write"
            truncation=write_agent("agent_truncation.py",'''
import json, sys
sys.stdin.readline()
payload="A"*9000
def call(cid, tool, **kw):
    print(json.dumps({"type": "tool_call", "id": cid, "tool": tool, **kw}), flush=True)
    return json.loads(sys.stdin.readline())
r=call("1", "write_file", path="big.txt", content=payload)
assert r["ok"] is True, r
r=call("2", "read_file", path="big.txt")
assert r["ok"] is True and len(r["content"])==9000, r
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.exit(0)
''')
            evidence,bundle=run_bridge(truncation,"executed")
            log_text=(bundle/"tool-log.jsonl").read_text()
            assert "A"*9000 not in log_text,"raw large payload present in attested log"
            assert '"truncated": true' in log_text,"no truncation marker in attested log"
            assert hashlib.sha256(("A"*9000).encode()).hexdigest() in log_text,"payload digest missing from attested log"
            assert len(log_text.encode())<3*1024*1024,"attested log exceeded byte budget"
            assert evidence["tool_log_sha256"]==attest.file_hash(bundle/"tool-log.jsonl")
            disclosed=write_agent("agent_disclosed_env.py",'''
import json, os, sys
sys.stdin.readline()
present="PWS_BRIDGE_DISCLOSE" in os.environ
print(json.dumps({"type": "finish", "model": "fake", "provider": "deterministic-control",
                  "tokens": "not_measured", "cost": "not_measured"}), flush=True)
sys.stderr.write("PRESENT=%s\\n" % present); sys.stderr.flush()
sys.exit(0)
''')
            os.environ["PWS_BRIDGE_DISCLOSE"]="operator-approved-marker"
            try:
                evidence,_=run_bridge(disclosed,"executed",allow_env=["PWS_BRIDGE_DISCLOSE"])
            finally:
                os.environ.pop("PWS_BRIDGE_DISCLOSE",None)
            assert evidence["trusted_side"]["allow_env"]==["PWS_BRIDGE_DISCLOSE"],evidence.get("trusted_side")
            assert "PRESENT=True" in evidence["agent_stderr_tail"],evidence["agent_stderr_tail"]
            disclosed_neg=write_agent("agent_disclosed_env_neg.py",disclosed.read_text())
            evidence,_=run_bridge(disclosed_neg,"executed")
            assert evidence["trusted_side"]["allow_env"]==[],evidence.get("trusted_side")
            assert "PRESENT=False" in evidence["agent_stderr_tail"],evidence["agent_stderr_tail"]
            return "positive bindings, forbidden tool, traversal, timeout, env isolation, S06 run_tests unavailability; orphan kill, malformed schema, non-zero exit after finish, immutable inputs, bounded log, allow-env disclosure"
    tests=[required,manifest,origins,safe_files,bundles_and_pairs,fail_closed_acceptance,agent_bridge]
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
