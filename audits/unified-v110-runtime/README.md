# Unified Development & Design 1.1.0 — host and external engine verification

Status: **package and ChatGPT host enumeration checked; Codex Cloud v1.1.0 and isolated A/B remain unverified**. This is not a comparative model-effectiveness result. All user-private plugin source files remain outside this public repository.

## Host skill registry comparison

- Current installed private plugin: `unified-development-design` **1.1.0**.
- Current ChatGPT `skills.list` response, filtered by plugin URI: **122 unique skill names** (2026-11-12).
- Installed package `skills/*/SKILL.md`: **122 names**, all names and mandatory frontmatter valid.
- Earlier Codex Cloud audit in [PR #53](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/53) reported **106** Unified skill names, while its installed plugin metadata identified **v1.0.1**.
- A set comparison finds exactly **16** currently visible skills absent from the earlier Codex report; none of its 106 are absent from the current ChatGPT listing:

`ask-matt`, `grill-me`, `grill-with-docs`, `handoff`, `implement`, `implement-spec`, `improve-codebase-architecture`, `retro`, `setup-matt-pocock-skills`, `teach`, `to-questionnaire`, `to-spec`, `to-tickets`, `triage`, `wait-what`, `wayfinder`.

All 16 entries are independently confirmed present with valid frontmatter in the **archived private v1.0.1 package**. Therefore the old Codex count is not evidence of missing packaged skill files. The reason the *old* Codex host exposed only 106 is not known; the current ChatGPT registry does not prove what a *new* Codex Cloud v1.1.0 session will expose.

The current package-local `python -m unittest discover -s tests -p 'test_*.py' -v` ran **9/9 PASS**. `scripts/host_skill_inventory.py` reports **122/122** packaged names and explicitly `host_queried: false`.

## External Impeccable runtime: bounded smoke

- Bundled Impeccable skill/reference version **4.8.0**; package pins external engine **0.1.18**.
- Bundled `scripts/impeccable_preflight.py` reports the launcher and manifest are present and consistent, but the external executable is not bundled.
- In the assistant's local container `IMPECCABLE_LAUNCHER_PROBE=1 .../impeccable engine-probe` returned **127**: no local engine. Network download could not proceed because the local container cannot resolve `github.com` (curl exit 6).
- The GitHub Actions workflow `.github/workflows/unified-v110-impeccable-smoke.yml` separately downloads the **official public engine 0.1.18 Linux x64 binary**, validates its exact pinned SHA-256 before executing it, then checks the `engine-probe` handshake and the command rule listing. It uses no model API and has read-only GitHub permissions.
- Passing CI proves this pinned **external engine binary** is executable in a Linux GitHub runner; it does **not** demonstrate Impeccable functionality inside ChatGPT or Codex, installation of the private plugin there, or end-to-end plugin quality.

Expected official public binary SHA-256: `736ed785e74ae2344d3036127f614ddde5ab520a527d8bc82a891612ef71f648`.

Upstream has newer releases; this test intentionally preserves the installed v1.1.0 pin rather than silently upgrading the plugin.

## Independent A/B

Frozen original protocol: [PR #52](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/52). Execution isolation audit: [PR #53](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/53). **0/6** independently controlled model-agent trials were run. This session provides no Codex agent launcher with per-run plugin allowlists and model/effort receipts. GitHub Actions is deterministic verification, not an LLM-agent runner.

## Non-destructive policy

This audit is a standalone draft PR. No edits to `main`, PR #52/#53, benchmark tasks, or the private Unified plugin. No private ZIP, token, paid API or model-agent runs.
