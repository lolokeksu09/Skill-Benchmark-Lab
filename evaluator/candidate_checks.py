"""Non-executing, fixture-specific preflight checks for generated Web candidates.

Static results are not proof of runtime correctness or XSS resistance.
"""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CHECK_NAMES = ("html_escaping", "save_button_accessible_name", "responsive_feed_width")


def check_candidate(files):
    """Examine text only; never import, eval, or execute generated JavaScript."""
    if (not isinstance(files, dict) or set(files) != {"feed.mjs", "feed.css"}
            or not all(isinstance(value, str) for value in files.values())):
        raise ValueError("Expected complete feed.mjs and feed.css string values")
    js, css = files["feed.mjs"], files["feed.css"]
    title = re.search(r"\bpost\s*\.\s*title\b", js) is not None

    # This is a negative check for a known wrong encoding approach, not a JS parser.
    percent_encoding = re.search(
        r"\bencodeURI(?:Component)?\s*\(\s*(?:String\s*\(\s*)?post\s*\.\s*title\b",
        js,
    ) is not None
    raw_title = re.search(r"\+\s*post\s*\.\s*title\s*\+", js) is not None

    if percent_encoding:
        html = ("fail", "encodeURI/encodeURIComponent performs URL encoding, not HTML escaping")
    elif raw_title:
        html = ("fail", "post.title is concatenated directly into HTML")
    elif (title and all(entity in js for entity in ("&amp;", "&lt;", "&gt;"))
          and ("replace(" in js or "replaceAll(" in js)):
        html = ("possible", "HTML escape entities found; execution is required to confirm behavior")
    else:
        html = ("unknown", "Could not prove escaping from text alone")

    aria = re.search(r"""aria-label\s*=\s*\\?["']Save post\\?["']""", js)
    if aria:
        accessible = ("pass", "Save post accessible name appears in the button markup")
    elif re.search(r"<button\b", js):
        accessible = ("fail", "Icon-only button is missing the required aria-label")
    else:
        accessible = ("unknown", "Could not locate a statically recognizable save button")

    responsive = re.search(r"\.feed\s*\{[^}]*\bmax-width\s*:\s*100%\s*(?:;|})", css, re.S)
    if responsive:
        width = ("pass", "Found max-width: 100% in .feed ruleset")
    else:
        width = ("fail", "Missing required max-width: 100% in .feed ruleset")

    checks = dict(zip(CHECK_NAMES, (
        {"status": html[0], "detail": html[1]},
        {"status": accessible[0], "detail": accessible[1]},
        {"status": width[0], "detail": width[1]},
    )))
    return {
        "method": "static_text_only",
        "checks": checks,
        "static_passed": sum(c["status"] == "pass" for c in checks.values()),
        "static_failed": sum(c["status"] == "fail" for c in checks.values()),
        "static_uncertain": sum(c["status"] in ("possible", "unknown") for c in checks.values()),
        "runtime_tests_executed": False,
        "runtime_tests_passed": None,
        "disclaimer": "Heuristics only; static pass/possible does not establish executable correctness.",
    }


def main():
    parser = argparse.ArgumentParser(description="Inspect saved Qwen Web candidate without executing JavaScript")
    parser.add_argument("--candidate", default="results/raw/local-qwen-web-candidates/trial-001.txt")
    args = parser.parse_args()
    candidate = Path(args.candidate)
    try:
        files = json.loads(candidate.read_text(encoding="utf-8"))
        report = check_candidate(files)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
