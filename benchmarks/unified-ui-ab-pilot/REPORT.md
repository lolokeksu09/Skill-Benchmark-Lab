# Recorded local UI pilot outcome

Date: 2026-11-11. Local executable: Chromium via Playwright; no browser HTTP server, no native Android SDK or emulator.

| Objective UI check | Frozen V4 control | Manually guided candidate |
|---|---:|---:|
| 375px no horizontal overflow | FAIL | PASS |
| 768px no horizontal overflow | FAIL | PASS |
| 1280px no horizontal overflow | PASS | PASS |
| Bookmark accessible names | FAIL | PASS |
| Untrusted title does not execute JS | FAIL | PASS |
| Bookmark touch target at least 44px | FAIL | PASS |
| Rejected 412 bookmark rolls back and alerts | FAIL | PASS |
| Feed 503 preserves prior cards and reports error | FAIL | PASS |
| Stale slow search cannot overwrite newer fast search | FAIL | PASS |
| Pagination handles overlapping IDs | FAIL | PASS |
| **Total** | **1/10** | **10/10** |

**Control was intentionally broken. Candidate was manually authored within a single assistant session.** Not a blinded A/B or independent model evaluation. No measured improvement in visual originality or independent developer productivity is claimed.

## Follow-up on native Android

Four Espresso tests were authored and checked syntactically at the XML/source level. They are intended to run in the proposed GitHub Actions emulator workflow. Local device execution has **not** occurred. Android tests evaluate native Java View interaction correctness, **not** the plugin's Compose skills.

## Reproducibility

Runner: `run_browser_ab.py`. Immutable source control Git SHA values and conditions: see `README.md`. Generated screenshots/JSON are produced locally rather than checked into this public repo. The private plugin ZIP is not committed.

The V4 44-point API/Chromium suite, independent agent arms, complete integration tests and human visual review were not executed by this exploratory pilot.
