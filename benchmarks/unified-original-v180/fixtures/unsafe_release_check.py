"""Intentionally vulnerable release verifier used only by Lab negative controls.

The bug is that it checks the already-listed hashes but never rejects an
unexpected extra file. This is not the real Unified plugin implementation.
"""
import hashlib

def verify_release(files, ledger):
    for name, expected in ledger.items():
        content=files.get(name)
        if content is None or hashlib.sha256(content).hexdigest()!=expected:
            return False
    return True
