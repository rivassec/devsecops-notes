#!/usr/bin/env python3
"""Generate 1200x630 Open Graph title cards for each article.

Reads every ``content/*.md``, parses the Pelican frontmatter for Title and
Slug, and writes a branded 1200x630 PNG title card to
``content/images/og/{slug}.png``. Each card is a dark brand background with
the post title wrapped in a large readable font and a small ``rivassec.com``
wordmark in the footer.

With ``--write-frontmatter`` it inserts an ``Og_image: /images/og/{slug}.png``
line into any post that is missing one (placed directly after the ``Slug:``
line). Lane B's template reads this per-post image for the ``og:image`` meta tag.

The generator is idempotent: rendering is deterministic, so re-running produces
byte-identical cards, and the frontmatter insert is skipped when already present.

Run from the repo root:

    python3 scripts/gen_og_cards.py                    # (re)generate all cards
    python3 scripts/gen_og_cards.py --write-frontmatter
    python3 scripts/gen_og_cards.py --skip-existing    # only missing cards
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
OG_DIR = CONTENT_DIR / "images" / "og"

# Font resolution: prefer the vendored Inter (also used by cover cards), then a
# system font that exists on the box, and finally PIL's built-in bitmap font.
VENDORED_BOLD = Path(__file__).resolve().parent / "cover_fonts" / "Inter-Bold.ttf"
VENDORED_REGULAR = Path(__file__).resolve().parent / "cover_fonts" / "Inter-Regular.ttf"
SYSTEM_BOLD_CANDIDATES = [
    "/usr/share/fonts/liberation-fonts/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
SYSTEM_REGULAR_CANDIDATES = [
    "/usr/share/fonts/liberation-fonts/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]

WIDTH, HEIGHT = 1200, 630
MARGIN = 80
BG_TOP = (11, 15, 20)        # near-black brand background
BG_BOTTOM = (22, 32, 52)     # deep muted blue
TEXT_PRIMARY = (240, 244, 248)
TEXT_MUTED = (139, 148, 158)
ACCENT = (88, 166, 255)      # brand blue

TITLE_SIZE_CANDIDATES = [78, 70, 62, 56, 50, 44]
MAX_TITLE_LINES = 4

FRONTMATTER_FIELD_RE = re.compile(r"^([A-Z][A-Za-z_]*):\s*(.*)$")


def _resolve_font_path(vendored: Path, candidates: list[str]) -> str | None:
    if vendored.exists():
        return str(vendored)
    for cand in candidates:
        if Path(cand).exists():
            return cand
    return None


BOLD_FONT_PATH = _resolve_font_path(VENDORED_BOLD, SYSTEM_BOLD_CANDIDATES)
REGULAR_FONT_PATH = _resolve_font_path(VENDORED_REGULAR, SYSTEM_REGULAR_CANDIDATES)


def load_font(bold: bool, size: int) -> ImageFont.ImageFont:
    path = BOLD_FONT_PATH if bold else REGULAR_FONT_PATH
    if path:
        return ImageFont.truetype(path, size)
    # Last-resort fallback: PIL's built-in font. Pillow >= 10 accepts a size.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


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


def wrap_title(text: str, font: ImageFont.ImageFont, max_width: int,
               max_lines: int) -> list[str] | None:
    """Greedy word-wrap. Returns None if it cannot fit within max_lines."""
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
    if current:
        lines.append(" ".join(current))
    # A single word wider than the line can never fit cleanly.
    for line in lines:
        if font.getlength(line) > max_width:
            return None
    if len(lines) > max_lines:
        return None
    return lines


def fit_title(text: str, max_width: int, max_height: int,
              max_lines: int) -> tuple[ImageFont.ImageFont, list[str], int]:
    """Pick the largest candidate size whose wrapped title fits the box."""
    for size in TITLE_SIZE_CANDIDATES:
        font = load_font(bold=True, size=size)
        lines = wrap_title(text, font, max_width, max_lines)
        if lines is None:
            continue
        line_height = int(size * 1.18)
        if line_height * len(lines) <= max_height:
            return font, lines, line_height
    # Nothing fit; force-wrap with the smallest size and truncate to max_lines.
    size = TITLE_SIZE_CANDIDATES[-1]
    font = load_font(bold=True, size=size)
    lines = wrap_title(text, font, max_width, max_lines=10) or [text]
    lines = lines[:max_lines]
    last = lines[-1]
    while font.getlength(last + "...") > max_width and " " in last:
        last = last.rsplit(" ", 1)[0]
    lines[-1] = last + "..."
    return font, lines, int(size * 1.18)


def render_card(title: str, out_path: Path) -> None:
    img = vertical_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Accent rule near the top-left as a small brand mark.
    draw.rectangle((MARGIN, MARGIN, MARGIN + 96, MARGIN + 8), fill=ACCENT)

    # Title, auto-fit within the central area.
    max_text_width = WIDTH - 2 * MARGIN
    max_text_height = HEIGHT - 2 * MARGIN - 120  # leave room for footer + rule
    font, lines, line_height = fit_title(
        title, max_text_width, max_text_height, MAX_TITLE_LINES)
    block_height = line_height * len(lines)
    title_y = (HEIGHT - block_height) // 2 - 6
    for i, line in enumerate(lines):
        draw.text((MARGIN, title_y + i * line_height), line,
                  font=font, fill=TEXT_PRIMARY)

    # Footer wordmark + strapline.
    site_font = load_font(bold=True, size=34)
    tag_font = load_font(bold=False, size=26)
    site_text = "rivassec.com"
    tag_text = "Infrastructure. Security. Insight."
    site_ascent, site_descent = site_font.getmetrics()
    site_h = site_ascent + site_descent
    draw.text((MARGIN, HEIGHT - MARGIN - site_h),
              site_text, font=site_font, fill=ACCENT)
    tag_w = int(tag_font.getlength(tag_text))
    tag_ascent, tag_descent = tag_font.getmetrics()
    draw.text((WIDTH - MARGIN - tag_w,
               HEIGHT - MARGIN - (tag_ascent + tag_descent)),
              tag_text, font=tag_font, fill=TEXT_MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def ensure_og_in_frontmatter(path: Path, og_rel: str) -> bool:
    """Insert ``Og_image: <og_rel>`` after the ``Slug:`` line if absent.

    Returns True if the file was modified.
    """
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    fm_end = None
    for idx, line in enumerate(lines):
        if not line.strip():
            fm_end = idx
            break
    if fm_end is None:
        return False
    fm = "".join(lines[:fm_end])
    if re.search(r"^Og_image:\s*", fm, re.MULTILINE):
        return False
    slug_idx = None
    for idx in range(fm_end):
        if lines[idx].startswith("Slug:"):
            slug_idx = idx
            break
    insert_at = slug_idx + 1 if slug_idx is not None else fm_end
    lines.insert(insert_at, f"Og_image: {og_rel}\n")
    path.write_text("".join(lines))
    return True


def iter_posts() -> Iterable[Path]:
    for md in sorted(CONTENT_DIR.glob("*.md")):
        yield md


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-frontmatter", action="store_true",
                        help="Insert `Og_image:` line into posts missing one")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip cards that already exist on disk")
    parser.add_argument("--only", metavar="SLUG",
                        help="Generate a single slug only (matches frontmatter)")
    args = parser.parse_args(argv)

    if BOLD_FONT_PATH is None:
        print("! no TrueType font found; falling back to PIL default bitmap font",
              file=sys.stderr)

    generated = 0
    skipped = 0
    fm_edits = 0

    for post in iter_posts():
        fm = load_frontmatter(post)
        title = fm.get("Title")
        slug = fm.get("Slug")
        if not title or not slug:
            print(f"! skipping {post.name}: missing Title or Slug", file=sys.stderr)
            continue
        if args.only and args.only != slug:
            continue

        card_path = OG_DIR / f"{slug}.png"
        og_rel = f"/images/og/{slug}.png"

        if card_path.exists() and args.skip_existing:
            print(f"  skip {slug} (exists)")
            skipped += 1
        else:
            render_card(title, card_path)
            print(f"  wrote {card_path.relative_to(REPO_ROOT)}")
            generated += 1

        if args.write_frontmatter:
            if ensure_og_in_frontmatter(post, og_rel):
                print(f"  +Og_image: line in {post.name}")
                fm_edits += 1

    print(f"\nDone. generated={generated} skipped={skipped} "
          f"frontmatter_edits={fm_edits}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
