# Benchmark v2 — Community Board bug-fix task

You are maintaining a small web community board implemented in vanilla JavaScript and CSS (Node.js 20+). Fix the seeded defects in `src/board.mjs` and `src/board.css` while preserving the existing exported functions and their intended public contracts.

Functional requirements:

- Treat `post.id`, `post.title`, and `post.summary` as untrusted data. Text and quoted HTML attributes must be safely escaped; URL encoding is not HTML escaping.
- The icon-only bookmark button must have an appropriate accessible name for saved and unsaved posts. Its `aria-pressed` state must remain accurate.
- Pagination is 1-based. Preserve the specified behavior for invalid page/pageSize inputs, and do not mutate input arrays.
- Toggling bookmarks must produce a new Set without mutating an existing state snapshot. Treat numeric and string IDs consistently.
- The card grid must fit phone viewports without horizontal overflow; keyboard users must be able to see focus on bookmark controls.

Constraints:

- Edit **only** `src/board.mjs` and `src/board.css`.
- Do not edit tests, `package.json`, workflow configuration, or the experiment protocol.
- Do not add dependencies or use network APIs.
- Run `npm test` and report test results; if a check cannot run, state that explicitly.
- Do not look up implementations or answers in other branches, past pull requests, conversation transcripts, or other benchmark results.
- Produce a brief description of the fix and any remaining limitations.
