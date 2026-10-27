# Project Workflow Standard — pilot v1.1 / v1.2

This track tests our portable project-workflow archive independently of the P2P/DDS V4–V6 experiments. Existing frozen branches and candidate implementations are unchanged.

## Recorded applications

Four fresh-context agents applied v1.1 or v1.2 instructions to two isolated Python CLI tasks on 2026-10-27. Each pair started from identical product files and the same raw task; instruction files and directory paths differed. Common host instructions remained in effect. No model override was requested; the exact model identifier, costs and full tool-call traces were not captured.

| Task | v1.1 | v1.2 |
|---|---:|---:|
| CSV import: BOM/trim/empty rows, email validation, CLI limit, docs | 12/12 | 12/12 |
| JSON check report: mandatory policy, dirty user edit, canceled plan, docs | 13/13 | 13/13 |
| External integration in JSON task | Unavailable, exit 2 | Unavailable, exit 2 |

The independent evaluator checks behavior, CLI output and selected document/file properties. The total includes those document/file checks. The missing real service is never counted as a successful integration. Both versions passed the recorded checks; superiority, lower token usage, faster completion and broad reliability are **not established**.

Manual review found explicit requirement/evidence tables in the v1.2 reports; the v1.1 reports also covered the requirements using lists. Both preserved the dirty STATUS_LABEL, canceled the obsolete CSV plan and disclosed the integration blocker. One application per version/task is a pilot, not a statistically reliable comparison. The blocked case was not used for post-result instruction tuning.

## Files and provenance

- `instructions/1.1` and `instructions/1.2`: nine-document package snapshots. The v1.2 README includes the later result write-up; executed instruction files are bound by `candidate-frozen.json`.
- `setup.py`: raw tasks and original defective product fixtures. Creates isolated Git directories; no AI or service calls.
- `manifests`: initial file hashes, fixture revision and task for each application.
- `runs`: resulting source/tests, product README, FINAL.md and applicable working plan. Repeated instruction copies and transient files are omitted; manifests bind original instruction inputs.
- `evaluate.py`: original independent grader, ported without changing check criteria.
- `results`: recorded grader outputs, implementation diffs and repeated agent-written unit-test logs.
- `review.json`: manual observations, kept separate from automated scores.
- `redactions.json`: original/published hashes for files with the local workspace prefix replaced by `<workspace>`. No task or scoring criteria were changed. Raw archive receipts remain in the conversation deliverables, not this public repository.
- `verify.py`: deterministic replay, input/provenance checks, and rejection of the known-broken fixtures.

The generator's instruction lookup was adapted to this repository layout. Saved fixture SHAs describe the original applications; freshly generated fixtures will have different Git SHAs. Future protocol changes must be versioned rather than silently rewriting this pilot's snapshots/results.

## Reproduce checks

Python 3.12+ and Git are required; no third-party Python dependencies or credentials.

```bash
python3 benchmarks/project-workflow-standard/verify.py
```

This replays saved implementations in a temporary directory and confirms that known-broken inputs fail the grader. It does **not** launch an AI agent. The GitHub workflow `Project Workflow Standard` runs only this deterministic verification with a read-only token and no deployment or AI-provider credentials.

For a new agent application, generate fresh projects into a new directory:

```bash
python3 benchmarks/project-workflow-standard/setup.py 1.1 --output-root /tmp/workflow-pilot-new
python3 benchmarks/project-workflow-standard/setup.py 1.2 --output-root /tmp/workflow-pilot-new
```

The generator refuses to overwrite an existing case directory. Give a fresh agent only its project directory and the raw task from the corresponding manifest. Keep the grader, expected scores and other implementations out of that agent's context. After completion:

```bash
python3 benchmarks/project-workflow-standard/evaluate.py 1.2 csv --work-root /tmp/workflow-pilot-new
```

Starting new AI applications and any associated costs require owner opt-in. CI alone never starts them. Do not provide a service address just to turn the intentionally unavailable integration into a pass; a real integration result requires separately authorized, real service evidence.

## Next measurements

Before making improvement claims, freeze a new protocol with additional unseen tasks, repeated applications, a confirmed model/environment identifier and separate scoring for requirement coverage, implementation correctness, evidence accuracy, preservation of user work and delivery boundaries. Retry handling, unknown-outcome writes, UI, publication and large production projects remain untested by this pilot.
