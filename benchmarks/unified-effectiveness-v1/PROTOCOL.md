# Unified Development & Design — independent-effectiveness protocol v1.0

Status: **preregistered infrastructure; agent trials NOT RUN**. Public GitHub fixture is a non-blind benchmark framework, not a statistically significant study. Task and evaluator must be frozen at SHA before the first independent trial; any scoring edit requires a new protocol version and fresh runs on all arms.

## Primary question
Does Unified Development & Design v1.0.1 improve web implementation correctness and rendered design versus the same model without the plugin, when both receive the same previously unseen task and starter files?

## Arms and allocation
A = no additional Development & Design P2P, Mobile Design Lab or Unified plugin. B = Unified Development & Design v1.0.1 only; no simultaneous standalone P2P/Mobile plugin. Run **A1, B1, A2, B2, A3, B3** in six new isolated sessions. Never copy a prior result or show a grader, competitor answer, design review or model tool trace to the next agent. Same model, thinking effort, tool access, permitted time and instructions. Record model and effort from actual host settings; mark unverified when unavailable. Do not assume session independence without separate contexts. Do not claim independent agents without completed logs.

## Frozen input and leakage prevention
Provide each agent only `TASK-WEB.md`, the files under `starter/` copied into its own unique worktree, and the immutable API contract/fixture if required for local execution. Keep evaluator and prior solutions out of candidate context, even when stored in the public repo. No edits to task, fixed fixture, test scripts or other candidate arms. Use one starting SHA for all. Do not publish private user code or secrets. Protect against candidate attempts to rewrite task/scorer. The fixture contains harmless intentionally HTML-looking content only.

## Outcomes and grading
The executable `score_web.py` gives **18 equally weighted contract points**: responsive overflow (3), filtering/search, race/rollback, safe rendering, a11y and state correctness. Security and state-integrity failures must also be named separately; high aggregate scores do not override such failures. Report exact failures and per-run results, mean, median and spread (n=3) for both arms.

Rendered screenshots at 375, 768 and 1280 px are assessed **without arm labels** by reviewers under a fixed 1–5 rubric: task fit, content hierarchy, typography, density, interaction hierarchy, UI state visibility, distinctiveness without ornamental AI-slop. Two independent reviewers are preferred; record reviewer disagreements. The same rubric and devices apply to all trials. Screenshots are artifact evidence, not proof of subjective quality by themselves.

Secondary: paths changed, changed lines, package additions, runtime exceptions, accessibility defects, missing states, whether an agent used the selected plugin skill (record paths, versions and hashes), actual CLI/test evidence, time/tokens only if truly observable. No invented costs, metrics or runs. A result with missing treatment verification must be labelled `unverified`, excluded from clean arm comparison and reported separately.

## Controls and threats
Baseline `starter/` is intentionally incomplete; expect the grader to reject it. A locally implemented positive calibration candidate is used only to show the grader can pass a valid implementation; it is **not an independent agent arm**, not uploaded to the public benchmark, and is barred from trial context. Code changes after seeing grader failures contaminate that trial and must be recorded. Public test knowledge means task is **not a hidden holdout**; use fresh unrelated tasks for future independent evaluation. One small web task is insufficient to generalize to Android or broad software engineering.

## Android
Run a **separate versioned Android Jetpack Compose benchmark** with actual on-emulator instrumentation and the same six-session treatment once new Android starter/tests are frozen. Prior Java Views smoke in PR #51 does not constitute Compose effectiveness testing. Never combine scores across platforms without preregistering weights.

## Costs and execution
No paid model API tokens or external service credentials. Agent execution may be done through authorized ChatGPT/Codex sessions if accessible. This repository's CI runs **deterministic tests only**, not AI agents. Do not use GitHub Actions secrets to auto-trigger paid inference without explicit approval. Keep PR draft; never merge frozen benchmark or candidate heads automatically.