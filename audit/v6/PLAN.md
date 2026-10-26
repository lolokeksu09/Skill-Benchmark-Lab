# V6 — compact differential benchmark protocol

**Status:** focused test baseline implemented; candidate runs not started.  
**V4 source SHA:** `efca49e75711b40a9fcdb2549434d810c8d35fd0`  
**V6 baseline branch:** `bench/v6-hard-base`  
**V5 review:** [PR #26](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/26)

## Decision

P2P Original is the **provisional behavioral reference** from V5, not the source base for other methods. All five candidates must branch from the exact same V6 baseline SHA. This avoids giving one method an implementation head start.

To reduce test fatigue and runtime, V6 runs **five grouped checks only**: three Node HTTP contract checks and two real-Chromium checks. The V4 suite's 44 checks already passed for all five V4 candidates, so the V6 workflow does not rerun them. This is a focused differential probe, not a replacement for the V4 regression evidence or a full security audit.

## Five checks

1. **Authorization, privacy, malformed JSON and recovery** — anonymous 401, private-record access control, malformed authenticated JSON rejected without mutation, server remains responsive.
2. **Pagination and cursor contract** — full traversal without duplicates, invalid limits, impossible cursor, and cursor/query binding.
3. **HTTP bookmark CAS** — two concurrent PUTs with the same ETag yield one 200 and one 412; ETag and final version/state agree.
4. **Chromium rendering smoke** — no XSS injection, accessible bookmark name/state, no horizontal overflow at 375px.
5. **Chromium rollback and Load more** — failed un-save restores prior `saved=true`; rapid double activation does not issue duplicate cursor requests or duplicate cards.

Files:
- `tests/v6-contract.test.mjs`: three grouped HTTP tests.
- `tests/browser_v6.py`: two grouped Chromium tests.
- `.github/workflows/benchmark-v6.yml`: candidate-path guard and focused test workflow.

## Run protocol

1. Keep V4 and PRs #21–#25 unchanged.
2. Freeze `bench/v6-hard-base` after the five tests and workflow are verified.
3. Run Control, P2P Original, P2P Improved, DDS 2.0.5 and Combined from that exact SHA, one branch/PR each; do not merge.
4. Report contract failures separately from defensive fault injection. Do not convert five grouped checks into a universal quality score.
5. Record generation time, CI time, and authoritative token usage as separate fields. If the platform does not expose a value, record `null` and its reason. Never infer actual tokens from patch size or coding time from CI duration.

## Limits

- V6's five checks are intentionally selective; they do not cover every V4 requirement, dynamic dataset mutation, full manual accessibility, or distributed-database concurrency.
- The HTTP CAS test exercises the current single-process fixture, not a multi-process production store.
- Fault-injection results do not prove the normal server emits malformed success responses.
- No merge or deployment is authorized by this protocol.
