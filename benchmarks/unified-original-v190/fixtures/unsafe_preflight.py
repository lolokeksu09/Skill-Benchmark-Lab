"""Deliberately unsafe example for testing a missing-manifest bypass.

NOT the Unified plugin. Never use in production.
"""
def can_install(files):
    required=('plugin.json','.codex-plugin/plugin.json','scripts/skill_hashes.json')
    # BUG: missing all markers is treated as an intentional unversioned fixture.
    if not any(name in files for name in required):
        return True
    return all(name in files and bool(files[name]) for name in required)
