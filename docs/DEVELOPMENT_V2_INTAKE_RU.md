# Intake: Development & Design Skills 1.6.0 versus 2.0.1

Recorded 2026-10-25 from uploaded ZIP archives. This is a **static intake and reproducible router smoke test**, not a model-evaluated Android/Web coding benchmark.

## Exact source artifacts

| | Baseline V1 | Candidate V2 |
|---|---|---|
| Uploaded filename | `plugin.zip` | `Development-Design-Skills-2.0.1.zip` |
| Plugin manifest version | `1.6.0` | `2.0.1` |
| Plugin identity | `development-design-skills` | `development-design-skills-v2` |
| Skill entry points | 115 | 116 (new `skill-router`) |
| ZIP files | 1,108 | 1,200 |
| Active SKILL.md UTF-8 bytes | 901,206 | 614,884 |

Hashes, byte sizes and machine-readable results are in [intake JSON](../benchmarks/snapshots/development-design-v1-v2-2026-10-25.json). Keep original ZIPs outside this public repository unless license and distribution scope are reviewed.

## Diff findings

- All 115 original skill names exist in V2.
- Of the original 1,108 files, 1,047 are byte-identical. Another 61 differ, including 59 modified SKILL.md and two plugin manifest files.
- All 59 modified SKILL.md have an exact byte-identical V1 copy in corresponding `V1-REFERENCE.md` inside V2.
- 92 additional files exist; none of the baseline files are missing.
- Active SKILL.md payload is 31.77% smaller by raw bytes; **this is not model token usage, time or billed cost**.
- V2 bundled router regression was independently re-executed against its own 56 cases: 56/56. It was developed using previously examined cases and cannot establish generalization.

## New adversarial smoke observations

The uploaded V2 router was imported from `skills/skill-router/scripts/route.py` together with its bundled `references/catalog.json`, and exercised on short Russian tasks. See [raw cases](../benchmarks/diagnostics/router-smoke-2026-10-25.json).

1. `Мы отказались от React Native. Нужен экран на Kotlin Compose.` gives both `android-jetpack-compose-expert` **and** unwanted `vercel-react-native-skills`.
2. `Мы обсуждали Compose, но теперь исправить CSS сетку веб страницы.` incorrectly includes `android-jetpack-compose-expert` for a web CSS task.

These are **targeted negative cases**, not an estimated error rate. They demonstrate gaps in handling abandoned stacks and transition words. Because the router produces suggestions, an agent may correct these with semantic reasoning; the failures concern the standalone lexical component.

## Reproduction commands

```bash
sha256sum plugin.zip Development-Design-Skills-2.0.1.zip

# Extract V2 to a local temporary directory, then from its plugin root:
python3 skills/skill-router/scripts/route.py --task 'Мы отказались от React Native. Нужен экран на Kotlin Compose.'
python3 skills/skill-router/scripts/route.py --task 'Мы обсуждали Compose, но теперь исправить CSS сетку веб страницы.'
```

The archive includes its own evaluation datasets at `docs/evaluation/`; they were read and the 56-case regression re-evaluated in an isolated temporary directory. The uploader's packages were not modified.

## Next benchmark phase

Pin a new hidden holdout **before** changing the router, apply identical prompts and confirmed-stack labels, compare qualified outputs with human-labeled required/forbidden skills, and finally test end-to-end coding performance with the separately controlled execution tools. Avoid using a public fixed holdout as an unbiased final score after repeated tuning.
