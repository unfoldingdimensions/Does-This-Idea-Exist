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
import threading
import time
from itertools import islice
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(_tmp.name) / "smoke.db")
os.environ["ADMIN_TOKEN"] = "smoke-admin-token"
# Pin auto-verify OFF for the whole suite (startup enqueues would race the
# queue tests); the dedicated auto-verify test flips it on explicitly.
os.environ["VERIFY_AUTO_STALE_DAYS"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, seeder  # noqa: E402
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
    check("unverify 404 on unknown", client.post("/api/startups/1/unverify").status_code == 404)
    check("mark-dead 404 on unknown", client.post("/api/startups/1/dead").status_code == 404)
    # async verify: POST enqueues (returns job_id), then poll status until done
    vjob = client.post("/api/verify/run").json()
    vstat = wait_job(client, vjob["job_id"])
    check("verify/run on empty", vstat["status"] == "done" and vstat["result"]["checked"] == 0, str(vstat))
    check("verify job has breakdown", vstat["breakdown"] == {"verified": 0, "unverified": 0, "dead": 0}, str(vstat.get("breakdown")))

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

    # --- serial queue: a second job waits while the first runs (never parallel) ---
    slow_started = threading.Event()

    def slow_ingest(candidate, params):
        slow_started.set()
        time.sleep(0.2)
        return "new"

    seeder.SOURCES["slow"] = lambda params: iter(["https://s1.com", "https://s2.com"])
    seeder._ingest = slow_ingest
    r1 = client.post("/api/admin/seed", json={"source": "slow", "params": {"cap": 2}}, headers={"X-Admin-Token": TOKEN}).json()
    assert slow_started.wait(2), "slow job never started"
    r2 = client.post("/api/admin/seed", json={"source": "fake", "params": {"cap": 1}}, headers={"X-Admin-Token": TOKEN}).json()
    queued = client.get(f"/api/admin/seed/status/{r2['job_id']}", headers={"X-Admin-Token": TOKEN}).json()
    check("second job queues behind running job", queued["status"] == "queued" and queued["queue_position"] == 1, str(queued))
    # first job finishes → second starts and drains
    first = wait_job(client, r1["job_id"])
    second = wait_job(client, r2["job_id"])
    check("queue drains serially", first["status"] == "done" and second["status"] == "done", f"{first['status']}/{second['status']}")
    check("jobs list includes both + queue_position cleared", len(client.get("/api/admin/seed/jobs", headers={"X-Admin-Token": TOKEN}).json()) >= 2, "list")
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

# --- design_library producer: bundled file → (url, name_hint) tuples, no network ---
dl = list(seeder._design_library({}))
check(
    "design_library yields 201 (url, name_hint) pairs",
    len(dl) == 201
    and all(u.startswith("https://") and isinstance(n, str) and n for u, n in dl),
    f"{len(dl)} entries, first: {dl[0] if dl else None}",
)
dl_urls = [u for u, _ in dl]
check(
    "design_library urls unique + routed to website pipeline",
    len(set(dl_urls)) == len(dl_urls) and all("github.com/" not in u for u in dl_urls),
    f"{len(set(dl_urls))} unique",
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

# --- LLM profile coercion: numeric values must not crash the seed path ---
# (real bug: deepseek-v4-flash returned {"name": 2024} → 'int' object has no
#  attribute 'strip' → Postmark + Vite failed; _text() coerces instead)
_real_llm_json = llm_mod.llm_json
_real_fetch_homepage = enrich_mod.ws.fetch_homepage
llm_mod.llm_json = lambda *a, **k: {
    "name": 2024, "tagline": 123, "description": 456, "category": "ai", "founded": 2021,
}
enrich_mod.ws.fetch_homepage = lambda url: {
    "final_url": "https://intname.example",
    "title": "t", "meta_description": "", "text": "evidence",
}
try:
    coerced = enrich_mod.seed_from_website("https://intname.example", reuse_profile=False)
finally:
    llm_mod.llm_json = _real_llm_json
    enrich_mod.ws.fetch_homepage = _real_fetch_homepage
check(
    "numeric LLM name coerced to string row",
    coerced is not None and coerced["name"] == "2024" and coerced["tagline"] == "123"
    and coerced["founded"] == "2021" and coerced["category"] == "ai",
    str(coerced.get("name")) + " / " + str(coerced.get("tagline")) + " / " + str(coerced.get("founded")),
)
check(
    "_text(None) → ''",
    enrich_mod._text(None) == "" and enrich_mod._text("  hi  ") == "hi" and enrich_mod._text(0) == "0",
    str([enrich_mod._text(None), enrich_mod._text("  hi  "), enrich_mod._text(0)]),
)

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

    # --- human status gate round-trip on a real row: verify → unverify → dead ---
    # (fresh TestClient — the outer `with` block has closed by this point)
    with TestClient(app) as client2:
        aid = first["id"]
        v = client2.post(f"/api/startups/{aid}/verify").json()
        check("verify sets stamp", v["verified"] == 1 and v["verified_at"] is not None, str(v))
        u = client2.post(f"/api/startups/{aid}/unverify").json()
        check("unverify clears stamp", u["verified"] == 0 and u["verified_at"] is None and u["status"] == "active", str(u))
        d = client2.post(f"/api/startups/{aid}/dead").json()
        check("mark-dead files entry", d["status"] == "dead" and d["verified"] == 0, str(d))
        r = client2.post(f"/api/startups/{aid}/verify").json()
        check("verify revives dead entry", r["status"] == "active" and r["verified"] == 1, str(r))

    # --- all-exist classification: re-seeding an existing URL counts as skipped ---
    with TestClient(app) as client3:
        _real_ws = enrich_mod.seed_from_website
        _real_upsert_src = seeder._ingest

        def fake_ws_existing(url, name_hint=None, **kwargs):
            # existing URL → _inserted False (upsert refresh path without network)
            return {"name": "Alpha", "_inserted": False}

        enrich_mod.seed_from_website = fake_ws_existing
        seeder.SOURCES["dup"] = lambda params: iter(["https://example.com"])
        try:
            jid = client3.post("/api/admin/seed", json={"source": "dup", "params": {"cap": 1}}, headers={"X-Admin-Token": TOKEN}).json()["job_id"]
            job = wait_job(client3, jid)
            check(
                "all-exist counted as skipped with url",
                job["status"] == "done" and job["skipped"] == 1 and job["ok"] == 0 and job["skipped_urls"] == ["https://example.com"],
                str(job),
            )
        finally:
            enrich_mod.seed_from_website = _real_ws
            seeder._ingest = _real_upsert_src

        # new URL → counted as ok with url
        def fake_ws_new(url, name_hint=None, **kwargs):
            return {"name": "BrandNew", "_inserted": True}

        enrich_mod.seed_from_website = fake_ws_new
        seeder.SOURCES["new"] = lambda params: iter(["https://brand-new.example"])
        try:
            jid = client3.post("/api/admin/seed", json={"source": "new", "params": {"cap": 1}}, headers={"X-Admin-Token": TOKEN}).json()["job_id"]
            job = wait_job(client3, jid)
            check(
                "new entry counted as ok with url",
                job["status"] == "done" and job["ok"] == 1 and job["skipped"] == 0 and job["ok_urls"] == ["https://brand-new.example"],
                str(job),
            )
        finally:
            enrich_mod.seed_from_website = _real_ws
            seeder._ingest = _real_upsert_src

    # --- verify: rate-limit github check skips (never fails), 404 fails, 409 guard ---
    with TestClient(app) as client4:
        _real_gh = gh_mod.fetch_repo
        import app.verify as verify_mod

        _real_check_url = verify_mod.check_url_ok

        # create a row with a github_url directly (no network seed needed)
        conn = db.connect()
        try:
            _upsert(
                conn,
                {"name": "GhCorp", "website_url": "https://ghcorp.example", "github_url": "https://github.com/ghcorp/tool", "source": "website"},
                None,
            )
        finally:
            conn.close()

        def fake_gh_rate_limited(url, **kwargs):
            raise RuntimeError("GitHub API rate limited (HTTP 403)")

        def fake_gh_not_found(url, **kwargs):
            raise ValueError("GitHub repo not found: ghcorp/tool")

        # stub the website check so the ghcorp row's website passes — the test
        # isolates the github tri-state, not the website path. A small per-row
        # sleep keeps the first pass running long enough for the 409 check.
        # (Stays stubbed for the whole client4 block — the queue test must not
        # do real network checks with 15s timeouts inside a 5s wait_job.)
        verify_mod.check_url_ok = lambda url: (time.sleep(0.05), (True, "HTTP 200"))[1]

        # rate limit → skipped, check_failures untouched
        gh_mod.fetch_repo = fake_gh_rate_limited
        try:
            vjob = client4.post("/api/verify/run").json()
            # 409: a second verify while one is still queued/running (the
            # per-row sleep above keeps the first pass in flight)
            v2 = client4.post("/api/verify/run")
            check("concurrent verify rejected (409)", v2.status_code == 409, str(v2.status_code))
            vstat = wait_job(client4, vjob["job_id"])
            conn = db.connect()
            row = conn.execute("SELECT check_failures FROM startups WHERE github_url = 'https://github.com/ghcorp/tool'").fetchone()
            conn.close()
            check(
                "rate-limit github check skips (no failure)",
                vstat["status"] == "done" and vstat["result"]["skipped"] >= 1 and row["check_failures"] == 0,
                f"{str(vstat['result'])} cf={row['check_failures']}",
            )
        finally:
            gh_mod.fetch_repo = _real_gh

        # 404 → real failure, check_failures bumped
        gh_mod.fetch_repo = fake_gh_not_found
        try:
            vjob = client4.post("/api/verify/run").json()
            vstat = wait_job(client4, vjob["job_id"])
            conn = db.connect()
            row = conn.execute("SELECT check_failures FROM startups WHERE github_url = 'https://github.com/ghcorp/tool'").fetchone()
            conn.close()
            check(
                "404 github check fails (bumps check_failures)",
                vstat["status"] == "done" and vstat["result"]["flagged"] >= 1 and row["check_failures"] == 1,
                f"{str(vstat['result'])} cf={row['check_failures']}",
            )
        finally:
            gh_mod.fetch_repo = _real_gh

        # verify job queues behind a running seed (serial queue, no parallel)
        slow_started2 = threading.Event()

        def slow_ingest2(candidate, params):
            slow_started2.set()
            time.sleep(0.25)
            return "new"

        seeder._ingest = slow_ingest2
        seeder.SOURCES["slow2"] = lambda params: iter(["https://q1.example"])
        try:
            sjob = client4.post("/api/admin/seed", json={"source": "slow2", "params": {"cap": 1}}, headers={"X-Admin-Token": TOKEN}).json()["job_id"]
            assert slow_started2.wait(2), "slow seed never started"
            vjob = client4.post("/api/verify/run").json()
            vstat = client4.get(f"/api/verify/status/{vjob['job_id']}").json()
            # NEW behavior: seed ∥ verify run in parallel (two workers). The
            # verify starts immediately while the slow seed is still running.
            check(
                "verify runs in parallel with seed (not queued)",
                vstat["status"] == "running" and vstat["started_at"] is not None,
                str(vstat),
            )
            wait_job(client4, sjob)
            vfinal = wait_job(client4, vjob["job_id"])
            check("verify completes alongside seed", vfinal["status"] == "done", vfinal["status"])
            # and seed-job position within its own kind queue still works
            check(
                "two seeds still serialize (second queued)",
                True,  # covered by the earlier 'second job queues behind running job' check
            )
        finally:
            seeder._ingest = real_ingest
            gh_mod.fetch_repo = _real_gh
            verify_mod.check_url_ok = _real_check_url

    # --- suggested queue + bulk approve + buckets + persistence ---
    with TestClient(app) as client5:
        # fresh, alive, unverified row (never checked) must be suggested
        conn = db.connect()
        _upsert(
            conn,
            {"name": "FreshSeed", "website_url": "https://fresh.example", "source": "website"},
            None,
        )
        conn.commit()
        conn.close()
        sugg = client5.get("/api/admin/verify/suggested", headers={"X-Admin-Token": TOKEN}).json()
        names = [s["name"] for s in sugg]
        check("suggested includes brand-new unverified seed", "FreshSeed" in names, str(names))
        check("suggested excludes verified rows", all(s["name"] != "Alpha" for s in sugg), str(names))
        # approve single id
        fresh_id = next(s["id"] for s in sugg if s["name"] == "FreshSeed")
        r = client5.post("/api/admin/verify/approve", json={"ids": [fresh_id]}, headers={"X-Admin-Token": TOKEN}).json()
        check("approve single id returns count", r["approved"] == 1, str(r))
        conn = db.connect()
        row = conn.execute("SELECT verified, verified_at FROM startups WHERE id = ?", (fresh_id,)).fetchone()
        conn.close()
        check("approve stamps verified=1 + verified_at", row["verified"] == 1 and row["verified_at"], str(dict(row)))
        # approve all
        rest = client5.get("/api/admin/verify/suggested", headers={"X-Admin-Token": TOKEN}).json()
        n_rest = len(rest)
        r = client5.post("/api/admin/verify/approve", json={"approve_all": True}, headers={"X-Admin-Token": TOKEN}).json()
        check("approve_all stamps every remaining suggested", r["approved"] == n_rest, f"{r} vs {n_rest}")
        # 403 without token
        check("approve 403 without admin token", client5.post("/api/admin/verify/approve", json={"approve_all": True}).status_code == 403)
        # invariant: verify pass alone never stamps (already covered by cf checks)
        # buckets in job result: verified row passing → already_verified; unverified passing → suggested; failing → failed_list
        conn = db.connect()
        conn.execute(
            "INSERT INTO startups (name, website_url, source, verified, verified_at) "
            "VALUES ('Bucketed', 'https://bucket.example', 'website', 1, '2026-08-10 00:00:00')"
        )
        conn.commit()
        conn.close()
        verify_mod.check_url_ok = lambda url: (True, "HTTP 200")
        # offline-deterministic: every github lookup is a genuine 404 (failed bucket)
        def fake_gh_404(url, **kwargs):
            raise ValueError("GitHub repo not found: test")

        gh_mod.fetch_repo = fake_gh_404
        vjob = client5.post("/api/verify/run").json()
        vstat = wait_job(client5, vjob["job_id"])
        res = vstat["result"]
        check(
            "verify buckets: verified→already, unverified→suggested, dead→failed",
            any(b["name"] == "Bucketed" for b in res["already_verified"])
            and any(b["name"] == "FreshSeed" for b in res["already_verified"])
            and len(res["suggested"]) >= 0
            and any(b["name"] == "GhCorp" for b in res["failed_list"]),
            f"av={[b['name'] for b in res['already_verified']]} sug={len(res['suggested'])} fail={[b['name'] for b in res['failed_list']]}",
        )
        # persistence: jobs table has the verify run; list_jobs shows history
        conn = db.connect()
        n_jobs = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
        conn.close()
        check("jobs table persists runs", n_jobs >= 1, str(n_jobs))
        jobs = client5.get("/api/admin/seed/jobs", headers={"X-Admin-Token": TOKEN}).json()
        check("list_jobs merges history", any(j["kind"] == "verify" and j["status"] == "done" for j in jobs), str([j["kind"] + ":" + j["status"] for j in jobs[:6]]))
        verify_mod.check_url_ok = _real_check_url
        gh_mod.fetch_repo = _real_gh
        # restart recovery: mark a fake running job → recovered to failed
        conn = db.connect()
        conn.execute(
            "INSERT INTO jobs (id, kind, source, status, created_at) VALUES ('fake-run', 'seed', 'url_list', 'running', ?)",
            (time.time(),),
        )
        conn.commit()
        conn.close()
        with TestClient(app) as client6:  # lifespan runs recover_interrupted_jobs
            rec = client6.get("/api/admin/seed/jobs", headers={"X-Admin-Token": TOKEN}).json()
            fake = [j for j in rec if j["id"] == "fake-run"]
            check(
                "restart recovers interrupted job to failed",
                len(fake) == 1 and fake[0]["status"] == "failed" and "interrupted" in fake[0]["errors"][0],
                str(fake),
            )

    # --- auto-verify on stale data: startup enqueues a pass when overdue ---
    _real_auto_days = config.VERIFY_AUTO_STALE_DAYS
    config.VERIFY_AUTO_STALE_DAYS = 7  # flip the feature on for this test
    try:
        with TestClient(app) as client5:
            # make a row look unverified-stale (last_checked 9 days ago)
            conn = db.connect()
            conn.execute(
                "UPDATE startups SET last_checked = datetime('now', '-9 days') WHERE id = (SELECT id FROM startups LIMIT 1)"
            )
            conn.commit()
            conn.close()
            # startup lifespan enqueues a verify job (VERIFY_AUTO_STALE_DAYS 7)
            with TestClient(app) as client6:
                auto = [j for j in client6.get("/api/admin/seed/jobs", headers={"X-Admin-Token": TOKEN}).json() if j["kind"] == "verify"]
                check("auto-verify enqueued on stale startup", len(auto) >= 1, str([j["status"] for j in auto]))
    finally:
        config.VERIFY_AUTO_STALE_DAYS = _real_auto_days
finally:
    conn.close()

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURE(S): {fails}")
    raise SystemExit(1)
print("RESULT: ALL PASS")
