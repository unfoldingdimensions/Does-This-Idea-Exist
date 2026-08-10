"""IdeaExists API — local FastAPI backend (:8020)."""
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
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


class GithubSeedIn(BaseModel):
    github_url: str


class WebsiteSeedIn(BaseModel):
    website_url: str
    name: str | None = None


class SeedIn(BaseModel):
    source: str
    params: dict = {}


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Owner gate: ADMIN_TOKEN from the environment — fails loudly (403), never silently."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(403, "Admin disabled — set ADMIN_TOKEN in backend/.env")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        raise HTTPException(403, "Invalid admin token")


admin = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


@admin.get("/check")
def admin_check() -> dict:
    return {"ok": True}


@admin.post("/seed")
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


@admin.get("/verify/suggested")
def admin_suggested() -> list[dict]:
    """Human-approval queue — entries the automated check considers alive (or
    never checked) that no human has stamped yet."""
    return verify.list_suggested()


@admin.post("/verify/approve")
def admin_approve(body: ApproveIn) -> dict:
    """Bulk human gate: stamp verified=1 on the given ids or every suggested
    row. The ONLY bulk writer of verified=1 — automation never stamps."""
    if body.approve_all:
        n = verify.approve_suggested(approve_all=True)
    elif body.ids:
        n = verify.approve_suggested(ids=body.ids)
    else:
        raise HTTPException(status_code=400, detail="Provide ids or approve_all=true")
    return {"approved": n}


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "llm_model": config.LLM_MODEL,
        "llm_configured": bool(config.LLM_API_KEY),
        "db": str(config.DB_PATH),
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


@app.post("/api/seed/github")
def seed_github(body: GithubSeedIn) -> dict:
    try:
        return enrich.seed_from_github(body.github_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — LLM/GitHub/network failures → 502 with detail
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/seed/website")
def seed_website(body: WebsiteSeedIn) -> dict:
    try:
        return enrich.seed_from_website(body.website_url, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/verify/run")
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


@app.post("/api/startups/{startup_id}/verify")
def mark_verified(startup_id: int) -> dict:
    """Human gate: confirm a startup exists → verified badge + verified_at.

    Also revives a filed entry: a human confirming a dead site is alive
    un-files it (status back to 'active') — the trust layer is reversible.
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now'), status = 'active' WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.post("/api/startups/{startup_id}/unverify")
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


@app.post("/api/startups/{startup_id}/dead")
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
