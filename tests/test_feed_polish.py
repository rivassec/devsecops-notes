"""Tests for plugins/feed_polish.py (stdlib unittest; Pelican not required)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugins"))

from feed_polish import absolutize, polish_feed  # noqa: E402

BASE = "https://rivassec.com/devsecops-guide.html"


class _Feed:
    def __init__(self, title, items):
        self.feed = {"title": title}
        self.items = items


class AbsolutizeTests(unittest.TestCase):
    def test_relative_links_become_absolute(self):
        html = '<a href="iam-safe-defaults-fail-loud.html">x</a> <a href="/tools/iam-blast-radius/">y</a>'
        out = absolutize(html, BASE)
        self.assertIn('href="https://rivassec.com/iam-safe-defaults-fail-loud.html"', out)
        self.assertIn('href="https://rivassec.com/tools/iam-blast-radius/"', out)

    def test_images_and_single_quotes(self):
        out = absolutize("<img src='images/a.png' alt=\"a\">", BASE)
        self.assertIn("src='https://rivassec.com/images/a.png'", out)

    def test_absolute_fragment_and_special_schemes_untouched(self):
        html = ('<a href="https://example.com/x">a</a><a href="#sec">b</a>'
                '<a href="mailto:me@example.com">c</a><img src="data:image/png;base64,AA">'
                '<a href="//cdn.example.com/y">d</a>')
        self.assertEqual(absolutize(html, BASE), html)

    def test_text_that_mentions_href_is_not_rewritten(self):
        html = "<code>href=foo.html</code>"
        self.assertEqual(absolutize(html, BASE), html)


class PolishFeedTests(unittest.TestCase):
    CTX = {"SITENAME": "RivasSec | DevSecOps, Kubernetes, AWS IAM", "FEED_TITLE": "RivasSec"}

    def test_feed_title_and_item_content(self):
        feed = _Feed(self.CTX["SITENAME"], [{"link": BASE, "description": '<a href="a.html">a</a>', "content": None}])
        polish_feed(self.CTX, feed)
        self.assertEqual(feed.feed["title"], "RivasSec")
        self.assertEqual(feed.items[0]["description"], '<a href="https://rivassec.com/a.html">a</a>')

    def test_category_feed_keeps_suffix(self):
        feed = _Feed(self.CTX["SITENAME"] + " - DevSecOps", [])
        polish_feed(self.CTX, feed)
        self.assertEqual(feed.feed["title"], "RivasSec - DevSecOps")

    def test_no_feed_title_setting_leaves_title(self):
        feed = _Feed("Site", [])
        polish_feed({"SITENAME": "Site"}, feed)
        self.assertEqual(feed.feed["title"], "Site")


if __name__ == "__main__":
    unittest.main()
