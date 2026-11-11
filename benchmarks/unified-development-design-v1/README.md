# Unified Development & Design v1.0.0 — deterministic plugin smoke track

New, isolated track for the unified plugin. It follows the isolation, provenance and negative-control principles of Skill-Benchmark-Lab without changing the frozen V4–V6 branches or the Project Workflow Standard track.

## Origin

- V4 task family: https://github.com/lolokeksu09/Skill-Benchmark-Lab/blob/bench/v4-hard-base/TASK.md
  - Git blob: eb05392482ab0a2bc933a8f41488e28e34da2212
- V4 protocol: https://github.com/lolokeksu09/Skill-Benchmark-Lab/blob/bench/v4-hard-base/docs/PROTOCOL.md
  - Git blob: 54accbc09f5167cadff8315cc0823d05cc3c812d
- User-supplied private plugin: Unified-Development-Design-v1.0.0.zip
  - SHA-256: 65c3fe72621d1c24579f2b744154efad71ef0e298777cfc66e6ba630ac28de18
- Ten new deterministic test prompts are contained in fixtures.json, with all expected and forbidden skill selections stated before running each case.

## Running locally

Python 3.12+ and a local copy of the plugin archive are required. No external Python dependencies or AI-provider credentials.

    python3 benchmarks/unified-development-design-v1/run.py \
      --archive /absolute/path/Unified-Development-Design-v1.0.0.zip \
      --out /tmp/unified-lab-v1

The runner creates an isolated temporary directory, unpacks the ZIP, validates plugin structure and safe member paths, runs the bundled P2P router suite, runs ten task-derived skill-routing probes, and runs the bundled UI/UX Pro Max unit suite. The exit code is nonzero if any group fails. Detailed local results are saved by the runner in results.json and ui-ux-unittest.log.

## Recorded outcomes, Python 3.13.5

| Check | Result |
| --- | --- |
| ZIP integrity and path safety | PASS, 1,252 entries |
| Manifest, 122 unique skills, 58 Impeccable files | PASS |
| Existing P2P routing regression | 158/158 PASS |
| New V4-inspired routing probes | 7/10 PASS |
| UI/UX Pro Max unit suite | 137 tests pass, 4 import errors, 141 discovered |
| Five required Anti-AI-Slop and Impeccable documents | PASS |
| Negative control: missing Impeccable entrypoint | Correctly rejected |

See REPORT.md for the exact failures. The four test-module import errors are inherited from the source P2P archive because development-only helper scripts were not bundled.

## Evidence boundaries

This track is a deterministic integration check and is **not** Lab V4's 44-point functional test, a blind holdout, or a comparison of AI-agent effectiveness. The test prompts were partly chosen after observing a router failure, so they are regression examples rather than unseen agent tasks. No AI agent, browser, emulator or external Impeccable engine was executed, and there is no measured improvement claim.

Neither the full plugin archive nor any private code is committed to this public repository. Its source is an externally provided local ZIP. The V4 benchmark and CI remain untouched.

To evaluate actual development or anti-AI-slop gains, freeze an independent protocol with repeated fresh-context agent trials, same model and tools across control and candidate arms, functional tests plus rendered-screen audits, and exact source/trace provenance.