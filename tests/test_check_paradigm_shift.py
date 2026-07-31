#!/usr/bin/env python3
"""Tests for scripts/check_paradigm_shift.py pattern coverage.

Positive cases come from the blog-review Ralph tuning corpus
(false_neg_candidate rows for the antithesis check). Run with:

    python3 -m unittest discover tests
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_paradigm_shift.py"

spec = importlib.util.spec_from_file_location("check_paradigm_shift", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["check_paradigm_shift"] = mod
spec.loader.exec_module(mod)


def labels_for(text: str) -> list[str]:
    """Run scan() on a temp markdown file, return the hit labels."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(text + "\n")
        tmp = Path(f.name)
    try:
        return [label for _, _, label, _, _ in mod.scan(tmp)]
    finally:
        tmp.unlink()


class TestPeriodSplitFormB(unittest.TestCase):
    """Form B: negated clause ending in a period, antithesis in the next
    sentence ("...is not a control. It is a checkbox.")."""

    def test_is_not_x_period_it_is_y(self):
        # paved-road-adoption-as-control L15 (tuning corpus)
        text = (
            "A security control developers can route around is not a "
            "control. It is a checkbox."
        )
        self.assertIn("antithesis-period-split", labels_for(text))

    def test_are_not_x_period_you_are_y(self):
        # paved-road-adoption-as-control L55 (tuning corpus)
        text = (
            "If you are not willing to break the side door, you are not "
            "actually building a paved road. You are building a "
            "recommendation."
        )
        self.assertIn("antithesis-period-split", labels_for(text))

    def test_are_not_just_about_x_period_it_is_y(self):
        # oom-killer-process-prioritization L133 (tuning corpus)
        text = (
            "Security considerations are not just about uptime. It is a "
            "security hardening technique:"
        )
        self.assertIn("antithesis-period-split", labels_for(text))

    def test_period_split_curly_apostrophe(self):
        # oom-killer-process-prioritization L133 — the live post uses a
        # typographic apostrophe (U+2019), not ASCII "'".
        text = (
            "From a DevSecOps perspective, OOM prioritization is not just "
            "about uptime. It’s a security hardening technique:"
        )
        self.assertIn("antithesis-period-split", labels_for(text))

    def test_negative_followup_without_parallel_verb(self):
        # Second sentence continues with a plain verb, not "It is Y" —
        # this is ordinary prose, not antithesis.
        text = "The test is not flaky. It failed for a real reason."
        self.assertNotIn("antithesis-period-split", labels_for(text))

    def test_negative_followup_with_different_subject(self):
        text = "This approach is not perfect. We can improve it later."
        self.assertNotIn("antithesis-period-split", labels_for(text))


class TestSubjectContractionFormC(unittest.TestCase):
    """Form C should also match contracted negation ("isn't"/"aren't")
    with a non-'it' subject."""

    def test_subject_isnt_just_about_x_its_y(self):
        # hardening-k8s L13 (tuning corpus miss)
        text = (
            "Securing Kubernetes workloads isn't just about scanning "
            "images or tweaking RBAC, it's about enforcing the right "
            "guardrails at the pod level to minimize risk by default."
        )
        self.assertIn("antithesis-subj-not-itis", labels_for(text))


class TestExistingPatternsStillWork(unittest.TestCase):
    def test_classic_form_a(self):
        text = "It is not a bug, it is a feature."
        self.assertIn("antithesis-it-not-it-is", labels_for(text))

    def test_classic_form_a_curly_apostrophe(self):
        text = "It’s not a bug, it’s a feature."
        self.assertIn("antithesis-it-not-it-is", labels_for(text))

    def test_subject_form_c_curly_apostrophe(self):
        text = "Least privilege isn’t fewer actions; it’s smaller blast radius."
        self.assertIn("antithesis-subj-not-itis", labels_for(text))

    def test_aristotelian_not_but(self):
        text = "The fix was not elegant but effective."
        self.assertIn("aristotelian-not-but", labels_for(text))


if __name__ == "__main__":
    unittest.main()
