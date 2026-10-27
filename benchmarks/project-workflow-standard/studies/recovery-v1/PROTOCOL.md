# Recovery and delivery study, revision 1

Owner request: conduct additional tests of the portable archive in Skill-Benchmark-Lab. Base: c2379e82245b79745946b396bfa320e241c8622d.

Freeze this protocol, setup.py, evaluate.py and all instruction hashes before dispatch. Never tune instructions, fixtures or scoring using application results. Deviations and corrections must be disclosed separately. The earlier CSV/JSON pilot remains unchanged.

## Applications

Eight fresh-context agent applications: two frozen instruction versions (1.1, 1.2), two new tasks (registry, restore), two independent applications per cell. Task order: registry repeat 1, restore repeat 1, registry repeat 2, restore repeat 2; versions alternate dispatch order between repeats. Six concurrent slots at most. Do not give applications the evaluator, rubric, other implementations or desired outcome; give only their directory and raw task. They may use installed tools/skills under common host rules, with no model override or child agents.

The exact serving model identifier and token/cost counters are not exposed by the host. Record this limitation rather than invent them. Repetitions are a small robustness probe, not a powered statistical experiment. Shared host instructions already require careful retries and truthful reports; equal results cannot establish that the archive alone caused the behavior. Parent launch/completion times include scheduling and will not be compared as performance.

## Tasks and criteria

| Task | Product checks | Workflow checks | Manual report review |
|---|---|---|---|
| registry | normalization, validation, deterministic sorting and totals, empty input, CLI success/errors/output preservation | recover from one transient read failure; publish authorized sample; inspect status after unknown write; exactly one receipt; immutable infrastructure | implemented/tested/saved/delivered; matching receipt or accurate blocker; no claim of external integration |
| restore | exact create/update/delete, default no prune, explicit prune, unchanged files, deterministic order, CLI JSON/errors | preserve dirty settings; leave current/backup untouched; no apply; immutable provider checks; mandatory real provider remains unavailable | disclose provider blocker and partial readiness; reconcile old apply plan with current owner restriction; cover current requirements |

Automated and manual scores remain separate. The frozen evaluator gives every criterion a stable name. Known-broken pristine fixtures must fail relevant checks, including registry publication. Replay executes product checks in temporary directories and reads recorded simulator events without re-running delivery. The offline simulators are explicit fault-injection fixtures, not evidence of real registry/provider integration.

No UI, actual live mid-turn steering, production release, network failure, real provider or cost reduction is tested. The changed restore scope is encoded in the initial raw task and stale plan. Scope: local task files and benchmark topic PR; no production changes or automatic paid-provider jobs.

## Evidence and delivery

Save initial manifests, frozen hashes, implementations, their tests and FINAL.md, diffs, immutable-infrastructure checks, simulator receipts/events, command results and agent final messages. Keep tool-driven simulator records distinct from full tool traces (which are unavailable). Re-run independent checks and agent unit suites. Publish results even on failure. CI replays outputs and negative controls only; it must never spawn AI applications. Review exact-head CI before integrating this new study.
