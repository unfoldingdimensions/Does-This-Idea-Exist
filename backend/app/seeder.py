"""Admin seeder: kind-scoped job queues that batch-ingest startups from multiple
sources and run verification passes.

Two workers, one per job kind: seed jobs drain FIFO on the seed worker (two
sources never seed in parallel — project contamination guard) while verify
jobs drain on the verify worker — so a seed and a verification can run at the
same time, but never two seeds or two verifies. Every job is visible to the
admin panel while queued, running, or finished. Fail-loud policy: every failure
is logged AND recorded in job["errors"] — nothing is swallowed.
"""
import html as html_lib
import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import httpx

from . import config, db, enrich
from .website import UA_BROWSER
from urllib.parse import urlparse

log = logging.getLogger("ideasexist")

JOBS: dict[str, dict] = {}
# One FIFO queue + condition per kind — the workers are the serialization points.
QUEUES: dict[str, list[dict]] = {"seed": [], "verify": []}
CONDS: dict[str, threading.Condition] = {
    "seed": threading.Condition(),
    "verify": threading.Condition(),
}
_LOCK = threading.Lock()

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
    as failed with an honest reason. Returns how many were recovered."""
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
    """True when a job of this kind is queued or running (kind-scoped guard)."""
    with _LOCK:
        return any(
            j["kind"] == kind and j["status"] in ("queued", "running")
            for j in JOBS.values()
        )


def list_jobs() -> list[dict]:
    """All jobs for the panel: live in-memory jobs (active first, then finished)
    merged with persisted history from the jobs table (survives restarts).
    Each carries its live queue position."""
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
    active = [j for j in jobs if j["status"] in ("queued", "running")]
    active.sort(key=lambda j: 0 if j["status"] == "running" else 1)
    finished = [j for j in jobs if j["status"] not in ("queued", "running")]
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
        _run(job)


def _run(job: dict) -> None:
    if job["kind"] == "verify":
        from . import verify  # local import — verify imports seeder at module level

        verify.run_verify_job(job)
        return
    job["status"] = "running"
    job["started_at"] = time.time()
    try:
        producer = SOURCES[job["source"]]
        cap = job["params"]["cap"]
        for i, candidate in enumerate(producer(job["params"])):
            if i >= cap:
                break
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
            except Exception as exc:  # noqa: BLE001 — per-entry failure is data, not a crash
                job["failed"] += 1
                job["errors"].append(f"{candidate}: {exc}")
                log.error("seed FAIL (%s): %s — %s", job["id"], candidate, exc)
            job["done"] += 1
            job["current"] = ""
            _persist_job(job)
        job["status"] = "done"
        _persist_job(job)
        log.info(
            "seed job %s done: %s ok, %s skipped, %s failed",
            job["id"], job["ok"], job["skipped"], job["failed"],
        )
    except Exception as exc:  # noqa: BLE001 — job-level crash is a loud failure
        job["status"] = "failed"
        job["errors"].append(f"job: {exc}")
        _persist_job(job)
        log.exception("seed job %s crashed", job["id"])
    finally:
        job["finished_at"] = time.time()
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


_TOPSTARTUPS_RE = re.compile(
    r'<a[^>]*href="([^"]+)"[^>]*id="startup-website-link"[^>]*>(.*?)</a>', re.S
)


def _strip_tags(text: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _topstartups(params: dict):
    """topstartups.io — server-rendered HTML list, ?page=N pagination (~20/page, 1,259 total).

    Yields (website_url, name_hint) tuples; requires the browser UA (blocks bare bots).
    UTM params are stripped from each company-site link. The directory's own domain and
    within-run URL repeats are skipped (scraper artifact guard — the source site is not
    a startup, and one company should seed exactly once per run).
    """
    page = 1
    seen: set[str] = set()
    while True:
        r = httpx.get(
            f"https://topstartups.io/?page={page}",
            headers=UA_BROWSER,
            timeout=30,
            follow_redirects=True,
        )
        if r.status_code != 200:
            raise RuntimeError(f"topstartups HTTP {r.status_code}: {r.text[:120]}")
        found = 0
        for href, raw_name in _TOPSTARTUPS_RE.findall(r.text):
            name = _strip_tags(raw_name)
            if not name:
                continue
            url = href.split("?")[0].strip().rstrip("/")  # strip ?utm_source=... + trailing slash
            if url in seen:
                continue
            host = (urlparse(url).hostname or "").lower().rstrip(".")
            if host in ("topstartups.io", "www.topstartups.io"):
                continue
            seen.add(url)
            yield url, name
            found += 1
            time.sleep(THROTTLE_S)
        if found == 0:
            return  # list exhausted
        page += 1


SOURCES = {
    "github_search": _gh_search,
    "url_list": _url_list,
    "famous": _famous,
    "topstartups": _topstartups,
    "design_library": _design_library,
}

# Start one worker per kind at import — seeds and verifies drain concurrently
# from here on (each kind serial within itself).
threading.Thread(target=_worker, args=("seed",), name="seed-worker", daemon=True).start()
threading.Thread(target=_worker, args=("verify",), name="verify-worker", daemon=True).start()
