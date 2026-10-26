# Benchmark V4 — Community Feed: consistency, privacy and browser recovery

This is a **new version of the frozen V3 local-only fixture** for controlled comparison. The seeded implementation intentionally contains interrelated backend, HTTP, concurrency, and frontend failures. Work only from this exact V4 baseline; do not reuse previous attempts.

## Required behavior

1. **Privacy and authorization.** A bearer demo viewer may read public posts and their own private posts; never expose or mutate another viewer's private record (404 for hidden IDs). Unauthorized API calls return 401. Public demo keys are local test fixtures, not production authentication.
2. **Feed stability.** Trim/casefold search, order posts by descending `createdAt` then ascending `id`; paginate via an opaque cursor bound to viewer and normalized query, including equal-timestamp pages and full traversal without missing/duplicate IDs. Reject malformed cursors and non-plain-decimal `limit` outside 1–15 with 400. Preserve the seed and result shape `{items,nextCursor}`.
3. **Bookmark concurrency.** PUT accepts **only** `{saved:boolean}`. `If-Match: "<version>"` is mandatory (428 absent, 400 malformed, 412 stale). Return correct per-viewer version and matching ETag. Real state changes increment once, valid current-version no-ops don't. Reject stale no-ops; competing writes with the same version cannot both succeed. Invalid JSON, unexpected keys, malformed ID decoding or missing records must fail cleanly without changing state; the server must stay responsive.
4. **Browser behavior.** Render untrusted post data through safe DOM text/attribute APIs; no HTML injection. Cards must fit 375px viewport without horizontal overflow. Icon-only bookmark buttons need clear labels, `aria-pressed`, visible focus ring, and Enter/Space activation.
5. **Transactional UI.** On rejected or malformed bookmark responses, restore the exact **previous** state (including a previously saved `true` when an un-save fails), preserve version, report a failure through the existing live region and allow subsequent retry. A failed feed search must report the error without losing the previously displayed cards. Rapid searches must never render stale requests. `Load more` must traverse all visible posts exactly once and eventually terminate.
6. **Quality.** Respect existing exported functions and routes, avoid new dependencies, avoid needless rewrites. Do not deploy this test-only application.

## Allowed source edits

**ONLY** `src/engine.mjs`, `src/server.mjs`, `web/app.mjs`, `web/styles.css`.

Forbidden: modifying tests, `TASK.md`, `web/index.html`, package scripts, CI, benchmark/scoring documents or fixtures. Do not inspect other branches, PRs, old candidate patches, benchmark reviews or prior conversation transcripts.

## Verification and report

Run `npm test`, `npm run test:browser` where Chromium is installed, and `git diff --check`. The CI supplies Chromium; never report a local browser pass without actually running it. State the exact start/head SHAs, altered paths, 33 Node test counts, 11 Chromium test counts, CI status, observed model/effort if available, skill files actually read, and limitations.

Create one independent PR against `bench/v4-hard-base`, **no merging**. Reply in **Russian**.
