"""Revive entries wrongly filed by the old verify logic (bot-wall 403s counted as strikes).

Real incident 2026-08-11: Cloudflare 403s dead-flipped healthy companies —
Capterra (cf=6 → dead) and WHOOP (cf=3 → dead); Product Hunt / Atlas Obscura /
Middesk carried bogus strikes. Since then verify treats only 404/410 as dead
and skips walls/transients, but dead rows are never auto-revived (revive is a
human action by design), so this script repairs the archive.

What it does per matched row:
  - status 'dead'/'pivoted' -> 'active'   (revive; verified is left untouched —
    a revive is NOT a verification)
  - check_failures -> 0                    (human judgment resets the streak)

Usage (from backend/, venv python):
    python -m scripts.restore_false_dead --names "WHOOP,Capterra"
    python -m scripts.restore_false_dead --ids 148,214
"""
import argparse
import sqlite3
import sys

from app import db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", help="comma-separated startup names")
    parser.add_argument("--ids", help="comma-separated startup ids")
    args = parser.parse_args()

    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        where, params = "name IN (%s)" % ",".join("?" * len(names)), names
    elif args.ids:
        ids = [int(i) for i in args.ids.split(",") if i.strip()]
        where, params = "id IN (%s)" % ",".join("?" * len(ids)), ids
    else:
        parser.error("provide --names or --ids")

    conn = db.connect()
    try:
        rows = conn.execute(f"SELECT id, name, status, verified, check_failures FROM startups WHERE {where}", params).fetchall()
        if not rows:
            print("no matching startups — nothing to do")
            return 1
        revived = 0
        cleared = 0
        for r in rows:
            changed = []
            if r["status"] in ("dead", "pivoted"):
                changed.append(f"status {r['status']} -> active")
                revived += 1
            if r["check_failures"]:
                changed.append(f"check_failures {r['check_failures']} -> 0")
                cleared += 1
            conn.execute(
                "UPDATE startups SET status = 'active', check_failures = 0 WHERE id = ?",
                (r["id"],),
            )
            print(f"  {r['name']} (id={r['id']}, verified={r['verified']}): " + ("; ".join(changed) if changed else "already clean"))
        conn.commit()
        print(f"\n{revived} revived, {cleared} strike counters cleared")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
