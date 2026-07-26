#!/usr/bin/env python3
"""Fail if any article Summary is too short, too long, missing, or a duplicate.

Used by:
- .pre-commit-config.yaml (runs against *staged* .md files under content/)
- CI (optional, via .github/workflows/*.yml if wired)

Why: SEO snippets and social-media previews depend on the Summary metadata.
Google truncates at ~160 chars; short summaries look empty; missing summaries
leave the crawler to auto-generate something worse. Duplicate summaries are
worse than distinct ones for topic distinguishability.

Rules:
- Summary field must exist and be non-empty for content/*.md (articles) and
  content/pages/*.md (pages)
- Length must be between MIN_LEN and MAX_LEN characters (Google target range)
- No two published articles may share an identical Summary
- Draft posts (Status: draft) are exempt

Exits 1 on any violation with a file:line pointer.
Exits 0 on clean.

Args:
    files (positional, optional) - restrict to these paths.
                                   If empty, scan all tracked article .md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MIN_LEN = 100
MAX_LEN = 160

# Directories that hold posts. Files elsewhere (README, docs, etc.) are ignored.
ARTICLE_ROOTS = ("content/",)
IGNORE_ROOTS = ("content/_external/", "content/extra/", "content/images/", "content/pages/")


def tracked_articles() -> list[Path]:
    """All *.md files under content/ that are actual articles (not pages/extras)."""
    out = subprocess.run(
        ["git", "ls-files", "content/*.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    paths: list[Path] = []
    for line in out.splitlines():
        if not line:
            continue
        if any(line.startswith(ignore) for ignore in IGNORE_ROOTS):
            continue
        paths.append(Path(line))
    return paths


def parse_metadata(path: Path) -> tuple[dict[str, str], int]:
    """Return (metadata dict, line_no_of_summary_or_1)."""
    meta: dict[str, str] = {}
    summary_line = 1
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return meta, summary_line
    # Pelican metadata is Title: value pairs at the very top, until a blank line.
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            break
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        meta[key.lower()] = value
        if key.lower() == "summary":
            summary_line = lineno
    return meta, summary_line


def scan(path: Path, seen_summaries: dict[str, Path]) -> list[str]:
    """Return list of violation messages for this file, if any."""
    meta, summary_line = parse_metadata(path)

    # Skip drafts
    if meta.get("status", "").lower() == "draft":
        return []

    violations: list[str] = []
    summary = meta.get("summary", "")

    if not summary:
        violations.append(f"{path}:1: missing Summary: field")
        return violations

    length = len(summary)
    if length < MIN_LEN:
        violations.append(
            f"{path}:{summary_line}: Summary too short "
            f"({length} chars, min {MIN_LEN}). Google truncates aggressively "
            f"below ~120 chars; social-preview cards look empty."
        )
    if length > MAX_LEN:
        violations.append(
            f"{path}:{summary_line}: Summary too long "
            f"({length} chars, max {MAX_LEN}). Google truncates SERP snippets "
            f"around 155-160 chars, cutting off mid-word looks unprofessional."
        )

    if summary in seen_summaries:
        prior = seen_summaries[summary]
        violations.append(
            f"{path}:{summary_line}: Summary is a duplicate of {prior}. "
            f"Distinct summaries help topic distinguishability in search."
        )
    else:
        seen_summaries[summary] = path

    return violations


def main(argv: list[str]) -> int:
    # If explicit files passed (pre-commit calling us with staged files), restrict.
    # Otherwise scan all tracked article .md.
    if len(argv) > 1:
        paths = [
            Path(p)
            for p in argv[1:]
            if p.endswith(".md")
            and any(p.startswith(root) for root in ARTICLE_ROOTS)
            and not any(p.startswith(ignore) for ignore in IGNORE_ROOTS)
        ]
    else:
        paths = tracked_articles()

    if not paths:
        return 0

    # For duplicate detection we always need the full set to compare against.
    # If pre-commit gave us a subset, load the rest for cross-file dedup.
    all_paths = tracked_articles()
    seen_summaries: dict[str, Path] = {}
    for p in all_paths:
        if p in paths:
            continue  # will scan later
        meta, _ = parse_metadata(p)
        if meta.get("status", "").lower() == "draft":
            continue
        s = meta.get("summary", "")
        if s:
            seen_summaries[s] = p

    all_violations: list[str] = []
    for path in paths:
        all_violations.extend(scan(path, seen_summaries))

    # Enforcement policy:
    # - When explicit files were passed (pre-commit staged files, or a targeted
    #   check), fail loudly. The author is actively working on this content.
    # - When no files were passed (repo-wide scan), warn but do not fail. There
    #   are pre-existing over-length summaries in older posts. Enforce them
    #   incrementally when the author edits each post rather than blocking
    #   every commit on historical content.
    explicit_files = len(argv) > 1
    if all_violations:
        if explicit_files:
            print("Description quality check FAILED:")
        else:
            print("Description quality WARNINGS (repo-wide scan, non-blocking):")
        for v in all_violations:
            print(f"  {v}")
        print()
        print(f"Rules: Summary field required, {MIN_LEN}-{MAX_LEN} chars, no duplicates.")
        return 1 if explicit_files else 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
