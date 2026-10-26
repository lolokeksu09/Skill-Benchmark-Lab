# HTML Creation Benchmark

Frozen single-page HTML fixture. The baseline is intentionally incomplete. Run:

```sh
python -m unittest discover -s html-benchmark/tests -p 'test_*.py' -v
```

Chromium requires Playwright 1.56.0 and a browser install. The tests open the local file directly and do not use a server.
