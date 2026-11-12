# Unified Development & Design original v1.6.0 — benchmark preparation

This is a **public, reviewable benchmark track** for the independently written Unified Development & Design skill pack. It does not contain the plugin source archive, private credentials, paid-model calls or any alleged model-performance result.

## Frozen subject

- **Candidate:** Unified Development & Design original **v1.6.0**, 122 skills, one root MIT license.
- **Candidate ZIP SHA-256:** `4ff398e18db9d0cb86b9b63a738a5fec5cf2e4aa129e4257bf5e312e213ea023`.
- **Earlier comparator:** independently released original **v1.5.0**; check its exact archive hash when preparing trial profiles.
- **Local engineering preflight, not agent efficacy:** v1.5.0 had 85 passing unit tests / 72 deterministic routing scenarios. Candidate v1.6.0 has 112 passing unit tests / 84 deterministic routing scenarios on the independently extracted release, plus structural ZIP checks. These are distinct suites and cannot be treated as an A/B effect size.
- **External trial executions:** **0**. No candidate patches, measured agent quality or per-arm results yet.

## Benchmark materials

- [TASKS.json](TASKS.json) freezes 10 concrete engineering scenarios, each with three acceptance criteria and two negative controls. Do not tune the plugin to this locked evaluation set after reviewing agent outputs.
- [PROTOCOL.md](PROTOCOL.md) defines fresh-session A/B/C isolation, artifact and scoring rules, and the stop conditions.
- [SCORING.md](SCORING.md) defines 0/1/2 per criterion and negative-control failures.
- [fixtures/invoice_service.py](fixtures/invoice_service.py) is the *intentionally vulnerable* seed for task U160-06; [fixtures/test_invoice_service.py](fixtures/test_invoice_service.py) is its evaluator-only regression suite. A correct fix must prevent cross-tenant reads without exposing another tenant's invoice existence. Never copy the evaluator tests into candidate-agent context.
- [validate_suite.py](validate_suite.py) validates the frozen suite and includes three negative self-checks. All validation is deterministic Python stdlib, offline.

## Replay verification

From repository root:

```bash
python3 benchmarks/unified-original-v160/validate_suite.py --selftest
cd benchmarks/unified-original-v160/fixtures
python3 -m unittest -v test_invoice_service.py
```

**Expected for the unmodified seed:** suite validation passes; the invoice fixture test run **fails** because the cross-tenant boundary is intentionally broken. It must not be counted as a candidate-agent run. The CI workflow checks that this deliberately broken baseline is rejected.

To conduct the actual benchmark, pin matching agent/model/effort/tool settings and isolate plugin loading per arm, run with fresh input histories and a blind reviewer, and attach actual code diffs, runtime receipts, test logs and artifact hashes. If those conditions cannot be attested, report **blocked**, not 0-score or success.

## Repository and safety boundaries

This branch is a standalone draft PR. No edits to `main`, the existing draft protocols in PR #52/#53, or the private ChatGPT plugin. Source plugin ZIP is distributed separately to the user, not committed to this public Lab repository. CI performs no AI inference or deployment.
