#!/usr/bin/env python3
"""Fail on contradictory noindex/canonical signals or a hidden page in the sitemap.

Used by:
- .github/workflows/canonical-check.yml (builds the site, then scans output/)

Why: a page that says <meta name="robots" content="noindex"> while pointing its
<link rel="canonical"> at a DIFFERENT URL sends Google two contradictory signals
("don't index me" vs "index that other page as the master of this content").
The one legitimate exception is a redirect stub: a moved page that noindexes
itself and canonicalizes to its new home. Those carry a matching
<meta http-equiv="refresh"> (or location.replace) to the same target, so we
recognise and allow them.

Separately, we must never advertise a URL in sitemap.xml that we ask Google not
to crawl or index. The 404 page and every redirect stub are hidden pages; none
of them may appear in sitemap.xml.

What this catches:
- noindex page whose canonical href != its own URL and which is NOT a redirect
  stub (the canonical does not match its refresh target).
- 404.html or any redirect-stub URL leaking into sitemap.xml.

What this does NOT flag:
- A noindex page with a SELF-referential canonical (tag/pagination/404 pages).
- A noindex page with no canonical at all (archives/tags index pages).
- A redirect stub whose canonical matches its refresh/replace target.

The check BUILDS the site first with the same command deploy.yml uses
(pelican content -o output -s publishconf.py) then scans output/. If a built
tree already exists (output/ or out/) and the build cannot run, it scans that.

Exits 1 with GitHub Actions ::error annotations for every violation. Exits 0
when clean.
"""
from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The <link rel="canonical" ...> tag, tolerating attribute order and quote style.
CANONICAL_RE = re.compile(
    r"""<link\b(?=[^>]*\brel\s*=\s*["']canonical["'])[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>""",
    re.IGNORECASE,
)
# <meta name="robots" content="..."> tag.
ROBOTS_RE = re.compile(
    r"""<meta\b(?=[^>]*\bname\s*=\s*["']robots["'])[^>]*\bcontent\s*=\s*["']([^"']*)["'][^>]*>""",
    re.IGNORECASE,
)
# <meta http-equiv="refresh" content="0; url=TARGET">
REFRESH_RE = re.compile(
    r"""<meta\b(?=[^>]*\bhttp-equiv\s*=\s*["']refresh["'])[^>]*\bcontent\s*=\s*["'][^"']*?url=([^"'\s]+)["']""",
    re.IGNORECASE,
)
# JS fallback: location.replace("TARGET") / location.href = "TARGET"
JS_REDIRECT_RE = re.compile(
    r"""location\.(?:replace\(|href\s*=\s*)["']([^"']+)["']""",
    re.IGNORECASE,
)
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
        # Fall back to the module form so `python check.py` works even when the
        # pelican console script is not on PATH.
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


def norm(url: str) -> str:
    """Loose URL normalisation for comparison: drop trailing slash + fragment."""
    url = url.strip().split("#", 1)[0]
    return url.rstrip("/")


def self_urls(rel: str, siteurl: str) -> set[str]:
    """The set of URL forms that count as self-referential for this file."""
    rel = rel.replace("\\", "/")
    forms: set[str] = set()
    if rel == "index.html":
        forms.add(siteurl + "/")
        forms.add(siteurl + "/index.html")
    elif rel.endswith("/index.html"):
        d = rel[: -len("index.html")]  # keeps trailing slash, e.g. "accessibility/"
        forms.add(siteurl + "/" + d)
        forms.add(siteurl + "/" + rel)
    else:
        forms.add(siteurl + "/" + rel)
    return {norm(u) for u in forms}


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    if idx == -1:
        return 1
    return text.count("\n", 0, idx) + 1


def scan_pages(out: Path, siteurl: str) -> int:
    """Check every HTML page for a contradictory noindex/cross-canonical. Also
    return the count of noindex pages inspected via the module-level counter."""
    global _noindex_inspected
    violations = 0
    for html in sorted(out.rglob("*.html")):
        rel = html.relative_to(out).as_posix()
        text = html.read_text(encoding="utf-8", errors="replace")

        rm = ROBOTS_RE.search(text)
        if not rm or "noindex" not in rm.group(1).lower():
            continue
        _noindex_inspected += 1

        cm = CANONICAL_RE.search(text)
        if not cm:
            # noindex with no canonical is fine (archives/tags index pages).
            continue
        canonical = cm.group(1)
        if norm(canonical) in self_urls(rel, siteurl):
            continue  # self-referential canonical, allowed

        # Cross-canonical. Allowed only if this is a redirect stub whose refresh
        # (or JS) target matches the canonical.
        rf = REFRESH_RE.search(text)
        js = JS_REDIRECT_RE.search(text)
        targets = {norm(m.group(1)) for m in (rf, js) if m}
        if norm(canonical) in targets:
            continue  # legitimate moved-page redirect stub

        lineno = line_of(text, cm.group(0))
        print(
            f"::error file={out.name}/{rel},line={lineno}::"
            f"noindex page canonicalizes to a different URL ({canonical}) "
            f"and is not a redirect stub"
        )
        print(f"  {rel}: robots=noindex, canonical={canonical}, own={siteurl}/{rel}")
        violations += 1
    return violations


def hidden_page_urls(out: Path, siteurl: str) -> dict[str, str]:
    """Map hidden-page URL -> reason. Hidden = the 404 page or a redirect stub."""
    hidden: dict[str, str] = {}
    for html in sorted(out.rglob("*.html")):
        rel = html.relative_to(out).as_posix()
        text = html.read_text(encoding="utf-8", errors="replace")
        reason = None
        if rel == "404.html" or rel.endswith("/404.html"):
            reason = "404 page"
        elif REFRESH_RE.search(text) or JS_REDIRECT_RE.search(text):
            reason = "redirect stub"
        if reason:
            for form in self_urls(rel, siteurl):
                hidden[form] = reason
    return hidden


def scan_sitemap(out: Path, siteurl: str) -> int:
    sitemap = out / "sitemap.xml"
    if not sitemap.is_file():
        print(f"::error file={out.name}/sitemap.xml::sitemap.xml not found")
        return 1
    try:
        root = ET.fromstring(sitemap.read_text(encoding="utf-8", errors="replace"))
    except ET.ParseError as e:
        print(f"::error file={out.name}/sitemap.xml::sitemap.xml is not valid XML: {e}")
        return 1

    locs = {norm(loc.text or "") for loc in root.iter() if loc.tag.endswith("}loc") or loc.tag == "loc"}
    hidden = hidden_page_urls(out, siteurl)

    violations = 0
    for url, reason in sorted(hidden.items()):
        if url in locs:
            print(
                f"::error file={out.name}/sitemap.xml::sitemap advertises a hidden "
                f"page ({reason}): {url}"
            )
            violations += 1
    return violations


_noindex_inspected = 0


def main() -> int:
    siteurl = read_siteurl()

    out = find_output_dir()
    if out is None:
        build_site()
        out = find_output_dir()
    if out is None:
        print("::error::no built site found and the build produced no output/")
        return 1

    page_violations = scan_pages(out, siteurl)
    sitemap_violations = scan_sitemap(out, siteurl)
    total = page_violations + sitemap_violations

    print(
        f"\nInspected {_noindex_inspected} noindex page(s) in {out.name}/; "
        f"{page_violations} bad canonical(s), {sitemap_violations} hidden page(s) "
        f"in sitemap.",
        file=sys.stderr,
    )
    if total:
        print(
            f"Found {total} canonical/noindex violation(s). See annotations above.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
