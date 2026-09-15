"""Merge duplicate startup filings — the ONE destructive step in the plan.

Rule: group filings by NORMALISED REGISTRABLE DOMAIN (hostname minus
www/path/port, public-suffix aware for common TLDs). Same registrable domain
= same company filed twice (v2.vuejs.org / vuejs.org, about.gitlab.com/... /
gitlab.com). Different registrable domains sharing a name = flagged for
manual review, NEVER merged (bird.com vs bird.co are different companies).

Keep: the verified row if any, else the longest description, else lowest id.
Fold: best root URL + longest tagline/description into the keeper.
Delete: the other filings in the group.

Safety: dry-run is the DEFAULT. `--apply` takes a timestamped SQLite backup
first (sqlite3 backup API — WAL-safe, unlike cp).

Usage (from backend/):
    .venv/Scripts/python.exe scripts/merge_duplicates.py            # dry run
    .venv/Scripts/python.exe scripts/merge_duplicates.py --apply    # backup + merge
"""
import argparse
import datetime
import re
import sqlite3
import sys
from pathlib import Path

# Names that are NEVER auto-merged even if a future rule would group them —
# human-verified to be different companies (bird.com email vs bird.co scooters).
NEVER_MERGE = {"Bird"}

# Country-style suffixes where the registrable domain is the LAST THREE labels.
_THREE_PART = {
    "com.au", "co.uk", "org.uk", "co.nz", "com.br", "co.jp", "co.in",
    "com.sg", "co.za", "com.mx", "com.ar", "co.il", "com.tr", "com.my",
    "com.hk", "co.kr", "com.tw", "com.pl", "com.ua", "co.id",
}


def registrable_domain(url: str | None) -> str | None:
    """Normalised registrable domain for a URL, or None if it has no host."""
    if not url:
        return None
    m = re.match(r"^[a-z][a-z0-9+.-]*://([^/?#]+)", url.strip().lower())
    host = m.group(1) if m else url.strip().lower().split("/")[0]
    host = host.split("@")[-1].split(":")[0]
    host = host.lstrip(".")
    if not re.match(r"^[a-z0-9.-]+$", host):
        return None
    labels = [x for x in host.split(".") if x]
    if len(labels) <= 1:
        return host
    for suffix in _THREE_PART:
        if host.endswith("." + suffix):
            return ".".join(labels[-3:])
    # Two-part suffixes (and the len==2 degenerate case) both reduce to the
    # last two labels; unknown TLDs fall back to the same heuristic.
    return ".".join(labels[-2:])


def identity_key(url: str | None) -> str | None:
    """The identity anchor for a URL.

    Registrable domain for normal sites (apple.com, gitlab.com) — but GitHub
    hosts get owner/repo granularity: every repo on github.com shares one
    registrable domain, and grouping them would merge 13 unrelated
    'karpathy/*' repos into one filing (the first dry run's mistake).
    """
    if not url:
        return None
    dom = registrable_domain(url)
    if not dom:
        return None
    rest = url.strip().lower().split("://", 1)[-1].split("/", 1)
    host = rest[0]
    path = rest[1] if len(rest) > 1 else ""
    if host in ("github.com", "www.github.com"):
        owner_repo = path.strip("/").split("/")[:2]
        return f"github:{'/'.join(owner_repo) or 'root'}"
    if host.endswith(".github.io"):
        return f"githubio:{host.split('.')[0]}"
    return f"dom:{dom}"


def best_url(candidates: list[str]) -> str | None:
    """Prefer a clean root (https, no path) over scraped subpages."""
    ranked = sorted(
        (u for u in candidates if u),
        key=lambda u: (
            not u.startswith("https://"),  # https first
            len(u.split("://", 1)[-1].split("/", 1)[-1]) > 0,  # no path first
            len(u),
        ),
    )
    return ranked[0] if ranked else None


def group_filings(rows: list[dict]) -> list[dict]:
    """Rows -> merge groups. Grouped by identity key (website wins over
    github); then a same-name/different-home pass flags human reviews."""
    by_key: dict[str, list[dict]] = {}
    for r in rows:
        key = identity_key(r["website_url"]) or identity_key(r["github_url"])
        by_key.setdefault(key or f"NO-HOME:{r['name']}", []).append(r)

    groups = []
    for key, filings in by_key.items():
        if len(filings) < 2:
            continue
        name = filings[0]["name"]
        if key.startswith("NO-HOME:"):
            continue  # no URL to compare — leave for human eyes
        if name in NEVER_MERGE:
            groups.append(
                {"domain": key, "names": name, "verdict": "SKIP (never-merge list)", "filings": filings}
            )
            continue
        groups.append({"domain": key, "names": name, "verdict": "MERGE", "filings": filings})

    # Same name, different homes: possibly the same company filed twice with
    # different URLs, or genuinely different companies (bird.com vs bird.co —
    # human-verified different). Always a human call; never auto-merged.
    by_name: dict[str, set[int]] = {}
    for r in rows:
        by_name.setdefault(r["name"], set()).add(r["id"])
    merged_ids = {f["id"] for g in groups for f in g["filings"]}
    for name, ids in sorted(by_name.items()):
        if len(ids) < 2:
            continue
        ungrouped = ids - merged_ids
        if len(ungrouped) >= 2:
            groups.append(
                {
                    "domain": "same-name",
                    "names": name,
                    "verdict": "MANUAL REVIEW (same name, different homes)",
                    "filings": [r for r in rows if r["id"] in ungrouped],
                }
            )
    return groups


def pick_keeper(filings: list[dict]) -> dict:
    # Longest description wins; ties break to the LOWEST id (the original
    # filing), matching the docstring rule.
    key = lambda f: (len(f.get("description") or ""), -f["id"])
    verified = [f for f in filings if f["verified"] == 1]
    return max(verified or filings, key=key)


def plan_groups(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, website_url, github_url, tagline, description, verified FROM startups ORDER BY name"
    ).fetchall()
    cols = ["id", "name", "website_url", "github_url", "tagline", "description", "verified"]
    return group_filings([dict(zip(cols, r)) for r in rows])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="backup then merge (default: dry run)")
    args = ap.parse_args()

    db_path = Path(__file__).resolve().parents[1] / "data" / "ideasexist.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        groups = plan_groups(conn)
        merge_groups = [g for g in groups if g["verdict"] == "MERGE"]
        skipped = [g for g in groups if g["verdict"] != "MERGE"]

        print(f"duplicate groups by registrable domain: {len(merge_groups)} to merge, {len(skipped)} skipped")
        for g in sorted(merge_groups, key=lambda g: g["names"].lower()):
            keeper = pick_keeper(g["filings"])
            doomed = [f for f in g["filings"] if f["id"] != keeper["id"]]
            urls = [f["website_url"] for f in g["filings"]] + [f["github_url"] for f in g["filings"]]
            print(
                f"  MERGE {g['names']!r} ({g['domain']}): keep id={keeper['id']} "
                f"(verified={keeper['verified']}, desc={len(keeper['description'] or '')}ch), "
                f"delete ids={[f['id'] for f in doomed]}, url-> {best_url(urls)}"
            )
        for g in skipped:
            print(
                f"  SKIP  {g['names']!r} ({g['domain']}): {g['verdict']} — "
                f"ids={[f['id'] for f in g['filings']]}"
            )

        if not args.apply:
            print("\nDry run — nothing changed. Re-run with --apply to merge (backs up first).")
            return 0

        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = db_path.with_name(f"ideasexist.backup-{stamp}.db")
        dest = sqlite3.connect(backup)
        with dest:
            conn.backup(dest)
        dest.close()
        print(f"\nBackup: {backup}")

        for g in merge_groups:
            keeper = pick_keeper(g["filings"])
            doomed = [f["id"] for f in g["filings"] if f["id"] != keeper["id"]]
            urls = [f["website_url"] for f in g["filings"]] + [f["github_url"] for f in g["filings"]]
            url = best_url(urls)
            # Build SET clauses and bindings together — a per-doomed-filing loop
            # used to append "tagline = ?" once per filing while the params
            # builder added a single value, crashing the UPDATE mid-apply with
            # a binding-count error (after earlier groups were already merged).
            updates: list[str] = []
            params: list[object] = []
            if url and not (keeper["website_url"] or keeper["github_url"]):
                updates.append("website_url = ?")
                params.append(url)
            if not keeper["tagline"]:
                donor = next(
                    (f["tagline"] for f in g["filings"] if f["id"] != keeper["id"] and f["tagline"]),
                    None,
                )
                if donor is not None:
                    updates.append("tagline = ?")
                    params.append(donor)
            if not keeper["description"]:
                donor = next(
                    (f["description"] for f in g["filings"] if f["id"] != keeper["id"] and f["description"]),
                    None,
                )
                if donor is not None:
                    updates.append("description = ?")
                    params.append(donor)
            if updates:
                params.append(keeper["id"])
                conn.execute(f"UPDATE startups SET {', '.join(updates)} WHERE id = ?", params)
            conn.executemany("DELETE FROM startups WHERE id = ?", [(i,) for i in doomed])
        conn.commit()
        print(f"Merged {len(merge_groups)} groups; {sum(len(g['filings']) - 1 for g in merge_groups)} rows deleted.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
