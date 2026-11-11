# Unified Development & Design — UI comparison pilot (2026-11-11)

An **exploratory, non-blinded** comparison using the frozen Skill-Benchmark-Lab V4 web fixture. The source control is intentionally defective. The candidate was created manually in one session using the Unified Development & Design UX and anti-AI-slop guidance, **not by independently randomized agents**.

**This pilot does not establish that the plugin is better than no plugin.** It demonstrates executable browser checks and prepares a native Android instrumented test environment for subsequent independent trials.

## Provenance and scope

- Frozen source: `bench/v4-hard-base` in this repository. The three files under `web/control` are byte-identical to the frozen source: `index.html` Git blob `967e604704ff90dd310ef6e4da8c0b395cf24dd4`, `styles.css` `3b6fdf093c77882d97803cde7831f428bd001aeb`, `app.mjs` `2029eebd1caadb921ac4303d1b6c1fafac0e44e1`.
- Candidate: `web/candidate`; identical HTML contract, manually rewritten styling and client interaction logic.
- Both use the same mocked network behavior and Chromium viewport sizes.
- Source plugin: Unified Development & Design v1.0.1, **not** published into this public repository.
- No official V4/V6 benchmark, grading rule, frozen branch, or main application source was modified.

## Web pilot: locally executed

Install Playwright for Python and its Chromium browser (system Chromium is used if available):

```bash
python3 -m pip install -r benchmarks/unified-ui-ab-pilot/requirements.txt
python3 -m playwright install chromium
python3 benchmarks/unified-ui-ab-pilot/run_browser_ab.py
```

The script writes `results/web-ab-results.json` and screenshots next to the script. It stubs API responses because the local sandbox blocked browser navigation to localhost.

Observed on Python 3.13.5 / Playwright 1.57.0 / Chromium:
- Control: **1/10** checks passed.
- Candidate: **10/10** passed.
- Checks: no overflow at 375, 768 and 1280 px; accessible bookmark labels; safe text rendering; >=44px touch targets; rollback after 412; error recovery; stale-search response handling; pagination without duplicate IDs.
- This is a **functional/UX check**, not a psychometric score, visual taste rating, blind human review or evidence of originality.

## Native Android instrumented test

The isolated sample under `android/` is a small **Java Views** UI fixture, not a Compose project and not a generated sample from an independent agent. Four AndroidX Espresso tests cover heading/search, button accessibility and state, rejection/rollback and retry, and layout/touch target dimensions.

GitHub Actions workflow: `.github/workflows/unified-ui-android.yml`. On pull requests touching this sample, it attempts an Android API 35 emulator with JDK 17, AGP 8.13.2, Gradle 8.13, then runs:

```bash
cd benchmarks/unified-ui-ab-pilot/android
gradle --no-daemon :app:connectedDebugAndroidTest
```

**Do not call native tests passed until CI reports success**. Local environment has no Android SDK, emulator or ADB. The workflow consumes runner time when triggered.

## Evidence boundary and next experiment

Real causal testing requires a *new frozen benchmark*: at least 3 independent fresh-context agent attempts per arm (control and Unified), exactly the same unseen task, model, effort, time, and tools; isolation between trials; browser/native tests plus blinded design review; captured invocation/provenance; and no access to the other arm. Keep those results separate from this pilot.

This PR is intentionally a draft. Do not merge into main as an official benchmark score without reviewing baseline provenance, CI behavior, costs, and experimental validity.
