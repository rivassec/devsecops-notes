#!/usr/bin/env python3
"""Generate 1200x630 Open Graph cover images for each article.

Reads every `content/*.md` (skipping `content/_external`), parses the Pelican
frontmatter for Title, Category, and Slug, and writes a branded cover PNG
to `content/images/covers/{slug}.png`. With --write-frontmatter, inserts a
`Cover: images/covers/{slug}.png` line into any post missing one.

Run from the repo root:

    python3 scripts/generate_covers.py                # generate missing
    python3 scripts/generate_covers.py --force        # regenerate all
    python3 scripts/generate_covers.py --write-frontmatter
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
COVERS_DIR = CONTENT_DIR / "images" / "covers"
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONT_REGULAR = FONTS_DIR / "Inter-Regular.ttf"
FONT_BOLD = FONTS_DIR / "Inter-Bold.ttf"

WIDTH, HEIGHT = 1200, 630
MARGIN = 72
BG_TOP = (13, 17, 23)       # GitHub dark bg
BG_BOTTOM = (30, 42, 68)    # muted blue
TEXT_PRIMARY = (255, 255, 255)
TEXT_MUTED = (139, 148, 158)
ACCENT = (88, 166, 255)     # GitHub blue

FRONTMATTER_FIELD_RE = re.compile(r"^([A-Z][A-Za-z_]*):\s*(.*)$")


def load_frontmatter(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    with path.open() as fh:
        for line in fh:
            if not line.strip():
                break
            m = FRONTMATTER_FIELD_RE.match(line)
            if m:
                fields[m.group(1)] = m.group(2).strip()
    return fields


def vertical_gradient(width: int, height: int, top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / (height - 1)
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def wrap_title(text: str, font: ImageFont.FreeTypeFont, max_width: int,
               max_lines: int = 3) -> list[str]:
    """Greedy word-wrap; truncate with ellipsis if it exceeds max_lines."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        probe = " ".join(current + [word])
        if font.getlength(probe) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(" ".join(current))
    # If we broke early, indicate truncation on the last line.
    joined_words = " ".join(" ".join(lines).split())
    if joined_words != text.strip() and lines:
        last = lines[-1]
        while font.getlength(last + "...") > max_width and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "..."
    return lines


def category_pill(draw: ImageDraw.ImageDraw, text: str, pos: tuple[int, int],
                  font: ImageFont.FreeTypeFont) -> None:
    pad_x, pad_y = 18, 10
    text_w = int(font.getlength(text))
    ascent, descent = font.getmetrics()
    text_h = ascent + descent
    x, y = pos
    rect = (x, y, x + text_w + 2 * pad_x, y + text_h + 2 * pad_y)
    draw.rounded_rectangle(rect, radius=8, fill=ACCENT)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=TEXT_PRIMARY)


def render_cover(title: str, category: str, out_path: Path) -> None:
    if not FONT_REGULAR.exists() or not FONT_BOLD.exists():
        raise FileNotFoundError(
            f"Inter fonts not found under {FONTS_DIR}. Did you vendor them?"
        )

    img = vertical_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Category pill.
    pill_font = ImageFont.truetype(str(FONT_BOLD), 26)
    category_pill(draw, category.upper(), (MARGIN, MARGIN), pill_font)

    # Title.
    title_font = ImageFont.truetype(str(FONT_BOLD), 76)
    max_text_width = WIDTH - 2 * MARGIN
    lines = wrap_title(title, title_font, max_text_width, max_lines=3)
    line_height = int(title_font.size * 1.18)
    block_height = line_height * len(lines)
    title_y = (HEIGHT - block_height) // 2 - 10
    for i, line in enumerate(lines):
        draw.text((MARGIN, title_y + i * line_height), line,
                  font=title_font, fill=TEXT_PRIMARY)

    # Footer: site + strapline.
    site_font = ImageFont.truetype(str(FONT_BOLD), 32)
    tag_font = ImageFont.truetype(str(FONT_REGULAR), 26)
    site_text = "rivassec.com"
    tag_text = "Infrastructure. Security. Insight."
    site_w = int(site_font.getlength(site_text))
    tag_w = int(tag_font.getlength(tag_text))
    site_ascent, site_descent = site_font.getmetrics()
    site_h = site_ascent + site_descent
    draw.text((WIDTH - MARGIN - site_w, HEIGHT - MARGIN - site_h),
              site_text, font=site_font, fill=ACCENT)
    draw.text((MARGIN, HEIGHT - MARGIN - 36),
              tag_text, font=tag_font, fill=TEXT_MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)

    pngquant = shutil.which("pngquant")
    if pngquant:
        subprocess.run(
            [pngquant, "--quality=70-90", "--strip", "--ext", ".png",
             "--force", str(out_path)],
            check=True,
        )
    else:
        print(f"  ! pngquant not found on PATH; cover left uncompressed "
              f"({out_path.name})", file=sys.stderr)


def ensure_cover_in_frontmatter(path: Path, cover_rel: str) -> bool:
    """Insert `Cover: <cover_rel>` into frontmatter if not present.

    Returns True if the file was modified.
    """
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    # Find end of frontmatter (first blank line).
    for idx, line in enumerate(lines):
        if not line.strip():
            fm_end = idx
            break
    else:
        return False
    fm = "".join(lines[:fm_end])
    if re.search(r"^Cover:\s*", fm, re.MULTILINE):
        return False
    new_line = f"Cover: {cover_rel}\n"
    # Insert after Summary: if present, else at end of frontmatter.
    summary_idx = None
    for idx in range(fm_end):
        if lines[idx].startswith("Summary:"):
            summary_idx = idx
            break
    insert_at = summary_idx + 1 if summary_idx is not None else fm_end
    lines.insert(insert_at, new_line)
    path.write_text("".join(lines))
    return True


def iter_posts() -> Iterable[Path]:
    for md in sorted(CONTENT_DIR.glob("*.md")):
        yield md


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Regenerate covers that already exist")
    parser.add_argument("--write-frontmatter", action="store_true",
                        help="Insert `Cover:` line into posts missing one")
    parser.add_argument("--only", metavar="SLUG",
                        help="Generate a single slug only (matches frontmatter)")
    args = parser.parse_args(argv)

    generated = 0
    skipped = 0
    fm_edits = 0

    for post in iter_posts():
        fm = load_frontmatter(post)
        title = fm.get("Title")
        slug = fm.get("Slug")
        category = fm.get("Category", "DevSecOps")
        if not title or not slug:
            print(f"! skipping {post.name}: missing Title or Slug", file=sys.stderr)
            continue
        if args.only and args.only != slug:
            continue

        cover_path = COVERS_DIR / f"{slug}.png"
        cover_rel = f"images/covers/{slug}.png"

        if cover_path.exists() and not args.force:
            print(f"  skip {slug} (exists)")
            skipped += 1
        else:
            render_cover(title, category, cover_path)
            print(f"  wrote {cover_path.relative_to(REPO_ROOT)}")
            generated += 1

        if args.write_frontmatter:
            if ensure_cover_in_frontmatter(post, cover_rel):
                print(f"  +Cover: line in {post.name}")
                fm_edits += 1

    print(
        f"\nDone. generated={generated} skipped={skipped} "
        f"frontmatter_edits={fm_edits}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
