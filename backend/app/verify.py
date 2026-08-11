"""Verification pass. Non-destructive: 3 consecutive failures → status='dead'
(never delete). Every check is logged to verify_log.

Runs as a background job on the seeder's serial queue (kind="verify") so it
never overlaps a seed and reports live progress (total/done/ok/skipped/failed
+ a verified/unverified/dead breakdown of checked entries). The GitHub check is
tri-state: a genuine 404 counts as a failure, but a rate-limit (403/429) is a
SKIP — it never increments check_failures, so three rate-limited runs can't
wrongly dead-flip healthy repos.
"""
import time
import uuid

from . import db, github as gh, netguard

UA_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

# Statuses that mean "filed away" — the breakdown buckets them as dead.
_FILED = ("dead", "pivoted")


def check_url_ok(url: str) -> tuple[bool, str, bool]:
    """Tri-state website check: (ok, note, skipped).

    A genuine 404/410 is the ONLY website signal that counts as dead — bot
    walls (401/403), rate limits (429), and transient 5xx/network errors are
    ambiguous (the site exists, the fetcher was refused), so they SKIP and
    never accumulate check_failures. Three bot-walled runs must never
    dead-flip a healthy company (real incident: WHOOP + Capterra filed dead
    by Cloudflare 403s).
    """
    if not url:
        return False, "no website_url", False
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = netguard.safe_get(url, headers=UA_BROWSER, timeout=15)
        status = r.status_code
        if status in (404, 410):
            return False, f"HTTP {status}", False  # genuinely gone — a real strike
        if 200 <= status < 400:
            return True, f"HTTP {status}", False
        return False, f"HTTP {status}", True  # wall / rate limit / transient — skip
    except netguard.BlockedAddressError as exc:
        # SSRF guard refusal (non-public target). Counts as a failure with an
        # honest note — a junk internal URL must not masquerade as alive.
        return False, str(exc)[:80], False
    except Exception as exc:  # noqa: BLE001 — network/parse failure → skip, never strike
        return False, str(exc)[:80], True


def check_github_ok(github_url: str) -> tuple[bool, str, bool]:
    """Tri-state GitHub check: (ok, note, skipped).

    - 404 (ValueError)  → (False, reason, False) — a genuine failure, counts.
    - rate limit 403/429 (RuntimeError) → (False, reason, True) — SKIPPED, never
      counts toward check_failures (three rate-limited runs must not dead-flip
      a healthy repo).
    - success / archived → (True, note, False).
    """
    try:
        repo = gh.fetch_repo(github_url)
        if repo["archived"]:
            return True, "repo archived (flag)", False
        return True, f"repo ok, {repo['stars']}★", False
    except ValueError as exc:  # repo genuinely gone
        return False, str(exc)[:80], False
    except RuntimeError as exc:  # rate limited or API error → skip, never fail
        return False, str(exc)[:80], True
    except Exception as exc:  # noqa: BLE001 — unexpected → treat as skipped too
        return False, str(exc)[:80], True


def start_verification() -> str:
    """Enqueue a verify job on the serial queue. Raises RuntimeError (loud 409
    upstream) if one is already queued or running — two passes in flight is a
    bug, not a feature (they would double-hit the GitHub rate limit)."""
    from . import seeder  # local import — seeder imports verify lazily in _run

    if seeder.has_active_job("verify"):
        raise RuntimeError("A verification pass is already queued or running")
    job = {
        "id": uuid.uuid4().hex[:12],
        "kind": "verify",
        "source": "verify",
        "params": {},
        "status": "queued",
        "queue_position": None,
        "total": 0,
        "done": 0,
        "ok": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
        "ok_urls": [],
        "skipped_urls": [],
        "current": "",
        "created_at": time.time(),
        "started_at": None,
        "finished_at": None,
        "breakdown": {"verified": 0, "unverified": 0, "dead": 0},
        "already_verified": [],
        "suggested": [],
        "failed_list": [],
        "result": None,
    }
    seeder.enqueue_job(job)
    return job["id"]


def get_verify_job(job_id: str) -> dict | None:
    from . import seeder  # local import — keeps module import order simple

    return seeder.get_job(job_id)


def get_active_verify_job() -> dict | None:
    """The queued/running verification job, or None — lets the panel re-attach
    to a pass already in flight instead of starting a second one."""
    from . import seeder  # local import

    for job in seeder.list_jobs():
        if job["kind"] == "verify" and job["status"] in ("queued", "running"):
            return job
    return None


def list_suggested() -> list[dict]:
    """The human-approval queue: entries the automated check considers alive
    (or never checked) that no human has stamped yet. Includes brand-new seeds;
    excludes dead, already-verified, and 1-2 strike failures."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT id, name, website_url, github_url, category, last_checked, created_at "
            "FROM startups "
            "WHERE verified = 0 AND status = 'active' AND check_failures = 0 "
            "ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def approve_suggested(
    ids: list[int] | None = None,
    approve_all: bool = False,
    created_after: str | None = None,
    created_before: str | None = None,
) -> int:
    """Human gate, in bulk: stamp verified=1 + verified_at on the given rows
    (or every suggested row, or every suggested row in a created_at window —
    the batch boundary for "approve this seed run"). The ONLY writers of
    verified=1 are this function and the single-row /verify endpoint —
    automation never stamps."""
    conn = db.connect()
    try:
        base = "verified = 0 AND status = 'active' AND check_failures = 0"
        if created_after or created_before:
            conds, params = [base], []
            if created_after:
                conds.append("created_at >= ?")
                params.append(created_after)
            if created_before:
                conds.append("created_at < ?")
                params.append(created_before)
            cur = conn.execute(
                f"UPDATE startups SET verified = 1, verified_at = datetime('now') "
                f"WHERE {' AND '.join(conds)}",
                params,
            )
        elif approve_all:
            cur = conn.execute(
                f"UPDATE startups SET verified = 1, verified_at = datetime('now') "
                f"WHERE {base}"
            )
        else:
            ids = [int(i) for i in (ids or [])]
            if not ids:
                return 0
            placeholders = ",".join("?" * len(ids))
            cur = conn.execute(
                f"UPDATE startups SET verified = 1, verified_at = datetime('now') "
                f"WHERE id IN ({placeholders})",
                ids,
            )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def run_verify_job(job: dict) -> None:
    """The verification pass, writing progress into the job dict as it walks
    every startup. Runs on the verify worker (parallel with seeds)."""
    from . import seeder  # local import — seeder imports verify lazily in _run

    job["status"] = "running"
    job["started_at"] = time.time()
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM startups").fetchall()
        job["total"] = len(rows)
        dead_flipped: list[str] = []
        for row in rows:
            job["current"] = row["name"]
            # Bucket the entry's CURRENT state (at check time) for the panel
            # breakdown — before the check, so the archive composition shows.
            if row["status"] in _FILED:
                job["breakdown"]["dead"] += 1
            elif row["verified"] == 1:
                job["breakdown"]["verified"] += 1
            else:
                job["breakdown"]["unverified"] += 1

            notes = []
            web_ok, web_note, web_skipped = check_url_ok(row["website_url"])
            notes.append(f"website: {web_note}")
            gh_ok = None
            gh_skipped = False
            if row["github_url"]:
                gh_ok, gh_note, gh_skipped = check_github_ok(row["github_url"])
                notes.append(f"github: {gh_note}")
            # Real failure = website genuinely gone (404/410) OR repo genuinely
            # gone (404). Bot walls, rate limits and transient errors are SKIPs
            # — ambiguous signals never count as a strike.
            web_failed = not web_ok and not web_skipped
            gh_failed = gh_ok is False and not gh_skipped
            failed = web_failed or gh_failed
            inconclusive = not failed and (web_skipped or gh_skipped)

            # Human-stamped rows never accumulate auto-strikes and never
            # auto-flip — the human gate outranks robot checks. They surface
            # in failed_list as re-check items for the curator instead.
            human_owned = row["verified"] == 1

            if failed:
                job["failed"] += 1
                job["errors"].append(f"{row['name']}: {'; '.join(notes)}")
                job["failed_list"].append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "url": row["website_url"] or row["github_url"] or "",
                        "reason": "; ".join(notes),
                    }
                )
                if not human_owned:
                    new_failures = row["check_failures"] + 1
                    status = row["status"]
                    if new_failures >= 3 and status == "active":
                        status = "dead"
                        dead_flipped.append(row["name"])
                else:
                    # Flag for human re-check, never strike: the verified stamp
                    # stays until a human changes it.
                    new_failures = row["check_failures"]
                    status = row["status"]
            elif inconclusive:
                # Machine couldn't confirm — a non-failure pass clears the
                # streak (3 CONSECUTIVE genuine failures flip, a skip resets).
                job["skipped"] += 1
                job["skipped_urls"].append(f"{row['name']} ({'; '.join(notes)})")
                new_failures = 0
                status = row["status"]
            elif human_owned:
                job["already_verified"].append(
                    {"id": row["id"], "name": row["name"], "url": row["website_url"] or row["github_url"] or ""}
                )
                job["ok"] += 1
                new_failures = 0
                status = row["status"]
            else:
                job["suggested"].append(
                    {"id": row["id"], "name": row["name"], "url": row["website_url"] or row["github_url"] or ""}
                )
                job["ok"] += 1
                new_failures = 0
                status = row["status"]
            conn.execute(
                "UPDATE startups SET check_failures = ?, last_checked = datetime('now'), status = ? WHERE id = ?",
                (new_failures, status, row["id"]),
            )
            conn.execute(
                "INSERT INTO verify_log (startup_id, website_ok, github_ok, notes) VALUES (?, ?, ?, ?)",
                (row["id"], 1 if web_ok else 0, (1 if gh_ok else 0) if gh_ok is not None else None,
                 "; ".join(notes)),
            )
            job["done"] += 1
            job["current"] = ""
            # Commit per row — the verify pass runs on its own worker in
            # parallel with seeds; holding one giant write transaction for the
            # whole pass would block any concurrent seed (busy_timeout waits,
            # but a 10-minute lock is a stall). Tiny commits interleave fine.
            conn.commit()
            seeder._persist_job(job)  # live progress survives a restart too
        job["result"] = {
            "checked": job["done"],
            "ok": job["ok"],
            "skipped": job["skipped"],
            "flagged": job["failed"],
            "dead_flipped": dead_flipped,
            "breakdown": dict(job["breakdown"]),
            "already_verified": job["already_verified"],
            "suggested": job["suggested"],
            "failed_list": job["failed_list"],
        }
        job["status"] = "done"
        seeder._persist_job(job)
    except Exception as exc:  # noqa: BLE001 — job-level crash is a loud failure
        job["status"] = "failed"
        job["errors"].append(f"job: {exc}")
        seeder._persist_job(job)
    finally:
        job["finished_at"] = time.time()
        job["current"] = ""
        seeder._persist_job(job)
        conn.close()
