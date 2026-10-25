# Skill Benchmark Lab — V3 hard coding fixture

A real Node HTTP server, shared state, a browser-facing client, 26 API tests and 7 Chromium E2E tests. This branch intentionally contains security, state-concurrency, pagination, and UX defects. It is a benchmark fixture, **not deployable production software**. Never use the `demo-*` tokens for real authentication.

## Run

Node.js >=22, no npm dependencies:

```sh
npm test
npm start
```

Browser E2E (Python 3.11+ and Chromium):

```sh
python -m pip install playwright==1.56.0
python -m playwright install chromium
npm run test:browser
```

If Chromium is installed at a custom path, set `CHROME_BIN` before the browser command. The GitHub Actions workflow runs both suites. The baseline intentionally fails; see the workflow for how baseline failures are distinguished from candidate failures.

**Main task:** [`TASK.md`](TASK.md). **Protocol:** [`docs/PROTOCOL.md`](docs/PROTOCOL.md).
