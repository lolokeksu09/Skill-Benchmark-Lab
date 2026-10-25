import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import evaluator.thinking_pilot as p


class ThinkingPilotTests(unittest.TestCase):
    def test_identical_user_task_across_arms(self):
        control = p.messages_for("control")
        dds = p.messages_for("development", [{
            "name": "systematic-debugging", "path": "x", "sha256": "a" * 64,
            "content": "do not guess"
        }])
        self.assertEqual(control[-1]["content"], dds[-1]["content"])
        self.assertTrue(control[-1]["content"].endswith("/think"))
        self.assertIn("do not guess", dds[0]["content"])

    def test_separates_reasoning_without_executing(self):
        body = '{"feed.mjs":"x","feed.css":"y"}'
        self.assertEqual(p.final_content({"content": body}), (body, False))
        self.assertEqual(p.final_content({"content": "<think>why</think>" + body}), (body, True))
        self.assertEqual(p.final_content({"content": body, "reasoning_content": "why"}), (body, True))

    def test_trial_records_actual_usage(self):
        old = p.request_model
        try:
            p.request_model = lambda *args: {
                "model": "local-mock", "choices": [{"finish_reason": "stop", "message": {
                    "content": '{"feed.mjs":"x","feed.css":".feed {max-width: 100%;}"}',
                    "reasoning_content": "thought"
                }}],
                "usage": {"prompt_tokens": 255, "completion_tokens": 150, "total_tokens": 405},
                "timings": {"prompt_ms": 120.5, "predicted_ms": 400.5},
            }
            with TemporaryDirectory() as folder:
                root = Path(folder)
                rec = p.trial("control", p.messages_for("control"), None, (), root/"candidates",
                              root/"results.jsonl", timeout=30)
                self.assertEqual(rec["status"], "candidate_saved")
                self.assertEqual(rec["total_tokens"], 405)
                self.assertTrue(rec["reasoning_present"])
                self.assertFalse(rec["runtime_tests_executed"])
                self.assertTrue((root/"candidates"/"trial-001.response.json").is_file())
                with self.assertRaises(FileExistsError):
                    p.trial("control", p.messages_for("control"), None, (), root/"candidates",
                            root/"results.jsonl", timeout=30)
        finally:
            p.request_model = old
