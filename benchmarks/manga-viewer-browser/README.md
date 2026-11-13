# Manga viewer browser checks

This track runs real Chromium against the exact viewer, source-transcription
workbench and review-record validator from Manga Translation Studio, plus the
1.17 candidate's ordered reading-window viewer.
`SOURCE.json` binds the vendored files to the saved plugin release and SHA-256.

All images, OCR alternatives and review entries are generated synthetic test
fixtures. No user scans, private chapter files, fonts, models, credentials or AI
provider calls are included. Existing benchmark tracks are unchanged.

Run:

```bash
python -m pip install -r benchmarks/manga-viewer-browser/requirements.txt
python -m playwright install --with-deps chromium
python benchmarks/manga-viewer-browser/test_browser.py --out browser-artifacts
```

The runner starts a loopback-only HTTP server on the GitHub runner, checks native
100% and 390px views, the comparison slider, stage-specific changes, edit-region
crops, review exports, stale-inventory rejection, mobile overflow, corrected
source inventory export and native/390px reading-window crops. HTML must not
request external resources. The original 1.16.0 source snapshot and passing run
remain in Git history; SOURCE.json identifies the current candidate precisely.

GitHub Actions uploads the generated HTML, JSON findings, screenshots and a
Playwright trace for seven days, including on a failed test. The JSON records the
actual Chromium version, commit SHA and generator hashes. Installing the pinned
Python and Chromium dependencies requires network access; tests make no AI calls.

A passing UI test does not establish accurate Korean OCR, correct translation,
faithful reconstruction inside a mask, or human/independent review. Checked
review entries in this track are synthetic format/interaction fixtures only.
