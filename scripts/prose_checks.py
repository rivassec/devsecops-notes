#!/usr/bin/env python3
"""Prose-quality regex checks for Markdown posts.

Emits ::warning lines in the same shape as check_paradigm_shift.py so the
Ralph harness can consume them generically:

  ::warning file=PATH,line=N,col=M::label: text

Three checks, all informational (always exits 0):

* passive-voice — be-verb + past participle, with a small allow-list of
  common idioms ("is needed", "is required", "was created")
* weasel-word — hedging vocabulary that softens claims
* filler-opener — sentence starts that delay the actual content

Run on a single post: prose_checks.py path/to/post.md
Run on tracked Markdown: prose_checks.py (no args)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# A "sentence-ish" splitter: cheap, not perfect. Markdown bodies are not
# going to be Stanford-parsed prose; this only needs to be good enough to
# locate roughly-where the next sentence starts on a line.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"`(])")

# --- 1. Passive voice ----------------------------------------------------
# Match "(am|is|are|was|were|be|been|being) <past participle>".
# Past participle is approximated as a word ending in -ed (regular) plus
# a curated list of irregulars. Allow-list common technical idioms that
# are semantically active.
PV_BE = r"(?:am|is|are|was|were|be|been|being)"
PV_IRREGULAR = r"(?:built|broken|chosen|done|driven|forgotten|given|gone|known|made|meant|seen|shown|spoken|taken|thrown|written)"
PV_RE = re.compile(
    rf"\b{PV_BE}\s+(\w+ed|{PV_IRREGULAR})\b",
    re.IGNORECASE,
)
# These are common phrases that match the regex but read as active or
# stative idioms. Suppress them.
PV_ALLOWLIST = {
    "is needed", "are needed", "was needed", "were needed",
    "is required", "are required", "was required", "were required",
    "is allowed", "are allowed",
    "is expected", "are expected",
    "is supposed", "are supposed",
    "is based", "are based", "was based", "were based",
    "is located", "are located",
    "is named", "are named",
    "be done", "is done", "was done", "are done", "were done",
    "is used", "are used", "was used", "were used",
    "is shown", "are shown",
    "is called", "are called", "was called", "were called",
    "be made", "is made", "are made",
    "be added", "is added", "are added",
    "is set", "are set", "was set", "were set",
    "is left", "are left",
    "be aware",
    "is known", "are known",
}

# --- 2. Weasel words -----------------------------------------------------
# Hedging vocabulary. Word-boundary anchored to avoid catching e.g.
# "perhaps" inside a longer token.
WEASEL_TERMS = [
    r"arguably",
    r"perhaps",
    r"essentially",
    r"basically",
    r"generally",
    r"largely",
    r"somewhat",
    r"relatively",
    r"fairly",
    r"rather",
    r"in\s+some\s+cases",
    r"in\s+many\s+cases",
    r"tends?\s+to",
    r"seems?\s+to",
    r"appears?\s+to",
    r"may\s+be",
    r"might\s+be",
    r"could\s+be",
    r"of\s+course",
    r"clearly",
    r"obviously",
]
WEASEL_RE = re.compile(rf"\b(?:{'|'.join(WEASEL_TERMS)})\b", re.IGNORECASE)

# --- 3. Filler openers ---------------------------------------------------
# Sentence-start phrases that postpone the real content. Only flag when
# they begin a sentence (i.e. line start or after a sentence boundary).
FILLER_OPENERS = [
    r"There\s+is",
    r"There\s+are",
    r"There\s+was",
    r"There\s+were",
    r"It\s+is\s+important",
    r"It\s+is\s+worth",
    r"It\s+should\s+be\s+noted",
    r"Note\s+that",
    r"So,",
    r"Now,",
    r"Well,",
    r"Of\s+course,",
    r"Obviously,",
    r"Clearly,",
    r"Needless\s+to\s+say,",
]
FILLER_RE = re.compile(
    rf"^(?:{'|'.join(FILLER_OPENERS)})\b",
    re.IGNORECASE,
)


def _in_code_or_frontmatter(text: str, pos: int) -> bool:
    """True if pos lies inside a fenced code block or frontmatter block.

    Cheap counter approach: count opening fences and frontmatter delimiters
    before pos. This is good enough for the kinds of false positives we
    actually hit (curl examples, YAML frontmatter blocks).
    """
    prefix = text[:pos]
    # Frontmatter: opens with `---\n` at the very start, closes with the
    # next `\n---\n`. Treat as "inside" only if we have seen one delimiter
    # but not the second.
    if prefix.startswith("---\n"):
        # Count `---` lines up to pos.
        n = sum(1 for line in prefix.splitlines() if line.strip() == "---")
        if n == 1:
            return True
    # Fenced code blocks: count ```'s. Odd count = inside.
    fences = prefix.count("\n```")
    if prefix.startswith("```"):
        fences += 1
    return fences % 2 == 1


def _allow(match_text: str) -> bool:
    return match_text.strip().lower() in PV_ALLOWLIST


def scan_post(path: Path) -> list[tuple[int, int, str, str]]:
    """Return (line_no, col, label, snippet) per finding."""
    text = path.read_text()
    findings: list[tuple[int, int, str, str]] = []
    # Build a map from char offset to (line, col).
    offsets = []  # (start_offset, line_number 1-indexed)
    line_starts = [0]
    for m in re.finditer(r"\n", text):
        line_starts.append(m.end())

    def offset_to_line_col(off: int) -> tuple[int, int]:
        # Binary search would be tidier; linear is fine for blog-sized files.
        ln = 0
        for i, start in enumerate(line_starts):
            if start <= off:
                ln = i
            else:
                break
        return ln + 1, off - line_starts[ln] + 1

    # 1. passive voice
    for m in PV_RE.finditer(text):
        if _in_code_or_frontmatter(text, m.start()):
            continue
        # Pull the be-verb + participle as the test phrase
        phrase = text[m.start():m.end()].lower()
        if _allow(phrase):
            continue
        # Crop a small window around the match for the snippet
        snippet_start = max(0, m.start() - 30)
        snippet_end = min(len(text), m.end() + 30)
        snippet = text[snippet_start:snippet_end].replace("\n", " ").strip()
        line, col = offset_to_line_col(m.start())
        findings.append((line, col, "passive-voice", snippet))

    # 2. weasel
    for m in WEASEL_RE.finditer(text):
        if _in_code_or_frontmatter(text, m.start()):
            continue
        snippet_start = max(0, m.start() - 30)
        snippet_end = min(len(text), m.end() + 30)
        snippet = text[snippet_start:snippet_end].replace("\n", " ").strip()
        line, col = offset_to_line_col(m.start())
        findings.append((line, col, "weasel-word", snippet))

    # 3. filler openers — line-anchored so we walk lines
    for i, line_text in enumerate(text.splitlines(), start=1):
        # Skip frontmatter and fenced code lines (cheap version)
        if _in_code_or_frontmatter(text, sum(len(s) + 1 for s in text.splitlines()[:i - 1])):
            continue
        m = FILLER_RE.match(line_text.lstrip())
        if m:
            findings.append((i, 1, "filler-opener", line_text.strip()[:80]))

    return findings


def emit(path: Path, findings: list[tuple[int, int, str, str]]) -> None:
    for line, col, label, text in findings:
        # Quote/strip newlines defensively.
        safe_text = text.replace("\n", " ").replace("::", ":")
        print(f"::warning file={path},line={line},col={col}::{label}: {safe_text}")


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md", "**/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = [Path(p) for p in argv[1:]]
    else:
        targets = tracked_markdown()
    for p in targets:
        if not p.exists():
            continue
        try:
            emit(p, scan_post(p))
        except Exception as e:
            print(f"# scan error for {p}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
