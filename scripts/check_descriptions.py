#!/usr/bin/env python3
"""Fail if any post's meta description exceeds 160 characters.

Used by:
- .github/workflows/description-check.yml (runs against all content/**/*.md)

Why: The <meta name="description"> and Open Graph description come from a
post's `Description:` metadata (falling back to `Summary:` when no
Description is set). Google truncates snippets around 155-160 characters,
so anything longer is wasted or gets cut mid-sentence in the SERP. Keeping
the source metadata at or under 160 keeps the rendered snippet intact.

For each Markdown file under content/, this takes the `Description:` value
if present, otherwise the `Summary:` value, and fails when that value is
longer than 160 characters. Files with neither field are skipped (they fall
back to Pelican's auto-summary, which is handled elsewhere).

Exits 1 with a file + length pointer for every over-length value.
Exits 0 on clean.

Args:
    files (positional, optional) - restrict to these paths.
                                   If empty, scan all of content/**/*.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Google truncates snippets around here; keep source metadata at/under it.
MAX_LEN = 160

# Content root, relative to the repo (this script lives in scripts/).
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def content_markdown() -> list[Path]:
    """All *.md under content/, recursively."""
    return sorted(CONTENT_DIR.rglob("*.md"))


def meta_value(path: Path, key: str) -> str | None:
    """Return the value of a Pelican metadata `Key:` from the file header.

    Reads the leading metadata block (up to the first blank line) and
    supports indented continuation lines, which Pelican folds into the
    value with a space. Matching is case-insensitive on the key, matching
    Pelican's own metadata handling. Returns None if the key is absent.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return None

    key_lower = key.lower()
    value: list[str] | None = None
    for line in text.splitlines():
        # Metadata block ends at the first blank line.
        if line.strip() == "" and value is not None:
            break
        if line.strip() == "":
            # Leading blank line before any metadata; keep scanning.
            continue
        if value is not None and (line.startswith(" ") or line.startswith("\t")):
            # Continuation of the current value.
            value.append(line.strip())
            continue
        if ":" in line:
            name, _, rest = line.partition(":")
            if name.strip().lower() == key_lower:
                value = [rest.strip()]
                continue
            # A different metadata key ends any in-progress value.
            if value is not None:
                break
    if value is None:
        return None
    return " ".join(v for v in value if v).strip()


def effective_description(path: Path) -> str | None:
    """Description if present, else Summary, else None."""
    desc = meta_value(path, "Description")
    if desc:
        return desc
    return meta_value(path, "Summary")


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:] if p.endswith(".md")]
    else:
        paths = content_markdown()

    total = 0
    for path in paths:
        if not path.is_file():
            continue
        value = effective_description(path)
        if value is None:
            continue
        length = len(value)
        if length > MAX_LEN:
            print(
                f"::error file={path}::description/summary is {length} "
                f"chars (max {MAX_LEN})"
            )
            print(f"  {path}: {length} chars")
            print(f"    {value}")
            total += 1

    if total:
        print(
            f"\nFound {total} post(s) whose Description/Summary exceeds "
            f"{MAX_LEN} characters. Shorten the metadata so search snippets "
            f"are not truncated.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
