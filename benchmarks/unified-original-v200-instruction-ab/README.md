# Unified Development & Design v2.0.0 — measurable Codex instruction A/B

**Status: harness implemented and locally verified. Actual independent Codex agent runs: 0. Model quality effect: not measured.**

This track tests whether adding *text generated from the actual Unified original v2.0.0 skill files* changes the result of a coding agent on a frozen web-development task. It compares **control** (task only) with **treatment** (same task + generated Unified Task Pack). This is **not** automatically equivalent to testing an installed ChatGPT/Codex plugin: the two arms may still share account-level skills, and this runner cannot inspect the host plugin registry.

## Frozen inputs and evaluation

- Plugin ZIP: `Unified-Development-Design-v2.0.0-Original-122-4PDA.zip` — SHA-256 `a951ab9776879734331ace4267b5900b0a92977830453fe96336490764dd2b6d`.
- Benchmark scorer and task: [Skill-Benchmark-Lab PR #52](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/52), fixed revision `fe1dc4ced57c608bda314ad5d082cdf644361273`.
- Exactly three editable files per trial: `index.html`, `styles.css`, `app.js`. Both arms receive the same read-only `queue-api.js` source fixture. The scorer is not present while Codex runs.
- Six trials in a fixed shuffled order: three control, three treatment. Each has its own work directory, fresh Codex exec session, explicit model and thinking effort, and full JSONL/patch evidence.
- The unchanged scorer tests **18 behavior/UX contracts** using Chromium/Playwright; the deliberately broken starter is known to score **3/18**. The scorer is calibrated before any Codex invocation.
- Outcomes: complete and failed trials, raw 18-point results, per-arm means and raw point difference. Report **all 18 checks**, including cross-site rendering and safe data display failures; no fabricated 0 scores for absent runs.

## Run on a machine with authenticated Codex CLI

Obtain `Skill-Benchmark-Lab`, fetch the frozen source branch and check out the exact test revision:

```bash
 git clone https://github.com/lolokeksu09/Skill-Benchmark-Lab.git
 cd Skill-Benchmark-Lab
 git fetch origin bench/unified-effectiveness-v1-web-20261111
 git worktree add ../frozen-unified-web fe1dc4ced57c608bda314ad5d082cdf644361273
```

Install only the scorer dependencies listed by that frozen suite and its Chromium runtime in a disposable Python environment:

```bash
 python3 -m venv .venv
 . .venv/bin/activate
 pip install -r ../frozen-unified-web/benchmarks/unified-effectiveness-v1/requirements.txt
 python -m playwright install chromium
```

Use the `run_codex_ab.py` shipped in this benchmark ZIP or in the new Lab draft PR. Place the original Unified `v2.0.0` ZIP nearby; do **not** install Unified globally for the experiment. First perform the offline check:

```bash
 python3 run_codex_ab.py --suite ../frozen-unified-web/benchmarks/unified-effectiveness-v1 --candidate-zip ./Unified-Development-Design-v2.0.0-Original-122-4PDA.zip --model gpt-6-astra
```

To deliberately launch Codex sessions using the same specified model and effort in both arms:

```bash
 python3 run_codex_ab.py --suite ../frozen-unified-web/benchmarks/unified-effectiveness-v1 --candidate-zip ./Unified-Development-Design-v2.0.0-Original-122-4PDA.zip --model gpt-6-astra --effort medium --repetitions 3 --out ./ab-results --run
```

Use a model **actually available** in your Codex CLI account; `gpt-6-astra` is an example, not proof that the account supports it. This invokes model sessions and may consume quota. Neither command requires an API key in the script itself; your Codex installation must already be authorized. Never set `--dangerously-bypass-approvals-and-sandbox` for this test.

## Reproducible evidence / integrity

`--run` does not overwrite an existing results directory. Each arm has a private work directory and identical starter and supplied API fixture. The script freezes and validates six Git blob IDs for the task, three starter files, fixture and scorer **before** a run. It checks the candidate archive SHA-256 and that it contains 122 skill entrypoints.

For the treatment arm, the bundled offline task-packet generator selects four source skills with `platform=web`, `focus=ui` and inserts the **full, original SKILL.md content** in the agent prompt. The control receives the same task and common instructions but not the skill packet. Each run records the exact prompt SHA-256, output file SHA-256, Codex version string, event logs, tool status and scorer output. Do not replace tasks or grader after seeing a result; create a new protocol version instead.

No model is invoked by the harness unless `--run` is passed. The repository CI runs `test_runner.py` only, not Codex. Missing Codex, authentication, Chromium or suite files is a **blocked condition**, not a 0 score or successful run.

## Interpretation

A completed `--run` can show a difference in **instruction/task-pack augmentation**, under the local CLI's actual setup. It **cannot establish the causal benefit of host-installed Unified alone** without independent verification that account-level P2P/Mobile/Unified skill catalogs are absent or identical in both arms, and actual model/effort parity. CLI settings and prompts are documented; the host may not expose authoritative plugin registry evidence.

Three repeats of one web task do not establish broad software-engineering superiority. Keep failed trials; seek blind visual review of the generated screenshots, then add independent Android, API and security coding tasks in separately frozen tracks.

No code changes to `main`, existing PR #52 or the private ChatGPT plugin are part of this track.