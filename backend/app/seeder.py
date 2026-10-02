"""Admin seeder: kind-scoped job queues that batch-ingest startups from multiple
sources and run verification passes.

Two workers, one per job kind: seed jobs drain FIFO on the seed worker (two
sources never seed in parallel — project contamination guard) while verify
jobs drain on the verify worker — so a seed and a verification can run at the
same time, but never two seeds or two verifies. Every job is visible to the
admin panel while queued, running, or finished. Fail-loud policy: every failure
is logged AND recorded in job["errors"] — nothing is swallowed.
"""
import json
import logging
import sqlite3
import threading
import time
import uuid

import httpx

from . import config, db, enrich, meter

log = logging.getLogger("ideasexist")

JOBS: dict[str, dict] = {}
# One FIFO queue + condition per kind — the workers are the serialization points.
# "capture" is the just-in-time teardown capture (F-22): its own kind so a
# founder's first request never waits behind a 500-candidate seed run and a seed
# never waits behind a capture, while captures of one competitor still collapse
# into a single job (see try_enqueue_exclusive's `key`).
QUEUES: dict[str, list[dict]] = {"seed": [], "verify": [], "capture": []}
CONDS: dict[str, threading.Condition] = {
    "seed": threading.Condition(),
    "verify": threading.Condition(),
    "capture": threading.Condition(),
}
_LOCK = threading.Lock()

# The job vocabulary, in one place: queued | running | paused | done | failed.
#
# `paused` is the spend brake's state (§7.4): the batch stopped at a per-candidate
# boundary with every row it already wrote left in place, and it stays there until
# an operator resumes or cancels it (tasks 6-7).
#
# Two distinctions this tuple exists to keep straight:
#   * IN_FLIGHT — the kind's worker slot is genuinely occupied.
#   * a PAUSED job is NOT in flight and NOT finished. It is deliberately not
#     treated as in-flight by the exclusivity guards, because blocking a path that
#     has no release valve is a deadlock: a paused capture would refuse every
#     later request for that competitor with "capture in progress" while nothing
#     progressed. Resume/Cancel (task 6) are the release valve; until they exist,
#     nothing may depend on them.
IN_FLIGHT = ("queued", "running")
PAUSED = "paused"
CANCELLED = "cancelled"
FINISHED = ("done", "failed", "cancelled")


class JobCancelled(RuntimeError):
    """The operator cancelled this job.

    Raised at a candidate boundary, so the loop stops where it stands and every
    row already written stays. Deliberately NOT a JobFailed: the panel and the
    history must be able to tell "I stopped this" from "this broke".
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__("cancelled by the operator")


# Cancel requests for jobs that are RUNNING. A flag, not a status change, because
# the worker owns the job's state while it runs — the request only tells it to
# stop at the next boundary (between two candidates, never mid-write).
#
# Not persisted, and it does not need to be: a restart kills every in-flight job
# anyway (recover_interrupted_jobs marks it failed/interrupted), so there is no
# running job left for a stale flag to cancel. What survives a restart is the
# OUTCOME — a cancelled job's status and its kept rows, written to the jobs table.
_CANCELS: set[str] = set()


def cancel_requested(job_id: str) -> bool:
    """Has this job been asked to stop? Checked at each candidate boundary."""
    with _LOCK:
        return job_id in _CANCELS


def _db_status(job_id: str) -> str | None:
    """The persisted status of a job that is not in memory (history)."""
    conn = db.connect()
    try:
        row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()
    return row["status"] if row else None


def _finish_cancelled(job: dict) -> None:
    """Mark a job cancelled and persist it. Keeps everything already written."""
    job["status"] = CANCELLED
    job["result"] = {
        **(job.get("result") or {}),
        "stop_reason": "cancelled",
        "cancelled_at": time.time(),
    }
    job["errors"].append("cancelled by the operator")
    job["finished_at"] = time.time()
    with _LOCK:
        _CANCELS.discard(job["id"])
    _persist_job(job)
    log.warning("job %s cancelled by the operator after %s ok / %s done",
                job["id"], job.get("ok"), job.get("done"))


def request_cancel(job_id: str) -> dict:
    """Stop a job. Returns a state the API can translate into a response.

    Three routes, because the three cases are genuinely different:
      * queued  → pulled out of the queue and cancelled NOW: the worker never
                  starts it, so there is nothing to interrupt.
      * paused  → cancelled NOW; it was already holding still.
      * running → a flag the worker reads at the next candidate boundary. Rows
                  already written stay; the response says it is in flight.
    A finished job (done/failed/cancelled) is not an error to cancel — there is
    simply nothing to stop, and the caller learns which it was.
    """
    with _LOCK:
        job = JOBS.get(job_id)
    if job is None:
        persisted = _db_status(job_id)
        if persisted is None:
            return {"state": "not_found", "job_id": job_id}
        return {"state": "already_finished", "job_id": job_id, "status": persisted}

    status = job["status"]
    if status == CANCELLED:
        return {"state": "already_cancelled", "job_id": job_id, "status": status}
    if status in FINISHED:
        return {"state": "already_finished", "job_id": job_id, "status": status}
    if status == "queued":
        with _LOCK:
            try:
                QUEUES[job["kind"]].remove(job)
            except ValueError:
                pass  # the worker just took it; the flag below covers that race
            _CANCELS.add(job_id)
        _finish_cancelled(job)
        return {"state": "cancelled", "job_id": job_id, "status": CANCELLED,
                "message": "removed from the queue before it started"}
    if status == PAUSED:
        _finish_cancelled(job)
        return {"state": "cancelled", "job_id": job_id, "status": CANCELLED,
                "message": "the parked batch will not be resumed"}

    # running (or anything else still in flight): ask the worker, do not seize
    # its state from another thread.
    with _LOCK:
        _CANCELS.add(job_id)
    return {"state": "cancel_requested", "job_id": job_id, "status": status,
            "message": "the worker stops at the next candidate boundary; rows "
                       "already written are kept"}


def request_resume(job_id: str, budget_usd=None) -> dict:
    """Re-enqueue a PARKED job's remaining work.

    Already-handled candidates are skipped by the loop, so a resume never re-pays
    for a row that is already filed — `ok_urls` and `skipped_urls` are persisted
    on the job, and they are the skip list.

    `budget_usd` optionally replaces this job's own cap, because the most common
    reason to resume is "the budget was too small and I am raising it" — without
    that, a resume of a job parked on its cap would park again immediately.
    """
    with _LOCK:
        job = JOBS.get(job_id)
    if job is None:
        persisted = _db_status(job_id)
        if persisted is None:
            return {"state": "not_found", "job_id": job_id}
        return {"state": "not_resumable", "job_id": job_id, "status": persisted,
                "message": f"this job is {persisted} and is not in memory; "
                           f"only a parked job can be resumed"}
    status = job["status"]
    if status == CANCELLED:
        return {"state": "cancelled", "job_id": job_id, "status": status,
                "message": "this job was cancelled on purpose; start a new seed of "
                           "the same source — URLs already filed are skipped and "
                           "never re-billed"}
    if status != PAUSED:
        return {"state": "not_resumable", "job_id": job_id, "status": status,
                "message": f"only a parked job can be resumed (this one is {status})"}

    if budget_usd is not None:
        job["params"]["budget_usd"] = float(budget_usd)
    job["status"] = "queued"
    job["finished_at"] = None
    job["result"] = {
        **(job.get("result") or {}),
        "resumed_at": time.time(),
        "resume_count": int((job.get("result") or {}).get("resume_count", 0)) + 1,
    }
    with _LOCK:
        JOBS.setdefault(job["id"], job)
        QUEUES[job["kind"]].append(job)
    with CONDS[job["kind"]]:
        CONDS[job["kind"]].notify()
    _persist_job(job)
    log.info("job %s resumed: %s already filed (skipped, never re-billed), budget %s",
             job["id"], len(job.get("ok_urls") or []) + len(job.get("skipped_urls") or []),
             job["params"].get("budget_usd"))
    return {"state": "queued", "job_id": job_id, "status": "queued",
            "already_handled": len(job.get("ok_urls") or []) + len(job.get("skipped_urls") or []),
            "budget_usd": job["params"].get("budget_usd"),
            "message": "re-queued; candidates already handled are skipped"}

CAP_MIN, CAP_MAX = 1, 500
THROTTLE_S = 1.0  # GitHub unauth: 60 repo/hr, 10 search/min
UA = {"User-Agent": "IdeaExists/0.1 (admin seeder)"}


def start_job(source: str, params: dict) -> str:
    """Validate and enqueue a seed job. Raises ValueError (loud 400 upstream) on bad input."""
    source = (source or "").strip()
    if source not in SOURCES:
        raise ValueError(f"Unknown seed source: {source!r}")
    cap = _parse_cap(params.get("cap"))
    job = {
        "id": uuid.uuid4().hex[:12],
        "kind": "seed",
        "source": source,
        "params": {**params, "cap": cap},
        "status": "queued",
        "queue_position": None,  # filled by _with_position
        "total": 0,
        "done": 0,
        "ok": 0,
        "skipped": 0,  # "all exist" — already filed, upsert-refreshed, not LLM'd
        "failed": 0,
        "errors": [],  # "candidate: reason" — loud, never swallowed
        "ok_urls": [],
        "skipped_urls": [],
        "current": "",
        "created_at": time.time(),
        "started_at": None,
        "finished_at": None,
    }
    enqueue_job(job)
    return job["id"]


def enqueue_job(job: dict) -> None:
    """Append a job to its kind's queue and wake that worker. Two jobs of the
    same kind never run in parallel; different kinds (seed ∥ verify) do."""
    kind = job["kind"]
    if kind not in QUEUES:
        raise ValueError(f"Unknown job kind: {kind!r}")
    with _LOCK:
        JOBS[job["id"]] = job
        QUEUES[kind].append(job)
    with CONDS[kind]:
        CONDS[kind].notify()
    _persist_job(job)
    log.info("job %s queued (kind=%s, source=%s)", job["id"], kind, job["source"])


def try_enqueue_exclusive(job: dict, key: str | None = None) -> bool:
    """Enqueue `job` only if no conflicting job is queued/running.

    Scope is the job's KIND by default — one verify pass at a time, one seed at a
    time. Pass `key` to scope it further: the JIT teardown capture (F-22) is keyed
    per competitor, so two concurrent requests for the SAME competitor collapse
    into one capture while captures of different competitors still queue.

    The active-check and the enqueue must share ONE critical section — a
    caller doing has_active_job() then enqueue_job() races a concurrent twin
    past the check and queues a double pass (the exact thing the guard
    exists to prevent). Returns False when a conflicting job is active."""
    kind = job["kind"]
    if kind not in QUEUES:
        raise ValueError(f"Unknown job kind: {kind!r}")
    scope = key if key is not None else job.get("key")
    with _LOCK:
        if any(
            j["kind"] == kind
            and (scope is None or j.get("key") == scope)
            and j["status"] in ("queued", "running")
            for j in JOBS.values()
        ):
            return False
        job.setdefault("key", scope)
        JOBS[job["id"]] = job
        QUEUES[kind].append(job)
    with CONDS[kind]:
        CONDS[kind].notify()
    _persist_job(job)
    log.info("job %s queued (kind=%s, source=%s)", job["id"], kind, job["source"])
    return True


def _parse_cap(raw) -> int:
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"cap must be an integer, got {raw!r}") from None
    if not CAP_MIN <= cap <= CAP_MAX:
        raise ValueError(f"cap must be between {CAP_MIN} and {CAP_MAX}, got {cap}")
    return cap


def _job_row(job: dict) -> tuple:
    """Flatten a job dict into the `jobs` table row (JSON for list fields)."""
    return (
        job["id"],
        job["kind"],
        job["source"],
        json.dumps(job.get("params", {}), default=str),
        job["status"],
        job.get("total", 0),
        job.get("done", 0),
        job.get("ok", 0),
        job.get("skipped", 0),
        job.get("failed", 0),
        json.dumps(job.get("errors", [])),
        json.dumps(job.get("ok_urls", [])),
        json.dumps(job.get("skipped_urls", [])),
        job.get("current", ""),
        job.get("created_at"),
        job.get("started_at"),
        job.get("finished_at"),
        json.dumps(job.get("breakdown", {})),
        json.dumps(job.get("result")),
    )


_JOB_COLUMNS = (
    "id, kind, source, params_json, status, total, done, ok, skipped, failed, "
    "errors_json, ok_urls_json, skipped_urls_json, current, created_at, "
    "started_at, finished_at, breakdown_json, result_json"
)


def _persist_job(job: dict) -> None:
    """Write the job's current state to the jobs table (upsert). Persistence
    means the admin panel's summaries survive backend restarts — a job is never
    silently lost."""
    conn = db.connect()
    try:
        conn.execute(
            f"INSERT INTO jobs ({_JOB_COLUMNS}) VALUES ({','.join('?' * 19)}) "
            "ON CONFLICT(id) DO UPDATE SET "
            "status=excluded.status, total=excluded.total, done=excluded.done, "
            "ok=excluded.ok, skipped=excluded.skipped, failed=excluded.failed, "
            "errors_json=excluded.errors_json, ok_urls_json=excluded.ok_urls_json, "
            "skipped_urls_json=excluded.skipped_urls_json, current=excluded.current, "
            "started_at=excluded.started_at, finished_at=excluded.finished_at, "
            "breakdown_json=excluded.breakdown_json, result_json=excluded.result_json",
            _job_row(job),
        )
        conn.commit()
    finally:
        conn.close()


def _load_db_job(row: sqlite3.Row) -> dict:
    """Rebuild a job dict from a jobs-table row."""
    return {
        "id": row["id"],
        "kind": row["kind"],
        "source": row["source"],
        "params": json.loads(row["params_json"] or "{}"),
        "status": row["status"],
        "queue_position": None,
        "total": row["total"],
        "done": row["done"],
        "ok": row["ok"],
        "skipped": row["skipped"],
        "failed": row["failed"],
        "errors": json.loads(row["errors_json"] or "[]"),
        "ok_urls": json.loads(row["ok_urls_json"] or "[]"),
        "skipped_urls": json.loads(row["skipped_urls_json"] or "[]"),
        "current": row["current"] or "",
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "breakdown": json.loads(row["breakdown_json"] or "{}"),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }


def recover_interrupted_jobs() -> int:
    """Startup recovery: mark jobs left queued/running (killed by a restart)
    as failed with an honest reason. Returns how many were recovered.

    PAUSED jobs are deliberately NOT touched: a parked batch is waiting on an
    operator, not on a crash. Flipping it to failed here would throw away the one
    state that says "this needs a decision" — and it would erase the resume point
    (the rows it already wrote and the spend it already recorded).
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE jobs SET status = 'failed', "
            "errors_json = ?, finished_at = ? "
            "WHERE status IN ('queued', 'running')",
            (
                json.dumps(["interrupted by server restart"]),
                time.time(),
            ),
        )
        conn.commit()
        n = cur.rowcount
    finally:
        conn.close()
    if n:
        log.warning("recovered %s interrupted job(s) → failed", n)
    return n


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        job = JOBS.get(job_id)
        if job:
            return _with_position(job)
    # Not in memory (post-restart history) — read from the jobs table.
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()
    return _load_db_job(row) if row else None


def has_active_job(kind: str) -> bool:
    """True when a job of this kind is queued or running (kind-scoped guard).

    A PAUSED job does not count: it occupies no worker, and treating it as active
    would let a parked batch veto every later job of its kind while nothing
    progressed — including the ones that would run perfectly well. `has_parked_job`
    is the predicate for "this kind needs an operator", and it is what the panel
    asks (§7.4 task 7).
    """
    with _LOCK:
        return any(
            j["kind"] == kind and j["status"] in IN_FLIGHT
            for j in JOBS.values()
        )


def has_parked_job(kind: str | None = None) -> list[dict]:
    """Every job sitting in `paused`, optionally filtered by kind.

    These are the jobs waiting on a human: the batch kept what it wrote and
    stopped at a candidate boundary when it reached its budget.
    """
    with _LOCK:
        return [
            dict(j) for j in JOBS.values()
            if j["status"] == PAUSED and (kind is None or j["kind"] == kind)
        ]


def list_jobs() -> list[dict]:
    """All jobs for the panel: live in-memory jobs (active first, then finished)
    merged with persisted history from the jobs table (survives restarts).
    Each carries its live queue position.

    A PAUSED job belongs to the active group — it has not finished, and filing it
    under "finished" would hide the one thing that needs an operator. Its
    queue_position is None (it is in no queue).
    """
    with _LOCK:
        jobs = list(JOBS.values())
    # Fill in history not currently in memory (e.g. after a backend restart).
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM jobs").fetchall()
    finally:
        conn.close()
    known = {j["id"] for j in jobs}
    jobs += [_load_db_job(r) for r in rows if r["id"] not in known]
    moving = (*IN_FLIGHT, PAUSED)
    active = [j for j in jobs if j["status"] in moving]
    rank = {"running": 0, "queued": 1, "paused": 2}
    active.sort(key=lambda j: rank.get(j["status"], 3))
    finished = [j for j in jobs if j["status"] not in moving]
    finished.sort(key=lambda j: j.get("finished_at") or j["created_at"] or 0, reverse=True)
    return [_with_position(j) for j in active + finished]


def _with_position(job: dict) -> dict:
    view = dict(job)
    try:
        view["queue_position"] = QUEUES[job["kind"]].index(job) + 1
    except ValueError:
        view["queue_position"] = None  # running or finished
    return view


def _worker(kind: str) -> None:
    """Kind-scoped worker: pops the next job of its kind and runs it. This is
    the serialization point — no two jobs of the SAME kind ever run
    concurrently (seed ∥ verify run on different workers on purpose)."""
    q = QUEUES[kind]
    cond = CONDS[kind]
    while True:
        with cond:
            while not q:
                cond.wait()
            job = q.pop(0)
        try:
            _run(job)
        finally:
            # One place to drop a cancel flag, for every job kind: the worker
            # thread is the only thing that knows the job is no longer running,
            # and a stale id in the set would cancel nothing and leak.
            with _LOCK:
                _CANCELS.discard(job["id"])


def _run(job: dict) -> None:
    if job["kind"] == "verify":
        from . import verify  # local import — verify imports seeder at module level

        verify.run_verify_job(job)
        return
    if job["kind"] == "capture":
        from . import capture  # local import — capture imports seeder at module level

        capture.run_capture_job(job)
        return
    job["status"] = "running"
    job["started_at"] = time.time()
    purpose = f"seed:{job['source']}"
    try:
        producer = SOURCES[job["source"]]
        cap = job["params"]["cap"]
        # A RESUMED job never re-pays for what it already handled: the URLs it
        # filed (or found already filed) are its skip list, and both lists are
        # persisted on the job, so this survives the restart that parked it.
        already_handled = set(job.get("ok_urls") or []) | set(job.get("skipped_urls") or [])
        resumed_skipped = 0
        # One attribution for the whole batch: every call this job makes is
        # stamped with the job id, which is what makes a per-job $ figure and
        # the budget brake (§7.4 tasks 4-6) possible. enrich stamps its own
        # `purpose` inside this block — nested contexts merge. A job may carry its
        # own `budget_usd`, which the brake prefers over the configured cap.
        with meter.attributing(job_id=job["id"], purpose=purpose,
                               budget_usd=job["params"].get("budget_usd")):
            for i, candidate in enumerate(producer(job["params"])):
                if i >= cap:
                    break
                # The cancel boundary (§7.4 task 6): between two candidates, never
                # mid-write, so a cancelled batch keeps every row it wrote.
                if cancel_requested(job["id"]):
                    raise JobCancelled(job["id"])
                if str(candidate) in already_handled:
                    resumed_skipped += 1
                    continue
                job["total"] = min(i + 1, cap)
                job["current"] = str(candidate)
                try:
                    outcome = _ingest(candidate, job["params"])
                    if outcome == "existing":
                        job["skipped"] += 1
                        job["skipped_urls"].append(str(candidate))
                        log.info("seed skip (%s): %s — already filed", job["id"], candidate)
                    else:
                        job["ok"] += 1
                        job["ok_urls"].append(str(candidate))
                        log.info("seed ok   (%s): %s", job["id"], candidate)
                except (meter.BudgetExceeded, JobCancelled):
                    # Neither the brake nor a cancel is a CANDIDATE failure:
                    # counting them here would burn the remaining candidates one
                    # refusal at a time and report them all as failures. They go
                    # up to the job handler, which stops the batch with the reason.
                    raise
                except Exception as exc:  # noqa: BLE001 — per-entry failure is data, not a crash
                    job["failed"] += 1
                    job["errors"].append(f"{candidate}: {exc}")
                    log.error("seed FAIL (%s): %s — %s", job["id"], candidate, exc)
                job["done"] += 1
                job["current"] = ""
                _persist_job(job)
        if resumed_skipped:
            job["result"] = {**(job.get("result") or {}),
                             "resumed_skipped": resumed_skipped}
        job["status"] = "done"
        _persist_job(job)
        log.info(
            "seed job %s done: %s ok, %s skipped, %s failed%s",
            job["id"], job["ok"], job["skipped"], job["failed"],
            f" ({resumed_skipped} already handled before the resume)" if resumed_skipped else "",
        )
    except JobCancelled:
        # §7.4 task 6: the operator stopped it. Everything written stays; the
        # status says a human ended this, not that it broke.
        job["status"] = CANCELLED
        job["result"] = {
            **(job.get("result") or {}),
            "stop_reason": "cancelled",
            "cancelled_at": time.time(),
        }
        job["errors"].append("cancelled by the operator")
        log.warning("seed job %s cancelled at a candidate boundary (%s ok, %s done kept)",
                    job["id"], job["ok"], job["done"])
    except meter.BudgetExceeded as exc:
        # §7.4 task 5: the batch PARKS here — at the candidate boundary it just
        # finished, with every row already written left in place. Nothing rolls
        # back, and the job is not "failed": it is waiting on an operator who can
        # resume or cancel it. The figures ride on `result` (the jobs table's
        # result_json), because that is the only column that can carry them.
        job["status"] = PAUSED
        job["result"] = {
            **(job.get("result") or {}),
            "stop_reason": exc.kind,  # "budget" (cap reached) or "metering" (blind brake)
            "spend_usd": exc.spend_usd,
            "cap_usd": exc.cap_usd,
            "rate_version": exc.rate_version,
            "cost_complete": exc.cost_complete,
            "paused_at": time.time(),
        }
        job["errors"].append(f"{exc.kind}: {exc}")
        log.warning("seed job %s parked at the spend brake: %s", job["id"], exc)
    except Exception as exc:  # noqa: BLE001 — job-level crash is a loud failure
        job["status"] = "failed"
        job["errors"].append(f"job: {exc}")
        _persist_job(job)
        log.exception("seed job %s crashed", job["id"])
    finally:
        # The flag dies with the job: a stale id in the set would cancel nothing
        # (the job is terminal) and would leak memory.
        with _LOCK:
            _CANCELS.discard(job["id"])
        # Only a FINISHED job gets a finished_at. A parked one has not finished,
        # and stamping it would tell the panel to file it under "history".
        job["finished_at"] = time.time() if job["status"] in FINISHED else None
        _persist_job(job)


def _ingest(candidate, params: dict) -> str:
    """Route a candidate (URL string or (url, name_hint) tuple) through the seed
    pipeline. Returns "new" when a row was created, "existing" when the entry
    was already filed (upsert refresh, LLM skipped), or raises on failure."""
    name_hint = None
    if isinstance(candidate, tuple):
        candidate, name_hint = candidate
    url = str(candidate).strip()
    reuse = bool(params.get("reuse_profile", True))
    if "github.com/" in url:
        row = enrich.seed_from_github(url, reuse_profile=reuse)
    else:
        row = enrich.seed_from_website(url, name_hint=name_hint, reuse_profile=reuse)
    return "existing" if row.get("_inserted") is False else "new"


def _gh_search(params: dict):
    """GitHub Search API — hottest repos matching the query, sorted by stars."""
    query = (params.get("query") or "stars:>10000").strip()
    try:
        per_page = min(max(int(params.get("per_page", 20)), 1), 20)
    except (TypeError, ValueError):
        per_page = 20
    headers = dict(UA)
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    page = 1
    while True:
        r = httpx.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page, "page": page},
            headers=headers,
            timeout=30,
        )
        if r.status_code == 403:
            raise RuntimeError(f"GitHub search rate limited (HTTP 403) — add GITHUB_TOKEN for big batches: {r.text[:120]}")
        if r.status_code != 200:
            raise RuntimeError(f"GitHub search HTTP {r.status_code}: {r.text[:120]}")
        items = r.json().get("items", [])
        if not items:
            return
        for item in items:
            yield f"https://github.com/{item['full_name']}"  # full URLs — _ingest routes on "github.com/"
            time.sleep(THROTTLE_S)
        page += 1


def _url_list(params: dict):
    """One candidate per non-empty line of the pasted URL list."""
    for line in (params.get("urls") or "").splitlines():
        url = line.strip()
        if url:
            yield url


def _famous(params: dict):
    """Bundled famous-startup list (data/seed_famous.json) → (url, name_hint)."""
    path = config.BASE_DIR / "data" / "seed_famous.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data:
        url = entry.get("github_url") or entry.get("website_url")
        if not url:
            log.warning("seed_famous entry missing url: %r", entry)
            continue
        yield url, entry.get("name")


def _design_library(params: dict):
    """Bundled design-reference library (data/seed_design_library.json) → (url, name_hint).

    201 curated product/startup sites captured by the design-scope library (Ui Design MCP):
    real homepages with design fingerprints. Website-only — every entry is a product site,
    so _ingest routes each to the website pipeline (no github.com/ entries by construction).
    """
    path = config.BASE_DIR / "data" / "seed_design_library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data:
        url = (entry.get("website_url") or "").strip()
        if not url:
            log.warning("seed_design_library entry missing website_url: %r", entry)
            continue
        yield url, entry.get("name")


SOURCES = {
    "github_search": _gh_search,
    "url_list": _url_list,
    "famous": _famous,
    "design_library": _design_library,
}

# Start one worker per kind at import — seeds, verifies and captures drain
# concurrently from here on (each kind serial within itself).
threading.Thread(target=_worker, args=("seed",), name="seed-worker", daemon=True).start()
threading.Thread(target=_worker, args=("verify",), name="verify-worker", daemon=True).start()
threading.Thread(target=_worker, args=("capture",), name="capture-worker", daemon=True).start()
