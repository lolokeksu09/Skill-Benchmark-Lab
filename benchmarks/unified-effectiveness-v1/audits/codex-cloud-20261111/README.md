# Codex Cloud feasibility audit — 2026-11-11

**Blocked before trial 1. Independent A/B executions: 0/6. No treatment-effect result.**

This audit directly inspected the current Cloud session, repository and available
control surfaces. It does not repeat the earlier Work limitation as an assumed
platform-wide fact. The limitation below applies to the capabilities exposed in
this session; a differently configured host may support a valid experiment.

## Frozen source

- Repository: `lolokeksu09/Skill-Benchmark-Lab`.
- [PR #52](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/52): open, draft, unmerged when inspected.
- Exact inspected head: `fe1dc4ced57c608bda314ad5d082cdf644361273`.
- PR base: `c2379e82245b79745946b396bfa320e241c8622d`.
- Local checkout was clean at that head before adding this audit.
- No root/workspace `AGENTS.md` was present; AGENTS files under the unrelated
  project-workflow track do not govern this track.
- Frozen task, starter, fixture, scorer, self-test, protocol and original run
  matrix are unchanged. This audit is on a separate branch based on the PR head.

## What is actually available

| Capability | Observed evidence | Consequence |
| --- | --- | --- |
| Cloud executor | One selected environment, provider `cloud`, phase `running`, connected, current observations, enforced unrestricted network; see [environment.json](environment.json) | Shell/Git and deterministic browser scoring work. No second selected executor/profile exists in this thread. |
| Browser | Headless Chromium successfully ran the existing scorer and wrote PNGs | Browser availability is tested, not inferred from desktop readiness. Shared desktop was advertised but its readiness was unknown and it was not needed. |
| Agents | Only `/root` active; seven total concurrency slots advertised | Child contexts are possible, but concurrency does not establish treatment isolation. No child was launched. |
| Child launcher | `fork_turns`, `model`, `reasoning_effort` are exposed; all-history forks inherit model/effort; fresh-history forks retain tools; filesystem is shared | No per-child plugin/skill/tool allowlist, separate environment selector, or effective model/effort receipt. Fresh history alone cannot establish a clean A or B. |
| Skills | Full cloud catalog: 237 entries; executor skill list: empty | P2P **100**, Unified **106**, Mobile Design Lab **2** are exposed together. Metadata exposure is not a claim that all skill bodies were read. See [skills.json](skills.json). |
| Unified identity | Plugin Creator reports `unified-development-design` **1.0.1**, release `pluginrel_6af4b7d539208191aeb08b3e20699ee5` | Confirms stored release metadata, not exclusive loading by a trial host. See [unified-metadata.json](unified-metadata.json). No private plugin source was published. |
| Tools/plugins | 299 tools in the audit discovery snapshot, including GitHub, Cloud Environment, Plugin Management and Plugin Creator; see [tools.json](tools.json) | Cloud tools inspect readiness; Plugin Management exposes discovery, permission policy and account-level uninstall; Plugin Creator manages artifacts/releases. None exposes isolated A/B child configuration. Tool permission policy does not remove skill metadata. |
| Model/effort | Launcher accepts requested settings, but no trial runtime attestation is exposed | Exact effective model and effort remain null/unverified, rather than copied from a client label or the older requested `gpt-6`/`medium`. |
| Git SHA | Immutable checkout and hashes available | Same source can be pinned. Git isolation cannot fix host plugin/context isolation. |
| Codex CLI | Preinstalled ELF at `/opt/codex/bin/codex` | It was neither installed nor executed. This differs from the earlier status document's observation in another environment and is not evidence of a usable Cloud trial launcher. |

Public Plugin Management search did not resolve the private Unified package.
Plugin Creator's owned-personal listing and exact metadata read did resolve it.
Search absence was not treated as proof that the plugin was absent.

## Execution decision

[PROTOCOL.md](../../PROTOCOL.md) and [EXECUTION-BLOCKERS.md](../../EXECUTION-BLOCKERS.md)
require actual plugin isolation and recorded effective model/effort before trial
1. A must have no Unified/P2P/Mobile package; B must have Unified v1.0.1 without
standalone P2P/Mobile. Both would currently share the exposed catalog. An
instruction to ignore skills, an empty local config, fresh conversation history,
or separate Git worktrees cannot attest those conditions.

The same base tool configuration can be requested, but a permitted tool budget
and effective per-trial tool manifest cannot be independently enforced/attested
through the exposed child launcher. The auditor has also inspected evaluator
internals and cannot be recycled as a fresh candidate agent.

Accordingly A1, B1, A2, B2, A3 and B3 remain blocked in this audit's
[RUN-MATRIX.csv](RUN-MATRIX.csv). Missing scores are blank, not zeros. There are no
candidate diffs, six candidate branches, trial screenshots, blinded visual
reviews, arm averages, or efficacy claims. Creating empty arm branches would
not remedy the missing executions. One separate audit branch/draft PR preserves
the evidence. No changes or merge to main or PR #52 were performed.

## Existing Lab infrastructure verified

The frozen `score_web.py` was run against the frozen broken `starter/`, using
already available dependencies. It returned **exit 1, 3/18**, as expected.
The existing `selftest.py` returned **exit 0**, confirming the exact baseline
score and rejection of its five required critical negative controls.

- [All 18 baseline results and input SHA-256 values](preflight/results.json).
- [Scorer stdout/stderr](preflight/scorer.log).
- [Self-test stdout/stderr](preflight/selftest.log).
- [375 px screenshot](preflight/responsive_375.png) and
  [1280 px screenshot](preflight/responsive_1280.png).
- The scorer also checked overflow at 768 px; its existing screenshot option
  only writes the two widths above. No scorer changes were made.
- [Commands and exits](commands.log), [machine-readable decision](decision.json),
  and [artifact checksums](SHA256SUMS).

These are infrastructure preflight artifacts, **not A/B observations**. No new
framework, positive reference solution, CLI execution, paid model API call or
AI-run GitHub Actions workflow was created. Browser tests use the fixed mock
API; no external model service is called by the scorer.

## Supported route to resume without installing CLI or using paid API

1. Configure plugin availability through the owning product's Plugins settings,
   outside this already-exposed conversation. For workspace-managed plugins,
   the supported admin surface is **Admin console > workspace > Plugins**, with
   disabled/installation and, where supported, role-specific settings. Review
   every role override. For personal plugins, use the personal plugin settings.
   Prepare separately configured accounts/workspaces if the product does not
   offer per-task plugin profiles: A without all three packages; B with the
   pinned Unified v1.0.1 only among the tested design/development packages.
   Keep common infrastructure tools identical. Do not uninstall user plugins
   globally as a substitute for independent run profiles.
2. Start fresh authorized Cloud sessions after configuration, with no inherited
   conversation, memory/retrieval of other trials, shared outputs or evaluator
   access. First export the actual skill/tool catalog and plugin state from
   each session. Verify B's loaded version/content hashes against the intended
   release; metadata in this audit alone is insufficient. An account/workspace
   split is a setup route, not proof of independence by itself.
3. Select the same available model and thinking effort in both hosts and retain
   the host's effective execution settings/run receipt. If Cloud cannot expose
   these, this protocol remains blocked even after the catalogs differ; request
   host support for exported effective configuration rather than guessing.
4. Use the frozen SHA above and only `TASK-WEB.md`, starter files and the fixed
   API contract as candidate input. Ensure the candidate cannot inspect the
   public evaluator or other runs. Enforce identical tools, time and budget.
   Complete the protocol's pre-trial gate, then run **A1, B1, A2, B2, A3, B3**.
5. Grade each submitted frozen solution outside its candidate context with the
   existing 18-check scorer, collect screenshots at the protocol's three widths
   for blinded review, retain logs/hashes, and publish separate draft candidate
   PRs. Do not merge. No API-based substitute is authorized by this audit.

This is a supported configuration/admin route plus the protocol's required
validation, not a claim that this thread can perform those host controls. There
is no exposed tool here to create the two profiles or export their effective
model settings. Local `.codex/config.toml` plugin switches are documented for
supported local clients/local marketplaces; they do not alter the already
injected cloud skill catalog or workspace-managed plugin installation state.

Official documentation checked on 2026-11-11:

- [Plugin controls](https://learn.chatgpt.com/docs/enterprise/apps-and-connectors)
  (installation settings, role overrides, permissions versus installation).
- [Skill controls](https://learn.chatgpt.com/docs/enterprise/skills)
  (separate ownership of filesystem, workspace-skill and plugin controls).
- [Package your plugin](https://developers.openai.com/plugins/build/plugins#enable-or-disable-a-plugin-for-a-repo)
  (scope and limits of project plugin switches).
- [Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)
  (named profiles documented for CLI; not an exposed Cloud child profile API).

The report describes observed capabilities and missing attestation. It makes no
platform-wide impossibility claim and no claim that Unified improves results.
