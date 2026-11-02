# CI metadata consistency and descriptive timing

`ci_evidence.py` checks supplied GitHub Actions run and job JSON against a separately specified expected repository, workflow, run, attempt, head SHA and required job/step names. It distinguishes conflict, failed, pending, inconclusive, invalid input and consistent metadata. Duplicate JSON keys, ambiguous required names and incomplete first pages cannot pass. Fetch the inputs through a trusted channel and independently verify the workflow, checkout, required coverage and authorization; the tool cannot authenticate JSON or prove what actually ran, an agent's actions, or the truth of logs. `consistent` is not an attestation or a readiness decision. Expectations must come from an independent trusted source, not the input being checked. Checks of run identity do not verify a PR's actual checkout.

The reduced example under `fixtures/` was obtained via the GitHub connector from [run 41502465618](https://github.com/lolokeksu09/Skill-Benchmark-Lab/actions/runs/41502465618); it is a reproducible sample, not an authenticated archive. The expected values were fixed for that run. Verify locally:

```sh
python3 ci_evidence.py --run fixtures/run.json --jobs fixtures/jobs.json --expect fixtures/expected.json
python3 -m unittest discover -s . -p 'test*.py' -v
```

Exit codes: 0 consistent; 2 pending or inconclusive; 1 conflict, failed or invalid input. GitHub's first jobs page can omit later pages; the checker refuses it when the supplied total exceeds the supplied list. A forged total remains undetectable offline.

`timing.py ../behavior-1.4-next/cohort.json.gz` reproduces `timing-descriptive.json` from the frozen data. The median is over each trial's recorded command durations or first recorded start through last recorded completion. This is post-hoc, excludes unobserved time, and is affected by missing actions and concurrent load; it is not total agent runtime or a causal comparison. No token usage, price, or model backend identity was recorded. Candidate compressed payload hashes are checked against the cohort, but this does not authenticate the cohort. Three trials declare action-chain gaps.

## Unseen control scenarios

The tests include new deterministic controls: success with a skipped required step, stale head, wrong retry, truncated jobs page, and duplicate names. These check the verifier; they are not new independent model trials. For future blinded trials, prepare held-out tasks and independent hidden assertions, randomize arm order before execution, run each agent in a real per-trial isolated environment with immutable task inputs and externally collected actions, and record provider token usage, total wall time and actual cost. Preserve incomplete traces as inconclusive and publish the preregistered protocol and all deviations. This environment cannot provide the necessary isolated model process or historical usage data.
