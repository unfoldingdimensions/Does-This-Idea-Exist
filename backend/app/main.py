"""IdeaExists API — local FastAPI backend (:8020)."""
import hmac
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config, db, enrich, seeder, verify


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


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
    return verify.run_verification()


@app.post("/api/startups/{startup_id}/verify")
def mark_verified(startup_id: int) -> dict:
    """Human gate: confirm a startup exists → verified badge + verified_at."""
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now') WHERE id = ?",
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
