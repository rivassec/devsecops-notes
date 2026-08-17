#!/usr/bin/env python3
"""Guard: inter-post link-graph invariant for published posts.
- each non-hub post links to <=2 other posts (in-body {filename} or bare slug.html)
- every post has >=1 inbound link (no orphans)
- every post is reachable (directed) from the hub pillar (devsecops-guide)
Published = article pages built at the output root (drafts land under drafts/).
Links are read from content/*.md source (the editorial links)."""
from __future__ import annotations
import glob, os, re, subprocess, sys
from collections import defaultdict, deque
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent
HUB="devsecops-guide"; MAXOUT=2
def find_out():
    for n in ("output","out"):
        d=REPO/n
        if d.is_dir() and any(d.glob("*.html")): return d
    return None
def build():
    try: subprocess.run(["pelican","content","-o","output","-s","publishconf.py"],cwd=REPO,check=True)
    except (FileNotFoundError,subprocess.CalledProcessError):
        subprocess.run([sys.executable,"-m","pelican","content","-o","output","-s","publishconf.py"],cwd=REPO,check=True)
def fm_slug(text, stem):
    for line in text.splitlines():
        if not line.strip(): break
        m=re.match(r"^[Ss]lug:\s*(\S+)\s*$", line)
        if m: return m.group(1)
    return stem
def main():
    out=find_out()
    if out is None:
        build(); out=find_out()
    if out is None:
        print("::error::no built site"); return 1
    published={h.stem for h in out.glob("*.html")
               if "schema.org/BlogPosting" in h.read_text(encoding="utf-8",errors="replace")}
    slugmap={}; texts={}
    for p in glob.glob(str(REPO/"content"/"*.md")):
        stem=os.path.basename(p)[:-3]; txt=open(p,encoding="utf-8").read()
        slugmap[stem]=fm_slug(txt,stem); texts[stem]=txt
    slug2stem={v:k for k,v in slugmap.items()}
    fre=re.compile(r"\]\(\{filename\}[./]*([A-Za-z0-9\-_]+)\.md")
    hre=re.compile(r"\]\((?:https://rivassec\.com)?/?([a-z0-9][a-z0-9-]*)\.html")
    edges=defaultdict(set)
    for slug in published:
        stem=slug2stem.get(slug)
        if not stem: continue
        txt=texts[stem]
        for t in fre.findall(txt):
            tgt=slugmap.get(t)
            if tgt in published and tgt!=slug: edges[slug].add(tgt)
        for t in hre.findall(txt):
            if t in published and t!=slug: edges[slug].add(t)
    v=0
    for s in sorted(published):
        if s!=HUB and len(edges.get(s,()))>MAXOUT:
            print(f"::error::{s} links to {len(edges[s])} posts (>{MAXOUT}): {sorted(edges[s])}"); v+=1
    inb={n:0 for n in published}
    for s,ts in edges.items():
        for t in ts: inb[t]+=1
    for n in sorted(published):
        if inb[n]==0: print(f"::error::orphan (0 inbound article-links): {n}"); v+=1
    if HUB in published:
        seen={HUB}; q=deque(seen)
        while q:
            for t in edges.get(q.popleft(),()):
                if t not in seen: seen.add(t); q.append(t)
        for n in sorted(published-seen):
            print(f"::error::not reachable from hub: {n}"); v+=1
    print(f"link-graph guard: {len(published)} posts, {v} issue(s)", file=sys.stderr)
    return 1 if v else 0
if __name__=="__main__": sys.exit(main())
