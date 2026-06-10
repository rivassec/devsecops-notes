#!/usr/bin/env python3
"""Warn on antithesis / paradigm-shift sentence structures in Markdown.

Hunts for the rhetorical construct "It is not [X], it is [Y]" and close
relatives. The shape is technically correct rhetoric (antithesis with
parallelism) but it has become an LLM tell, especially in opener
sentences and conclusion paragraphs. This check surfaces matches as
yellow warnings; it does NOT fail CI.

Used by:
- .pre-commit-config.yaml (runs against staged .md files)
- .github/workflows/paradigm-shift-check.yml (runs against all tracked .md)

Always exits 0. Output is informational. Trim or rewrite at your
discretion; sometimes the construct is exactly what you want.

Patterns scanned (most precise first):

  A — "It is not X, it is Y"      (classic; high confidence)
       "It's not X; it's Y"
       "It isn't X, it's Y"

  C — "<noun> is not X, it is Y"  (subject-led variant)

  D — "Not X but Y"               (Aristotelian inversion; informational)

Form B (period-split "Not X. Y.") is deliberately omitted in v1 — too
noisy without semantic parallelism check.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# (regex, label, severity)
# severity in {"high", "info"}  — high gets warnings, info just listed
PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"(?i)\bit(?:\s+is|'s|\s+isn'?t|\s+is\s+not)"
            r"\s+[^,.;\n]{1,80}[,;]\s+"
            r"(?:it\s+is|it'?s|but\s+(?:it\s+is|it'?s))\b"
        ),
        "antithesis-it-not-it-is",
        "high",
    ),
    (
        re.compile(
            r"(?i)\b\w+\s+(?:is|are)\s+not\s+[^,.;\n]{1,80}[,;]\s+"
            r"(?:it|they)(?:\s+is|'s|\s+are)\b"
        ),
        "antithesis-subj-not-itis",
        "high",
    ),
    (
        re.compile(
            r"(?i)\bnot\s+[a-z]\w+(?:ing|ed|s|ly)?[,.\s]+but\s+[a-z]\w+"
        ),
        "aristotelian-not-but",
        "info",
    ),
]


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md", "**/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def scan(path: Path) -> list[tuple[int, int, str, str, str]]:
    """Return (line_no, col, label, severity, match_text) per hit."""
    hits: list[tuple[int, int, str, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return hits

    # Build line-offset index for efficient line/col lookup
    offsets = [0]
    for ch in text:
        if ch == "\n":
            offsets.append(len(offsets))  # placeholder, set below
    # Re-derive using splitlines starts
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    def line_col(pos: int) -> tuple[int, int]:
        # Binary search would be faster; this is fine for ~100KB files
        line = 0
        for i, start in enumerate(line_starts):
            if start <= pos:
                line = i
            else:
                break
        return line + 1, pos - line_starts[line] + 1

    # Collect across all patterns, then dedupe by (line, col) so the same
    # sentence isn't reported twice when it matches both form A and form C.
    # Earlier patterns in PATTERNS win (higher precision first).
    seen_positions: set[tuple[int, int]] = set()
    for pattern, label, severity in PATTERNS:
        for m in pattern.finditer(text):
            line_no, col = line_col(m.start())
            if (line_no, col) in seen_positions:
                continue
            seen_positions.add((line_no, col))
            match_text = m.group(0).replace("\n", " ").strip()
            if len(match_text) > 100:
                match_text = match_text[:100] + "…"
            hits.append((line_no, col, label, severity, match_text))
    return hits


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:] if p.endswith(".md")]
    else:
        paths = tracked_markdown()

    high_total = 0
    info_total = 0
    for path in paths:
        if not path.is_file():
            continue
        for line_no, col, label, severity, match_text in scan(path):
            if severity == "high":
                high_total += 1
                # GitHub Actions warning annotation (yellow, non-blocking)
                print(
                    f"::warning file={path},line={line_no},col={col}::"
                    f"{label}: {match_text}"
                )
                print(f"  {path}:{line_no}:{col}: [{label}] {match_text}")
            else:
                info_total += 1
                print(f"  {path}:{line_no}:{col}: [{label}] {match_text}")

    if high_total or info_total:
        print(
            f"\nFound {high_total} high-confidence + {info_total} informational "
            f"antithesis-style match(es).",
            file=sys.stderr,
        )
        print(
            "These are NOT errors. The construct is sometimes correct. "
            "But if you didn't write it deliberately, consider rephrasing.",
            file=sys.stderr,
        )

    # Always exit 0 — this is a warning, not a gate.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
