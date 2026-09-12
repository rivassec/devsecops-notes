#!/usr/bin/env python3
"""Tests for scripts/check_anchors.py (broken #fragment anchor guard).

The guard is a merge gate; a guard that silently breaks fails OPEN (a green
check that verified nothing). These tests build tiny fixture site trees and
assert the checker catches a broken same-page fragment and a broken cross-page
fragment, ignores external/empty/query-only links, and stays quiet on a clean
tree.

Run with:

    python3 -m unittest discover tests
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def load_script(filename: str, modname: str):
    """Import a scripts/*.py file as a module (they have no package)."""
    spec = importlib.util.spec_from_file_location(modname, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


class TestCheckAnchors(unittest.TestCase):
    """check_anchors.py: catch broken in-page #fragment targets."""

    SITEURL = "https://rivassec.com"  # the script's default when no conf exists

    def setUp(self):
        self.mod = load_script("check_anchors.py", "check_anchors_under_test")
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "output"
        self.out.mkdir(parents=True)
        self.mod.REPO_ROOT = self.tmp

    def page(self, rel: str, body: str):
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"<html><head></head><body>{body}</body></html>",
            encoding="utf-8",
        )

    def test_valid_same_page_fragment_passes(self):
        self.page(
            "post.html",
            '<a href="#intro">jump</a><h2 id="intro">Intro</h2>',
        )
        self.assertEqual(self.mod.main(), 0)

    def test_broken_same_page_fragment_fails(self):
        self.page(
            "post.html",
            '<a href="#missing">jump</a><h2 id="intro">Intro</h2>',
        )
        self.assertEqual(self.mod.main(), 1)

    def test_valid_cross_page_fragment_passes(self):
        self.page("a.html", '<a href="b.html#target">to b</a>')
        self.page("b.html", '<h2 id="target">Target</h2>')
        self.assertEqual(self.mod.main(), 0)

    def test_broken_cross_page_fragment_fails(self):
        self.page("a.html", '<a href="b.html#nope">to b</a>')
        self.page("b.html", '<h2 id="target">Target</h2>')
        self.assertEqual(self.mod.main(), 1)

    def test_broken_siteurl_absolute_fragment_fails(self):
        self.page("a.html", f'<a href="{self.SITEURL}/b.html#nope">to b</a>')
        self.page("b.html", '<h2 id="target">Target</h2>')
        self.assertEqual(self.mod.main(), 1)

    def test_valid_siteurl_absolute_fragment_passes(self):
        self.page("a.html", f'<a href="{self.SITEURL}/b.html#target">to b</a>')
        self.page("b.html", '<h2 id="target">Target</h2>')
        self.assertEqual(self.mod.main(), 0)

    def test_legacy_name_anchor_resolves(self):
        self.page(
            "post.html",
            '<a href="#old">jump</a><a name="old"></a>',
        )
        self.assertEqual(self.mod.main(), 0)

    def test_external_host_fragment_ignored(self):
        # Different host: not ours to check, even with a bogus fragment.
        self.page("a.html", '<a href="https://example.com/x.html#nope">ext</a>')
        self.assertEqual(self.mod.main(), 0)

    def test_bare_hash_and_query_only_ignored(self):
        # href="#" alone and a query-only link have no fragment to resolve.
        self.page(
            "a.html",
            '<a href="#">top</a><a href="b.html?x=1">q</a>',
        )
        self.page("b.html", "<p>b</p>")
        self.assertEqual(self.mod.main(), 0)

    def test_missing_target_page_ignored(self):
        # A fragment to a page not in output/ is link rot (lychee's job),
        # not an anchor violation.
        self.page("a.html", '<a href="gone.html#whatever">to gone</a>')
        self.assertEqual(self.mod.main(), 0)

    def test_query_before_fragment_resolves(self):
        self.page("a.html", '<a href="b.html?v=2#target">to b</a>')
        self.page("b.html", '<h2 id="target">Target</h2>')
        self.assertEqual(self.mod.main(), 0)


if __name__ == "__main__":
    unittest.main()
