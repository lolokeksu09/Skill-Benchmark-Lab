#!/usr/bin/env python3
"""Sanity-check scorer rejects an intentionally incomplete baseline. No AI invoked."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    command=[sys.executable,str(ROOT/'score_web.py'),'--candidate',str(ROOT/'starter'),'--out',tmp]
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    doc=json.loads((Path(tmp)/'results.json').read_text())
    checks={c['name']:c['status'] for c in doc['checks']}
    required_fail=['untrusted_data_safe_text','responsive_375','failed_search_preserves_cards','rejected_bookmark_restores_true','stale_search_response_discarded']
    assert result.returncode==1, ('expected broken baseline exit=1',result.returncode,result.stderr)
    assert doc['summary']=={'passed':3,'total':18},doc['summary']
    assert all(checks[n]=='fail' for n in required_fail),checks
    assert doc['agent_trials']==0
    print('PASS: 18 scorer checks; known broken baseline 3/18; 5 critical negative controls rejected; no AI run')
