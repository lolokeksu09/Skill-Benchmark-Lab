# Skill Benchmark Lab V4 — frozen, isolated comparison protocol

## Objective
Evaluate the value of supplementary skill/prompt instructions on **one strong coding model**, not whether a test author can influence scores. The experiment uses Codex Cloud within the user's existing ChatGPT subscription, never paid API tokens. V3 revealed a cross-test server state leak; V4 does **not** reuse that broken isolation method.

## Fixed execution configuration
- User-selected Codex Cloud model: **GPT-6.1 Sol**; effort **Medium**. Verify in UI for every attempt. Codex text reports and GitHub commits cannot attest the actual model independently; mark absent evidence `unverified`.
- Base is the **exact frozen commit** of `bench/v4-hard-base`; no starting from `main` or another trial branch.
- Node 22, Python 3.12, Playwright 1.56.0, Chromium in CI. Same tools and available effort budget per arm; if limit exhausted, stop and mark trial incomplete, do not pay for API/credits.
- New conversation/session per attempt. Do not browse other PRs, other candidate branches, discussions, history of solutions or reviews.

## Arms and repetitions
**5 variants × 3 independently initiated trials = 15**:
1. `control`: no P2P or extra DDS package.
2. `p2p-original`: externally pre-composed prompt with actual P2P 9 original package, checked against frozen SHA `daee2df26f09c7b9bd0b11a5af4675c738dd119a7c8da0744c1e55c226bd23a8`.
3. `p2p-improved`: externally pre-composed prompt with improved P2P package SHA `b4162a2c6118a4f12bbbd1bcc0d6acd5311c671cce56e3ff58f158722ef0f1d5`.
4. `development`: actual DDS 2.0.5 Full Patched SKILL.md instructions used in execution; expected package SHA `c6fe56e96644ae30b8ba07c35cd6a52a5a7ad34920558923ea1c947023db3439`.
5. `combined`: exact P2P Improved prompt preparation + real DDS instructions.

Do not pretend a cloud-preinstalled skill is necessarily version 2.0.5. Record actual loaded paths and digest/commit if possible; missing provenance = **unverified treatment**, not a clean result.

**Branch naming:** `v4-control-001` to `003`; `v4-p2p-original-001`…`003`; `v4-p2p-improved-001`…; `v4-development-001`…; `v4-combined-001`….
For every run, create a PR against `bench/v4-hard-base`, unmerged.

## Scoring (frozen before any trials)
- **33 Node/API** checks + **11 isolated Chromium** checks = **44 public contract points**. Both pass counts, total and exact failures must be captured; security/privacy defects are tracked separately even at a high total.
- Each browser test gets its **own Node server and browser context**. The new failed-un-save and failed-search tests prevent prior false skill uplift due to state leaks.
- Secondary metrics: number of commits, scope violations, diff size, independent maintainability/security review (variant names masked); CI result and original task compliance.
- Any test artifact edited by a candidate invalidates that trial. Baseline tests are public; this is **not** a blind holdout.
- Repetitions within arms are distinct; report `n=3`, mean/median and dispersion, per-run results and failures, not one "winner" from a single run.
- Since tasks and solution patterns resemble V3, prior-model/user familiarity is a contamination risk. Interpret comparative conclusions as *this task family only*, never proof of broad skills superiority.
- Do not invent elapsed time or token counts that the client does not expose. Preserve model configuration evidence and execution environment metadata.
- Hash, tag and freeze task/tests/CI at baseline. Fixing any scoring defect thereafter requires a separately versioned fixture and fresh reruns for all arms.

## Reporting
Use `docs/V4_RUN_MATRIX_RU.md` as run ledger. Store **measurement notes outside the frozen base**, such as discussion on its draft PR or separate non-candidate analysis branch. Keep result PRs unmerged; never push audit corrections into candidate heads.
