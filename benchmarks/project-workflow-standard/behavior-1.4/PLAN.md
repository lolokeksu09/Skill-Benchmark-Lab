# Behavior benchmark plan

Scope: owner authorized comprehensive comparative behavior experiments after archive audit. Use supplied PWS rules; no standard edits, production, release or merge.

| ID | Requirement | Acceptance | State |
|---|---|---|---|
| REQ-B01 | Preserve four instruction arms | Input hash manifest, original snapshots unchanged | In progress |
| REQ-B02 | Freeze meaningful scenarios/oracle | Baseline/golden/mutation self-check before runs | In progress |
| REQ-B03 | Real model applications | 4 arms × 3 fresh contexts × 12 cases, raw outputs | Pending |
| REQ-B04 | Independently score results | Deterministic grader + separate reviewer | Pending |
| REQ-B05 | Report limits, evidence and comparison | Reproducible report/ZIP, no fabricated metrics | Pending |
| REQ-B06 | Save code/results and CI | Separate branch/PR; replay exact submitted artifacts | Pending |

Sequence: freeze → self-check → concurrent applications → grade → independent audit → report/package/CI. Next action is the first available unfinished requirement. Agent reports do not close product checks. Missing gates remain unavailable; exceptions do not imply success.
