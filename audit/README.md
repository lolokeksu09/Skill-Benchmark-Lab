# V3 post-hoc browser audit (independent; non-scoring)

This branch is intentionally rooted at the lightweight `main` and contains **no candidate source**. All candidates are checked out by their **exact frozen commit SHA**. It does not modify the 33-point V3 trial results.

The original Chromium test suite starts one Node server in `setUpClass` and shares it across tests. In alphabetic order, `test_bookmark_button_has_name_and_reflects_successful_toggle` saves the initial post. `test_failed_bookmark_write_rolls_back_and_reports_error` then assumes the same post is initially unsaved and insists the end state is false. This assumption is invalid when bookmark state persists in server memory.

Here, the original seven browser test bodies are copied verbatim, but setup/teardown changes from once-per-class to **once-per-test**. Every test starts a fresh Node server and Chromium context. One **new** test checks the reverse direction: save successfully, then mock HTTP 412 on attempted un-save and assert previous `true` state survives. Both directions are required by TASK.md, but the original V3 suite only checks failed save from false.

All candidates use the exact same post-hoc suite and environment; browser results are logged with frozen SHA to prevent conflation or patch contamination. **A pass or fail here does not retroactively change the frozen original 33-point score.** It may revise interpretation of benchmark reliability and reveal uncovered bugs. Failing audit jobs are legitimate observations, not a CI setup fault if the browser tests actually ran.

Original P2P improved report suggested that the previously observed failure was due to fixture state leakage. This audit was independently designed after that report, so it is *post-hoc*, not a blinded holdout. No model benefits are attributed causally based on this audit alone.
