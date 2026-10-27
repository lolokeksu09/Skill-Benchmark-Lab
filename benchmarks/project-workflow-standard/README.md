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

## Additional recovery study

The separate [recovery-v1 study](studies/recovery-v1/README.md) adds eight fresh-context applications of the unchanged v1.1/v1.2 instructions: two new tasks, two applications per cell. Both versions pass 78/78 repeated independent checks. It covers transient reads, local simulator writes with an unknown outcome, preservation of user work, a canceled apply step and accurate reporting of an unavailable provider gate. [Results and limits](studies/recovery-v1/RESULTS.md). It does not establish superiority or real-provider/UI/production behavior; the serving model identifier remains unavailable.

## Safe replay and evaluation

Use `python3 benchmarks/project-workflow-standard/hardened.py replay` for both frozen studies. This entry point rejects optimized Python because the preserved verifiers use assertions. It does not change historical snapshots or scores.

For a fresh recovery application, use `python3 benchmarks/project-workflow-standard/hardened.py evaluate --work-root /path/to/isolated-work VERSION CASE REPEAT`. Exit 0 means automated checks passed, 1 means a failed or unexpected result, and 2 means at least one unavailable check; review the JSON for details. Evaluation works on temporary copies. These checks do not establish that reports are truthful or complete: review document meaning separately, and treat agent-controlled event files as evidence of recorded state rather than an independent action log.

## Observer-controlled local registry

`observer.py` provides an ephemeral loopback HTTP registry for **new controlled trials**. It records accepted publish and status requests in the serving process, outside the candidate's project files. `RegistryObserver().snapshot()` returns the observed requests and receipts, and `assess(snapshot)` checks one committed-unknown write followed by a successful status for its receipt. CI exercises correct recovery, missing or mismatched status, duplicate writes, empty observations and a forged workspace state file. A recorded found status means the server processed a matching request and prepared a response; it does not prove that a client received or understood it.

The fixture is not a hardened sandbox. It does not observe commands, other files, external networks or every tool call; running untrusted code under the same OS identity is not a security boundary. The server records only requests that reach it, and its in-memory data must be exported and preserved by the supervising runner before shutdown if a future trial needs a durable record. Old recovery-v1 results were produced using the original simulator and have not been retroactively upgraded. No new AI application is run by CI.

`python3 benchmarks/project-workflow-standard/observer_demo.py` runs three synthetic subprocess controls and emits their recorded events and assessments as JSON; CI preserves that output in the job log. These controls do not represent new agent applications.

For runners that do not share a network namespace, `fifo_observer.py` offers a Linux named-pipe transport: start `serve PIPE ALLOWED_PROJECT_DIRECTORY` in a supervising process, wait for its ready message, then use `client PIPE publish REQUEST_ID PAYLOAD` or `client PIPE status REQUEST_ID` from the allowed project directory. A newline on the server's standard input stops it and outputs the observer snapshot and assessment. Preserve its stdout outside the candidate project. The FIFO adapter and HTTP fixture have the same evidence limitations; neither proves a complete process history or provides isolation from a malicious process under the same OS identity.

One exploratory agent application, the failed TCP attempt, the successful FIFO observation, and the parent preflight are documented in [observer-pilot-v1](studies/observer-pilot-v1/README.md). This does not change or re-score historical applications.
