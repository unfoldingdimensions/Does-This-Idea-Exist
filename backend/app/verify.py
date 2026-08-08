"""Weekly verification pass. Non-destructive: 3 consecutive failures → status='dead'
(never delete). Every check is logged to verify_log."""
import httpx

from . import db, github as gh

UA_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def check_url_ok(url: str) -> tuple[bool, str]:
    if not url:
        return False, "no website_url"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = httpx.get(url, headers=UA_BROWSER, follow_redirects=True, timeout=15)
        ok = 200 <= r.status_code < 400
        return ok, f"HTTP {r.status_code}"
    except Exception as exc:  # noqa: BLE001 — report any failure, keep the pass going
        return False, str(exc)[:80]


def check_github_ok(github_url: str) -> tuple[bool, str]:
    try:
        repo = gh.fetch_repo(github_url)
        if repo["archived"]:
            return True, "repo archived (flag)"
        return True, f"repo ok, {repo['stars']}★"
    except ValueError as exc:
        return False, str(exc)[:80]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:80]


def run_verification() -> dict:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM startups").fetchall()
        results = {"checked": 0, "ok": 0, "flagged": 0, "dead_flipped": []}
        for row in rows:
            notes = []
            web_ok, web_note = check_url_ok(row["website_url"])
            notes.append(f"website: {web_note}")
            gh_ok = None
            if row["github_url"]:
                gh_ok, gh_note = check_github_ok(row["github_url"])
                notes.append(f"github: {gh_note}")
            failed = (not web_ok) or (gh_ok is False)
            new_failures = row["check_failures"] + 1 if failed else 0
            status = row["status"]
            if new_failures >= 3 and status == "active":
                status = "dead"
                results["dead_flipped"].append(row["name"])
            conn.execute(
                "UPDATE startups SET check_failures = ?, last_checked = datetime('now'), status = ? WHERE id = ?",
                (new_failures, status, row["id"]),
            )
            conn.execute(
                "INSERT INTO verify_log (startup_id, website_ok, github_ok, notes) VALUES (?, ?, ?, ?)",
                (row["id"], 1 if web_ok else 0, (1 if gh_ok else 0) if gh_ok is not None else None,
                 "; ".join(notes)),
            )
            results["checked"] += 1
            if failed:
                results["flagged"] += 1
            else:
                results["ok"] += 1
        conn.commit()
        return results
    finally:
        conn.close()
