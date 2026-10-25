# Frozen fixture contract (v2)

These are **synthetic** open examples, not extracts of NOX or WrCommunity. A failing *baseline* is intentional; the *reference* contains only the expected correction. The known defects are published to make the benchmark repeatable.

## Web
- `benchmarks/fixtures/web/baseline/feed.mjs` contains 2 defects: unescaped user text (XSS risk when rendered as HTML) and an icon-only button with no accessible name.
- `baseline/feed.css` uses an unresponsive fixed width.
- `reference/` corrects all three. `tests/feed.test.mjs` is run against either variant.
- Run: `FIXTURE_VARIANT=reference node --test benchmarks/fixtures/web/tests/feed.test.mjs`; the baseline is **expected to fail**.

## Android-associated Kotlin (JVM)
- `baseline/FeedState.kt` has a state-management bug: repeated post reads reduce the unread count and zero may become negative.
- `reference/FeedState.kt` ensures idempotency and nonnegative unread counts. No Android SDK or Jetpack Compose is required for this *core logic* microbenchmark; it is not an APK test.
- `shared/FixtureCheck.kt` uses plain Kotlin assertions and prints `REFERENCE_OK`.
- Run `gradle -p benchmarks/fixtures/android run -PfixtureVariant=reference`. The baseline must exit with marker `EXPECTED_FIXTURE_FAILURE`.

## Do not conflate fixture validation with model evaluation
Green CI demonstrates that the test can distinguish deliberately broken from corrected code, **not** that a model found or fixed the issue. Actual model evaluation requires independent blind trials with prompts, logs, verified tool permissions and token usage. No paid API credentials are present.

The seeded defects may be provided to an agent without the reference files to avoid answer leakage. Keep the reference in a separate evaluation-only checkout when running benchmark trials.
