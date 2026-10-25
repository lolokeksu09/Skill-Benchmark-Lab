import json
from pathlib import Path
import unittest
from evaluator.candidate_checks import check_candidate, ROOT

class CandidateChecksTests(unittest.TestCase):
    def test_trial_001_known_two_failures_one_static_pass(self):
        candidate = {
            "feed.mjs": (
                'export function renderPost(post) { return \'<article class="post"><h2>\' + '
                'encodeURIComponent(post.title) + \'</h2><button class="save" type="button">'
                '<svg aria-hidden="true"></svg></button></article>\'; }'
            ),
            "feed.css": ".feed { width: 960px; margin: 0 auto; max-width: 100%; } "
                        ".post { border: 1px solid #ddd; padding: 16px; }",
        }
        result = check_candidate(candidate)
        self.assertEqual([v["status"] for v in result["checks"].values()], ["fail", "fail", "pass"])
        self.assertEqual((result["static_passed"], result["static_failed"], result["static_uncertain"]),
                         (1, 2, 0))
        self.assertFalse(result["runtime_tests_executed"])
        self.assertIsNone(result["runtime_tests_passed"])

    def test_reference_is_only_potential_html_pass_without_execution(self):
        base = ROOT / "benchmarks/fixtures/web/reference"
        result = check_candidate({
            "feed.mjs": (base / "feed.mjs").read_text(),
            "feed.css": (base / "feed.css").read_text(),
        })
        self.assertEqual(result["checks"]["html_escaping"]["status"], "possible")
        self.assertEqual(result["checks"]["save_button_accessible_name"]["status"], "pass")
        self.assertEqual(result["checks"]["responsive_feed_width"]["status"], "pass")

    def test_raw_title_concatenation_is_caught(self):
        result = check_candidate({
            "feed.mjs": "export function renderPost(post){return '<h2>' + post.title + '</h2>';}",
            "feed.css": ".feed { width: 960px; }",
        })
        self.assertEqual(result["checks"]["html_escaping"]["status"], "fail")
        self.assertEqual(result["checks"]["responsive_feed_width"]["status"], "fail")

    def test_unrecognized_html_is_uncertain_not_pass(self):
        result = check_candidate({
            "feed.mjs": "export function renderPost(post){return specialSanitizer(post.title);}",
            "feed.css": ".feed { max-width: 100%; }",
        })
        self.assertEqual(result["checks"]["html_escaping"]["status"], "unknown")

    def test_rejects_malformed_structures(self):
        for candidate in ([], {"feed.mjs": "x"}, {"feed.mjs": "x", "feed.css": 3},
                          {"feed.mjs": "x", "feed.css": "y", "unexpected": "x"}):
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    check_candidate(candidate)
