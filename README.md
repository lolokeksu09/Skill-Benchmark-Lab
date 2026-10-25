# Skill Benchmark Lab

A reproducible, isolated laboratory for measuring AI skill-assisted prompt quality and engineering effectiveness.

**Variants:** no-skill control, P2P Original, P2P Improved, Development & Design Skills, and combined P2P + Development.

## Current capabilities (v1 + proposed v2)

- Four scenarios: Android/Kotlin, Web, debugging, and complex planning.
- Python offline evaluator for recorded runs: input validation, medians and human review scores. Missing measurements remain `null`.
- Synthetic **Web** reference/baseline fixture with three deliberate defects. Tested with Node 22 builtin test runner.
- Synthetic **Kotlin/JVM** reference/baseline fixture for Android-adjacent state logic. Built and executed with Gradle + Kotlin JVM plugin.
- CI checks that references pass and seeded baselines fail **for the expected reason**.
- Version/provenance manifest in `benchmarks/versions.json`. P2P original/improved archive hashes pinned; Development Skills awaiting immutable snapshot.

### Run locally

```bash
python -m unittest discover -s tests -v
python -m evaluator.benchmark --scenarios benchmarks/scenarios.json
FIXTURE_VARIANT=reference node --test benchmarks/fixtures/web/tests/feed.test.mjs
gradle -p benchmarks/fixtures/android run -PfixtureVariant=reference
```

The baseline runs intentionally fail:

```bash
FIXTURE_VARIANT=baseline node --test benchmarks/fixtures/web/tests/feed.test.mjs
gradle -p benchmarks/fixtures/android run -PfixtureVariant=baseline
```

See [fixtures guide](benchmarks/fixtures/README.md) and [comparison protocol](docs/PROTOCOL.md).

## Important limits

**No actual model benchmark has been run.** Passing CI proves only that fixture tests distinguish seeded defects from corrected reference code; it does not rank the models or Skills. Kotlin/JVM is a small logic test, not an Android APK or instrumented Compose test.

Model invocation, API costs, exact token usage, blinded human ratings and complete skill snapshots require a separate controlled evaluation phase. The repository is public: **never store tokens, private files, production code or personal information.**

## Workflow

- PR #1 introduces the offline evaluator and protocol.
- PR #2 adds verified fixtures and pins P2P metadata; it is stacked on PR #1.
- Merge PR #1 before merging PR #2. The `main` branch stays unchanged until review.

NOX and WrCommunity repositories are not modified.
