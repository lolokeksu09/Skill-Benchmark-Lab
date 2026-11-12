# Unified Development & Design — original v1.9.0 Lab guardrails

**Purpose:** evaluate explicit user exclusions, fail-closed package installation,
and specialized Russian skill routing. This public branch does not redistribute
the plugin ZIP or include private project data.

## Candidate

- Unified original **v1.9.0**, 122 SKILL.md files, one root MIT LICENSE.
- User-delivered ZIP SHA-256:
  `4bd709d5c5797966a4242eb20ac46cfdd03fe9abf69a2f52ee272320b9f0c47d`.
- Local ZIP tests on extracted release: 142/142 PASS; 92/92 router cases PASS;
  source package integrity audit PASS; two-skill install/verify PASS.
- Independent model-agent trial count: **0**. No efficacy conclusion.

## Frozen tasks

[TASKS.json](TASKS.json) fixes four practical scenarios with three measurable
acceptance criteria and two negative controls each. A reviewer should distinguish
any real candidate output from deterministic metadata checks.

- U190-01: deleting every release marker must not bypass integrity preflight.
- U190-02: 'No web' versus stale web platform hints and manual web pipeline.
- U190-03: security-fix pipeline must respect explicit 'No security audit'.
- U190-04: Russian navigation/API contract routing without broad false matches.

[validate_suite.py](validate_suite.py) checks all four tasks and rejects four
deliberately malformed test specifications; it uses only Python stdlib.

[fixtures/unsafe_preflight.py](fixtures/unsafe_preflight.py) is **deliberately
vulnerable** and should fail exactly one unit test in
[fixtures/test_unsafe_preflight.py](fixtures/test_unsafe_preflight.py):
the case where all release markers are missing. This verifies the negative
control's discriminating power; it does **not** test the candidate's code.

Run preflight:

```bash
python3 benchmarks/unified-original-v190/validate_suite.py
cd benchmarks/unified-original-v190/fixtures
python3 -m unittest -v test_unsafe_preflight.py
```

The fixture baseline test should fail. CI requires and verifies the intentional
failure, so GitHub Actions can be green when the negative control is working.

## Actual A/B evidence gate

A valid comparison with v1.8.0 requires fresh isolated agent sessions with
source-attributed skill registry, actual model/thinking effort receipts,
same tools and task inputs, and independent blind scoring on saved candidate
artifacts with hashes. The evaluator's hidden tests cannot be included in
candidate prompts. No AI agent trials or paid inference APIs are run by CI;
all trial slots remain unexecuted. Missing results are blank, not zero.

This is a separate draft PR; do not merge into `main` automatically.
