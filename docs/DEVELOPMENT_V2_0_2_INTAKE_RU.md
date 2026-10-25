# Development & Design Skills 2.0.2: external retest

Date: 2026-10-25. Input: uploaded ZIP files; the packages were never committed to this public repository. Exact SHA-256 checksums are in [intake snapshot](../benchmarks/snapshots/development-design-2.0.2-2026-10-25.json).

## Findings

- The two issues reported in PR #3 (negated React Native; abandoned Compose before CSS task) **are fixed**.
- The bundled test runner `skills/skill-router/scripts/test_router_context.py` completed: **76/76**.
- `docs/reproduce/reproduce.py` completed with exit status **0**.
- All **116** `SKILL.md` files are byte-identical to 2.0.1 (active SKILL.md 614,884 bytes).
- Compared with 2.0.1: 1,195 existing files unchanged, 5 modified, 5 added, 0 removed.
- The release plugin identity changed from `development-design-skills-v2` to `development-design-skills` while version increased to 2.0.2. Treat installation/update collision behavior as **unverified**.

## Additional checks (not included in the release's 76)

Using 18 prewritten RU/EN prompts (see [cases](../benchmarks/diagnostics/router-independent-cases-v202.json)), with required and forbidden skills **including deferred suggestions** and predicted stack:

| Version | Passing / Total |
|---|---|
| 2.0.1 | 6 / 18 |
| 2.0.2 | 17 / 18 |

This is a small targeted functional check, not a representative or blinded accuracy estimate. The cases were written after the reviewer had access to the implementation. No timed GPT runs, token measurements or actual app code quality trials were conducted.

## Remaining reproducible defect

**Prompt:** `Build an Android Compose page without using React Native.`

**Expected:** `android-jetpack-compose-expert`, with no React Native expert.

**Observed (2.0.2):** only `verification-before-completion`; no technology stack is detected.

**Cause:** `active_text()` splits text into punctuation-delimited clauses and removes any clause containing `without using`. When the negative technology occurs *after* the positive target in the same clause, it drops `Android Compose` as well.

**Acceptance criteria for next fix:** mask only the forbidden technology, preserving active technologies, explicit skill requests and intended action. Add the prompt to the regression suite and check nearby RU/EN variants and false positive negations.

## Reproduction

1. Verify ZIP SHA-256 against the snapshot and extract into separate temporary directories. Do not execute untrusted code.
2. Run 2.0.2's built-in suite: `python3 skills/skill-router/scripts/test_router_context.py` from any directory.
3. Run its offline reproduction script: `python3 docs/reproduce/reproduce.py`.
4. Run [external comparison script](../benchmarks/diagnostics/check_router_variants.py) with both extracted plugin roots.

*Exit status of the external comparison script is 1 when at least one candidate scenario fails; for this known artifact, 17/18 is expected.* Both prior user projects remain untouched.
