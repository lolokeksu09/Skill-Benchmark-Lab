# Development & Design Skills 2.0.3: independent review (2026-10-25)

**Source:** uploaded `Development-Design-Skills-2.0.3.zip`, SHA-256 `42d5a5b060ebdb2e89645ce63f88f94c148babde4b69d60e1efff8c14ab984cb`.

## Reproduced release checks

- CRC/testzip passed; 1,208 files in archive, including 116 `SKILL.md`.
- Against 2.0.2: 1,201 unchanged files, 4 modified, 3 added, none removed. All 116 `SKILL.md` files are byte-for-byte unchanged.
- `python3 skills/skill-router/scripts/test_router_context.py` passes **77/77**, preserving 76 existing scenarios and adding the previously failing English exclusion.
- `python3 docs/reproduce/reproduce.py` exits 0.
- Exact prior independent corpus of 18 cases, reexecuted locally against both routers: **2.0.2 17/18** → **2.0.3 18/18**.

### Fixed defect

`Build an Android Compose page without using React Native.`

Now selects `android-jetpack-compose-expert` and suppresses `vercel-react-native-skills`. Result includes android + compose and excludes react-native.

## Newly discovered negation gaps

Eleven additional focused RU/EN formulations were exercised against both packages after the fix was available; see [input cases](../benchmarks/diagnostics/router-negation-extended-v203.json) and [observed results](../benchmarks/diagnostics/router-negation-extended-results-v203.json).

- 2.0.2: **2/11** passed; 2.0.3: **4/11** passed.
- Current 2.0.3 still selects React Native when asked `Build an Android Compose screen without React Native.`, `Use Kotlin Compose rather than React Native.`, or `Сделай Android Compose экран без React Native.`.
- `React Native is not allowed` and `Stop using React Native and build Compose UI` likewise remain out of scope of the exclusion patterns.
- The inverse prompt `Implement React Native UI without using Compose.` was fixed in 2.0.3.
- **These are limitations of the lexical routing helper**, not proof that the full model will follow forbidden-technology suggestions.

## Recommended next fix

Use bounded phrase-level negation/exclusion patterns for `without <technology>`, `rather than <technology>`, `<technology> is not allowed`, `stop using <technology>`, RU `без <technology>` and `без использования <technology>`, while retaining the affirmative stack from adjacent or preceding clauses. Avoid removing the entire sentence or blocking explicitly requested skills.

Record new regression cases before editing the route implementation. Preserve 77 existing checks. There is no need to modify the 116 specialist `SKILL.md` files.

**Scope:** no actual model tasks, deployments or token-cost measurements were performed; both ZIP packages are kept out of the public repository.
