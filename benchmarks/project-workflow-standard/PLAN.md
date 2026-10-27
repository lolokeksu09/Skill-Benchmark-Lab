# Workflow archive track — integration plan

Base: `main` at `961706ada8a6513a5c96b77d2f1fe6ec44ca3194`.
Scope: preserve the completed v1.1/v1.2 pilot, add deterministic replay and an isolated CI job. No new AI applications, changes to V4–V6 branches, production code, secrets or deployment.

1. Preserve raw tasks, instruction snapshots and application provenance. Publish workspace-path redactions explicitly.
2. Port generator paths, keep grader criteria unchanged, verify archived outputs and reject known-broken fixtures.
3. Open a topic PR; exercise a deliberate integrity failure and a passing final revision in GitHub Actions.
4. Record exact commit/job evidence in the PR. Leave integration unmerged for review; no claim of superiority from the small pilot.

Delivery: local checks plus a saved GitHub branch/PR. Final status comes from the PR description and exact-head checks.
