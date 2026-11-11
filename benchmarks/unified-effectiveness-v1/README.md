# Unified Effectiveness Benchmark v1 — web preflight

**Scope:** New independent A/B evaluation framework for `Unified Development & Design v1.0.1` in the user's `Skill-Benchmark-Lab`. Not a completed A/B experiment.

## Reproduce locally

Python 3.12+ and Chromium installed:

```sh
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 score_web.py --candidate starter --out /tmp/unified-control
python3 selftest.py
```

`score_web.py` accepts any folder with `index.html`, `styles.css`, `app.js`, and writes JSON and optional screenshots (`--screenshot`). It returns **0 only for 18/18**; any failure returns nonzero. Use `--out` outside the candidate folder. The fixed mocked queue API lives under `fixtures/`, not in candidate files. Browser rendering uses in-memory HTML/CSS/JS to avoid dependence on blocked localhost navigation. The scorer never invokes an LLM.

## Recorded calibration (2026-11-11)

| Artifact | Browser contract | Status |
|---|---:|---|
| Intentionally incomplete `starter/` | **3/18** | Correctly rejected (exit 1) |
| Locally authored reference (not in public repo) | **18/18** | Positive calibration (exit 0), **not an agent trial** |
| Six independent agent arms | **0/6 executed** | No agent-run tool available in the current session |

Results can establish deterministic contract compliance but **not visual originality or benefit caused by a plugin**. The reference implementation was authored by the same assistant and is excluded from this benchmark's comparison arms.

## Run matrix

See `RUN-MATRIX.csv`: three fresh independent sessions per arm with identical input snapshot/model/effort. Record artifact hashes and exact evidence. Keep source `main`, existing PR #50/#51 and all frozen Lab tracks untouched. Use a new branch/PR for trial outputs; do not upload private plugin ZIP to a public repository.