# Execution blocker: ChatGPT Work plugin isolation

Status: **0/6 independent agent trials executed.** This document records a user-supplied report from an attempted ChatGPT Work launch; it is not a verified agent trace and supplies no measured treatment effect.

## Observation reported from Work

- Work has agents with separate contexts but cannot assign different **installed plugin sets** to each child agent.
- The active session exposes Unified Development & Design, Development & Design Skills P2P, and Mobile Design Lab.
- The running environment did not expose trustworthy per-agent proof of Unified plugin v1.0.1 and identical model/thinking-effort settings.
- Consequently A1–A3 and B1–B3 were **not run**; no individual 18-point scores, screenshots, CI of candidate implementations, blinded reviews, or effect estimate exist.

## Preserved primary estimand

Under PROTOCOL.md, A must run without any P2P, Mobile Design Lab or Unified Development & Design plugin; B must run with **only Unified Development & Design v1.0.1**. Both arms must use the same exact starting Git SHA, task, model, thinking effort, tool budget and run duration. A shared plugin registry with prompt-only instructions such as “ignore those skills” does **not** demonstrate plugin isolation.

## Strict execution gate (required before trial 1)

1. Two verifiably distinct execution profiles or isolated environments: A has no three relevant plugins or skills; B loads only the pinned Unified v1.0.1 artifact.
2. Record each profile's actual loaded tool/skill manifest, effective plugin state, and Unified archive version/hash where relevant.
3. Record exact **model ID**, thinking-effort configuration and permitted tool set for each execution from the execution host; do not guess from a ChatGPT client label.
4. Pin the immutable `benchmarks/unified-effectiveness-v1` starting commit, with isolated worktrees and fresh agent contexts. Do not expose the positive calibration candidate, previous trial outputs, or evaluation internals.
5. Have a way to invoke the **same** agent runner in both profiles and to capture the final source diff, execution trace, screenshots, and stdout/stderr per trial. Disable all cross-run retrieval/memory.
6. Refuse to execute/score as clean A/B if any criterion above is not attestable. Do not modify frozen scoring to fit the available runner.

## Feasible next approach

Use an agent runner that explicitly supports per-process isolated skill/plugin configuration, or two separately configured Work/accounts/workspaces **only if their effective plugin state can be independently verified**. A shell-controlled runner can use isolated worktrees and environment-specific config, but the exact agent CLI and its plugin-loading controls must be verified before commands are published. The CI currently evaluates submitted candidates; it does not launch model agents or alter ChatGPT plugins.

If per-agent plugin isolation is impossible, a new versioned study may compare **explicitly provided skill instructions** versus no additional instructions using separately initialized API contexts. Label that as an *instruction-prompt ablation*, **not** as the original plugin A/B experiment. This would require an authorized model API and cost approval.

## Current evidence boundaries

- Lab scorer preflight CI: PASS (18-point test harness correctly distinguishes broken starter from a separately authored positive control).
- Independent agent trials: 0/6.
- Unified model/plugin performance comparison: **no result**.
- Existing Lab PR #52, main branch and plugin v1.0.1 remain unchanged except for this blocker documentation on PR #52's draft branch.
