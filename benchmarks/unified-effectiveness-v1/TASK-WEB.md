# Unified UI Effectiveness v1 — independent web task

## Scenario
A field-service coordinator uses a queue of maintenance requests. Build a usable, responsive request dashboard from the provided three-file starter. Do not copy the presentation from other Lab branches. This is an isolated, fictional dataset, not a live service.

## Allowed changes
Edit ONLY `index.html`, `styles.css`, and `app.js` in your assigned isolated working directory. Do not edit the fixture API, benchmark evaluator, tests, protocol, or other trials. Vanilla HTML/CSS/JS; no packages, frameworks, CDN, remote fonts, images, telemetry, or build step.

## Functional contract
- Display six requests from `window.queueApi.list({query,status,signal})` on initial load; expose a readable loading state and count in `#feedback` (aria-live polite). Use `.card` elements with `data-id` for each rendered record.
- Search request titles/notes with trimming and case-insensitive matching, via the fixture API. `#search` is a labelled text input. `#filter` is a labelled native select with `all`, `open`, `done` values. Changes to either must reflect each other's values. Show a useful empty state for no matches.
- An API list rejection must retain the previously displayed cards, communicate the failure and permit subsequent retry. A slower older request must never overwrite a faster newer request; `AbortController` may be used.
- Each request's saved state is represented by a `.bookmark` button with descriptive accessible name and `aria-pressed` state. A click must call `queueApi.toggle(id, nextSaved)`; if that operation fails, restore the exact previous state, preserve version and announce the failure in the live region. The button must remain retryable. Keyboard Space/Enter should activate it.
- Never render user-supplied title/note as HTML. Use textContent or equivalent safe APIs. The fixture includes HTML-looking hostile data.
- Maintain no horizontal page overflow at viewport widths 375, 768 and 1280 CSS px. Interactive elements require a 44x44 CSS-px touch target and visible keyboard focus. UI should be coherent, readable and appropriate for coordinators scanning long records; avoid repetitive decorative cards, irrelevant metrics, or arbitrary gradients.
- Keep error, loading, empty and success states distinct; provide reduced-motion-friendly behavior.

## Available API (read only)
`queueApi.list({query: string,status: 'all'|'open'|'done',signal?: AbortSignal})` returns `{items:[{id,title,note,status,saved,version}], nextCursor:null}`. `queueApi.toggle(id, saved)` returns `{saved,version}`, rejects for injected failures. No network access. Additional APIs (`rejectNextToggle`, diagnostic counters) are for the independent grader and must not be used by the UI.

## Reporting
Run your allowed local checks. Report exact paths, commands, pass/fail evidence, and any unresolved limitation. Do not claim that tests you did not run passed. Do not access other candidate branches, scorer output, benchmark findings or another trial's implementation.
