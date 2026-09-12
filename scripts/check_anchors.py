#!/usr/bin/env python3
"""Fail on broken in-page anchor links (#fragment targets) in the built site.

Used by:
- .github/workflows/anchor-check.yml (builds the site, then scans output/)

Why: lychee (link-rot.yml) verifies that a linked *page* exists, but it does not
verify that a URL fragment resolves to a real element on that page. A link like
<a href="#the-nosec-discipline"> or <a href="tls-three-jobs.html#tls-three-jobs">
is only useful if the destination document actually contains an element whose
id (or legacy name=) is "the-nosec-discipline" / "tls-three-jobs". When a
heading is renamed the anchor silently rots: the link still 200s, it just lands
at the top of the page instead of the section. This guard catches that class.

What this catches:
- A same-page fragment (href="#id") with no matching id/name on that page.
- A cross-page fragment (href="post.html#id" or the SITEURL-absolute
  href="https://rivassec.com/post.html#id") whose destination page exists in
  output/ but has no matching id/name.

What this does NOT flag:
- External links to a different host (only the SITEURL host is ours).
- href="#" alone, or any link with no fragment (query-only links included).
- A cross-page fragment whose destination page is not in output/ at all: a
  missing page is link rot, which lychee (link-rot.yml) already owns. We stay
  in our lane and only assert fragment integrity against pages we built.

The check BUILDS the site first with the same command deploy.yml uses
(pelican content -o output -s publishconf.py) then scans output/. If a built
tree already exists (output/ or out/) it scans that. Falls back to
`python -m pelican` when the pelican console script is not on PATH.

Exits 1 with GitHub Actions ::error annotations for every broken fragment.
Exits 0 when clean.
"""
from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent

# Any href="..." / href='...' attribute value.
HREF_RE = re.compile(r"""<a\b[^>]*\bhref\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
# id="..." on any element (tolerating quote style).
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
# Legacy <a name="..."> anchors.
NAME_RE = re.compile(r"""<a\b[^>]*\bname\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
SITEURL_RE = re.compile(r"""^\s*SITEURL\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def read_siteurl() -> str:
    """Read SITEURL from publishconf.py (the config deploy builds with)."""
    for name in ("publishconf.py", "pelicanconf.py"):
        cfg = REPO_ROOT / name
        if cfg.is_file():
            m = SITEURL_RE.search(cfg.read_text(encoding="utf-8", errors="replace"))
            if m:
                return m.group(1).rstrip("/")
    return "https://rivassec.com"


def build_site() -> None:
    """Build with the same command deploy.yml uses. Best-effort."""
    cmd = ["pelican", "content", "-o", "output", "-s", "publishconf.py"]
    try:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run(
            [sys.executable, "-m", "pelican", "content", "-o", "output",
             "-s", "publishconf.py"],
            cwd=REPO_ROOT,
            check=True,
        )


def find_output_dir() -> Path | None:
    for name in ("output", "out"):
        d = REPO_ROOT / name
        if d.is_dir() and any(d.glob("**/*.html")):
            return d
    return None


def anchors_of(text: str) -> set[str]:
    """Every fragment target a page offers: id= on any element + <a name=>."""
    return set(ID_RE.findall(text)) | set(NAME_RE.findall(text))


def resolve_target(href: str, current_rel: str, siteurl: str) -> str | None:
    """Map an href with a fragment to the output-relative page it points at.

    Returns the target page's output-relative path (e.g. "post.html" or
    "tag/tls.html"), "" for a same-page link, or None if the link is external
    or otherwise not ours to check.
    """
    # Fragment is everything after the first '#'. No '#' => nothing to check.
    if "#" not in href:
        return None
    path, _, _frag = href.partition("#")

    # Same-page link (href="#id"): destination is the current page.
    if path == "":
        return ""

    # Strip a query string before the fragment (path?query#frag).
    path = path.split("?", 1)[0]
    if path == "":
        return ""

    scheme = path.split("://", 1)[0].lower() if "://" in path else ""
    if path.startswith(siteurl + "/") or path == siteurl:
        # SITEURL-absolute link: strip the host, keep the site-root path.
        rest = path[len(siteurl):]
        target = rest.lstrip("/")
    elif scheme in ("http", "https") or path.startswith("//") or ":" in path.split("/", 1)[0]:
        # A different host, protocol-relative, or a non-http scheme
        # (mailto:, tel:, ...) => external, not ours to check.
        return None
    elif path.startswith("/"):
        # Root-relative link resolves against the output root.
        target = path.lstrip("/")
    else:
        # Document-relative link resolves against the current file's directory.
        target = posixpath.normpath(
            posixpath.join(posixpath.dirname(current_rel), path)
        )

    # A directory URL (or the site root) maps to its index.html.
    if target in ("", "."):
        target = "index.html"
    elif target.endswith("/"):
        target += "index.html"
    return target


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    if idx == -1:
        return 1
    return text.count("\n", 0, idx) + 1


def scan(out: Path, siteurl: str) -> tuple[int, int, int]:
    """Return (pages, fragment_links_checked, violations)."""
    pages = sorted(out.rglob("*.html"))
    texts: dict[str, str] = {}
    anchors: dict[str, set[str]] = {}
    for html in pages:
        rel = html.relative_to(out).as_posix()
        texts[rel] = html.read_text(encoding="utf-8", errors="replace")
        anchors[rel] = anchors_of(texts[rel])

    checked = 0
    violations = 0
    for html in pages:
        rel = html.relative_to(out).as_posix()
        text = texts[rel]
        for m in HREF_RE.finditer(text):
            href = m.group(1).strip()
            target = resolve_target(href, rel, siteurl)
            if target is None:
                continue
            frag = unquote(href.partition("#")[2]).strip()
            if frag == "":
                continue  # href="#" or href="page.html#"
            if target == "":
                target = rel  # same-page
            if target not in anchors:
                # Destination page is not in output/. Missing pages are link
                # rot (lychee's job); we only assert fragments on built pages.
                continue
            checked += 1
            if frag not in anchors[target]:
                lineno = line_of(text, m.group(0))
                where = "same page" if target == rel else target
                print(
                    f"::error file={out.name}/{rel},line={lineno}::"
                    f"broken anchor: href=\"{href}\" -> #{frag} "
                    f"has no matching id/name in {where}"
                )
                violations += 1
    return len(pages), checked, violations


def main() -> int:
    siteurl = read_siteurl()

    out = find_output_dir()
    if out is None:
        build_site()
        out = find_output_dir()
    if out is None:
        print("::error::no built site found and the build produced no output/")
        return 1

    pages, checked, violations = scan(out, siteurl)
    print(
        f"anchor guard: {pages} page(s), {checked} fragment link(s) checked, "
        f"{violations} broken",
        file=sys.stderr,
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
