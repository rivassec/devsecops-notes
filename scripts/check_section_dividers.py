#!/usr/bin/env python3
"""Fail if any post body uses a horizontal-rule section divider.

Used by:
- .pre-commit-config.yaml (runs against *staged* post .md files)
- .github/workflows/section-divider-check.yml (runs against *all* posts)

Why: house style separates sections with headings only (14 of 22 posts
did, before the stragglers were cleaned up). A `---` divider renders as an
<hr> that duplicates the heading right after it, adds visual noise, and
drifts the style from post to post. Use a `## ` heading instead.

A "divider" is a CommonMark thematic break: a line of 3+ `-`, `*` or `_`
(optionally space-separated, up to 3 leading spaces). Not flagged: Pelican
frontmatter (everything before the first blank line), fenced code blocks
(``` and ~~~), table separator rows, list items. A `---` directly under a
text line is a setext H2 underline in CommonMark; this blog does not use
that heading style, so it is flagged too, with its own message.

Scope: posts and pages under content/. Two things are excluded because we
do not author them here: content/tools/ (vendored third-party docs such as
VENDORED.md) and content/pages/about.md (regenerated from the GitHub profile
README by scripts/fetch_about.sh on every deploy, so edits would be lost).

Exits 1 with a file:line:col pointer for every hit. Exits 0 on clean.

Args:
    files (positional, optional) - restrict to these paths.
                                   If empty, scan all tracked post *.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# CommonMark thematic break: 0-3 spaces, then 3+ of the same marker char,
# optionally separated by spaces/tabs, nothing else on the line.
THEMATIC = re.compile(r"^ {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$")
# A contiguous-dash run under text is a setext H2 underline.
SETEXT_UNDERLINE = re.compile(r"^ {0,3}-+[ \t]*$")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
# Lines that cannot be a paragraph line a setext underline would attach to.
NOT_PARAGRAPH = re.compile(r"^ {0,3}(?:#|>|[-*+][ \t]|\d+[.)][ \t]|\|)")

MESSAGE = "horizontal-rule section divider; use a ## heading to separate sections instead"
SETEXT_MESSAGE = (
    "'---' under a text line is a setext H2 heading, a style this blog does "
    "not use; use a ## heading to separate sections instead"
)


def is_post(path: str) -> bool:
    """True for content Markdown we author (not vendored tool docs)."""
    p = Path(path).as_posix()
    if not p.startswith("content/") or not p.endswith(".md"):
        return False
    # content/tools/** is vendored third-party material (VENDORED.md etc.).
    # content/pages/about.md is overwritten by scripts/fetch_about.sh at deploy.
    return not p.startswith("content/tools/") and p != "content/pages/about.md"


def tracked_markdown() -> list[Path]:
    """All post *.md tracked in git."""
    out = subprocess.run(
        ["git", "ls-files", "*.md", "**/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p and is_post(p)]


def scan(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, line_text, message) for each divider in path."""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return hits

    in_meta = True
    fence: str | None = None
    prev = ""
    for lineno, line in enumerate(text.splitlines(), start=1):
        if in_meta:
            # Pelican metadata runs to the first blank line after it starts.
            if line.strip() == "" and lineno > 1:
                in_meta = False
            elif line.strip() == "":
                pass
            continue

        if fence is not None:
            close = re.match(r"^ {0,3}(" + re.escape(fence[0]) + r"{%d,})[ \t]*$" % len(fence), line)
            if close:
                fence = None
            prev = ""
            continue
        m = FENCE_OPEN.match(line)
        if m:
            fence = m.group(1)
            prev = ""
            continue

        if THEMATIC.match(line):
            setext = (
                SETEXT_UNDERLINE.match(line)
                and prev.strip() != ""
                and not NOT_PARAGRAPH.match(prev)
                and not prev.startswith("    ")
            )
            hits.append((lineno, line.rstrip(), SETEXT_MESSAGE if setext else MESSAGE))
        prev = line
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
        for lineno, line, message in scan(path):
            print(f"::error file={path},line={lineno},col=1::{message}")
            print(f"  {path}:{lineno}:1: {line}")
            total += 1

    if total:
        print(
            f"\nFound {total} section divider(s). Delete the rule and let a "
            f"## heading separate the sections.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
