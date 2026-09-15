"""Just-in-time teardown capture (F-22).

Never on seed, never on approval: the trigger is **the first founder request for
a competitor**. Phase 3 wires `/api/compare` to `start_capture()`; this phase
ships and tests the callable and the job, and records the wiring in the ledger.

Serialization: one job per competitor, created under
`seeder.try_enqueue_exclusive(..., key="capture:<id>")`, so two concurrent
requests for the same competitor collapse into ONE capture. While one is in
flight the caller gets an explicit "capture in progress — retry" state — never a
partial teardown assembled from whatever happened to be done.

Freshness: a cached teardown is re-capturable after `CAPTURE_STALE_DAYS` (7),
the same number and the same clock as `VERIFY_AUTO_STALE_DAYS`, because the
product should have ONE staleness rhythm rather than two.

The freshness anchor is **the teardown evidence itself** (the newest
feature/pricing/positioning/negative/review row), with the pricing stamp as a
secondary signal. A capture that could read nothing writes no rows, so it is
retried instead of being mistaken for a cache — an empty teardown is not a
cache entry.

No public job-detail endpoint exists for captures: a job payload carries error
strings and fetched URLs, which is why the admin panel is the only reader.
"""
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from . import config, db, llm, negatives, pages as pages_mod, reviews as reviews_mod
from . import teardown as td

log = logging.getLogger("ideasexist")

JOB_KIND = "capture"
CAPTURE_IN_PROGRESS = "capture in progress — retry"

# Every evidence type a teardown writes. The newest of these is what "we have a
# teardown for this competitor, captured at X" means.
TEARDOWN_EVIDENCE_TYPES = ("feature", "pricing", "positioning", "negative", "review")


def key_for(startup_id: int) -> str:
    return f"capture:{startup_id}"


def parse_ts(value: str | None):
    """Parse the app's `datetime('now')` stamps (UTC) and bare dates."""
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def age_days(value: str | None) -> float | None:
    parsed = parse_ts(value)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0


def last_capture_at(conn: sqlite3.Connection, startup_id: int, row=None) -> str | None:
    """When this competitor's teardown was last captured, or None."""
    marks = ",".join("?" * len(TEARDOWN_EVIDENCE_TYPES))
    found = conn.execute(
        f"SELECT MAX(captured_at) AS m FROM evidence "
        f"WHERE startup_id = ? AND evidence_type IN ({marks})",
        (startup_id, *TEARDOWN_EVIDENCE_TYPES),
    ).fetchone()
    stamps = [found["m"] if found else None]
    if row is not None:
        try:
            stamps.append(row["pricing_captured_at"])
        except (KeyError, IndexError, TypeError):
            pass
    present = [s for s in stamps if s]
    return max(present) if present else None


def needs_capture(conn: sqlite3.Connection, row, *, now: str | None = None) -> bool:
    """True when this competitor has no usable teardown or it has aged out."""
    last = last_capture_at(conn, row["id"], row)
    if not last:
        return True
    age = age_days(last)
    if age is None:
        return True
    return age >= config.CAPTURE_STALE_DAYS


def new_job(startup_id: int) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "kind": JOB_KIND,
        "source": "capture",
        "key": key_for(startup_id),
        "params": {"startup_id": startup_id},
        "status": "queued",
        "queue_position": None,
        "total": 1,
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
        "result": None,
    }


def start_capture(startup_id: int) -> dict:
    """The JIT entry point Phase 3 calls on the first founder request.

    Returns exactly one of:

        cached       a teardown captured inside the freshness window — use it
        queued       a capture job was created; the caller waits or retries
        in_progress  another capture for the SAME competitor is in flight
        not_found    no such competitor
    """
    from . import seeder  # local import — seeder imports capture lazily

    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        if not row:
            return {"state": "not_found", "startup_id": startup_id}
        if not needs_capture(conn, row):
            return {
                "state": "cached",
                "startup_id": startup_id,
                "captured_at": last_capture_at(conn, startup_id, row),
                "message": "teardown served from cache",
            }
    finally:
        conn.close()

    job = new_job(startup_id)
    if not seeder.try_enqueue_exclusive(job, key=job["key"]):
        return {"state": "in_progress", "startup_id": startup_id, "message": CAPTURE_IN_PROGRESS}
    return {"state": "queued", "startup_id": startup_id, "job_id": job["id"],
            "message": "capture queued"}


def capture_teardown(
    startup_id: int,
    *,
    fetcher=None,
    llm_fn=None,
    sources=None,
    timeout: float = 25.0,
) -> dict:
    """The capture itself: page plan -> teardown draft -> negatives -> reviews.

    Stubs are injectable (fetcher / llm_fn / sources) so the exit gate runs this
    whole path with no network at all.
    """
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        if not row:
            return {"state": "not_found", "startup_id": startup_id}
        base = (row["website_url"] or "").strip()
        if not base:
            # A name is not a URL. Guessing one would be the "guessed URL" the
            # negative rule forbids, so this is an explicit state instead.
            return {"state": "no_website", "startup_id": startup_id,
                    "message": "no website_url — nothing to read"}

        pages = pages_mod.fetch_pages(base, fetcher=fetcher, timeout=timeout)
        page_states = {
            role: {"url": rec["url"], "state": rec["state"], "reason": rec["reason"]}
            for role, rec in pages.items()
        }
        if not pages_mod.readable(pages):
            # Nothing readable: record nothing, invent nothing, and do NOT stamp a
            # freshness date — this is not a cache entry.
            return {"state": "unreadable", "startup_id": startup_id, "pages": page_states,
                    "message": "no page could be read — teardown unknown"}

        raw: dict = {}
        try:
            call = llm_fn or llm.llm_teardown
            raw = call(llm.teardown_brief(pages_mod.brief(pages), pages_mod.urls(pages))) or {}
        except Exception as exc:  # noqa: BLE001 — a failed call means unknown, never a retry
            log.warning("capture %s: teardown LLM failed (%s) — fields stay unknown", startup_id, exc)

        teardown = td.clean_teardown(raw)
        # Deterministic probes first, the LLM's negatives second and validated
        # against the pages we actually read (F-09).
        teardown["negatives"] = negatives.capture(pages, teardown, row, raw.get("negatives"))

        summary = td.write_teardown(conn, startup_id, teardown, pages, existing=row)

        reviews = reviews_mod.capture(row, sources=sources, fetcher=fetcher, timeout=min(timeout, 20.0))
        summary["reviews"] = reviews_mod.store(conn, startup_id, reviews)
        summary["reviews_skipped"] = len(reviews.get("skipped") or [])
        summary["asks"] = sum(len(r.get("asks") or []) for r in reviews.get("reviews") or [])
        summary["state"] = "captured"
        summary["startup_id"] = startup_id
        summary["pages"] = page_states
        return summary
    finally:
        conn.close()


def run_capture_job(job: dict) -> None:
    """Run one capture job on the seeder's capture worker."""
    from . import seeder  # local import — keeps the import graph one-directional

    job["status"] = "running"
    job["started_at"] = time.time()
    try:
        startup_id = int((job.get("params") or {}).get("startup_id") or 0)
        result = capture_teardown(startup_id)
        job["result"] = result
        job["done"] = 1
        if result.get("state") == "captured":
            job["ok"] = 1
            job["ok_urls"].append(f"startup:{startup_id}")
        elif result.get("state") == "unreadable":
            job["skipped"] = 1
            job["skipped_urls"].append(f"startup:{startup_id}")
        else:
            job["failed"] = 1
            job["errors"].append(f"startup:{startup_id}: {result.get('state')}")
        job["status"] = "done"
    except Exception as exc:  # noqa: BLE001 — a job-level crash is a loud failure
        job["status"] = "failed"
        job["errors"].append(f"job: {exc}")
        log.exception("capture job %s crashed", job["id"])
    finally:
        job["finished_at"] = time.time()
        job["current"] = ""
        seeder._persist_job(job)


def get_capture_job(job_id: str) -> dict | None:
    from . import seeder  # local import

    return seeder.get_job(job_id)


def active_capture_jobs() -> list[dict]:
    """Queued/running captures — admin visibility only, never a public endpoint."""
    from . import seeder  # local import

    return [
        job for job in seeder.list_jobs()
        if job["kind"] == JOB_KIND and job["status"] in ("queued", "running")
    ]
