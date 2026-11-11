# Next phase: genuinely independent agent evaluation (not executed)

The 1/10 vs 10/10 exploratory repair pilot in this PR is **not** proof of plugin efficacy. The frozen V4 control is known to be defective, and the candidate was authored manually in a single session.

## Preregistration

Before generating any new outputs, freeze:
- two or more unseen web/native tasks, starter Git SHA, functional contract, viewport/device matrix, expected outputs and hidden tests;
- **arms:** A = same model with no Unified plugin; B = same model with Unified Development & Design v1.0.1;
- at least **three independent fresh-context attempts per arm and task**, identical model/effort, tool permissions, execution budget, starter code and task text;
- no access to other attempts, previous candidate fixes, holdout test code or review results before submitting;
- exact loaded skill files/versions and archive SHA, environment, tool trace, elapsed time/token data only when actually observable.

## Scoring

Record objective tests (failures are non-negotiable), test coverage and regression risk, source diff and scope violations, basic a11y metrics, responsive overflow, frontend injection safety, interactions, and empty/loading/error states. Review anonymized screenshots independently on design fit, typographic hierarchy, information architecture, mobile use, visual individuality, gratuitous decoration and coherence. Use the same rubric for both arms. Shuffle labels; prevent judges from learning the arm. Report missing evidence as missing, not PASS.

## Analysis

Report **per-attempt** results, mean/median, variance and defects; do not infer causality from one successful example. Separate web and native outcomes. Android Compose claims need Compose fixtures and real SDK/emulator instrumentation, not just the Java Views smoke fixture here. State device API and viewport.

## Release / safety

Never modify frozen V4–V6 tests or leak hidden answers into agent contexts. Keep the independent trial on another branch/PR with a new protocol version. No paid API calls or model execution without separate authorization and an auditable configuration. Do not overwrite or merge this draft PR to start agent trials.
