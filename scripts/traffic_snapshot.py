#!/usr/bin/env python3
"""Snapshot the four GitHub repo-traffic endpoints into traffic-data/.

Layout produced (all under repo root traffic-data/):

  traffic-data/snapshots/<YYYY>/<MM>/<YYYY-MM-DD>-{views,clones,paths,referrers}.json
      Raw API payloads, audit trail. One set per day.

  traffic-data/traffic.sqlite
      Time-series store. Five tables:
        views(date PRIMARY KEY, count, uniques)
        clones(date PRIMARY KEY, count, uniques)
        paths_daily(captured_on, path, title, count, uniques, PRIMARY KEY (captured_on, path))
        referrers_daily(captured_on, referrer, count, uniques, PRIMARY KEY (captured_on, referrer))
        runs(captured_on PRIMARY KEY, run_id, sha)

  traffic-data/weekly-summary.md
      Top-line digest, regenerated each run from SQLite. Sundays only by
      default; pass --regen-summary to force.

Auth comes from GH_TOKEN in env (the workflow injects ${{ secrets.GITHUB_TOKEN }}).

Important caveat (2026-06-11): the GitHub Traffic API reports *repo*
traffic on github.com, NOT blog traffic on rivassec.com. The latter
goes through GitHub Pages' edge and is not exposed via API. Anyone
hoping to use this for blog analytics: see Cloudflare Analytics
instead.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("REPO", "rivassec/devsecops-notes")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "traffic-data"
DB_PATH = DATA_DIR / "traffic.sqlite"
SUMMARY_PATH = DATA_DIR / "weekly-summary.md"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

API_BASE = "https://api.github.com"


def _get(path: str) -> dict | list:
    """GET an authenticated API endpoint and return the parsed JSON."""
    if not TOKEN:
        sys.exit("GH_TOKEN or GITHUB_TOKEN must be set")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rivassec-traffic-snapshot",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_all() -> dict[str, dict | list]:
    return {
        "views": _get(f"/repos/{REPO}/traffic/views"),
        "clones": _get(f"/repos/{REPO}/traffic/clones"),
        "paths": _get(f"/repos/{REPO}/traffic/popular/paths"),
        "referrers": _get(f"/repos/{REPO}/traffic/popular/referrers"),
    }


def write_raw_snapshots(payloads: dict, today: dt.date) -> None:
    out_dir = SNAPSHOTS_DIR / f"{today.year:04d}" / f"{today.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        path = out_dir / f"{today.isoformat()}-{name}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS views ("
        "date TEXT PRIMARY KEY, count INTEGER NOT NULL, uniques INTEGER NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS clones ("
        "date TEXT PRIMARY KEY, count INTEGER NOT NULL, uniques INTEGER NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS paths_daily ("
        "captured_on TEXT NOT NULL, path TEXT NOT NULL, title TEXT, "
        "count INTEGER NOT NULL, uniques INTEGER NOT NULL, "
        "PRIMARY KEY (captured_on, path))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS referrers_daily ("
        "captured_on TEXT NOT NULL, referrer TEXT NOT NULL, "
        "count INTEGER NOT NULL, uniques INTEGER NOT NULL, "
        "PRIMARY KEY (captured_on, referrer))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs ("
        "captured_on TEXT PRIMARY KEY, run_id TEXT, sha TEXT)"
    )
    return conn


def upsert_views_clones(conn: sqlite3.Connection, payloads: dict) -> None:
    """Each call to /views and /clones returns the last 14 days. Re-running
    on the same day overwrites the same row; running on a new day adds it.
    The historical rows in older API responses are immutable on GitHub's
    side, so an UPSERT semantically equals 'replace if newer'."""
    for table, key in (("views", "views"), ("clones", "clones")):
        for row in payloads[key].get(table, []):
            date = row["timestamp"][:10]
            conn.execute(
                f"INSERT INTO {table}(date, count, uniques) VALUES (?, ?, ?) "
                f"ON CONFLICT(date) DO UPDATE SET "
                f"count=excluded.count, uniques=excluded.uniques",
                (date, int(row["count"]), int(row["uniques"])),
            )


def insert_paths_referrers(conn: sqlite3.Connection, payloads: dict, today: str) -> None:
    """Both endpoints are 14-day aggregates with no per-day breakdown. We
    capture them dated as the snapshot day so trends emerge from successive
    snapshots, not from any time series GitHub gives us."""
    for row in payloads["paths"]:
        conn.execute(
            "INSERT INTO paths_daily(captured_on, path, title, count, uniques) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(captured_on, path) DO UPDATE SET "
            "title=excluded.title, count=excluded.count, uniques=excluded.uniques",
            (today, row["path"], row.get("title", ""), int(row["count"]), int(row["uniques"])),
        )
    for row in payloads["referrers"]:
        conn.execute(
            "INSERT INTO referrers_daily(captured_on, referrer, count, uniques) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(captured_on, referrer) DO UPDATE SET "
            "count=excluded.count, uniques=excluded.uniques",
            (today, row["referrer"], int(row["count"]), int(row["uniques"])),
        )


def record_run(conn: sqlite3.Connection, today: str) -> None:
    conn.execute(
        "INSERT INTO runs(captured_on, run_id, sha) VALUES (?, ?, ?) "
        "ON CONFLICT(captured_on) DO UPDATE SET "
        "run_id=excluded.run_id, sha=excluded.sha",
        (today, os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_SHA", "")),
    )


def regenerate_summary(conn: sqlite3.Connection, today: dt.date) -> None:
    """Top-line digest: views and clones over the last 7 / 28 / all days,
    plus current top paths and referrers from the latest snapshot."""
    cur = conn.cursor()

    def _sum(table: str, since_iso: str) -> tuple[int, int]:
        row = cur.execute(
            f"SELECT COALESCE(SUM(count),0), COALESCE(SUM(uniques),0) FROM {table} "
            f"WHERE date >= ?",
            (since_iso,),
        ).fetchone()
        return int(row[0]), int(row[1])

    iso_today = today.isoformat()
    seven = (today - dt.timedelta(days=7)).isoformat()
    twentyeight = (today - dt.timedelta(days=28)).isoformat()

    v7 = _sum("views", seven)
    v28 = _sum("views", twentyeight)
    v_all = _sum("views", "0000-00-00")
    c7 = _sum("clones", seven)
    c28 = _sum("clones", twentyeight)
    c_all = _sum("clones", "0000-00-00")

    latest = cur.execute(
        "SELECT MAX(captured_on) FROM paths_daily"
    ).fetchone()[0]
    latest_paths = []
    latest_refs = []
    if latest:
        latest_paths = cur.execute(
            "SELECT path, title, count, uniques FROM paths_daily "
            "WHERE captured_on=? ORDER BY count DESC LIMIT 10",
            (latest,),
        ).fetchall()
        latest_refs = cur.execute(
            "SELECT referrer, count, uniques FROM referrers_daily "
            "WHERE captured_on=? ORDER BY count DESC LIMIT 10",
            (latest,),
        ).fetchall()

    runs_count = cur.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    earliest_run = cur.execute("SELECT MIN(captured_on) FROM runs").fetchone()[0]

    lines: list[str] = []
    lines.append(f"# Repo traffic summary — {iso_today}")
    lines.append("")
    lines.append(
        "Snapshots of `rivassec/devsecops-notes` repo traffic. **This does "
        "NOT include blog traffic at rivassec.com**; the GitHub Traffic API "
        "only covers github.com itself. Re-evaluate this layer if you wire "
        "up edge analytics for the published site."
    )
    lines.append("")
    lines.append(f"- Snapshots collected: {runs_count} (earliest: {earliest_run or 'n/a'})")
    lines.append("")
    lines.append("## Views (github.com)")
    lines.append("")
    lines.append("| Window | count | uniques |")
    lines.append("|---|---:|---:|")
    lines.append(f"| Last 7 days | {v7[0]} | {v7[1]} |")
    lines.append(f"| Last 28 days | {v28[0]} | {v28[1]} |")
    lines.append(f"| All-time captured | {v_all[0]} | {v_all[1]} |")
    lines.append("")
    lines.append("## Clones")
    lines.append("")
    lines.append("| Window | count | uniques |")
    lines.append("|---|---:|---:|")
    lines.append(f"| Last 7 days | {c7[0]} | {c7[1]} |")
    lines.append(f"| Last 28 days | {c28[0]} | {c28[1]} |")
    lines.append(f"| All-time captured | {c_all[0]} | {c_all[1]} |")
    lines.append("")
    lines.append(f"## Top paths (snapshot {latest or 'n/a'})")
    lines.append("")
    if latest_paths:
        lines.append("| count | uniques | path |")
        lines.append("|---:|---:|---|")
        for path, title, count, uniques in latest_paths:
            lines.append(f"| {count} | {uniques} | `{path}` |")
    else:
        lines.append("(no data yet)")
    lines.append("")
    lines.append(f"## Top referrers (snapshot {latest or 'n/a'})")
    lines.append("")
    if latest_refs:
        lines.append("| count | uniques | referrer |")
        lines.append("|---:|---:|---|")
        for ref, count, uniques in latest_refs:
            lines.append(f"| {count} | {uniques} | {ref} |")
    else:
        lines.append("(no data yet)")
    lines.append("")
    lines.append(
        f"_Generated by `scripts/traffic_snapshot.py` on {iso_today}._"
    )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Snapshot GitHub repo traffic.")
    parser.add_argument(
        "--regen-summary",
        action="store_true",
        help="Force-regenerate weekly-summary.md even on non-Sunday runs.",
    )
    args = parser.parse_args(argv[1:])

    today = dt.date.today()
    today_iso = today.isoformat()

    payloads = fetch_all()
    write_raw_snapshots(payloads, today)

    conn = open_db()
    with conn:
        upsert_views_clones(conn, payloads)
        insert_paths_referrers(conn, payloads, today_iso)
        record_run(conn, today_iso)

    # Regenerate summary on Sundays (weekday 6) or when forced. The cheap
    # cost makes "always regenerate" tempting, but writing the summary
    # changes the file mtime in git history every day; weekly cadence
    # keeps the diff signal clean.
    if today.weekday() == 6 or args.regen_summary:
        regenerate_summary(conn, today)

    conn.close()
    print(
        f"snapshot {today_iso}: views_14d={payloads['views'].get('count', 0)} "
        f"uniques_14d={payloads['views'].get('uniques', 0)} "
        f"clones_14d={payloads['clones'].get('count', 0)} "
        f"top_paths={len(payloads['paths'])} top_refs={len(payloads['referrers'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
