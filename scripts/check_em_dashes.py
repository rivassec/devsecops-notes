#!/usr/bin/env python3
"""Fail if any tracked Markdown contains an em dash (U+2014).

Used by:
- .pre-commit-config.yaml (runs against *staged* .md files)
- .github/workflows/em-dash-check.yml (runs against *all* tracked .md files)

Why: I deliberately stopped using em dashes in published prose. They render
differently across feeds and Telegram clients, and are an LLM tell. Colon,
comma, period, or parens cover every legitimate use I had.

Exits 1 with a file:line:col pointer for every hit. Exits 0 on clean.

Args:
    files (positional, optional) — restrict to these paths.
                                    If empty, scan all tracked *.md.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# U+2014 EM DASH only. We do NOT flag U+2013 EN DASH (used legitimately for
# numeric ranges like "pages 12–15") or U+2212 MINUS SIGN.
FORBIDDEN = "—"
FORBIDDEN_NAME = "em dash (U+2014)"


def tracked_markdown() -> list[Path]:
    """All *.md tracked in git, recursively."""
    out = subprocess.run(
        ["git", "ls-files", "*.md", "**/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def scan(path: Path) -> list[tuple[int, int, str]]:
    """Return (line_no, col_no, line_text) for each em dash in path."""
    hits: list[tuple[int, int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return hits
    for lineno, line in enumerate(text.splitlines(), start=1):
        col = line.find(FORBIDDEN)
        while col != -1:
            hits.append((lineno, col + 1, line.rstrip()))
            col = line.find(FORBIDDEN, col + 1)
    return hits


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:] if p.endswith(".md")]
    else:
        paths = tracked_markdown()

    total = 0
    for path in paths:
        if not path.is_file():
            continue
        hits = scan(path)
        if not hits:
            continue
        for lineno, col, line in hits:
            # GitHub Actions annotation format on CI; on local pre-commit it
            # just renders as a leading "::error file=...,line=...". Both
            # are readable.
            print(
                f"::error file={path},line={lineno},col={col}::"
                f"{FORBIDDEN_NAME} found"
            )
            print(f"  {path}:{lineno}:{col}: {line}")
            total += 1

    if total:
        print(
            f"\nFound {total} em dash(es). Replace with colon, comma, period, "
            f"or parentheses depending on context.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
