#!/usr/bin/env python3
"""Fail if any tracked Markdown post contains an image without alt text.

Used by:
- .github/workflows/image-alt-check.yml (runs against all tracked content/*.md)

Why: WCAG 1.1.1 (Level A) requires text alternatives for non-text content.
Empty alt is allowed for purely decorative images, but in this blog every
image so far has been informational, so empty alt is almost always a bug.

What this catches:
- ![](src) — empty alt
- ![ ](src) — whitespace-only alt
- <img src="..."> with no alt= attribute
- <img src="..." alt=""> with empty alt (decorative; emit a soft note)

What this does NOT catch:
- Whether the alt text is GOOD. That is a manual judgment.
- Images outside content/ (theme assets, covers).

Exits 1 if any image is missing alt text. Empty alt prints a warning
but does not fail the build, since decorative images are valid.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Markdown image: ![alt](src) — alt may be empty.
# The src can contain {static}/path or a relative URL; we don't care about it.
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

# HTML <img> tag. Match opening tag only.
HTML_IMG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
HTML_ALT_RE = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)


def tracked_markdown() -> list[Path]:
    """All *.md tracked in git under content/."""
    out = subprocess.run(
        ["git", "ls-files", "content/*.md", "content/**/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def scan(path: Path) -> tuple[list[tuple[int, int, str, str]], list[tuple[int, int, str]]]:
    """Return (errors, warnings).

    errors: (line_no, col, kind, snippet) for images missing alt entirely.
    warnings: (line_no, col, snippet) for empty-alt images (decorative).
    """
    errors: list[tuple[int, int, str, str]] = []
    warnings: list[tuple[int, int, str]] = []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return errors, warnings

    in_code_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip fenced code blocks. Markdown image syntax inside ``` is
        # not rendered as an image.
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        for m in MD_IMAGE_RE.finditer(line):
            alt = m.group(1)
            col = m.start() + 1
            snippet = m.group(0)[:80]
            if not alt.strip():
                # Empty alt in markdown is rare and usually a mistake.
                # We emit it as a warning (not an error) because it is
                # technically valid for decorative images.
                warnings.append((lineno, col, snippet))

        for m in HTML_IMG_RE.finditer(line):
            attrs = m.group(1)
            col = m.start() + 1
            snippet = m.group(0)[:80]
            alt_match = HTML_ALT_RE.search(attrs)
            if alt_match is None:
                errors.append((lineno, col, "missing-alt", snippet))
            elif not alt_match.group(2).strip():
                warnings.append((lineno, col, snippet))

    return errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:] if p.endswith(".md")]
    else:
        paths = tracked_markdown()

    total_errors = 0
    total_warnings = 0
    for path in paths:
        if not path.is_file():
            continue
        errors, warnings = scan(path)
        for lineno, col, kind, snippet in errors:
            print(
                f"::error file={path},line={lineno},col={col}::"
                f"image missing alt text ({kind})"
            )
            print(f"  {path}:{lineno}:{col}: {snippet}")
            total_errors += 1
        for lineno, col, snippet in warnings:
            print(
                f"::warning file={path},line={lineno},col={col}::"
                f"image has empty alt (decorative?). Confirm this is intentional."
            )
            print(f"  {path}:{lineno}:{col}: {snippet}")
            total_warnings += 1

    if total_errors:
        print(
            f"\nFound {total_errors} image(s) missing alt text. WCAG 1.1.1 "
            f"(Level A) requires a text alternative for every informational "
            f"image. Add an alt that describes what the image shows.",
            file=sys.stderr,
        )
        return 1
    if total_warnings:
        print(
            f"\n{total_warnings} image(s) have empty alt. Empty alt is valid "
            f"for purely decorative images. Verify each one is intentionally "
            f"decorative.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
