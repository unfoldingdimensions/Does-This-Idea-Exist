"""Admin seeder: background jobs that batch-ingest startups from multiple sources.

Fail-loud policy: every failure is logged AND recorded in job["errors"] — nothing
is swallowed. A "done" job with failed > 0 reads as done-with-failures.
"""
import json
import logging
import threading
import time
import uuid
from pathlib import Path

import httpx

from . import config, enrich

log = logging.getLogger("ideasexist")

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()

CAP_MIN, CAP_MAX = 1, 500
THROTTLE_S = 1.0  # GitHub unauth: 60 repo/hr, 10 search/min
UA = {"User-Agent": "IdeaExists/0.1 (admin seeder)"}


def start_job(source: str, params: dict) -> str:
    """Validate and launch a seed job. Raises ValueError (loud 400 upstream) on bad input."""
    source = (source or "").strip()
    if source not in SOURCES:
        raise ValueError(f"Unknown seed source: {source!r}")
    cap = _parse_cap(params.get("cap"))
    job = {
        "id": uuid.uuid4().hex[:12],
        "source": source,
        "params": {**params, "cap": cap},
        "status": "queued",
        "total": 0,
        "done": 0,
        "ok": 0,
        "failed": 0,
        "errors": [],
        "current": "",
        "started_at": None,
        "finished_at": None,
    }
    with _LOCK:
        JOBS[job["id"]] = job
    log.info("seed job %s queued (source=%s, cap=%s)", job["id"], source, cap)
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return job["id"]


def _parse_cap(raw) -> int:
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"cap must be an integer, got {raw!r}") from None
    if not CAP_MIN <= cap <= CAP_MAX:
        raise ValueError(f"cap must be between {CAP_MIN} and {CAP_MAX}, got {cap}")
    return cap


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        return JOBS.get(job_id)


def _run(job: dict) -> None:
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
                _ingest(candidate, job["params"])
                job["ok"] += 1
                log.info("seed ok   (%s): %s", job["id"], candidate)
            except Exception as exc:  # noqa: BLE001 — per-entry failure is data, not a crash
                job["failed"] += 1
                job["errors"].append(f"{candidate}: {exc}")
                log.error("seed FAIL (%s): %s — %s", job["id"], candidate, exc)
            job["done"] += 1
        job["status"] = "done"
        log.info(
            "seed job %s done: %s ok, %s failed", job["id"], job["ok"], job["failed"]
        )
    except Exception as exc:  # noqa: BLE001 — job-level crash is a loud failure
        job["status"] = "failed"
        job["errors"].append(f"job: {exc}")
        log.exception("seed job %s crashed", job["id"])
    finally:
        job["finished_at"] = time.time()


def _ingest(candidate, params: dict) -> None:
    """Route a candidate (URL string or (url, name_hint) tuple) through the seed pipeline."""
    name_hint = None
    if isinstance(candidate, tuple):
        candidate, name_hint = candidate
    url = str(candidate).strip()
    reuse = bool(params.get("reuse_profile", True))
    if "github.com/" in url:
        enrich.seed_from_github(url, reuse_profile=reuse)
    else:
        enrich.seed_from_website(url, name_hint=name_hint, reuse_profile=reuse)


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
            yield item["full_name"]
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


SOURCES = {
    "github_search": _gh_search,
    "url_list": _url_list,
    "famous": _famous,
}
