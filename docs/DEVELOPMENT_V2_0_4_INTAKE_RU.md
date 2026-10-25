# Development & Design Skills 2.0.4 — verification

**Source archive:** `Development-Design-Skills-2.0.4.zip` (SHA-256 `f9df305963c4d9554cdd467b2973d5f2d5c0b99cd1463158406d0cf15ad8b642`). Locally generated from uploaded and pinned v2.0.3 archive. No files from the user's NOX/WrCommunity projects were read or modified.

## Verification results

- ZIP CRC and traversal checks passed; **1211 ZIP entries**.
- Diff vs 2.0.3: **6 existing files edited, 3 files added**, no removals.
- All **116 SKILL.md** files are byte-identical.
- Original **77** router cases preserved; **23** regression cases added.
- Fresh re-extraction from final ZIP then `python skills/skill-router/scripts/test_router_context.py`: **100/100 passed**.
- Comparison from exact archives on 23 new prompts: **2.0.3 9/23** → **2.0.4 23/23**.
- Comparison from exact archives on the previously published eleven targeted prompts in PR #5: **2.0.3 4/11** → **2.0.4 11/11**.
- Legacy `docs/reproduce/reproduce.py` exited 0. It recreates the historical 2.0.1 **skill texts**, not exact v2.0.4 routing logic.

## Technical fix

The candidate router now masks *only directly rejected technology tokens* for `without <stack>`, `rather than <stack>`, `<stack> is not allowed`, `stop using <stack>`, `без <stack>` and similar RU/EN forms. `instead of` is no longer confused with a historical stack switch. Contrast boundaries `but` / `но` and `and build` / `и сделай` keep the positive target available. Explicit selection and positive React Native scenarios remain checked.

The 23 prompts and recorded pass/fail evidence are in [cases](../benchmarks/diagnostics/router-negation-v204-cases.json) and [results](../benchmarks/diagnostics/router-negation-v204-results.json). This is a **deterministic offline helper test**, not a model benchmark.

## Next stage

Review PRs #1 through #6 in dependency order before merging into main. To test agent quality, capture reproducible prompts, model/runtime settings, tool permissions, measured latency/cost and blinded results. No paid inference is invoked in CI.
