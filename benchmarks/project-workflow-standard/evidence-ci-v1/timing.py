#!/usr/bin/env python3
"""Post-hoc descriptive command timing; never estimates full agent duration or cost."""
import base64
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


def summarize(path):
    raw = Path(path).read_bytes()
    cohort = json.loads(gzip.decompress(raw))
    groups = {}
    for name, trial in cohort['trials'].items():
        arm = name.split('-')[1]
        compressed = base64.b64decode(trial['candidate_gzip_b64'], validate=True)
        if hashlib.sha256(compressed).hexdigest() != trial['candidate_sha256']:
            raise ValueError('candidate hash mismatch: ' + name)
        candidate = json.loads(gzip.decompress(compressed))
        actions = candidate['actions']
        entry = groups.setdefault(arm, {'trials': 0, 'observed_actions': 0, 'command_seconds': [], 'observed_span_seconds': [], 'trials_with_chain_gaps': 0, 'timing_unavailable': 0})
        entry['trials'] += 1
        entry['observed_actions'] += len(actions)
        entry['trials_with_chain_gaps'] += bool(candidate.get('chain_gaps'))
        valid = bool(actions) and all(type(a.get('started_ns')) is int and type(a.get('seconds')) in (int, float) and math.isfinite(a['seconds']) and a['seconds'] >= 0 for a in actions)
        if not valid:
            entry['timing_unavailable'] += 1
            continue
        entry['command_seconds'].append(sum(a['seconds'] for a in actions))
        start = min(a['started_ns'] for a in actions)
        end = max(a['started_ns'] + round(a['seconds'] * 1e9) for a in actions)
        entry['observed_span_seconds'].append((end - start) / 1e9)
    for entry in groups.values():
        for key in ('command_seconds', 'observed_span_seconds'):
            values = entry.pop(key)
            entry['median_' + key] = round(statistics.median(values), 3) if values else None
    return {'cohort_sha256': hashlib.sha256(raw).hexdigest(), 'groups': groups,
            'tokens': None, 'cost': None, 'agent_total_runtime': None,
            'limitation': 'Post-hoc descriptive measurements of recorded commands only. Spans exclude unobserved time before the first and after the last recorded action; missing actions, concurrency and scheduling can affect results. Not causal comparisons.'}

if __name__ == '__main__':
    print(json.dumps(summarize(sys.argv[1]), indent=2, ensure_ascii=False, sort_keys=True))
