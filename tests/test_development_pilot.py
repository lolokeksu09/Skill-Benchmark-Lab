import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

import evaluator.development_pilot as pilot
from evaluator.local_llama import ROOT, prompt_for_fixture


class DevelopmentPilotTests(unittest.TestCase):
    def test_reads_exact_sha_verified_skill_entries_without_extracting(self):
        with TemporaryDirectory() as tmp:
            archive = Path(tmp) / "skill.zip"
            sources = [
                "a debugging skill",
                "an accessibility skill",
            ]
            with zipfile.ZipFile(archive, "w") as z:
                for name, source in zip(pilot.SKILLS, sources):
                    z.writestr(pilot.SKILL_PREFIX + name + "/SKILL.md", source)
            sha = hashlib.sha256(archive.read_bytes()).hexdigest()
            frozen = Path(tmp) / "versions.json"
            frozen.write_text(json.dumps({"entries": [{"id": "development", "sha256": sha}]}))
            actual, selected = pilot.verified_skills(archive, frozen)
            self.assertEqual(actual, sha)
            self.assertEqual([s["content"] for s in selected], sources)
            messages = pilot.make_messages(ROOT, selected)
            self.assertEqual(messages[1]["content"], prompt_for_fixture(ROOT))
            self.assertIn("a debugging skill", messages[0]["content"])
            self.assertIn("an accessibility skill", messages[0]["content"])
            frozen.write_text(json.dumps({"entries": [{"id": "development", "sha256": "0" * 64}]}))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                pilot.verified_skills(archive, frozen)

    def test_skills_trial_records_real_metrics_and_does_not_execute_code(self):
        skills = [{"name": x, "path": "skills/" + x + "/SKILL.md",
                   "sha256": "a" * 64, "content": x} for x in pilot.SKILLS]
        with TemporaryDirectory() as tmp:
            prev = pilot.call_local_server
            try:
                def fake_call(messages, limit, timeout):
                    return ({
                        "model": "local-qwen", "choices": [{"finish_reason": "stop"}],
                        "usage": {"total_tokens": 42, "prompt_tokens": 32, "completion_tokens": 10}
                    }, json.dumps({"feed.mjs": "export function renderPost(post) {}",
                                    "feed.css": ".feed { max-width: 100%; }"}))
                pilot.call_local_server = fake_call
                path = Path(tmp) / "results.jsonl"
                record = pilot.run_once(pilot.make_messages(ROOT, skills), "f" * 64,
                                        skills, Path(tmp) / "candidates", path,
                                        "trial-001", 400, 600)
                self.assertEqual(record["total_tokens"], 42)
                self.assertEqual(record["variant"], "development")
                self.assertEqual(record["status"], "candidate_saved")
                self.assertFalse(record["runtime_tests_executed"])
                self.assertIsNone(record["runtime_tests_passed"])
                self.assertTrue(path.exists())
                self.assertTrue((Path(tmp) / "candidates/trial-001.txt").exists())
                with self.assertRaises(FileExistsError):
                    pilot.run_once(pilot.make_messages(ROOT, skills), "f" * 64,
                                    skills, Path(tmp) / "candidates", path,
                                    "trial-001", 400, 600)
            finally:
                pilot.call_local_server = prev
