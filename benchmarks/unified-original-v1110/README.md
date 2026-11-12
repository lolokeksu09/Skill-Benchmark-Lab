# Unified Development & Design original v1.11.0 — project-context benchmark

Five reproducible, **not-yet-executed** engineering scenarios evaluate whether
an agent uses project evidence safely and respects the actual task. The cases
cover Android, web/backend mixed repositories, user exclusions, comment-based
dependency false positives, and manifest privacy/symlink protection.

- Candidate: standalone original Unified Development & Design **v1.11.0**,
  122 original skills and one root MIT LICENSE.
- Candidate ZIP SHA-256: `a8081fcc24a2df3e38361bf2a9921d71a40f9622e19d5754e3550fcac960032a`.
- Candidate package was locally extracted and verified: **165/165 unit tests**,
  **92/92 deterministic routing cases**, strict 164-file integrity gate,
  plus two-skill preview/apply/verification smoke tests.
- New Lab tasks have 15 acceptance criteria and 10 negative controls. The task
  descriptions are visible; they are *not* hidden evaluator tests.
- `validate_suite.py` is a Python-stdlib metadata validator, with four
  negative mutation checks. It **does not run an AI agent**.
- Actual independent model-agent trials: **0**. No model-effectiveness claim.

## CI / local preflight

```bash
python3 benchmarks/unified-original-v1110/validate_suite.py
```

A green CI status validates the frozen benchmark specification, **not**
the model's quality. True A/B requires fresh isolated sessions with verified
loaded skills, model/effort parity, fixed inputs, independent reviewer scoring,
and artifact hashes. Do not infer improvement merely because the local router
or metadata tests pass.

This is a separate draft PR. Previous benchmark PRs and `main` are unchanged.
No plugin ZIP, private project data or model API secrets are committed.
