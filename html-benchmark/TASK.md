# HTML Creation Benchmark — single self-contained page

Improve only `html-benchmark/index.html` from the frozen baseline. Create one polished, self-contained page for a Wild Rift community feed.

## Required behavior

- One HTML file; all CSS and JavaScript inline.
- No external network requests, frameworks, fonts, images, or CDN assets.
- Responsive at 375px, 768px, and desktop widths without horizontal overflow.
- Header, hero section, search, category filter, post cards, and an empty state.
- Search and category filter work together and never render stale results.
- Like, Save, and Load more controls work with keyboard and pointer input.
- Save state uses `aria-pressed`; icon-only controls have accessible names.
- Theme toggle persists during the page session.
- User supplied search text is rendered safely as text.
- Visible focus styles, semantic landmarks, labels, and sufficient contrast.
- Keep the page usable with JavaScript disabled where practical.

## Allowed change

Only `html-benchmark/index.html` may be changed. Do not edit tests, task, workflow, or scoring files. Do not add dependencies.

## Verification

Run the static and Chromium checks from `html-benchmark/tests`. Report the exact changed path, test counts, and limitations in Russian. Do not deploy the page.
