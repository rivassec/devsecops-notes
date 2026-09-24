#!/usr/bin/env python3
"""Tests for the weasel-word pattern in scripts/prose_checks.py.

The negative cases come from the blog-review Ralph tuning corpus
(2026-09-20..23), where 16 of 22 weasel-word hits were "rather than" or
"would rather". Run with:

    python3 -m unittest discover tests
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "prose_checks.py"

spec = importlib.util.spec_from_file_location("prose_checks", SCRIPT)
prose_checks = importlib.util.module_from_spec(spec)
sys.modules["prose_checks"] = prose_checks
spec.loader.exec_module(prose_checks)


def flagged(text: str) -> list[str]:
    return [m.group(0).lower() for m in prose_checks.WEASEL_RE.finditer(text)]


class RatherTests(unittest.TestCase):
    def test_rather_than_is_a_comparison_not_a_hedge(self):
        for s in [
            "The watermark lives in token selection rather than hidden characters.",
            "It provides likelihood rather than the deterministic guarantee.",
            "The analogy is operational rather than cryptographic.",
            "Rather than dispute that, I closed the ticket.",
            "use minimal RBAC bindings rather\nthan relying on the default",
        ]:
            with self.subTest(s=s):
                self.assertEqual(flagged(s), [])

    def test_would_rather_is_a_preference_not_a_hedge(self):
        for s in [
            "the kind of artifact I would rather be evaluated on",
            "I'd rather ship it today.",
            "I’d rather ship it today.",
        ]:
            with self.subTest(s=s):
                self.assertEqual(flagged(s), [])

    def test_rather_as_intensifier_is_still_flagged(self):
        for s in ["The blast radius is rather large.", "Rather surprisingly, it worked."]:
            with self.subTest(s=s):
                self.assertEqual(flagged(s), ["rather"])


class OtherTermsUnchanged(unittest.TestCase):
    def test_real_hedges_from_the_corpus_are_still_flagged(self):
        self.assertEqual(flagged("In some cases, it's a quiet countdown."), ["in some cases"])
        self.assertEqual(flagged("dispositions tend to fall into three buckets"), ["tend to"])
        self.assertEqual(flagged("which could be weeks or months earlier"), ["could be"])


if __name__ == "__main__":
    unittest.main()
