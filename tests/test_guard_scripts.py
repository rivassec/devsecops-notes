#!/usr/bin/env python3
"""Tests for the load-bearing CI guard scripts.

The guards are the merge gate for every content PR; a guard that silently
breaks fails OPEN (a green check that verified nothing). These tests build
tiny fixture site trees and assert each guard still catches the failure
class it exists for - and stays quiet on a clean tree.

Covered guards:
- scripts/check_descriptions.py       (run as a subprocess on fixture files)
- scripts/check_link_graph.py         (imported; REPO pointed at a fixture)
- scripts/check_wellknown_llms.py     (imported; REPO pointed at a fixture)
- scripts/check_canonical_noindex.py  (imported; REPO_ROOT pointed at a fixture)

Run with:

    python3 -m unittest discover tests
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import subprocess
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


BLOGPOST_MARKER = '<html><body itemtype="https://schema.org/BlogPosting">post</body></html>'


class TestCheckDescriptions(unittest.TestCase):
    """check_descriptions.py: fail >160-char Description/Summary, pass at 160."""

    def run_on(self, text: str) -> int:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            tmp = Path(f.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "check_descriptions.py"), str(tmp)],
                capture_output=True,
                text=True,
            )
            return proc.returncode
        finally:
            tmp.unlink()

    def test_long_summary_fails(self):
        text = "Title: T\nSummary: " + "x" * 161 + "\n\nbody\n"
        self.assertEqual(self.run_on(text), 1)

    def test_exact_limit_passes(self):
        text = "Title: T\nSummary: " + "x" * 160 + "\n\nbody\n"
        self.assertEqual(self.run_on(text), 0)

    def test_description_overrides_long_summary(self):
        text = (
            "Title: T\nDescription: short and fine\nSummary: "
            + "x" * 300
            + "\n\nbody\n"
        )
        self.assertEqual(self.run_on(text), 0)


class LinkGraphFixture(unittest.TestCase):
    """Shared fixture plumbing for check_link_graph.py."""

    def setUp(self):
        self.mod = load_script("check_link_graph.py", "check_link_graph_under_test")
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "content").mkdir()
        (self.tmp / "output").mkdir()
        self.mod.REPO = self.tmp

    def post(self, stem: str, body_links: list[str]):
        links = " ".join(
            "[x]({{filename}}{0}.md)".format(t) for t in body_links
        )
        (self.tmp / "content" / f"{stem}.md").write_text(
            f"Title: {stem}\nSlug: {stem}\n\n{links}\n", encoding="utf-8"
        )
        (self.tmp / "output" / f"{stem}.html").write_text(
            BLOGPOST_MARKER, encoding="utf-8"
        )


class TestCheckLinkGraph(LinkGraphFixture):
    HUB = "devsecops-guide"

    def test_clean_graph_passes(self):
        self.post(self.HUB, ["a"])
        self.post("a", [self.HUB])
        self.assertEqual(self.mod.main(), 0)

    def test_orphan_fails(self):
        self.post(self.HUB, ["a"])
        self.post("a", [self.HUB])
        self.post("b", [self.HUB])  # nothing links to b
        self.assertEqual(self.mod.main(), 1)

    def test_hub_unreachable_fails(self):
        # a and b link each other; hub links only a; b is reachable from hub?
        # hub -> a -> b keeps b reachable, so instead: b linked only by c,
        # c linked only by b - an island with inbound links but no hub path.
        self.post(self.HUB, ["a"])
        self.post("a", [self.HUB])
        self.post("b", ["c"])
        self.post("c", ["b"])
        self.assertEqual(self.mod.main(), 1)

    def test_outbound_cap_fails(self):
        self.post(self.HUB, ["a", "b", "c", "d"])  # hub is exempt from the cap
        self.post("a", ["b", "c", "d"])  # 3 > MAXOUT=2
        self.post("b", [self.HUB, "a"])
        self.post("c", [self.HUB, "a"])
        self.post("d", [self.HUB, "a"])
        self.assertEqual(self.mod.main(), 1)


class TestCheckWellknownLlms(unittest.TestCase):
    """check_wellknown_llms.py: security.txt + llms invariants on a fixture."""

    def setUp(self):
        self.mod = load_script(
            "check_wellknown_llms.py", "check_wellknown_llms_under_test"
        )
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "output"
        (self.out / ".well-known").mkdir(parents=True)
        self.mod.REPO = self.tmp

    def clean_fixture(self):
        expires = (
            dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=120)
        ).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        (self.out / ".well-known" / "security.txt").write_text(
            f"Contact: https://example.test/about\nExpires: {expires}\n",
            encoding="utf-8",
        )
        (self.out / "a-post.html").write_text(BLOGPOST_MARKER, encoding="utf-8")
        (self.out / "a-post.md").write_text("Title: a-post\n", encoding="utf-8")
        llms = "# Site\n- [A post](https://example.test/a-post.html)\n"
        (self.out / "llms.txt").write_text(llms, encoding="utf-8")
        (self.out / "llms-full.txt").write_text(llms + "content\n", encoding="utf-8")
        (self.out / ".well-known" / "llms.txt").write_text(llms, encoding="utf-8")

    def test_clean_fixture_passes(self):
        self.clean_fixture()
        self.assertEqual(self.mod.main(), 0)

    def test_missing_markdown_mirror_fails(self):
        self.clean_fixture()
        (self.out / "a-post.md").unlink()
        self.assertEqual(self.mod.main(), 1)

    def test_draft_url_leak_fails(self):
        self.clean_fixture()
        with (self.out / "llms.txt").open("a", encoding="utf-8") as f:
            f.write("- [leak](https://example.test/drafts/secret.html)\n")
        self.assertEqual(self.mod.main(), 1)

    def test_post_missing_from_index_fails(self):
        self.clean_fixture()
        (self.out / "llms.txt").write_text("# Site\n(empty)\n", encoding="utf-8")
        (self.out / ".well-known" / "llms.txt").write_text(
            "# Site\n(empty)\n", encoding="utf-8"
        )
        self.assertEqual(self.mod.main(), 1)

    def test_expired_security_txt_fails(self):
        self.clean_fixture()
        (self.out / ".well-known" / "security.txt").write_text(
            "Contact: https://example.test/about\nExpires: 2020-01-01T00:00:00+00:00\n",
            encoding="utf-8",
        )
        self.assertEqual(self.mod.main(), 1)


class TestCheckCanonicalNoindex(unittest.TestCase):
    """check_canonical_noindex.py: contradictory signals + sitemap leaks."""

    SITEURL = "https://rivassec.com"  # the script's default when no conf exists

    def setUp(self):
        self.mod = load_script(
            "check_canonical_noindex.py", "check_canonical_under_test"
        )
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "output"
        self.out.mkdir(parents=True)
        self.mod.REPO_ROOT = self.tmp

    def page(self, rel: str, robots: str | None, canonical: str | None,
             refresh: str | None = None):
        bits = ["<html><head>"]
        if robots:
            bits.append(f'<meta name="robots" content="{robots}">')
        if canonical:
            bits.append(f'<link rel="canonical" href="{canonical}">')
        if refresh:
            bits.append(f'<meta http-equiv="refresh" content="0; url={refresh}">')
        bits.append("</head><body>x</body></html>")
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(bits), encoding="utf-8")

    def sitemap(self, urls: list[str]):
        rows = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
        (self.out / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns='
            '"http://www.sitemaps.org/schemas/sitemap/0.9">' + rows + "</urlset>",
            encoding="utf-8",
        )

    def test_self_canonical_noindex_passes(self):
        self.page("tag/x.html", "noindex, follow", f"{self.SITEURL}/tag/x.html")
        self.page("post.html", None, f"{self.SITEURL}/post.html")
        self.sitemap([f"{self.SITEURL}/post.html"])
        self.assertEqual(self.mod.main(), 0)

    def test_cross_canonical_noindex_fails(self):
        self.page("tag/x.html", "noindex, follow", f"{self.SITEURL}/other.html")
        self.sitemap([])
        self.assertEqual(self.mod.main(), 1)

    def test_redirect_stub_is_allowed(self):
        self.page(
            "old.html",
            "noindex",
            f"{self.SITEURL}/new.html",
            refresh=f"{self.SITEURL}/new.html",
        )
        self.page("new.html", None, f"{self.SITEURL}/new.html")
        self.sitemap([f"{self.SITEURL}/new.html"])
        self.assertEqual(self.mod.main(), 0)

    def test_noindex_page_in_sitemap_fails(self):
        self.page("tag/x.html", "noindex, follow", f"{self.SITEURL}/tag/x.html")
        self.sitemap([f"{self.SITEURL}/tag/x.html"])
        self.assertEqual(self.mod.main(), 1)


if __name__ == "__main__":
    unittest.main()
