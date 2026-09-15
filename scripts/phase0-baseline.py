"""Phase 0 baseline reporter — read-only.

Prints the current archive state so the orchestrator can record a baseline in
docs/phase-ledger.md before any implementation work starts. Opens the DB
read-only and never writes.

Usage (from the repo root):
    backend\\.venv\\Scripts\\python.exe scripts/phase0-baseline.py
    python scripts/phase0-baseline.py
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "backend" / "data" / "ideasexist.db"


def main() -> int:
    if not DB.exists():
        print(f"[baseline] DB not found at {DB}")
        return 1
    # Read-only connection: cannot modify the archive even by accident.
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        cur = conn.cursor()

        def one(sql: str, *params):
            return cur.execute(sql, params).fetchone()[0]

        total = one("SELECT COUNT(*) FROM startups")
        verified = one("SELECT COUNT(*) FROM startups WHERE verified=1")
        dead = one("SELECT COUNT(*) FROM startups WHERE status='dead'")
        website = one("SELECT COUNT(*) FROM startups WHERE website_url IS NOT NULL AND website_url != ''")
        github = one("SELECT COUNT(*) FROM startups WHERE github_url IS NOT NULL AND github_url != ''")
        last_checked = one("SELECT MAX(last_checked) FROM startups")
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

        print("[baseline] IdeaExists archive")
        print(f"  db_path      : {DB}")
        print(f"  tables       : {', '.join(tables)}")
        print(f"  total        : {total}")
        print(f"  verified     : {verified}")
        print(f"  dead         : {dead}")
        print(f"  website_url  : {website}")
        print(f"  github_url   : {github}")
        print(f"  last_checked : {last_checked}")
        print("  categories   :")
        for cat, n in cur.execute("SELECT category, COUNT(*) FROM startups GROUP BY category ORDER BY 2 DESC"):
            print(f"    {cat or 'null':<14} {n}")
        print("  sources      :")
        for src, n in cur.execute("SELECT source, COUNT(*) FROM startups GROUP BY source ORDER BY 2 DESC"):
            print(f"    {src or 'null':<14} {n}")
        expected = {"total": 1282, "verified": 1278, "dead": 0, "github": 57}
        drift = {k: (v, {"total": total, "verified": verified, "dead": dead, "github": github}[k])
                 for k, v in expected.items() if v != {"total": total, "verified": verified, "dead": dead, "github": github}[k]}
        if drift:
            print("[baseline] DRIFT vs expected (report this first):")
            for k, (exp, got) in drift.items():
                print(f"    {k}: expected {exp}, got {got}")
        else:
            print("[baseline] matches expected baseline (1282 / 1278 / 0 / 57)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
