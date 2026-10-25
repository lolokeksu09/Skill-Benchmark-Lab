# Separate V4 feasibility check

This branch is intentionally separate from frozen `bench/v4-hard-base` and holds **no implementation code**. It checks two existing frozen V3 source implementations, with the **V4 API and isolated browser tests**, to detect impossible or inconsistent tests before new model attempts.

Source candidate commits are fixed. The workflow temporarily copies **only** V4 test files into each checkout, never mutates candidate repository branches and never changes frozen V4 base. This is a non-scoring, **post-hoc feasibility check**: prior candidates have been seen during V3 and are not independent V4 model runs. Results are not added to the future 15-trial score table.

Avoid providing this branch or its results to Codex tasks. Each new V4 trial must start from `bench/v4-hard-base` with no previous implementation access.

V4 test head used for this repeat audit: `98245ac84bf3ff2f1a432f00e2e08097d4587b59`. The workflow checks out the live V4 baseline by branch; recording the SHA makes the rerun traceable.
