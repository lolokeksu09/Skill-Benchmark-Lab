import json
from pathlib import Path
import tempfile
import unittest
from evaluator.local_llama import parse_candidate, prompt_for_fixture, request_completion, run_once, ROOT
import evaluator.local_llama as mod

class LocalLLMTests(unittest.TestCase):
    def test_prompt_uses_frozen_fixture(self):
        prompt = prompt_for_fixture(ROOT)
        self.assertIn("renderPost(post)", prompt)
        self.assertIn("width: 960px", prompt)
        self.assertIn("/no_think", prompt)
    def test_candidate_rejects_extra_files_and_non_json(self):
        self.assertFalse(parse_candidate("not json")[0])
        self.assertFalse(parse_candidate('{"feed.mjs":"x","feed.css":"y","extra":"oops"}')[0])
        self.assertTrue(parse_candidate('{"feed.mjs":"x","feed.css":"y"}')[0])
    def test_nonlocal_endpoint_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, "Only a local"):
            request_completion("https://example.com", "hello", 16, 2)
    def test_records_real_usage_and_candidate_without_executing(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = mod.request_completion
            try:
                def fake_request(url, prompt, max_tokens, timeout):
                    self.assertEqual(url, "http://127.0.0.1:8080")
                    return ({"choices":[{"finish_reason":"stop"}],
                             "usage":{"total_tokens":35,"prompt_tokens":27,"completion_tokens":8},
                             "model":"mock"}, json.dumps({"feed.mjs":"export function renderPost(){}",
                                                        "feed.css":".feed { max-width: 100%; }"}))
                mod.request_completion = fake_request
                report = Path(tmp) / "result.jsonl"
                out = run_once(ROOT, Path(tmp)/"candidates", report,
                               "http://127.0.0.1:8080", 100, 5, "trial-001")
                self.assertEqual(out["status"], "candidate_saved")
                self.assertEqual(out["total_tokens"], 35)
                self.assertIsNone(out["review"])
                self.assertEqual(json.loads(report.read_text().splitlines()[0])["run_id"], "trial-001")
                self.assertTrue((Path(tmp)/"candidates"/"trial-001.txt").is_file())
            finally:
                mod.request_completion = previous
