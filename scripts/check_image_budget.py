#!/usr/bin/env python3
"""Fail if any image under content/images/ exceeds its size budget.

Used by:
- .github/workflows/image-budget.yml (runs against the whole tree on push)

Why: images are the heaviest thing we ship. Oversized files slow first paint,
waste crawl budget, and quietly creep upward as posts accumulate. A hard budget
enforced in CI keeps the page weight honest.

Budgets (1 KB == 1024 bytes):
- content/images/og/*.png ............ 250 KB  (social cards; larger canvas)
- every other file under content/images  150 KB

Exits 1 with a GitHub Actions ::error annotation per offending file, plus a
human-readable pointer. Exits 0 when every image is within budget.

Args:
    paths (positional, optional) - restrict the scan to these files or dirs.
                                   If empty, scan all of content/images.
"""
from __future__ import annotations

import sys
from pathlib import Path

KB = 1024
IMAGES_ROOT = Path("content/images")
OG_DIR = IMAGES_ROOT / "og"

OG_BUDGET = 250 * KB
DEFAULT_BUDGET = 150 * KB

# Extensions we treat as images worth budgeting.
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".avif"}


def budget_for(path: Path) -> int:
    """Return the byte budget that applies to path."""
    if path.suffix.lower() == ".png" and OG_DIR in path.parents:
        return OG_BUDGET
    return DEFAULT_BUDGET


def iter_images(paths: list[Path]) -> list[Path]:
    """Expand the given paths into a sorted list of image files."""
    roots = paths or [IMAGES_ROOT]
    found: set[Path] = set()
    for root in roots:
        if root.is_file():
            if root.suffix.lower() in IMAGE_SUFFIXES:
                found.add(root)
        elif root.is_dir():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
                    found.add(p)
    return sorted(found)


def fmt_kb(nbytes: int) -> str:
    return f"{nbytes / KB:.1f} KB"


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv[1:]]
    images = iter_images(paths)

    offenders = 0
    for path in images:
        size = path.stat().st_size
        budget = budget_for(path)
        if size > budget:
            offenders += 1
            print(
                f"::error file={path}::image {fmt_kb(size)} exceeds "
                f"{fmt_kb(budget)} budget"
            )
            print(f"  {path}: {fmt_kb(size)} > {fmt_kb(budget)}")

    if offenders:
        print(
            f"\nFound {offenders} image(s) over budget. Re-export or optimize "
            f"(Pillow save(optimize=True), or palette-quantize PNGs).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(images)} image(s) within budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
