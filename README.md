# Skill Benchmark Lab

A reproducible and isolated lab for testing AI skill-assisted development. Repository is **public**: do not commit private projects, tokens, personal data or redistributed third-party plugin ZIPs.

## Variants
1. `control` — same base model, no skills.
2. `p2p-original` — original uploaded P2P archive, pinned by SHA-256.
3. `p2p-improved` — improved P2P prompt generation, pinned by SHA-256.
4. `development` — **Development & Design Skills 2.0.5 Full Patched** (both Security Audit and API Object Access corrections), pinned by SHA-256.
5. `combined` — P2P Improved prompt preparation followed by Development & Design Skills for implementation (both inputs pinned; no combined archive exists).

See [versions and hashes](benchmarks/versions.json), [final 2.0.5 snapshot](benchmarks/snapshots/development-design-2.0.5-full-patched-2026-10-25.json) and [real experiment procedure](docs/REAL_EXPERIMENTS_RU.md).

## Current verified capabilities

- Python offline evaluator for JSONL run reports, human review and medians; missing measurements remain null.
- Four scenario definitions: Android UI, Web layout/a11y, debugging, and large patch planning.
- Web Node 22 reference/baseline with three deliberately seeded defects.
- Kotlin/JVM reference/baseline with state-management bugs; **not** a real APK build.
- GitHub Actions checking reference passes and baseline fails for the expected reason.
- Deterministic router tests recorded from external plugin ZIPs; final 2.0.5 tested **153/153 locally**, but this is NOT an AI coding benchmark.
- Reproducible SHA-256 provenance of the five experimental arms; the final plugin ZIP itself stays external.

## Reproduce available checks

```bash
python -m unittest discover -s tests -v
python -m evaluator.benchmark --scenarios benchmarks/scenarios.json
FIXTURE_VARIANT=reference node --test benchmarks/fixtures/web/tests/feed.test.mjs
gradle -p benchmarks/fixtures/android run -PfixtureVariant=reference
```

Baseline fixture runs intentionally fail:
```bash
FIXTURE_VARIANT=baseline node --test benchmarks/fixtures/web/tests/feed.test.mjs
gradle -p benchmarks/fixtures/android run -PfixtureVariant=baseline
```

## First measured control trial (Termux, Qwen3-8B)

One real phone-generated Web candidate is archived as a **synthetic public fixture**, with no skills loaded. The user-observed inference was **51.518 seconds, 365 tokens**. Node 22 executed the three fixture tests on the saved code: **1 passed, 2 failed** (HTML escaping, save-button accessible name). See [recorded measurement](benchmarks/measurements/qwen3-control-trial-001.json). This is a single observation, not a model or skills ranking. Candidate code was inspected before local Node execution; the temp directory is not a hardened sandbox.

To re-run the deterministic candidate checks:

```bash
FIXTURE_VARIANT=candidate-qwen3-control-001 node --test benchmarks/fixtures/web/tests/feed.test.mjs
```

This command **intentionally exits nonzero** with the two recorded defects. GitHub Actions asserts that exact fail/pass pattern.

## Next missing capability: real model-execution trials

**No controlled model-vs-model or skills-vs-no-skills coding experiment has been executed.** GitHub CI tests only offline evaluator and seeded fixture sensitivity. Do not rank the five variants from the router's 153 passing checks.

Record the same model/runtime, tool permissions, inputs and repeated trials per variant. Import a local `results/raw/<experiment>.jsonl` into `python -m evaluator.benchmark --scenarios benchmarks/scenarios.json --results ...`; never fabricate missing tokens, latency or review scores. Keep runnable candidate code and sensitive transcripts outside the public repository until reviewed.

See [experiment protocol](docs/PROTOCOL.md) and [Russian handoff](docs/REAL_EXPERIMENTS_RU.md).

## Pull requests and release hygiene

The repository currently has a stacked chain of draft PRs (#1–#7). This PR adds provenance on top; **main remains at the original README** until reviewed. Merge dependencies in order rather than assuming all proposed work is live.
