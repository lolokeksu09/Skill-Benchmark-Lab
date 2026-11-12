# Unified Development & Design — original v1.8.0 Lab track

This public Lab branch is an **offline benchmark preparation and negative-control test**, not an agent-effectiveness claim. It does not bundle or republish the plugin ZIP or private data.

## Frozen candidate

- Standalone Unified original **v1.8.0**: 122 SKILL.md entrypoints and one top-level MIT license.
- User-delivered ZIP SHA-256: `beb1455e2737cf41c5508816b14f57c5a98f60a83a9e89f8add40ad8903338cf`.
- Local package tests: **130/130 PASS** and **84/84 routing scenarios PASS**, plus ZIP extraction, integrity audit, install preview/apply/verification checks.
- No claim is made that deterministic regression checks measure independent agent output quality. **Independent agent runs: 0**.

## Lab scope

- [TASKS.json](TASKS.json): 5 fixed engineering prompts, 15 observable acceptance criteria and 10 negative controls, including tampered installer scripts, extra files, license text mutation, explicit Android pipeline exclusion and conflicting security context.
- [validate_suite.py](validate_suite.py): stdlib-only metadata validator with 4 deliberately corrupted variants that must be rejected.
- [fixtures/unsafe_release_check.py](fixtures/unsafe_release_check.py): **intentionally vulnerable** toy release verifier that checks known file digests but not unexpected new files.
- [fixtures/test_unsafe_release_check.py](fixtures/test_unsafe_release_check.py): proves the fixture's known deficiency is detectable, by requiring a failed unit test on the baseline.

Run locally:

```bash
python3 benchmarks/unified-original-v180/validate_suite.py
cd benchmarks/unified-original-v180/fixtures
python3 -m unittest -v test_unsafe_release_check.py
```

The first command must pass. The second intentionally **fails exactly one case** against the seeded vulnerable verifier. CI treats that expected negative result as evidence the test is discriminating; it is **not evidence of a candidate fix**.

## Independent comparison gate

A valid evaluation comparing original v1.7.0 and v1.8.0 requires a fresh host session for each run with independently attested loaded skill sets, actual model/effort receipts, controlled tools, identical task inputs, blinded scoring and real candidate artifacts/diffs. Do not expose evaluator-only tests to an agent under evaluation. If isolation/receipts cannot be established, mark **blocked**, do not invent runs or score unexecuted work.

Existing draft PR #55 and #56 and `main` remain untouched. This PR is prepared separately as draft and must not be merged automatically. No paid model APIs, credentials, third-party archives or model executions in CI.
