# PWS behavior benchmark 1.4

Start with [REPORT.md](REPORT.md), then [INDEPENDENT-REVIEW.md](INDEPENDENT-REVIEW.md).

- PROTOCOL.md and suite.py: frozen preregistration/fixtures/scorer (6e0073d).
- receipts/: twelve immutable compressed submissions and raw instrumented command traces, initial manifests and SHA-256 index.
- RESULTS.json: unchanged primary score, including known scorer defects.
- evaluate_v2.py / DIAGNOSTIC-V2.json: explicitly post-measurement evidence interpretation with case-level inconclusive outcomes.
- EXECUTION.json: host invocation provenance and unavailable model/usage metrics.

Replay (Python 3.10+ and Git; no provider key, no model calls):

```bash
python3 benchmarks/project-workflow-standard/behavior-1.4/verify.py
```

Regenerate fixtures into a new directory only with suite.py setup --root NEW_PATH. This creates inputs, not model executions. New owner-authorized applications must be launched separately; CI never does so. Do not overwrite these submissions or historical archive/V4/V5 results.
