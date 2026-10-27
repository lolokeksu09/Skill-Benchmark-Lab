# Recovery and delivery — additional applications

This study applies the unchanged v1.1/v1.2 archive instructions to two new local tasks, twice per version/task. The protocol and independent evaluator were saved in commit `0da941dde8648a3b9ccde093d3a0c75941e41ade` before agent execution. See [PROTOCOL.md](PROTOCOL.md) for the frozen scope and limits. The original CSV/JSON pilot remains separate and unchanged.

**Completed:** both versions scored 78/78 repeated independent checks; all eight unit suites passed. Four real-provider checks remain unavailable, excluded from pass counts. [Results and limitations](RESULTS.md), [per-application scores](summary.json), [manual report review](review.json). This does not establish superiority of v1.2.

`registry` combines manifest implementation with a transient read failure and an acknowledged connection loss after a committed local write. `restore` combines a preview-only feature with dirty user settings, a stale apply plan and an unavailable required provider check. Simulators record API events, enabling checks of behavior beyond generated code.

## Reproduce saved evidence

Python 3.12+ and Git, standard library only. For both frozen studies use the guarded entry point:

```bash
python3 benchmarks/project-workflow-standard/hardened.py replay
```

The verifier checks frozen input/output hashes, replays the independent product/workflow checks, runs application unit suites and rejects pristine broken fixtures. It does not start AI agents or perform delivery again. A passing replay means that saved results are reproducible; recorded application failures must still be read as failures.

To generate new independent directories, without launching an AI application:

```bash
python3 benchmarks/project-workflow-standard/studies/recovery-v1/setup.py --output-root /tmp/new-recovery-study
```

The generator refuses to overwrite existing application directories. Agent instructions and tasks must remain separate from the evaluator and other applications. A new model comparison requires a separately frozen protocol, not changes to this study's evidence.

Full tool-call traces, serving model identifier, token counts and costs are unavailable. Common host instructions may account for behavior shared by both versions. Eight applications cannot establish general superiority or production reliability. UI, actual mid-turn changes and real integrations remain untested.

The preserved `evaluate.py` is historical and its exit code does not account for `unexpected` statuses. For new applications use the `hardened.py evaluate` command documented in the track README: it separates failed, unavailable and successful checks and asks for human review of document content and agent-controlled logs.

Agent final messages are preserved in agent-finals/; their sandbox links refer to the original conversation workspace. Repository copies live under runs/VERSION/TASK/REPEAT/. No transcript path was silently rewritten. The initial relative-path control invocation and three neutral resumptions are disclosed in RESULTS.md. Automated replay uses absolute paths.
