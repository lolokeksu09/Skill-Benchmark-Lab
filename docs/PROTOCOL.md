# Skill Benchmark Lab: protocol v1

## Goal
Compare **prompt formulation** and **code execution** separately. P2P builds prompts; Development & Design Skills defines implementation methodology. A direct quality ranking of the two without a common downstream task is misleading.

## Test variants
- control: same base model without additional skills
- p2p-original: official P2P version 9.0
- p2p-improved: local improved P2P edition (pin archive SHA-256)
- development: Development & Design Skills (pin skill revision)
- combined: P2P Improved for task formulation followed by Development & Design Skills for implementation

## Fair comparison
1. Freeze each scenario, input files, source commit and tool permissions. Use **disposable** fixtures rather than production project secrets.
2. Pin the exact model, runtime, options, date, skill file hashes and prompt. Do not conflate simulated QUORUM roles with genuine independent agents.
3. For prompt-generation runs, assess the generated prompt contract. For execution runs, give the same model the generated prompt plus identical code fixtures.
4. Perform at least three independent runs per variant and scenario. Keep failures. Randomize evaluation order.
5. Blind-review results on 0–5 quality (40 points), correctness (30) and constraint adherence (20). Use at least two independent human reviewers when feasible.
6. Record measured wall time and token counts. Missing values stay null. The quality rubric has a maximum of **90**, not 100; efficiency is reported separately.
7. Publish medians plus distributions and limitations. No meaningful winner can be declared from unreplicated runs.

## Security and provenance
This repository is PUBLIC. Never commit API keys, private code or sensitive logs. Do not redistribute third-party skill bundles without reviewing licenses and attribution. GitHub Actions only validates local fixtures; it does not access paid LLM APIs.

## Scope of v1
The scenario definitions are **not** executable Android or Web projects. Automated tests verify the evaluator and input structure, not real agent effectiveness. The runner for controlled LLM calls and frozen production-like code fixtures are subsequent milestones.
