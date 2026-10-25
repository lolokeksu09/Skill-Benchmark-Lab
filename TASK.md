# Benchmark V3 — Community Board (complex, independent coding task)

You maintain a **local-only** Node.js 22 + vanilla JS community feed. The project boots with `npm start` and has seeded, interacting defects in the HTTP API, client behavior, and UI. Fix them **without replacing the application** or weakening the tests.

## Contracts to restore

1. **Privacy and authorization.** A viewer can read public posts plus their own private posts, but cannot read or bookmark another viewer's private posts (respond 404 to avoid record disclosure). Missing/invalid demo bearer tokens return 401. The static demo credentials in `src/engine.mjs`/`web/index.html` are intentionally public **test fixtures, not production authentication**.
2. **Feed/search/pagination.** Search is trimmed and case-insensitive. Preserve descending `createdAt`, with ascending `id` for timestamp ties. `limit` is a plain decimal integer from 1–15 inclusive. Page with an opaque keyset cursor: no overlaps, resilient to equal timestamps, reject malformed cursor (400) and cursor reuse across another viewer or search (400). Do not mutate the seed posts. Keep API response shape: `{items, nextCursor}`.
3. **Bookmark write semantics.** `PUT /api/bookmarks/:id` accepts only `{saved: boolean}`. It requires `If-Match: "<version>"` (428 missing; 412 stale) and returns `{id, saved, version}` plus matching `ETag`. A real change increments a per-viewer/per-post version once; a no-op with a *current* version is idempotent. Two simultaneous writes with the same version cannot both succeed. Invalid JSON/inputs yield 400 without mutation.
4. **Browser safety and UX.** No HTML/attribute injection from title, summary, or IDs. Use safe DOM APIs. At 375px viewport there must be no horizontal page overflow. Icon-only bookmark controls need an accessible name, accurate `aria-pressed`, a visible keyboard focus ring, and working keyboard activation. If a write fails, restore the previous UI state and report the error in the existing live region. Rapid searches must not display stale results from an older request. `Load more` must append without duplicates.
5. **Quality.** Retain existing module contracts, robust errors, and no unnecessary dependencies. Document genuine limitations in the final report. Do not deploy this demo beyond local/CI testing.

## Allowed edits

**Only** `src/engine.mjs`, `src/server.mjs`, `web/app.mjs`, and `web/styles.css`.

Do **not** edit `TASK.md`, `web/index.html`, the tests, package scripts, CI workflow, or scoring/protocol documents. Do not read other branches, PRs, past candidate solutions, or conversation transcripts.

## Verification

- `npm test` — Node 22 HTTP and state-contract tests.
- `npm run test:browser` — Chromium E2E tests; requires Python Playwright 1.56.0 and Chromium. In CI both checks run automatically; if browser dependencies are not installed in your Codex environment, make no unsupported claim of a local browser pass.
- `git diff --check`.

Do not change/skip any tests to improve the score. Report exact start SHA, end SHA, modified files, test counts, browser result, model and reasoning settings if observable, and any unresolved requirements. Save the attempt in an independent branch and PR **against the frozen V3 base**, without merging.
