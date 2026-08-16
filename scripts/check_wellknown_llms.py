#!/usr/bin/env python3
"""Guard: security.txt + llms.txt/llms-full.txt exist, valid, and stay complete.

Scans the built output dir (like check_canonical_noindex.py). Fails if:
- .well-known/security.txt missing, lacks Contact:/Expires:, or Expires is in
  the past or within 30 days (so it cannot silently rot).
- llms.txt or llms-full.txt missing, or llms-full.txt exceeds a size cap.
- any published BlogPosting page is not referenced in llms.txt (keeps the AI
  index from drifting out of sync as posts are added).
"""
from __future__ import annotations
import datetime as dt, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPIRES_MIN_DAYS = 30
LLMS_FULL_MAX_BYTES = 512 * 1024


def find_out():
    for n in ("output", "out"):
        d = REPO / n
        if d.is_dir() and any(d.glob("**/*.html")):
            return d
    return None


def build():
    cmd = ["pelican", "content", "-o", "output", "-s", "publishconf.py"]
    try:
        subprocess.run(cmd, cwd=REPO, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run([sys.executable, "-m", "pelican", "content", "-o",
                        "output", "-s", "publishconf.py"], cwd=REPO, check=True)


def main() -> int:
    out = find_out()
    if out is None:
        build(); out = find_out()
    if out is None:
        print("::error::no built site"); return 1
    v = 0
    st = out / ".well-known" / "security.txt"
    if not st.is_file():
        print("::error::missing .well-known/security.txt"); v += 1
    else:
        txt = st.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"(?im)^Contact:", txt):
            print("::error::security.txt missing Contact:"); v += 1
        m = re.search(r"(?im)^Expires:\s*(\S+)", txt)
        if not m:
            print("::error::security.txt missing Expires:"); v += 1
        else:
            try:
                exp = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
                days = (exp - dt.datetime.now(dt.timezone.utc)).days
                if days < EXPIRES_MIN_DAYS:
                    print(f"::error::security.txt Expires in {days}d (<{EXPIRES_MIN_DAYS}); bump it"); v += 1
            except ValueError as e:
                print(f"::error::security.txt Expires unparseable: {e}"); v += 1
    llms = out / "llms.txt"; llmsf = out / "llms-full.txt"
    if not llms.is_file():
        print("::error::missing llms.txt"); v += 1
    if not llmsf.is_file():
        print("::error::missing llms-full.txt"); v += 1
    elif llmsf.stat().st_size > LLMS_FULL_MAX_BYTES:
        print(f"::error::llms-full.txt too large ({llmsf.stat().st_size}B)"); v += 1
    if llms.is_file():
        body = llms.read_text(encoding="utf-8", errors="replace")
        for html in sorted(out.rglob("*.html")):
            rel = html.relative_to(out).as_posix()
            if rel.startswith("drafts/") or "/drafts/" in rel:
                continue  # drafts are noindex and intentionally not in llms.txt
            t = html.read_text(encoding="utf-8", errors="replace")
            if "schema.org/BlogPosting" in t and html.stem not in body:
                print(f"::error::llms.txt does not reference post: {rel}"); v += 1
    print(f"security.txt + llms guard: {v} issue(s)", file=sys.stderr)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
