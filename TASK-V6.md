# Skill Benchmark V6 — focused hard cases

V6 is a compact follow-up to V5. Do not change the frozen V4 branch or candidate PRs #21–#25.

## Goal

Distinguish the five approaches with **five high-signal grouped checks**, not another large test matrix. Each check combines related assertions; failures are reported by check name. Existing V4's 44 checks are not rerun by the V6 workflow because they already passed for all five candidates in V4. V6 is a focused differential probe, not a replacement for the V4 regression evidence.

## Required behavior

1. **Authorization, privacy and recovery**
   - Anonymous feed access returns 401.
   - Alice never sees or mutates Bob's private `secret-bob` record; Bob can see it.
   - Authenticated malformed bookmark JSON returns 400 without mutation.
   - A subsequent valid request still succeeds.

2. **Pagination contract**
   - Full traversal for Alice has no duplicate IDs and terminates.
   - Invalid limits (0, 16, exponent notation) return 400.
   - An impossible cursor position returns 400.
   - A cursor cannot be replayed against a different normalized query.

3. **Concurrent bookmark CAS**
   - Two overlapping authenticated PUTs with the same current ETag produce exactly one 200 and one 412.
   - The successful response's ETag matches its version.
   - Final state is saved=true with one version increment.

4. **Real-browser rendering and responsive/accessibility smoke**
   - At 375px there is no horizontal overflow.
   - Seeded HTML-like title/summary render as inert text, not injected elements.
   - Bookmark control has a useful accessible name and `aria-pressed`.

5. **Real-browser rollback and duplicate-load guard**
   - When un-saving an already-saved post fails, the UI restores the previous true state.
   - Two rapid Load more activations while a response is delayed must not issue duplicate requests or render duplicate cards.

## Scope and execution

- Frozen code starting point: V4 baseline SHA `efca49e75711b40a9fcdb2549434d810c8d35fd0`.
- Only candidate code files may change: `src/engine.mjs`, `src/server.mjs`, `web/app.mjs`, `web/styles.css`.
- Run only the focused V6 checks in the V6 candidate workflow: 3 Node integration checks and 2 Chromium checks. Do not add tests unless a demonstrated gap invalidates one of these five grouped checks.
- V6 is deliberately a small differentiating suite. Do not claim that it replaces all regression, security, performance or manual accessibility testing.
- Do not merge candidate PRs.
- Public report language: Russian.
