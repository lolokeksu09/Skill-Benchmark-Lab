# Unified original v1.7.0 — targeted regression Lab

This track prepares **four adversarial task specifications** and one public,
intentionally vulnerable cache fixture. It does **not** host, reproduce or
redistribute the plugin source ZIP. It extends, but does not change, the
frozen v1.6.0 effectiveness suite in draft PR #55.

- Candidate: Unified Development & Design original **v1.7.0**, 122 skills, one
  MIT license, ZIP SHA-256:
  `af88453b165389fde97b8762be255548b9e9b95455c01be683d02ac76b60f4bc`.
- Scope: task/context contradiction, read-only preview, offline digests,
  tenant-specific cache isolation.
- `TASKS.json` has four prompts, three observable acceptance criteria each,
  and two negative controls each.
- `validate_suite.py` checks metadata and rejects three deliberately
  corrupted specimens; it is not an agent-behavior evaluator.
- `fixtures/invoice_cache.py` intentionally leaks cached tenant data.
  The `fixtures/test_invoice_cache.py` regression suite should report
  **one failure** against this seed. That failure is required evidence that
  at least one intentionally broken case is detected.
- CI is deterministic, offline, read-only, uses no paid inference API.
- **Actual independent AI runs: 0**; no A/B scores or quality improvement
  conclusions. Do not claim model efficacy from structural tests.

Run locally:
```bash
python3 benchmarks/unified-original-v170/validate_suite.py
cd benchmarks/unified-original-v170/fixtures
python3 -m unittest -v test_invoice_cache.py
```

The second command must fail on the deliberately vulnerable seed. A candidate
agent would be tested in a fresh isolated workspace containing only its task
prompt and the task's starter. Do not expose evaluator tests to it when
performing a blinded comparison. Actual model, thinking effort, tool, plugin,
and environment receipts are needed before agent trials. Do not merge this
draft automatically; keep `main` unchanged.
