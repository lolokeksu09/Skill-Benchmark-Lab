# Unified Development & Design v1.0.1 — follow-up verification

New report for the **same deterministic Lab smoke track**. This is not a new frozen trial, independent agent comparison, or V4 functional score. The previous v1.0.0 report remains unchanged for auditability.

## Exact artifact and method

- Plugin ZIP: `Unified-Development-Design-v1.0.1.zip`
- SHA-256: `dbe9fa22c79e3b19c5de78078d7ebe46fc954fe5210437c00b4a3f908f693462`
- ZIP size: 4,455,434 bytes; 1,251 entries; 122 unique skill entrypoints.
- Test runner: `benchmarks/unified-development-design-v1/run.py`, now accepts `--expected-version` (defaults to v1.0.0 for backward compatibility).
- Fixture: unchanged `benchmarks/unified-development-design-v1/fixtures.json` (ten authored test prompts, **not** a blind holdout).
- Repro command: `python3 benchmarks/unified-development-design-v1/run.py --archive /local/path/Unified-Development-Design-v1.0.1.zip --expected-version 1.0.1 --out /tmp/unified-v101-results`.

## Deterministic results

| Check | v1.0.0 baseline | v1.0.1 |
| --- | --- | --- |
| P2P original routing regression | 158/158 PASS | **158/158 PASS** |
| Lab-derived routing probes | 7/10 | **10/10 PASS** |
| Portable UI/UX Pro Max tests | 137 pass + 4 upstream-only module import errors | **137/137 PASS; 4 upstream-only modules preserved, NOT RUN** |
| Plugin integrity, references, 122 skill entrypoints | PASS | **PASS** |
| Full independent AI agent executions | NOT RUN | **NOT RUN** |
| Impeccable external engine | NOT RUN | **NOT RUN** |
| Android device/emulator | NOT RUN | **NOT RUN** |

There are 121 entries in the offline router's specialist catalog, covering all six bundled integration-specific skills; the separate router itself is the 122nd entrypoint. The false `AI-slop` -> `observability-engineer` match is fixed with bounded SLO/SLI patterns, while a true SLO task continues to route. ETag/concurrent writes now classify as high risk and prioritize TDD in the initial specialist set.

**Developer-only test packaging:** Four source test files expected unbundled maintainer scripts and could never import in the distributed plugin; they are preserved byte-for-byte under `docs/upstream-source-only-tests/` and are not claimed as passing. This reduces import errors; it does not restore source-only coverage.

## Separate Chromium inspection of the frozen V4 web baseline

Local sources `web/index.html`, `web/styles.css` and `web/app.mjs` were fetched from `bench/v4-hard-base` and validated byte-for-byte using Git blob SHAs. Chromium launched under Playwright, but the environment blocked loopback navigation; the source was instead rendered with `document.set_content` and an in-memory `fetch` stub. Results on the **intentionally defective, unchanged baseline**:

- At **375 px**, `scrollWidth=1184` vs `clientWidth=375` (horizontal overflow).
- Two bookmark buttons lack `aria-label`/`aria-labelledby`.
- Test-only untrusted title HTML triggered a harmless local `window.__labXSS` flag, demonstrating unsafe `innerHTML`.
- Rejected bookmark update `412`: `aria-pressed` changed `false -> true` without rollback.
- At 1280 px, no horizontal page overflow.

These findings prove the fixture can expose specified issues in a real browser renderer. **They do not prove the unified plugin fixes them**, nor is this the repository's 11-point Chromium suite. No external server or user project was affected.

## Native Android evidence boundary

`native-android-compose` and `negative-react-request` routing probes passed. The Jetpack Compose UI/UX Pro Max lookup returned applicable guidance; Impeccable's Android/audit.native references are present. **No Android SDK/emulator/ADB or connected device was available**, so no on-device UI screenshot, APK or Compose build was produced.

## Preservation

The saved plugin was updated to v1.0.1 (same private plugin ID); prior P2P and Mobile Design Lab sources were unchanged. All frozen Lab branches, grading code, official test scores and `main` were left untouched. This follow-up is on the draft PR branch only.

## Next evidence for quality claims

Freeze unseen web/Android tasks, execute independently in fresh contexts with matched model/effort and control arms, run browser/native functional tests plus visually reviewed screenshots, and record exact tools/skills loaded. These new deterministic regressions are evidence of a router fix, **not measured design uplift**.
