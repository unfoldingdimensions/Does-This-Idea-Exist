"""IdeaExists API — local FastAPI backend (:8020)."""
import hmac
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config, db, enrich, seeder, verify

log = logging.getLogger("ideasexist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seeder.recover_interrupted_jobs()  # restart recovery: queued/running → failed(interrupted)
    _maybe_auto_verify()
    yield


def _maybe_auto_verify() -> None:
    """Set-and-forget: if the archive hasn't been checked recently (or at all),
    enqueue a verification pass at startup. Fails quietly on any guard — the
    weekly cron + the manual button are the primary triggers."""
    days = config.VERIFY_AUTO_STALE_DAYS
    if days <= 0:
        return
    conn = db.connect()
    try:
        # Stale = never checked, or last check older than the threshold.
        stale = conn.execute(
            "SELECT COUNT(*) AS c FROM startups "
            "WHERE last_checked IS NULL OR last_checked < datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()["c"]
    finally:
        conn.close()
    if stale == 0:
        return
    try:
        job_id = verify.start_verification()
    except RuntimeError:
        return  # a pass is already queued/running — nothing to do
    log.info("auto-verify: %s stale entries → verify job %s", stale, job_id)


app = FastAPI(title="IdeaExists API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Minimal security headers on every API response (additive)."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return resp


# --- Rate limiting: per-IP sliding window on mutating/admin endpoints ---
_RATE: dict[tuple[str, str], deque] = defaultdict(deque)
_RATE_LOCK = threading.Lock()


def rate_limited(bucket: str, limit: int, window_s: float = 60.0):
    """FastAPI dependency — at most `limit` requests per IP per window.

    Read endpoints (search/stats/job polling) stay unlimited; this guards the
    token gate (brute force) and the mutating endpoints (abuse / cost burn).
    """

    def dep(request: Request) -> None:
        if not config.RATE_LIMIT_ENABLED:
            return
        key = (bucket, request.client.host if request.client else "unknown")
        now = time.monotonic()
        with _RATE_LOCK:
            q = _RATE[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(status_code=429, detail="Too many requests — slow down a little")
            q.append(now)

    return dep


# --- Failed-auth lockout: counts *failed* admin-token checks per IP so a
# brute-force guesser burns quota, while legitimate (successful) usage and
# read polling are never throttled. ---
_FAILS: dict[tuple[str, str], deque] = defaultdict(deque)
_FAILS_LOCK = threading.Lock()


def _note_failed_auth(request: Request, bucket: str = "admin", limit: int = 10, window_s: float = 60.0) -> None:
    if not config.RATE_LIMIT_ENABLED:
        return
    key = (bucket, request.client.host if request.client else "unknown")
    now = time.monotonic()
    with _FAILS_LOCK:
        q = _FAILS[key]
        while q and now - q[0] > window_s:
            q.popleft()
        q.append(now)
        if len(q) > limit:
            raise HTTPException(status_code=429, detail="Too many failed attempts — try again later")


class GithubSeedIn(BaseModel):
    github_url: str


class WebsiteSeedIn(BaseModel):
    website_url: str
    name: str | None = None


class SeedIn(BaseModel):
    source: str
    params: dict = {}


def require_admin(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    """Owner gate: ADMIN_TOKEN from the environment — fails loudly (403), never
    silently. Failed attempts are counted per IP (10/min) so brute-forcing the
    token is throttled to a crawl."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(403, "Admin disabled — set ADMIN_TOKEN in backend/.env")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        _note_failed_auth(request)
        raise HTTPException(403, "Invalid admin token")


def require_mutation_auth(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    """Mutations stay open by default (local-first UX — the status pill and Add
    dialog work without unlocking admin). When MUTATION_AUTH=1 they demand the
    same admin token as the admin router. Hosting MUST set MUTATION_AUTH=1."""
    if not config.MUTATION_AUTH:
        return
    require_admin(request, x_admin_token)


admin = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


@admin.get("/check", dependencies=[Depends(rate_limited("admin_check", 20, 60))])
def admin_check() -> dict:
    return {"ok": True}


@admin.post("/seed", dependencies=[Depends(rate_limited("admin_seed", 20, 60))])
def start_seed(body: SeedIn) -> dict:
    try:
        job_id = seeder.start_job(body.source, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id}


@admin.get("/seed/status/{job_id}")
def seed_status(job_id: str) -> dict:
    job = seeder.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@admin.get("/seed/jobs")
def seed_jobs() -> list[dict]:
    """Every seed job — active first (running, then queued), then finished.
    The panel re-attaches to live progress on open via this list."""
    return seeder.list_jobs()


class ApproveIn(BaseModel):
    ids: list[int] | None = None
    approve_all: bool = False
    created_after: str | None = None
    created_before: str | None = None


@admin.get("/verify/suggested")
def admin_suggested() -> list[dict]:
    """Human-approval queue — entries the automated check considers alive (or
    never checked) that no human has stamped yet."""
    return verify.list_suggested()


@admin.post("/verify/approve", dependencies=[Depends(rate_limited("approve", 60, 60))])
def admin_approve(body: ApproveIn) -> dict:
    """Bulk human gate: stamp verified=1 on the given ids, every suggested
    row, or every suggested row in a created_at window (the batch boundary
    for "approve this seed run"). The ONLY bulk writer of verified=1 —
    automation never stamps."""
    if body.approve_all:
        n = verify.approve_suggested(approve_all=True)
    elif body.ids:
        n = verify.approve_suggested(ids=body.ids)
    elif body.created_after or body.created_before:
        n = verify.approve_suggested(
            created_after=body.created_after, created_before=body.created_before
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide ids, approve_all=true, or a created_after/created_before window",
        )
    return {"approved": n}


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "llm_model": config.LLM_MODEL,
        "db": config.DB_PATH.name,
    }


@app.get("/api/startups")
def list_startups(category: str | None = None, q: str | None = None) -> list[dict]:
    conn = db.connect()
    try:
        sql = "SELECT * FROM startups"
        conds, params = [], []
        if category:
            conds.append("category = ?")
            params.append(category)
        if q:
            conds.append("(name LIKE ? OR tagline LIKE ? OR description LIKE ?)")
            params += [f"%{q}%"] * 3
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY CASE status WHEN 'dead' THEN 1 ELSE 0 END, name COLLATE NOCASE"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@app.get("/api/categories")
def categories() -> list[dict]:
    conn = db.connect()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT category, COUNT(*) AS count FROM startups GROUP BY category ORDER BY count DESC"
            ).fetchall()
        ]
    finally:
        conn.close()


@app.post("/api/seed/github", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("seed_url", 20, 60))])
def seed_github(body: GithubSeedIn) -> dict:
    try:
        return enrich.seed_from_github(body.github_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — LLM/GitHub/network failures → 502 with detail
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/seed/website", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("seed_url", 20, 60))])
def seed_website(body: WebsiteSeedIn) -> dict:
    try:
        return enrich.seed_from_website(body.website_url, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/verify/run", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("verify_run", 10, 60))])
def run_verification() -> dict:
    """Enqueue a verification pass — returns immediately with a job_id; poll
    /api/verify/status/{job_id} for progress. Serialized on the seed queue."""
    try:
        job_id = verify.start_verification()
    except RuntimeError as exc:  # a verify pass is already queued/running
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": job_id}


@app.get("/api/verify/status/{job_id}")
def verify_status(job_id: str) -> dict:
    job = verify.get_verify_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/verify/current")
def verify_current() -> dict | None:
    """The active (queued/running) verification job, or None. Lets the panel
    re-attach to a pass already in flight (cron-triggered or from an earlier
    click) instead of starting a second one."""
    return verify.get_active_verify_job()


@app.post("/api/startups/{startup_id}/verify", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_verified(startup_id: int) -> dict:
    """Human gate: confirm a startup exists → verified badge + verified_at.

    Also revives a filed entry: a human confirming a dead site is alive
    un-files it (status back to 'active') and RESETS the strike counter —
    human judgment outranks automation (a revive is a fresh start, not a
    continuation of the old streak).
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now'), "
            "status = 'active', check_failures = 0 WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.post("/api/startups/{startup_id}/unverify", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_unverified(startup_id: int) -> dict:
    """Human gate: revoke the verified stamp → back to unverified (active)."""
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET verified = 0, verified_at = NULL, status = 'active' WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.post("/api/startups/{startup_id}/dead", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_dead(startup_id: int) -> dict:
    """Human gate: file as dead — checked and gone. Filed, never deleted."""
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET status = 'dead', verified = 0, verified_at = NULL WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.get("/api/stats")
def stats() -> dict:
    conn = db.connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) AS c FROM startups WHERE verified = 1").fetchone()["c"]
        dead = conn.execute("SELECT COUNT(*) AS c FROM startups WHERE status = 'dead'").fetchone()["c"]
        last = conn.execute("SELECT MAX(last_checked) AS m FROM startups").fetchone()["m"]
        return {"total": total, "verified": verified, "dead": dead, "last_checked": last}
    finally:
        conn.close()


# Admin router is defined above; include after all routes so it resolves at import time.
app.include_router(admin)
