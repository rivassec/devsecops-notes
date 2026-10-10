#!/usr/bin/env python3
"""Tests for scripts/check_section_dividers.py.

The guard keeps horizontal-rule section dividers out of post bodies (house
style: sections are separated by headings only). Each test writes a tiny
post to a temp file and runs the script as a subprocess, like the
check_descriptions tests do.

Run with:

    python3 -m unittest discover tests
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_section_dividers.py"

FRONT = "Title: T\nDate: 2026-01-01\nSummary: s\n\n"


class TestCheckSectionDividers(unittest.TestCase):
    def run_on(self, text: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            tmp = Path(f.name)
        try:
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(tmp)],
                capture_output=True,
                text=True,
            )
        finally:
            tmp.unlink()

    def assertFlags(self, body: str, lineno: int):
        proc = self.run_on(FRONT + body)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, rf"\.md:{lineno}:1:")
        self.assertIn("use a ## heading to separate sections instead", proc.stdout + proc.stderr)
        return proc

    def assertClean(self, body: str):
        proc = self.run_on(FRONT + body)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    # --- violations -------------------------------------------------------

    def test_clean_post_passes(self):
        self.assertClean("Intro.\n\n## One\n\nText.\n\n## Two\n\n- item\n- item\n")

    def test_dash_rule_fails(self):
        self.assertFlags("Intro.\n\n---\n\n## One\n", 7)

    def test_star_rule_fails(self):
        self.assertFlags("Intro.\n\n***\n\n## One\n", 7)

    def test_underscore_rule_fails(self):
        self.assertFlags("Intro.\n\n___\n\n## One\n", 7)

    def test_spaced_variants_fail(self):
        self.assertFlags("Intro.\n\n- - -\n\nMore.\n", 7)
        self.assertFlags("Intro.\n\n* * *\n\nMore.\n", 7)
        self.assertFlags("Intro.\n\n_ _ _\n\nMore.\n", 7)

    def test_long_run_fails(self):
        self.assertFlags("Intro.\n\n-----\n\nMore.\n", 7)

    def test_up_to_three_leading_spaces_fail(self):
        self.assertFlags("Intro.\n\n   ---\n\nMore.\n", 7)

    def test_four_leading_spaces_is_code_not_rule(self):
        self.assertClean("Intro.\n\n    ---\n\nMore.\n")

    def test_setext_h2_underline_fails_with_explanation(self):
        proc = self.assertFlags("Some text\n---\n\nMore.\n", 6)
        self.assertIn("setext", proc.stdout + proc.stderr)

    def test_multiple_hits_all_reported(self):
        proc = self.run_on(FRONT + "A.\n\n---\n\nB.\n\n***\n\nC.\n")
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, r"\.md:7:1:")
        self.assertRegex(proc.stdout, r"\.md:11:1:")

    # --- non-violations ---------------------------------------------------

    def test_frontmatter_not_scanned(self):
        text = "Title: T\n---\nDate: 2026-01-01\n\nBody.\n"
        self.assertEqual(self.run_on(text).returncode, 0)

    def test_backtick_fence_ignored(self):
        self.assertClean("Intro.\n\n```yaml\n---\nkey: v\n---\n```\n\nEnd.\n")

    def test_tilde_fence_ignored(self):
        self.assertClean("Intro.\n\n~~~yaml\n---\nkey: v\n~~~\n\nEnd.\n")

    def test_fence_closes_and_scanning_resumes(self):
        self.assertFlags("```\ncode\n```\n\n---\n\nEnd.\n", 9)

    def test_longer_fence_not_closed_by_shorter(self):
        self.assertClean("````\n```\n---\n```\n````\n\nEnd.\n")

    def test_table_separator_rows_ignored(self):
        self.assertClean("| a | b |\n| --- | --- |\n| 1 | 2 |\n\n|a|b|\n|---|---|\n|1|2|\n")

    def test_list_items_ignored(self):
        self.assertClean("- item\n- another\n* star item\n\n-item\n")

    def test_dash_text_not_rule(self):
        self.assertClean("Intro.\n\n--- not a rule\n\n-- also not\n\n--\n")

    # --- CLI --------------------------------------------------------------

    def test_non_md_args_ignored(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(FRONT + "A.\n\n---\n")
            tmp = Path(f.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(tmp)], capture_output=True, text=True
            )
        finally:
            tmp.unlink()
        self.assertEqual(proc.returncode, 0)

    def test_default_scope_excludes_vendored_tool_docs(self):
        spec = importlib.util.spec_from_file_location("check_section_dividers", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(mod.is_post("content/some-post.md"))
        self.assertTrue(mod.is_post("content/pages/accessibility.md"))
        self.assertFalse(mod.is_post("content/pages/about.md"))
        self.assertFalse(mod.is_post("content/tools/iam-blast-radius/VENDORED.md"))
        self.assertFalse(mod.is_post("themes/Flex/README.md"))
        self.assertFalse(mod.is_post("README.md"))


if __name__ == "__main__":
    unittest.main()
