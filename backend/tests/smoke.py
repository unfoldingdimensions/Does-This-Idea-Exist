"""IdeaExists backend smoke test — in-process, no live server or network needed.

Run (from backend/, with the venv python):
    python -m tests.smoke

Uses a throwaway SQLite DB + a throwaway ADMIN_TOKEN (env vars honored before
app import). Live LLM/GitHub seed paths are covered by manual runs — this suite
pins the API surface, schema bootstrap, error handling, dedup upsert, the admin
gate, the seeder job lifecycle (with fake sources), and reuse_profile behavior.
"""
import os
import tempfile
import time
from itertools import islice
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(_tmp.name) / "smoke.db")
os.environ["ADMIN_TOKEN"] = "smoke-admin-token"

from fastapi.testclient import TestClient  # noqa: E402

from app import db, seeder  # noqa: E402
from app.enrich import _upsert  # noqa: E402
from app.main import app  # noqa: E402

import app.enrich as enrich_mod  # noqa: E402
import app.github as gh_mod  # noqa: E402
import app.llm as llm_mod  # noqa: E402

TOKEN = "smoke-admin-token"
fails: list[str] = []

# Capture real functions so tests that monkeypatch can restore them in order.
real_ingest = seeder._ingest
real_seed_gh = enrich_mod.seed_from_github
real_seed_ws = enrich_mod.seed_from_website


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def wait_job(client: TestClient, job_id: str, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = client.get(f"/api/admin/seed/status/{job_id}", headers={"X-Admin-Token": TOKEN}).json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    return job


with TestClient(app) as client:
    # --- core surface ---
    check("health ok", client.get("/api/health").json().get("ok") is True)
    check("startups start empty", client.get("/api/startups").json() == [])
    check("categories start empty", client.get("/api/categories").json() == [])
    stats = client.get("/api/stats").json()
    check("stats zeroed", stats["total"] == 0 and stats["verified"] == 0, str(stats))
    check("mark-verify 404 on unknown", client.post("/api/startups/1/verify").status_code == 404)
    check("verify/run on empty", client.post("/api/verify/run").json()["checked"] == 0)

    # --- admin gate matrix (fails loudly: 403, never 404/200) ---
    check("admin 403 no token", client.post("/api/admin/seed", json={"source": "famous", "params": {}}).status_code == 403)
    check("admin 403 wrong token", client.get("/api/admin/check", headers={"X-Admin-Token": "wrong"}).status_code == 403)
    check("admin check ok", client.get("/api/admin/check", headers={"X-Admin-Token": TOKEN}).json().get("ok") is True)
    check("admin 400 unknown source", client.post("/api/admin/seed", json={"source": "nope", "params": {}}, headers={"X-Admin-Token": TOKEN}).status_code == 400)
    check("admin 400 cap=0", client.post("/api/admin/seed", json={"source": "famous", "params": {"cap": 0}}, headers={"X-Admin-Token": TOKEN}).status_code == 400)
    check("admin 400 cap=501", client.post("/api/admin/seed", json={"source": "famous", "params": {"cap": 501}}, headers={"X-Admin-Token": TOKEN}).status_code == 400)
    check("admin 404 unknown job", client.get("/api/admin/seed/status/nope", headers={"X-Admin-Token": TOKEN}).status_code == 404)

    # --- seeder job lifecycle via API with a fake source (no network) ---
    seeder.SOURCES["fake"] = lambda params: iter(["https://a.com", "https://b.com", "https://c.com"])
    calls: list[str] = []

    def fake_ingest(candidate, params):
        calls.append(str(candidate))
        if str(candidate) == "https://b.com":
            raise ValueError("boom")

    seeder._ingest = fake_ingest
    r = client.post("/api/admin/seed", json={"source": "fake", "params": {"cap": 3}}, headers={"X-Admin-Token": TOKEN})
    job = wait_job(client, r.json()["job_id"])
    check("fake job completes", job["status"] == "done", job["status"])
    check("fake job counts", job["ok"] == 2 and job["failed"] == 1 and job["done"] == 3, str(job))
    check("failures loud in errors", len(job["errors"]) == 1 and "boom" in job["errors"][0], str(job["errors"]))

    r = client.post("/api/admin/seed", json={"source": "fake", "params": {"cap": 2}}, headers={"X-Admin-Token": TOKEN})
    job2 = wait_job(client, r.json()["job_id"])
    # cap=2 processes candidates a and b only; b fails → ok=1, failed=1, done=2
    check("cap truncates cleanly", job2["done"] == 2 and job2["ok"] == 1 and job2["failed"] == 1 and job2["total"] == 2, str(job2))
    seeder._ingest = real_ingest  # restore for the routing/reuse tests below

# --- routing in _ingest (github vs website + name_hint passthrough) ---
routes: list[tuple[str, str]] = []


# --- gh_search producer yields full URLs (regression: bare owner/repo names were
#     misrouted to website seeding → "getaddrinfo failed" on every GitHub search) ---
class _FakeSearchResponse:
    status_code = 200

    def json(self):
        return {"items": [{"full_name": "acme/tool"}, {"full_name": "beta/app"}]}


_real_httpx_get = seeder.httpx.get
seeder.httpx.get = lambda *a, **k: _FakeSearchResponse()
try:
    produced = list(islice(seeder._gh_search({"query": "stars:>10000"}), 2))
finally:
    seeder.httpx.get = _real_httpx_get
check(
    "gh_search yields full github URLs",
    produced == ["https://github.com/acme/tool", "https://github.com/beta/app"],
    str(produced),
)


def fake_gh(url, **kwargs):
    routes.append(("github", url))
    return {}


def fake_ws(url, name_hint=None, **kwargs):
    routes.append(("website", url))
    return {}


enrich_mod.seed_from_github = fake_gh
enrich_mod.seed_from_website = fake_ws
seeder._ingest("https://github.com/a/b", {"reuse_profile": True})
seeder._ingest(("https://example.com", "Example"), {"reuse_profile": True})
check("routing github/website + name_hint", routes == [("github", "https://github.com/a/b"), ("website", "https://example.com")], str(routes))

# restore real enrich functions for the reuse_profile test
enrich_mod.seed_from_github = real_seed_gh
enrich_mod.seed_from_website = real_seed_ws

# --- reuse_profile: second seed skips the LLM, refreshes metadata ---
gh_calls = {"n": 0}
llm_calls = {"n": 0}


def fake_repo(url):
    gh_calls["n"] += 1
    return {
        "full_name": "acme/tool", "name": "tool", "description": "d",
        "created_at": "2020-01-01", "stars": 999, "language": "Go",
        "topics": [], "homepage": "https://tool.example",
        "archived": False, "html_url": "https://github.com/acme/tool",
    }


def fake_llm(*args, **kwargs):
    llm_calls["n"] += 1
    return {"name": "Acme Tool", "tagline": "t", "description": "d2", "category": "devtools", "founded": None}


gh_mod.fetch_repo = fake_repo
llm_mod.llm_json = fake_llm
enrich_mod.seed_from_github("https://github.com/acme/tool", reuse_profile=False)
enrich_mod.seed_from_github("https://github.com/acme/tool", reuse_profile=True)
check("reuse_profile: LLM called exactly once", llm_calls["n"] == 1, str(llm_calls))
check("reuse_profile: repo fetched twice", gh_calls["n"] == 2, str(gh_calls))
conn = db.connect()
row = conn.execute("SELECT stars, verified FROM startups WHERE github_url = 'https://github.com/acme/tool'").fetchone()
conn.close()
check("reuse_profile: stars refreshed to 999", row is not None and row["stars"] == 999 and row["verified"] == 0, str(dict(row) if row else None))

# --- dedup upsert (network-free part of the seed paths) ---
conn = db.connect()
try:
    first = _upsert(
        conn,
        {"name": "Alpha", "tagline": "t1", "website_url": "https://example.com", "category": "other", "source": "website"},
        None,
    )
    existing = db.find_by_url(conn, website_url="https://example.com")
    second = _upsert(
        conn,
        {"name": "Alpha", "tagline": "t2", "website_url": "https://example.com", "category": "other", "source": "website"},
        existing,
    )
    check("upsert inserts", first["id"] >= 1 and first["name"] == "Alpha", str(first))
    check("re-seed dedups (same id)", second["id"] == first["id"], f"{first['id']} vs {second['id']}")
    check("re-seed updates fields", second["tagline"] == "t2", second["tagline"])
finally:
    conn.close()

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURE(S): {fails}")
    raise SystemExit(1)
print("RESULT: ALL PASS")
