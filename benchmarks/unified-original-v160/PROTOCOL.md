# Protocol — Unified original 1.6.0 evaluation

**Pre-registration date:** 2026-11-12. **State:** tasks and rubric frozen; actual agent runs 0.

## Question and arms

Does giving the **independently written** Unified Development & Design skills to an otherwise matched assistant change the quality of results on the 10 tasks?

- **A / control:** no Unified skills.
- **B / comparator:** Unified original v1.5.0 only.
- **C / candidate:** Unified original v1.6.0 only, ZIP SHA-256 `4ff398e18db9d0cb86b9b63a738a5fec5cf2e4aa129e4257bf5e312e213ea023`.

Use the exact same accessible model, effective thinking effort, common tools, initial inputs and user-facing task prompt for all three arms. Pin actual host-loaded skill manifests and hashes, not just files stored on disk. At least three independent repetitions per task/arm are recommended (90 trials total); never treat one run as statistical confidence.

## Isolation gate (required *before* trial 1)

1. The candidate agent must run in a fresh session without evaluator source, earlier runs, source plugin in other arms, or cross-arm memory. Use separate accounts/workspaces or explicit per-session plugin profiles when supported; do not globally uninstall plugins merely to simulate isolation.
2. Export actual available skill registry per arm, tool manifests, model/effort execution receipt, environment identity and task input hash. A prompt saying 'ignore the plugin' is **not** isolation.
3. A human evaluator retains `TASKS.json` and evaluator-only tests; do not expose hidden acceptance criteria or its negative controls to candidate agents. The public GitHub repository itself is not secret. Create a candidate workspace containing only the applicable starter files and prompt.
4. Randomize run order; preserve exact budget/time/call limits and reset any persisted state between runs. Changes to frozen task/scorer after seeing outputs must be separately versioned.

If the host cannot attest plugin isolation or effective model/effort, do **not** run a claimed independent A/B evaluation. The current session does not provide these guarantees.

## Artifacts and evaluation

Each trial must have: task ID, arm, invocation/session receipt, exact input manifest hash, resulting patch/text, SHA-256 of output, build/test commands and logs, runtime environment, and omitted/untested cases. Candidate outputs are evaluated **blindly**, without knowing arm label.

Score every task's three acceptance criteria using [SCORING.md](SCORING.md). Reject a task when its two negative controls are violated. For fixture-backed tasks, execute evaluator tests against the candidate files; a narrative assertion without test evidence does not pass a behavior check.

Record failed runs and timeouts, not only successes. Report per-task distributions, paired comparisons and effect uncertainty; do not erase missing outcomes or assign unexecuted trials a zero score.

## Claims boundary

A suite-validator PASS confirms only that benchmark metadata is consistent. A broken baseline test rejection confirms the test can detect at least one seeded defect. Neither implies the plugin improves agent quality. No agent effectiveness result may be claimed until real isolated A/B/C trials produce auditable artifacts.
