import base64
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from timing import summarize

class TimingTests(unittest.TestCase):
    def cohort(self, actions):
        candidate = gzip.compress(json.dumps({'actions': actions, 'chain_gaps': []}).encode())
        cohort = {'trials': {'S01-control-r1': {'candidate_gzip_b64': base64.b64encode(candidate).decode(), 'candidate_sha256': hashlib.sha256(candidate).hexdigest()}}}
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(gzip.compress(json.dumps(cohort).encode())); f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name
    def test_recorded_span_and_missing_cost(self):
        result = summarize(self.cohort([{'started_ns': 1000000000, 'seconds': .5}, {'started_ns': 3000000000, 'seconds': 1}]))
        self.assertEqual(result['groups']['control']['median_observed_span_seconds'], 3)
        self.assertEqual(result['groups']['control']['median_command_seconds'], 1.5)
        self.assertIsNone(result['cost']); self.assertIsNone(result['agent_total_runtime'])
    def test_missing_actions_are_unknown(self):
        group = summarize(self.cohort([]))['groups']['control']
        self.assertEqual(group['timing_unavailable'], 1)
        self.assertIsNone(group['median_observed_span_seconds'])
