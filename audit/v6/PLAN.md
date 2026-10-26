# V6 — protocol for a reproducible, human-readable benchmark

**Status:** proposal; no candidate run has started.  
**Created:** 26 October 2026  
**Reference V5:** [PR #26](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/26)  
**Frozen V4 source baseline:** `efca49e75711b40a9fcdb2549434d810c8d35fd0`

## 1. Decision

Use **P2P Original as the provisional behavioral reference**, because it passed all five V5 distinguishing criteria. Do **not** use its source branch as the base for the other methods. That would give one method an implementation head start and invalidate the comparison.

Every V6 candidate must start from the same new frozen V6 baseline, receive the same task and verification suite, and be checked against an immutable full SHA. Keep the five V4 PRs and the V4 baseline unchanged.

V6 is a controlled pilot, not a statistically representative study. Its public report must separate correctness, defensive behavior, runtime, and model usage instead of collapsing them into one unexplained score.

## 2. V6 scope

V6 should test the same core product contract more deeply and add a small number of cases that V5 could not establish. Target **eight scenario groups**, not a large collection of loosely related tests. Existing V4 tests remain unchanged and run as regression checks.

### Group 1 — authorization and malformed input

- Missing/invalid bearer token with a normal request and with malformed JSON.
- Authenticated malformed JSON must fail cleanly without state mutation.
- Malformed percent-encoded bookmark ID must return 400 and must not stop the server from serving a subsequent valid request.
- Assert status, body shape where specified, state, and post-error server responsiveness.

### Group 2 — cursor contract and boundaries

Pre-register these semantics before running any candidate:

- Malformed encoding, cursor bound to another viewer/query, and a nonexistent cursor position return 400.
- A cursor position that cannot refer to an item in the filtered result set is invalid; it must not silently turn into a successful empty page.
- Limits 1 and 15 are accepted; 0, 16, decimals, exponent notation, negatives, and non-numeric values are rejected.
- Distinguish a malformed cursor from a valid terminal response; do not use a single broad label for both.

For keyset candidates, the impossible position is a missing anchor. For offset candidates, it is an offset at or beyond the filtered result length. These are equivalent contract intentions, not byte-identical tokens.

### Group 3 — complete pagination

- Traverse the full visible dataset with page sizes 1, 2, 7, and 15.
- Assert stable ordering, equal-timestamp tie-breaking, no missing IDs, no duplicate IDs, and termination.
- Verify cursor binding to viewer and normalized search query.
- **Dynamic insertion/deletion between pages is a separate V6 extension.** The current fixture exposes no post mutation API. Test it only after the new common baseline provides a deterministic test-only mutation seam; do not claim the current static fixture proves keyset stability under mutation.

### Group 4 — transactional bookmark rollback

Test both starting states: `saved=false` and `saved=true`.

- Stale `If-Match` / HTTP error.
- Network rejection or unreadable JSON.
- HTTP 200 with invalid field types.
- HTTP 200 with a mismatched post ID, classified as defensive fault injection rather than a normal server response.
- After failure, assert the exact previous `saved`, `version`, `aria-pressed`, error announcement, and the correct `If-Match` on retry.
- Verify successful response `id/saved/version` and ETag consistency.

### Group 5 — Load more and search races

Use real browser automation as the primary test:

- Two fast Load more activations while the first request is pending: one network request and one copy of each card.
- Two searches returning out of order: the older result must not overwrite the newer result.
- A failed search must preserve the previously displayed cards and announce failure.
- Measure duplicate DOM cards separately from redundant HTTP requests; these are different defects.

### Group 6 — XSS, keyboard, and responsive UI

Run in Chromium, not only a mocked DOM:

- Render the seeded HTML-like title and summary as text; assert no injected elements or event execution.
- Tab focus is visible; icon-only bookmark controls have accessible names and `aria-pressed`.
- Enter and Space activate the focused control.
- Check horizontal overflow at 320px and 375px viewport widths.
- Keep screen-reader/manual-device checks labelled as manual if they cannot be reliably automated in CI.

### Group 7 — bookmark concurrency at the HTTP boundary

- Two overlapping authenticated PUTs using the same current ETag must produce one 200 and one 412.
- Repeat the pair a small fixed number of times and preserve each raw result.
- Describe this as an HTTP contract test for the current single-process fixture, not a distributed-database or multi-process stress test.

### Group 8 — recovery and regression

- After each malformed request or injected client failure, perform a known-good request and verify the server/UI remains usable.
- Run the frozen V4 Node and Chromium suites plus the V6-specific cases.
- Record the exact commands, candidate SHA, runtime environment, pass/fail counts, and limitations. A green workflow means the harness ran successfully; it does not mean every candidate assertion passed.

## 3. Evaluation rubric

Do not rank candidates using one flat count in which all failures have equal weight.

Report three independent layers:

1. **Contract gates:** privacy/authorization, bookmark state integrity and CAS, complete pagination, XSS-safe rendering. A failure here must remain visible and cannot be compensated by passing cosmetic checks.
2. **Reliability and UX:** rollback/retry, stale-search protection, duplicate Load more behavior, accessibility and responsive layout.
3. **Defensive fault injection:** malformed HTTP 200 payloads, mismatched response IDs, and other responses the normal server should not emit. Report separately from contract failures and never imply that injection proves the production server emits that response.

Publish raw observations and severity for every failure. If an aggregate is shown at all, publish the weights and rationale before running candidates. Do not call the result a general winner or statistically significant.

## 4. Time and token accounting

V5 did not preserve authoritative model-usage data. Do not reconstruct or invent historical usage.

For each **new V6 generation run**, record the following in a versioned machine-readable ledger:

| Field | Rule |
|---|---|
| Method alias and run ID | Fixed, unique ID for every attempt |
| Base SHA and prompt SHA-256 | Exact immutable inputs |
| Model and reasoning effort | Record only if explicitly exposed by the execution environment |
| Generation start/end and elapsed seconds | Use execution-platform timestamps/logs, not PR creation time |
| Input/output/total tokens | Record only from an authoritative usage record; otherwise `null` plus reason |
| CI start/end and elapsed seconds | From GitHub Actions; keep separate from generation time |
| Node/browser results | Exact pass/fail counts and environment |
| Candidate head SHA and changed paths | Verify against GitHub |
| Diff bytes/lines | Optional objective size metric, clearly labelled as a proxy, never as token usage |

Never substitute CI duration for coding time. Never infer actual tokens from the patch length. If an exact tokenizer and exact prompt are available, an estimate may be reported in a separate field explicitly labelled **estimate**, not usage.

Keep the prompt, model, effort and verification environment identical across methods where the platform allows it. If model/effort or usage cannot be confirmed, say so in the public report rather than claiming comparability that the evidence does not establish.

## 5. Run protocol

1. Create a new `bench/v6-hard-base` from the frozen V4 baseline; do not move or rewrite the existing `bench/v4-hard-base`.
2. Add the V6-specific task/specification and focused tests to that new baseline. Freeze and record its full SHA before generating any candidates.
3. Run Control, P2P Original, P2P Improved, DDS 2.0.5, and Combined from that exact SHA, with the same scope and constraints.
4. Preserve one branch and PR per candidate; do not merge candidate PRs while collecting results.
5. Use aliases A–E in the result matrix until the rubric and raw observations are recorded. This reduces presentation bias but is not a claim of strict blinding.
6. Execute the new tests and existing regressions; store raw evidence per immutable SHA.
7. Publish the quality matrix and resource ledger separately. If authoritative generation-time/token data is missing, the benchmark remains a quality comparison and must not claim a cost comparison.

## 6. Explicit exclusions

- No changes to V4 baseline or PRs #21–#25.
- No production deployment or production-security claims.
- No model identity, reasoning effort, generation time, or token counts inferred from code appearance, PR timestamps, or CI runtime.
- No claim that a Node VM mock is a real browser test.
- No merge is authorized by this plan.

## Acceptance criteria for the V6 baseline

- One frozen baseline SHA is shared by all five methods.
- V6 contract expectations are written before candidate execution.
- The eight scenario groups above are represented by deterministic tests or explicitly marked as manual/unavailable.
- V4 regression tests remain intact and pass on the new baseline before candidate runs begin.
- Usage fields support `null` with a reason; missing usage data does not block quality reporting or get fabricated.
