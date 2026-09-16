"""IdeaExists backend functional suite — the Phase 5 gate.

One self-contained, in-process suite that asserts F-01..F-24 together, plus the
§6 invariants, so `npm test` re-checks the whole backend on every run instead of
trusting a script someone remembered to run.

Why this exists next to `scripts/phaseN-verify.py`: those four scripts are the
recorded per-phase audit evidence, and they need the live archive (and its
Phase 1 backup) to exist — they work on throwaway copies of it. This suite
depends on NOTHING outside itself, so it runs on any checkout, on any machine.
The four verifiers stay as audit history; this one is the continuous gate.

Discipline (mirrors `tests/smoke.py`):

  * its own throwaway SQLite archive + throwaway founder store, both inside one
    temp dir that is deleted afterwards — never `backend/data/ideasexist.db`;
  * no network and no LLM: the page fetcher (`netguard.safe_get`), both LLM
    prompts (`llm.llm_json`) and the two date sources (Wayback / RDAP) are
    stubbed, so the whole teardown -> founder -> compare -> export -> search
    path runs offline;
  * deterministic: no live archive, no assumption about which rows exist beyond
    the fixtures this file inserts, and every time window is exercised with
    explicit relative stamps rather than the wall clock;
  * fast: it runs on every `npm test` from now on;
  * a machine-readable summary line at the end and a non-zero exit on failure.

A failing check here is the gate working. Do not weaken, skip or delete one.

Run (from `backend/`, with the venv python):
    python -m tests.functional
"""
import csv
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

# Suite output carries arrows/em-dashes; a legacy Windows console (cp1252) raises
# on those mid-run and takes the whole suite down. Same fix as app/main.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# --- throwaway stores + pinned config, BEFORE the app is imported -----------
# (config reads the environment at import time, so the order matters.)
_tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["DB_PATH"] = str(Path(_tmp.name) / "functional.db")
os.environ["FOUNDER_DB_PATH"] = str(Path(_tmp.name) / "functional-founder.db")
# The LLM gateway settings are a third store, and they hold API KEYS (see
# app/gateways.py) — pinned into the throwaway dir for the same reason the
# founder store is: a test run must never touch a real settings file.
os.environ["SETTINGS_DB_PATH"] = str(Path(_tmp.name) / "functional-settings.db")
TOKEN = "functional-admin-token"
os.environ["ADMIN_TOKEN"] = TOKEN
os.environ["MUTATION_AUTH"] = "1"
# Endpoint flakiness is not this phase's subject; the rate limiter gets its own
# dedicated check below, which flips it back on for the duration of that check.
os.environ["RATE_LIMIT_ENABLED"] = "0"
# No auto-verify pass running behind our back (the verify pass is driven here).
os.environ["VERIFY_AUTO_STALE_DAYS"] = "0"
os.environ.pop("REVIEW_SOURCES", None)

from fastapi.testclient import TestClient  # noqa: E402

from app import capture, compare as cmp, config, db  # noqa: E402
from app import enrich, evidence as ev, founder, llm, negatives  # noqa: E402
from app import pages as pages_mod, reviews, search as search_mod, seeder  # noqa: E402
from app import teardown as td, verify  # noqa: E402
from app.main import app as api  # noqa: E402

import app.github as gh_mod  # noqa: E402
import app.main as main_mod  # noqa: E402 — rate-limiter internals
import app.netguard as netguard_mod  # noqa: E402
import app.website as ws_mod  # noqa: E402

MUT = {"X-Admin-Token": TOKEN}
AUTH = MUT

_total = 0
_fails: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global _total
    _total += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        _fails.append(name)


def wait_job(client: TestClient, job_id: str, timeout_s: float = 10.0) -> dict:
    deadline = time.time() + timeout_s
    job: dict = {}
    while time.time() < deadline:
        job = client.get(f"/api/admin/seed/status/{job_id}", headers=MUT).json()
        if job.get("status") in ("done", "failed"):
            return job
        time.sleep(0.02)
    return job


def wait_capture_job(startup_id: int, timeout_s: float = 10.0) -> list[dict]:
    key = capture.key_for(startup_id)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        jobs = [j for j in seeder.JOBS.values()
                if j.get("kind") == "capture" and j.get("key") == key]
        if jobs and all(j["status"] in ("done", "failed") for j in jobs):
            return jobs
        time.sleep(0.02)
    return []


def archive_count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
    finally:
        conn.close()


def row_of(startup_id: int):
    conn = db.connect()
    try:
        return conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
    finally:
        conn.close()


def insert_startup(name: str, website_url: str, **cols) -> int:
    """Fixture rows go in through the archive's own columns."""
    conn = db.connect()
    try:
        keys = ["name", "website_url", "source", *cols]
        values = [name, website_url, "website", *cols.values()]
        cur = conn.execute(
            f"INSERT INTO startups ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            values,
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def patch_startup(startup_id: int, **cols) -> None:
    conn = db.connect()
    try:
        sets = ", ".join(f"{k} = ?" for k in cols)
        conn.execute(f"UPDATE startups SET {sets} WHERE id = ?", (*cols.values(), startup_id))
        conn.commit()
    finally:
        conn.close()


def founder_rows() -> int:
    conn = founder.connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM founder_apps").fetchone()[0]
    finally:
        conn.close()


def table_names(path) -> set:
    conn = sqlite3.connect(str(path))
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def columns_of(path, table: str = "startups") -> list[str]:
    conn = sqlite3.connect(str(path))
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


def column_info(path, table: str, column: str):
    conn = sqlite3.connect(str(path))
    try:
        for r in conn.execute(f"PRAGMA table_info({table})"):
            if r[1] == column:
                return r
        return None
    finally:
        conn.close()


# ===========================================================================
# F-01 / F-02 / F-04 / F-05 / F-19 — schema, migration, evidence, provenance
# ===========================================================================
print("=" * 78)
print("IdeaExists backend functional suite — Phase 5 gate")
print("=" * 78)

# The legacy archive: the base table with NONE of the migration columns — a
# checkout that predates Phase 1. Built from the app's own base DDL, so "legacy"
# means exactly "the 18 recorded columns".
_legacy = sqlite3.connect(str(config.DB_PATH))
try:
    _legacy.executescript(db._STARTUPS_BASE + "\n);")
    _legacy.executemany(
        "INSERT INTO startups (name, website_url, founded, verified, source) VALUES (?,?,?,?,?)",
        [
            ("Legacy One", "https://legacy-one.example", "2020-05-08", 1, "website"),
            ("Legacy Two", "https://legacy-two.example", None, 0, "website"),
        ],
    )
    _legacy.commit()
finally:
    _legacy.close()

_before = columns_of(config.DB_PATH)
check("a legacy-shaped archive starts at the recorded 18 base columns (F-01)",
      len(_before) == 18, f"{len(_before)} columns")
check("the migration knows exactly 22 new teardown columns (F-01)",
      len(db.NEW_STARTUP_COLUMNS) == 22, str(len(db.NEW_STARTUP_COLUMNS)))

# init_db() = CREATE IF NOT EXISTS (fresh DBs) + migrate() (existing DBs).
db.init_db()
_after = columns_of(config.DB_PATH)
_expected = list(_before) + [name for name, _ in db.NEW_STARTUP_COLUMNS]
check("the migration takes the archive 18 -> 40 columns (F-01)",
      len(_after) == 40, f"{len(_before)} -> {len(_after)}")
check("no column is dropped or renamed by the migration (F-01)",
      all(col in _after for col in _before) and set(_after) == set(_expected),
      f"missing: {sorted(set(_before) - set(_after))}")
check("`founded` keeps its name (F-04 — the rename is rejected)",
      "founded" in _after and "founded_at" not in _after,
      f"founded={'founded' in _after} founded_at={'founded_at' in _after}")
check("`date_source` sits beside `founded` (F-04)", "date_source" in _after)
check("the two store-link columns are added (F-19)",
      "app_store_url" in _after and "play_store_url" in _after)

# The migration is additive by construction: watch the SQL it actually executes
# against a fresh legacy DB. Grepping the source would trip over the docstring's
# own "Never DROP, never RENAME"; tracing the statements is the real check.
_trace_conn = db.connect_path(str(Path(_tmp.name) / "legacy-trace.db"))
_trace_sql: list[str] = []
try:
    _trace_conn.executescript(db._STARTUPS_BASE + "\n);")
    _trace_conn.set_trace_callback(lambda stmt: _trace_sql.append(str(stmt)))
    _trace_added = db.migrate(_trace_conn)
    _trace_conn.set_trace_callback(None)
finally:
    _trace_conn.close()
check("the first migration run really adds all 22 columns (F-01)",
      len(_trace_added) == 22, f"added {len(_trace_added)}")
check("the migration executes only ADD COLUMN — no DROP, no RENAME (F-01)",
      len(_trace_sql) == 23
      and all(s.strip().upper().startswith("ALTER TABLE") and "ADD COLUMN" in s.upper()
              for s in _trace_sql if not s.strip().upper().startswith("PRAGMA"))
      and not any(("DROP" in s.upper() or "RENAME" in s.upper()) for s in _trace_sql),
      f"{len(_trace_sql)} statement(s): 1 PRAGMA table_info + 22 ALTER, nothing destructive")

_conn = db.connect()
try:
    _second_run = db.migrate(_conn)
finally:
    _conn.close()
check("re-running the migration is a no-op (idempotent) (F-01)",
      _second_run == [], str(_second_run))
check("existing rows survive the migration (F-01)",
      archive_count() == 2, f"{archive_count()} rows")
_legacy_one = row_of(1)
check("a legacy `founded` value is untouched by the migration (F-01/F-04)",
      _legacy_one["founded"] == "2020-05-08", str(_legacy_one["founded"]))
check("existing rows default date_source to 'unknown' (F-04)",
      _legacy_one["date_source"] == "unknown", str(_legacy_one["date_source"]))

# F-02 — the evidence table and its two NOT NULL columns.
check("the `evidence` table exists after the migration (F-02)",
      "evidence" in table_names(config.DB_PATH), str(sorted(table_names(config.DB_PATH))))
check("evidence has exactly the specified columns (F-02)",
      columns_of(config.DB_PATH, "evidence") ==
      ["id", "startup_id", "evidence_type", "source_url", "captured_at",
       "claim", "value", "provenance", "confidence", "reviewed_at"],
      str(columns_of(config.DB_PATH, "evidence")))
check("evidence.source_url is NOT NULL (F-02)",
      column_info(config.DB_PATH, "evidence", "source_url")[3] == 1,
      f"notnull={column_info(config.DB_PATH, 'evidence', 'source_url')[3]}")
check("evidence.captured_at is NOT NULL (F-02)",
      column_info(config.DB_PATH, "evidence", "captured_at")[3] == 1,
      f"notnull={column_info(config.DB_PATH, 'evidence', 'captured_at')[3]}")

_conn = db.connect()
try:
    _refused_module = False
    try:
        ev.write_evidence(_conn, 1, "feature", "")
    except ev.SourceRequiredError:
        _refused_module = True
    check("a source-less evidence row is refused by the writer (F-02)",
          _refused_module, "SourceRequiredError")
    _refused_db = False
    try:
        _conn.execute(
            "INSERT INTO evidence (startup_id, evidence_type, source_url) VALUES (?,?,?)",
            (1, "feature", None),
        )
    except sqlite3.IntegrityError:
        _refused_db = True
    check("a source-less evidence row is refused by the DB too (F-02)",
          _refused_db, "NOT NULL constraint")
    _auto_id = ev.write_evidence(_conn, 1, "reachability", "https://legacy-one.example",
                                 claim="legacy", value="HTTP 200")
    _auto = _conn.execute("SELECT captured_at FROM evidence WHERE id = ?", (_auto_id,)).fetchone()
finally:
    _conn.close()
check("evidence.captured_at is auto-filled (F-02)", bool(_auto["captured_at"]),
      str(_auto["captured_at"]))

# The silent-drop trap: a column in the schema but missing from enrich.UPDATABLE
# is written by nobody, with no error and no warning.
check("every new column is in enrich.UPDATABLE (F-01 — the silent-drop trap)",
      [n for n, _ in db.NEW_STARTUP_COLUMNS if n not in enrich.UPDATABLE] == [],
      str([n for n, _ in db.NEW_STARTUP_COLUMNS if n not in enrich.UPDATABLE]))
check("every UPDATABLE name is a real archive column (F-01)",
      all(c in _after for c in enrich.UPDATABLE),
      str([c for c in enrich.UPDATABLE if c not in _after]))

# F-19 — both store links are writable through the normal writer.
_conn = db.connect()
try:
    enrich._upsert(_conn, {"name": "Store Link Co", "website_url": "https://store-link.example",
                           "app_store_url": "https://apps.apple.com/app/id1",
                           "play_store_url": "https://play.google.com/store/apps/details?id=x"},
                   None)
    _store_row = _conn.execute(
        "SELECT app_store_url, play_store_url FROM startups WHERE website_url = ?",
        ("https://store-link.example",)).fetchone()
finally:
    _conn.close()
check("app_store_url / play_store_url are writable through the normal writer (F-19)",
      _store_row["app_store_url"].startswith("https://apps.apple.com")
      and _store_row["play_store_url"].startswith("https://play.google.com"),
      str(dict(_store_row)))

# --- stubs: one fetcher, one LLM, one date source. No network anywhere. -----
HOMEPAGE_HTML = (
    "<html><head><title>Acme Notes</title>"
    "<meta name='description' content='Acme Notes keeps your notes in local files.'>"
    "</head><body><h1>Acme Notes — a private, local-first note app</h1>"
    "<p>Acme Notes is a note app for small teams. Your notes live in local files you own.</p>"
    "<a href='/pricing'>Pricing</a> <a href='/docs'>Docs</a> "
    "<a href='https://acme.example/about'>About</a></body></html>"
)
PRICING_HTML = (
    "<html><body><h1>Pricing</h1><p>Free up to 3 docs. Pro $8 billed monthly. "
    "Team $12 per user monthly. Enterprise is custom, billed annual.</p></body></html>"
)
DOCS_HTML = (
    "<html><body><h1>Docs</h1><p>Getting started. Importing your files. "
    "Keyboard shortcuts. Troubleshooting. Backlinks and the graph view.</p></body></html>"
)

SITE = "https://acme.example"
SITE_TWO = "https://acme-two.example"      # its own row (unique website index)
SITE_WALLED = "https://walled.example"
SITE_JIT = "https://jit-compare.example"

FIXTURE: dict[str, tuple[int, str]] = {
    SITE: (200, HOMEPAGE_HTML),
    SITE + "/pricing": (200, PRICING_HTML),
    SITE + "/docs": (200, DOCS_HTML),
    SITE_TWO: (200, HOMEPAGE_HTML.replace("acme.example", "acme-two.example")),
    SITE_TWO + "/pricing": (200, PRICING_HTML),
    SITE_TWO + "/docs": (200, DOCS_HTML),
    SITE_JIT: (200, HOMEPAGE_HTML.replace("acme.example", "jit-compare.example")),
    SITE_JIT + "/pricing": (200, PRICING_HTML),
    SITE_JIT + "/docs": (200, DOCS_HTML),
    # A plain site for the seed/provenance checks.
    "https://prov-seed.example": (200, HOMEPAGE_HTML.replace("acme.example", "prov-seed.example")),
    # A site whose enumerating pages refuse us: neither may become a negative.
    SITE_WALLED: (200, HOMEPAGE_HTML.replace("acme.example", "walled.example")),
    SITE_WALLED + "/pricing": (403, "<html><body>Access denied</body></html>"),
    SITE_WALLED + "/docs": (200, ""),
}

REDDIT_BODY = json.dumps({
    "data": {"children": [
        {"data": {
            "title": "Needs a mobile app",
            "selftext": "I wish there was a native mobile app for this.",
            "permalink": "/r/notes/comments/aaa1/needs_mobile/",
            "score": 98765,          # deliberately not stored anywhere
            "ups": 98764,
        }},
        {"data": {
            "title": "Great, but no API",
            "selftext": "Love it, but I wish it had a public API.",
            "permalink": "/r/notes/comments/bbb2/api/",
            "score": 98763,
        }},
        {"data": {
            "title": "Works well for our team",
            "selftext": "We use it every day and it works well.",
            "permalink": "/r/notes/comments/ccc3/works_well/",
            "score": 98762,
        }},
    ]}
})

REVIEW_SOURCES = (
    {"name": "reddit", "kind": "reddit_json",
     "url_template": "https://www.reddit.com/search.json?q={q}&limit=25"},
    {"name": "g2", "kind": "rss",
     "url_template": "https://www.g2.com/products/{q}/reviews"},
)


class _Resp:
    def __init__(self, url, status, text, content_type="text/html"):
        self.url = url
        self.status_code = status
        self.text = text
        self.headers = {"content-type": content_type}


def fake_fetch(url, **kwargs):
    """The only way out to the network in this suite: a lookup table."""
    if url.startswith("https://www.reddit.com/search.json"):
        return _Resp(url, 200, REDDIT_BODY, "application/json")
    if url.startswith("https://www.g2.com/"):
        return _Resp(url, 403, "<html><body>Enable JavaScript</body></html>")
    hit = FIXTURE.get(url)
    if not hit:
        return _Resp(url, 404, "")
    status, body = hit
    return _Resp(url, status, body)


TEARDOWN_FIXTURE = {
    "features": ["local files", "markdown notes", "backlinks", "graph view",
                 "sync (paid)", "publish"],
    "positioning": "A private, local-first note app that links your thinking.",
    "pricing": {"free_tier": "Free up to 3 docs", "plans": [
        {"name": "Pro", "price": "$8", "period": "monthly"},
        {"name": "Team", "price": "$12", "period": "monthly"},
        {"name": "Enterprise", "price": "custom", "period": "annual"},
        {"name": "Malformed", "price": "", "period": "monthly"},        # dropped
        {"name": "HalfFormed", "price": "$3", "period": "whenever"},    # dropped
    ]},
    "negatives": [
        # A duplicate of the deterministic self-host probe -> dropped.
        {"claim": "no self-host", "observed_on": SITE + "/pricing",
         "why": "pricing page lists no self-host tier"},
        # Cites a page we read and that enumerates -> survives.
        {"claim": "no real-time collaboration", "observed_on": SITE + "/docs",
         "why": "the docs index lists no collaboration section"},
        # A GUESSED url that was never fetched -> dropped by validate().
        {"claim": "no offline mode", "observed_on": SITE + "/api",
         "why": "the guessed /api URL 404s"},
        # Verdict-shaped -> rephrased into an observation.
        {"claim": "Acme has no self-host tier", "observed_on": SITE + "/pricing",
         "why": "pricing page lists Free / Pro / Team"},
    ],
}

IDENTITY_FIXTURE = {
    "name": "Acme Notes",
    "tagline": "local-first notes for small teams",
    "description": "Acme Notes is a private note app for small teams. It keeps your notes in local files you own.",
    "category": "productivity",
    "founded": None,
}


def fake_llm_json(user_content, max_tokens=8000, timeout=180.0, system_prompt=None):
    """One stub for both prompts: the teardown prompt gets the teardown fixture."""
    if system_prompt == llm.TEARDOWN_SYSTEM_PROMPT:
        return json.loads(json.dumps(TEARDOWN_FIXTURE))
    return dict(IDENTITY_FIXTURE)


DATES = {"wayback": None, "rdap": None}
# Keep a handle on the REAL client before stubbing it suite-wide: the gateway
# checks further down must exercise the real request-building path (that is the
# whole point of them), and they cannot do that through a stub.
_real_llm_json = llm.llm_json
llm.llm_json = fake_llm_json
netguard_mod.safe_get = fake_fetch
ws_mod.wayback_first_snapshot = lambda domain: DATES["wayback"]
ws_mod.rdap_registration_date = lambda domain: DATES["rdap"]

# --- F-04: which branch produced `founded`, recorded ------------------------
check("an LLM-stated date is recorded as date_source='llm' (F-04)",
      enrich._resolve_founded("acme.example", "2015-06-01") == ("2015-06-01", "llm"),
      str(enrich._resolve_founded("acme.example", "2015-06-01")))
DATES["wayback"] = "2019-03-04"
check("a Wayback-derived date is recorded as date_source='wayback' (F-04)",
      enrich._resolve_founded("acme.example", "") == ("2019-03-04", "wayback"),
      str(enrich._resolve_founded("acme.example", "")))
DATES["wayback"] = None
DATES["rdap"] = "1997-10-06"
check("an RDAP-derived date is recorded as date_source='rdap' (F-04)",
      enrich._resolve_founded("acme.example", "") == ("1997-10-06", "rdap"),
      str(enrich._resolve_founded("acme.example", "")))
DATES["rdap"] = None
check("with no source the date stays NULL and date_source='unknown' (F-04)",
      enrich._resolve_founded("acme.example", "") == (None, "unknown"),
      str(enrich._resolve_founded("acme.example", "")))
check("date_source is one of the frozen values (F-04)",
      enrich._resolve_founded("z.example", "")[1] in ("llm", "wayback", "rdap", "human", "unknown"),
      str(enrich._resolve_founded("z.example", "")[1]))

# --- F-05: provenance flags -------------------------------------------------
_seed_id = insert_startup("Nothing", "https://prov-seed.example")
enrich.seed_from_website("https://prov-seed.example", reuse_profile=False)
_seeded = row_of(_seed_id)
check("a fresh seed is stamped provenance='machine_drafted' (F-05)",
      _seeded["provenance"] == enrich.MACHINE_DRAFTED, str(_seeded["provenance"]))
check("the seeded row carries date_source='unknown' when nothing stated a date (F-04/F-05)",
      _seeded["date_source"] == "unknown", str(_seeded["date_source"]))
_conn = db.connect()
try:
    enrich.mark_human_confirmed(_conn, _seed_id)
finally:
    _conn.close()
check("a human confirm flips provenance to human_confirmed (F-05)",
      row_of(_seed_id)["provenance"] == enrich.HUMAN_CONFIRMED,
      str(row_of(_seed_id)["provenance"]))
enrich.seed_from_website("https://prov-seed.example", reuse_profile=True)
check("a reuse_profile refresh does not downgrade human_confirmed (F-05)",
      row_of(_seed_id)["provenance"] == enrich.HUMAN_CONFIRMED,
      str(row_of(_seed_id)["provenance"]))
_conn = db.connect()
try:
    _bad_table = False
    try:
        enrich.mark_human_confirmed(_conn, _seed_id, table="jobs")
    except ValueError:
        _bad_table = True
finally:
    _conn.close()
check("mark_human_confirmed refuses a table outside its whitelist (F-05)",
      _bad_table, "jobs refused")

# ===========================================================================
# F-06 / F-07 / F-08 / F-09 — capture: features, pricing, positioning, negatives
# ===========================================================================
print("\n--- F-06/F-07/F-08/F-09: capture, evidence rows and the negative rule ---")
_comp_id = insert_startup("Acme Notes", SITE)
_cap = capture.capture_teardown(_comp_id, fetcher=fake_fetch,
                                llm_fn=lambda brief: TEARDOWN_FIXTURE)
_row = row_of(_comp_id)
_features = json.loads(_row["features_json"] or "[]")
_pricing = json.loads(_row["pricing_json"] or "{}")
_plans = _pricing.get("plans") or []
_ev_rows = ev.for_startup(db.connect(), _comp_id)
_feat_rows = [r for r in _ev_rows if r["evidence_type"] == "feature"]
_price_rows = [r for r in _ev_rows if r["evidence_type"] == "pricing"]
_neg_rows = [r for r in _ev_rows if r["evidence_type"] == "negative"]
_pos_rows = [r for r in _ev_rows if r["evidence_type"] == "positioning"]

check("a capture reports state=captured (F-06)", _cap.get("state") == "captured",
      str(_cap.get("state")))
check("features_json holds 5-10 items (F-06)", 5 <= len(_features) <= 10,
      f"{len(_features)}: {_features}")
check("fewer than 5 supported features become unknown, never padded (F-06)",
      td.clean_features(["a", "b"]) == [] and td.clean_features([]) == [],
      str(td.clean_features(["a", "b"])))
check("more than 10 features are capped, not stored raw (F-06)",
      len(td.clean_features([f"cap {i}" for i in range(15)])) == 10,
      str(len(td.clean_features([f"cap {i}" for i in range(15)]))))
check("one evidence row per feature, each with a source_url (F-06)",
      len(_feat_rows) == len(_features) and all(r["source_url"] for r in _feat_rows),
      f"{len(_feat_rows)} rows for {len(_features)} features")
check("pricing rows each carry a price and a period (F-07)",
      bool(_plans) and all(p.get("price") and p.get("period") in td.PERIODS for p in _plans),
      str(_plans))
check("malformed plan rows are dropped, not stored half-formed (F-07)",
      len(_plans) == 3 and all(p["name"] not in ("Malformed", "HalfFormed") for p in _plans),
      str([p["name"] for p in _plans]))
check("pricing_captured_at is stamped (F-07)", bool(_row["pricing_captured_at"]),
      str(_row["pricing_captured_at"]))
check("pricing_source_url is stamped (F-07)", _row["pricing_source_url"] == SITE + "/pricing",
      str(_row["pricing_source_url"]))
check("the free tier is captured as its own claim (F-07)",
      bool(_pricing.get("free_tier"))
      and any(r["claim"] == "free_tier" for r in _price_rows),
      str(_pricing.get("free_tier")))
check("one evidence row per pricing plan + the free tier (F-07)",
      len(_price_rows) == len(_plans) + 1
      and all(r["source_url"] == SITE + "/pricing" for r in _price_rows),
      f"{len(_price_rows)} rows for {len(_plans)} plans + free tier")
check("positioning is non-empty (F-08)", bool((_row["positioning"] or "").strip()),
      str(_row["positioning"]))
check("the positioning line carries its source (F-08)",
      len(_pos_rows) == 1 and _pos_rows[0]["source_url"] == SITE, str(_pos_rows))
check("provenance is machine_drafted until a human confirms (F-05/F-08)",
      _row["provenance"] == enrich.MACHINE_DRAFTED, str(_row["provenance"]))
check("every teardown evidence row is machine_drafted (F-05)",
      all(r["provenance"] == "machine_drafted" for r in _ev_rows
          if r["evidence_type"] in ("feature", "pricing", "positioning", "negative", "review")),
      str(sorted({r["provenance"] for r in _ev_rows})))
check("teardown evidence is unknown rather than invented when a page is unreadable (F-06)",
      all(r["confidence"] is not None for r in _ev_rows),
      "every evidence row carries a confidence")

_neg_claims = [r["claim"] for r in _neg_rows]
_neg_sources = {r["source_url"] for r in _neg_rows}
check("a sourced negative traces to an enumerating page (F-09)",
      "no self-host" in _neg_claims and SITE + "/pricing" in _neg_sources,
      f"{_neg_claims} from {sorted(_neg_sources)}")
check("no negative is derived from a guessed URL (F-09)",
      not any("/api" in (s or "") for s in _neg_sources) and "no offline mode" not in _neg_claims,
      str(sorted(_neg_sources)))
check("the LLM's negatives survive only when they trace to a page we read (F-09)",
      "no real-time collaboration" in _neg_claims and SITE + "/docs" in _neg_sources,
      str(_neg_claims))
check("a deterministic probe wins over the LLM's duplicate of the same fact (F-09)",
      sum(1 for c in _neg_claims if "self-host" in (c or "")) == 1, str(_neg_claims))
check("a verdict-shaped claim is rephrased into an observation (F-09)",
      all(not (c or "").lower().startswith(("acme has no", "they have no"))
          for c in _neg_claims), str(_neg_claims))
_guessed = {"role": "api", "url": SITE + "/api", "state": "unreadable",
            "http_status": 404, "reason": "HTTP 404"}
check("a 404 on a guessed URL produces nothing at all (F-09)",
      negatives.probe_absence(_guessed, "API", why="guessed", hints=negatives.API_HINTS) is None,
      "guessed-record probe returned None")
check("the page plan never fetches a guessed capability path (F-09)",
      all(path not in negatives.GUESSED_CAPABILITY_PATHS for _, path in pages_mod.PLAN),
      str(pages_mod.PLAN))
check("a negative with no enumerating source is refused, not stored (F-09)",
      negatives.validate({"claim": "no API", "observed_on": ""}, {}) is None
      and negatives.validate(
          {"claim": "no API", "observed_on": SITE + "/api"},
          {"pricing": {"role": "pricing", "url": SITE + "/pricing",
                       "state": "readable", "text": "x"}}) is None,
      "empty source and non-enumerating source both refused")

_walled_id = insert_startup("Walled Notes", SITE_WALLED)
capture.capture_teardown(_walled_id, fetcher=fake_fetch,
                         llm_fn=lambda brief: TEARDOWN_FIXTURE)
_walled_negs = ev.for_startup(db.connect(), _walled_id, "negative")
_unknowns = [r for r in _walled_negs if (r["value"] or "") == "unknown"]
check("a retrieval failure is unknown with low confidence, never a negative (F-09)",
      bool(_unknowns) and all((r["confidence"] or 1) <= 0.1 for r in _unknowns),
      f"{len(_unknowns)} unknown row(s), conf={[r['confidence'] for r in _unknowns]}")
check("an unreadable page still gets a source_url (the page we tried) (F-09)",
      all(r["source_url"] for r in _walled_negs),
      str(sorted({r["source_url"] for r in _walled_negs})))
check("no pricing is stored when the pricing page could not be read (F-07)",
      not row_of(_walled_id)["pricing_json"] and not row_of(_walled_id)["pricing_captured_at"],
      f"pricing_json={row_of(_walled_id)['pricing_json']!r}")

# ===========================================================================
# F-23 — reviews: what their users ask for, never a score
# ===========================================================================
print("\n--- F-23: reviews ---")
_rev_id = insert_startup("Acme Reviews Co", SITE_TWO)
_rev_cap = capture.capture_teardown(_rev_id, fetcher=fake_fetch,
                                    llm_fn=lambda brief: TEARDOWN_FIXTURE,
                                    sources=REVIEW_SOURCES)
_review_rows = ev.for_startup(db.connect(), _rev_id, "review")
check("one evidence row per review, source_url = the review permalink (F-23)",
      len(_review_rows) == 3
      and all(r["source_url"].startswith("https://www.reddit.com/r/") for r in _review_rows),
      str([r["source_url"] for r in _review_rows]))
check("a walled provider (403) is a skip, not a failure (F-23)",
      _rev_cap.get("reviews_skipped") == 1 and len(_review_rows) == 3,
      f"skipped={_rev_cap.get('reviews_skipped')} rows={len(_review_rows)}")
_review_values = [json.loads(r["value"] or "{}") for r in _review_rows]
check("positive and negative are both classified (F-23)",
      {v.get("classification") for v in _review_values} == {"negative", "positive"},
      str([v.get("classification") for v in _review_values]))
check("no score, aggregate or NPS of our own is stored (F-23)",
      all(set(v) == {"classification", "asks"} for v in _review_values)
      and not any("98765" in (r["value"] or "") for r in _review_rows),
      str([sorted(v) for v in _review_values]))
_asks = reviews.asks_from_evidence(db.connect(), _rev_id)
check("every extracted ask links to the review it came from (F-23)",
      bool(_asks) and all(a["source_url"].startswith("https://www.reddit.com/r/") for a in _asks),
      str(_asks[:2]))
check("every review evidence row is machine_drafted (F-05/F-23)",
      all(r["provenance"] == "machine_drafted" for r in _review_rows),
      str(sorted({r["provenance"] for r in _review_rows})))

# ===========================================================================
# F-10 .. F-14, F-20, F-24 — the founder app: three paths, two gates, one store
# ===========================================================================
print("\n--- F-10..F-14 / F-20 / F-24: founder app, gates, submissions ---")
_base_count = archive_count()
FORM_PAYLOAD = {
    "name": "Loom-note",
    "description": "An online-first note app with an API and collaboration.",
    "target_user": "small teams that write together",
    "category": "productivity",
    "features": ["local files", "markdown notes", "public API",
                 "real-time collaboration", "export"],
    "positioning": "Notes for teams that live online.",
    "pricing": {"free_tier": "Free up to 5 docs",
                "plans": [{"name": "Pro", "price": "$7", "period": "monthly"}]},
    "website_url": "https://loom-note.example",
}

with TestClient(api) as client:
    _url_app = client.post("/api/founder-app", json={"url": SITE}).json()
    check("URL path drafts the founder's app (F-10)",
          bool(_url_app.get("founder_app_id"))
          and _url_app["profile"]["name"] == "Acme Notes"
          and _url_app.get("confirmed") is False,
          str(_url_app.get("profile", {}).get("name")))
    check("the URL path does not invent the founder's feature list (F-10)",
          _url_app["profile"]["features"] == [], str(_url_app["profile"]["features"]))

    _form_app = client.post("/api/founder-app", json=FORM_PAYLOAD).json()
    _fid = _form_app["founder_app_id"]
    check("form path drafts a full teardown record (F-11)",
          bool(_form_app.get("founder_app_id"))
          and 5 <= len(_form_app["profile"]["features"]) <= 10
          and _form_app["profile"]["pricing"].get("plans"),
          str(_form_app["profile"]["features"]))

    _missing = client.post("/api/founder-app", json={**FORM_PAYLOAD, "features": None})
    _short = client.post("/api/founder-app", json={**FORM_PAYLOAD, "features": ["a", "b", "c", "d"]})
    check("a form without 5-10 features is a clear 400 (F-11)",
          _missing.status_code == 400 and "features" in _missing.json()["detail"]
          and _short.status_code == 400,
          f"{_missing.status_code}/{_short.status_code}: {_missing.json().get('detail')}")

    _agent_payload = {
        "name": "Agent Co",
        "description": "Drafted by the founder's own agent.",
        "target_user": "teams that write",
        "category": "devtools",
        "features": ["local files", "public API", "webhooks", "search", "export", "themes"],
        "positioning": "Docs that stay in your repo.",
        "pricing": {"free_tier": "No free tier",
                    "plans": [{"name": "Solo", "price": "$9", "period": "monthly"}]},
        "links": {"website": "https://agent.example",
                  "app_store": "https://apps.apple.com/app/id12345",
                  "play_store": "", "github": ""},
    }
    _agent = client.post("/api/founder-app", json={"agent_json": json.dumps(_agent_payload)})
    check("agent-JSON path drafts the founder's app (F-12)",
          _agent.status_code == 200
          and _agent.json()["profile"]["app_store_url"].startswith("https://apps.apple.com"),
          str(_agent.status_code))
    _malformed = client.post("/api/founder-app", json={"agent_json": "{not json,"})
    _unknown_key = client.post(
        "/api/founder-app",
        json={"agent_json": json.dumps({**_agent_payload, "invented_field": 1})})
    check("malformed agent JSON is a 400 (F-12)",
          _malformed.status_code == 400 and "malformed" in _malformed.json()["detail"].lower(),
          str(_malformed.json().get("detail"))[:70])
    check("unknown agent keys are a 400, never silently dropped (F-12)",
          _unknown_key.status_code == 400 and "invented_field" in _unknown_key.json()["detail"],
          str(_unknown_key.json().get("detail"))[:90])

    check("nothing the founder path wrote reached the archive (F-20)",
          archive_count() == _base_count, f"{_base_count} -> {archive_count()}")
    _names = {r["name"] for r in client.get("/api/startups").json()}
    _stats = client.get("/api/stats").json()
    _cats = client.get("/api/categories").json()
    _founder_names = {"Loom-note", "Agent Co", "Linkless Co", "Rejected Co"}
    check("no founder record appears in /api/startups (F-20)",
          not (_founder_names & _names), str(sorted(_founder_names & _names)))
    check("no founder record is counted by /api/stats (F-20)",
          _stats["total"] == _base_count, f"{_stats['total']} vs {_base_count}")
    check("no founder record appears in /api/categories and the facets still answer (F-20)",
          bool(_cats) and all(c["count"] > 0 for c in _cats), str(_cats[:3]))
    check("the verify walk never sees the founder store (F-20)",
          not ({"Loom-note", "Agent Co"} & {s["name"] for s in verify.list_suggested()}),
          "list_suggested is archive-only")
    _ac = db.connect()
    _fc = founder.connect()
    try:
        _archive_has_founder = bool(_ac.execute(
            "SELECT name FROM sqlite_master WHERE name='founder_apps'").fetchone())
        _founder_has_startups = bool(_fc.execute(
            "SELECT name FROM sqlite_master WHERE name='startups'").fetchone())
    finally:
        _ac.close()
        _fc.close()
    check("the two stores are two files, each with its own schema (F-10/F-20)",
          str(config.FOUNDER_DB_PATH) != str(config.DB_PATH)
          and not _archive_has_founder and not _founder_has_startups,
          "founder_apps is absent from the archive; startups is absent from the founder store")

    # eligibility gate — no link, no consent question
    _linkless = client.post("/api/founder-app",
                            json={**FORM_PAYLOAD, "name": "Linkless Co",
                                  "website_url": None}).json()
    check("a link-less submission is comparison-only (F-20)",
          _linkless["publish_offered"] is False
          and _linkless["archive_status"] == "local_only"
          and _linkless["eligibility"]["has_link"] is False, str(_linkless["eligibility"]))
    _linkless_pub = client.post(f"/api/founder-app/{_linkless['founder_app_id']}/publish")
    check("no consent question is asked when there is no link (F-20)",
          _linkless_pub.status_code == 400
          and "comparison-only" in _linkless_pub.json()["detail"],
          str(_linkless_pub.json().get("detail"))[:90])
    _store_only = client.post("/api/founder-app", json={
        "name": "Play Only Co", "category": "other",
        "features": ["a", "b", "c", "d", "e"],
        "play_store_url": "https://play.google.com/store/apps/details?id=co",
    }).json()
    check("a store-only link satisfies eligibility (F-19/F-20)",
          _store_only["eligibility"]["link_field"] == "play_store_url"
          and _store_only["publish_offered"] is True,
          str(_store_only["eligibility"]))

    # confirm gate + compare guard
    _refused = False
    try:
        founder.assert_comparable(_fid)
    except ValueError as exc:
        _refused = "not confirmed" in str(exc)
    check("the compare path refuses an unconfirmed founder app (F-13)", _refused,
          "assert_comparable raised")
    _unconfirmed_app = client.post("/api/founder-app",
                                   json={**FORM_PAYLOAD, "name": "Unconfirmed Gate Co"}).json()
    _gate = client.post("/api/compare", json={"you": {"id": _unconfirmed_app["founder_app_id"]},
                                              "competitors": [{"id": _comp_id}]})
    _gate_detail = _gate.json().get("detail")
    check("the endpoint refuses an unconfirmed app with an explicit 409 not_confirmed (F-13)",
          _gate.status_code == 409 and isinstance(_gate_detail, dict)
          and _gate_detail.get("state") == "not_confirmed"
          and "confirm" in _gate_detail.get("message", ""),
          f"{_gate.status_code}: {_gate_detail}")

    _confirmed = client.post(f"/api/founder-app/{_fid}/confirm").json()
    _conn = founder.connect()
    try:
        _prov = _conn.execute("SELECT provenance, confirmed_at FROM founder_apps WHERE id = ?",
                              (_fid,)).fetchone()
    finally:
        _conn.close()
    check("confirm flips the record to human_confirmed (F-05/F-13)",
          _confirmed["confirmed"] is True and _prov["provenance"] == enrich.HUMAN_CONFIRMED
          and bool(_prov["confirmed_at"]), f"{_prov['provenance']} at={_prov['confirmed_at']}")
    check("nothing is auto-confirmed by a draft (F-13)",
          _form_app["confirmed"] is False and _url_app["confirmed"] is False
          and _agent.json()["confirmed"] is False, "all three drafts start unconfirmed")

    # Consent is not a field on the create endpoint (F-13).
    _rows_before_flag = founder_rows()
    _legacy_flag = client.post("/api/founder-app",
                               json={**FORM_PAYLOAD, "name": "Legacy Flag Co", "publish": True})
    check("a `publish` key on the create endpoint is refused, not ignored (F-13)",
          _legacy_flag.status_code in (400, 422), f"HTTP {_legacy_flag.status_code}")
    check("the refusal names the call that does publish (F-13)",
          "founder-app/{id}/publish" in json.dumps(_legacy_flag.json()),
          str(_legacy_flag.json())[:130])
    check("the refused request wrote no draft (F-13 — no partial write to retry)",
          founder_rows() == _rows_before_flag, f"{_rows_before_flag} -> {founder_rows()}")
    _typo = client.post("/api/founder-app",
                        json={**FORM_PAYLOAD, "name": "Typo Co", "positioningg": "oops"})
    check("an unknown top-level key is refused too (F-12's rule, one level up)",
          _typo.status_code in (400, 422) and founder_rows() == _rows_before_flag,
          f"HTTP {_typo.status_code}")

    # consent -> pending -> approve -> archive_startup_id
    _published = client.post(f"/api/founder-app/{_fid}/publish").json()
    check("ticking the opt-in creates a pending submission (F-13/F-24)",
          _published["submitted"] is True and _published["archive_status"] == "pending",
          str(_published))
    _queue = client.get("/api/admin/verify/suggested", headers=AUTH).json()
    _in_queue = [r for r in _queue if r.get("kind") == "founder_submission"]
    check("the admin queue unions founder submissions with the archive's rows (F-24)",
          any(r["founder_app_id"] == _fid for r in _in_queue)
          and any(r.get("kind") == "archive" for r in _queue),
          f"{len(_in_queue)} founder row(s) among {len(_queue)} queue rows")
    _sub_id = _published["submission_id"]
    _approved = client.post(f"/api/admin/founder/submissions/{_sub_id}/approve",
                            headers=AUTH).json()
    _archive_id = _approved["archive_startup_id"]
    _archived = row_of(_archive_id)
    check("approval creates the archive row and links it (F-13/F-24)",
          _archived is not None and _archived["name"] == "Loom-note",
          f"archive_startup_id={_archive_id} name={_archived['name'] if _archived else None}")
    check("the founder record keeps its own row — the archive got a twin (F-10)",
          founder.get(_fid)["id"] == _fid and archive_count() == _base_count + 1,
          f"archive {_base_count} -> {archive_count()}")
    check("archive_status is derived from the newest submission (F-24)",
          founder.archive_status(_fid) == "approved" and "archive_status" not in founder.get(_fid),
          str(founder.archive_status(_fid)))

    # rejection carries a note; a resubmission is a NEW row
    _reject_app = client.post("/api/founder-app",
                              json={**FORM_PAYLOAD, "name": "Rejected Co"}).json()
    _rid = _reject_app["founder_app_id"]
    client.post(f"/api/founder-app/{_rid}/confirm")
    _first_sub = client.post(f"/api/founder-app/{_rid}/publish").json()["submission_id"]
    _rejected = client.post(f"/api/admin/founder/submissions/{_first_sub}/reject",
                            json={"note": "The site is behind a login, so nothing could be read."},
                            headers=AUTH).json()
    check("a rejection carries a note the founder can read (F-24)",
          _rejected["submission"]["status"] == "rejected"
          and "login" in (_rejected["submission"]["note"] or ""),
          str(_rejected["submission"]["note"])[:60])
    check("a rejection with no note is refused (F-24)",
          client.post(f"/api/admin/founder/submissions/{_first_sub}/reject",
                      json={"note": "  "}, headers=AUTH).status_code == 400, "400")
    _second_sub = client.post(f"/api/founder-app/{_rid}/publish").json()["submission_id"]
    _history = founder.decisions(_rid)
    check("resubmitting after a rejection creates a NEW row, never an edit (F-24)",
          len(_history) == 2 and [h["status"] for h in _history] == ["rejected", "pending"]
          and _first_sub != _second_sub,
          str([(h["id"], h["status"]) for h in _history]))
    check("archive_status follows the newest submission (F-24)",
          founder.archive_status(_rid) == "pending", founder.archive_status(_rid))
    check("the founder draft is readable back from its own endpoint (F-10)",
          client.get(f"/api/founder-app/{_fid}").json()["profile"]["name"] == "Loom-note",
          "GET /api/founder-app/{id}")

    # --- F-14: idempotency kept, with the teardown carve-out ----------------
    _before_seed = row_of(_comp_id)
    enrich.seed_from_website(SITE, reuse_profile=True)
    _after_seed = row_of(_comp_id)
    check("a re-seed does not duplicate the row (F-14)",
          _after_seed["id"] == _before_seed["id"],
          f"id {_before_seed['id']} -> {_after_seed['id']}")
    check("a re-seed keeps the teardown fields (F-14 carve-out)",
          _after_seed["features_json"] == _before_seed["features_json"]
          and _after_seed["pricing_json"] == _before_seed["pricing_json"]
          and _after_seed["positioning"] == _before_seed["positioning"]
          and _after_seed["pricing_captured_at"] == _before_seed["pricing_captured_at"],
          f"features={bool(_after_seed['features_json'])} "
          f"pricing={bool(_after_seed['pricing_json'])}")
    _conn = db.connect()
    try:
        enrich.mark_human_confirmed(_conn, _comp_id)
    finally:
        _conn.close()
    enrich.seed_from_website(SITE, reuse_profile=True)
    check("a re-seed never downgrades human_confirmed (F-14 carve-out)",
          row_of(_comp_id)["provenance"] == enrich.HUMAN_CONFIRMED,
          str(row_of(_comp_id)["provenance"]))
    _conn = db.connect()
    try:
        _dedup_refused = False
        try:
            enrich._upsert(_conn, {"name": "Twin Co", "website_url": SITE,
                                   "source": "website"}, None)
        except ValueError as exc:
            _dedup_refused = "already filed" in str(exc)
    finally:
        _conn.close()
    check("a unique-index collision is still a clear ValueError -> 400 (F-14)",
          _dedup_refused, "duplicate website_url refused")

# ===========================================================================
# F-15 / F-16 / F-17 / F-21 — comparison, exports, slug, badges
# ===========================================================================
print("\n--- F-15 / F-16 / F-17 / F-21: gap table, exports, slug, badges ---")


def find(table: dict, band: str, dimension=None, you_has=None):
    for r in table.get(band) or []:
        if dimension and r["dimension"] != dimension:
            continue
        if you_has and you_has not in r["you"].lower():
            continue
        return r
    return None


_fid_confirmed = _fid  # Loom-note, confirmed and published above
with TestClient(api) as client:
    check("compare refuses a `you` it cannot resolve (F-13/F-15)",
          client.post("/api/compare",
                      json={"you": {"id": "no-such-founder-app"},
                            "competitors": [{"id": _comp_id}]}).status_code in (400, 404),
          "unresolvable 'you'")

    _table_resp = client.post("/api/compare",
                              json={"you": {"id": _fid_confirmed},
                                    "competitors": [{"id": _comp_id}]})
    check("compare returns the table for a confirmed founder app (F-15/F-22)",
          _table_resp.status_code == 200 and "you_have_they_dont" in _table_resp.json(),
          f"{_table_resp.status_code}")
    table = _table_resp.json()

    _you_only = find(table, cmp.BAND_YOU_HAVE, cmp.DIM_FEATURES, you_has="public api")
    check("a capability only 'you' have lands in you_have_they_dont (F-15)",
          _you_only is not None and bool(_you_only["source"]), str(_you_only))
    check("that edge traces to the competitor's enumerating page (F-09/F-15)",
          _you_only is not None and _you_only["source"] == SITE + "/docs",
          str(_you_only and _you_only["source"]))
    _them_only = find(table, cmp.BAND_THEY_HAVE, cmp.DIM_FEATURES, you_has="not offered")
    check("a capability only 'they' have lands in they_have_you_dont (F-15)",
          _them_only is not None and bool(_them_only["source"]), str(_them_only))
    _both = next((r for r in table[cmp.BAND_BOTH]
                  if r["dimension"] == cmp.DIM_FEATURES and "markdown" in r["them"].lower()), None)
    check("a capability both have lands in both_have (F-15)",
          _both is not None and bool(_both["source"]), str(_both))
    check("every band is present in the payload (F-15)",
          all(b in table for b in cmp.BANDS) and set(table["bands"]) == set(cmp.BANDS),
          str(table["bands"]))
    _unknown_feature = find(table, cmp.BAND_UNKNOWN, cmp.DIM_FEATURES)
    check("missing data is shown as unknown, never scored (F-15)",
          _unknown_feature is None or _unknown_feature["them"].lower().startswith("unknown"),
          str(_unknown_feature))
    check("the activity row is unknown — the 'you' side has no liveness signal (dim 6)",
          all(r["band"] == cmp.BAND_UNKNOWN for r in table["rows"]
              if r["dimension"] == cmp.DIM_ACTIVITY),
          str([r["band"] for r in table["rows"] if r["dimension"] == cmp.DIM_ACTIVITY]))

    _sourced_bands = (cmp.BAND_YOU_HAVE, cmp.BAND_THEY_HAVE, cmp.BAND_BOTH, cmp.BAND_ASKED_FOR)
    _unsourced = [(r["band"], r["dimension"]) for r in table["rows"]
                  if r["band"] in _sourced_bands and not r["source"]]
    check("every non-unknown 'they' cell carries a source (cell rule 1)",
          not _unsourced, str(_unsourced))
    check("every row is exactly {dimension, band, you, them, source, captured_at}",
          all(set(r) == {"dimension", "band", "you", "them", "source", "captured_at"}
              for r in table["rows"]),
          str(sorted({k for r in table["rows"] for k in r})))
    check("no verdict line is emitted (cell rule 5)",
          not any(w in json.dumps(table).lower()
                  for w in ("you should", "you will beat", "recommend")),
          "no 'you should' / 'you will beat' / 'recommend' anywhere")
    _dim5 = [r for r in table["rows"] if r["dimension"] == cmp.DIM_DOESNT_DO]
    check("a negative is only rendered from an enumerating page (F-09/F-15)",
          bool(_dim5) and all(r["source"] for r in _dim5)
          and not any("/api" in r["source"] for r in _dim5),
          str(sorted({r["source"] for r in _dim5})))
    check("a negative whose capability you cover is an edge (dim 5)",
          find(table, cmp.BAND_YOU_HAVE, cmp.DIM_DOESNT_DO) is not None,
          str(find(table, cmp.BAND_YOU_HAVE, cmp.DIM_DOESNT_DO)))

    _orphan_id = insert_startup("Orphan Negative Co", "https://orphan-neg.example")
    _conn = db.connect()
    try:
        _conn.execute(
            "INSERT INTO evidence (startup_id, evidence_type, source_url, captured_at, "
            "claim, value, provenance, confidence) VALUES (?,?,?,?,?,?,?,?)",
            (_orphan_id, "negative", "", "2026-09-15 00:00:00", "no self-host",
             "observed: x", "machine_drafted", 0.8),
        )
        _conn.commit()
        _orphan_table = cmp.build_table(founder.get(_fid_confirmed), [row_of(_orphan_id)], _conn)
    finally:
        _conn.close()
    _orphan_row = next((r for r in _orphan_table["rows"]
                        if r["dimension"] == cmp.DIM_DOESNT_DO), None)
    check("an unsourced doesn't-do cell renders unknown, never 'no' (cell rule 2)",
          _orphan_row is not None and _orphan_row["band"] == cmp.BAND_UNKNOWN
          and _orphan_row["them"].lower().startswith("unknown"),
          str(_orphan_row))

    _asks_rows = [r for r in table["rows"] if r["dimension"] == cmp.DIM_ASKS]
    check("a reviewer ask neither side covers lands in asked_for (dim 7)",
          find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS) is not None
          and "reviewer" in find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS)["them"],
          str(find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS)))
    _covered_ask = find(table, cmp.BAND_YOU_HAVE, cmp.DIM_ASKS)
    check("the same ask, when your declared features cover it, lands in you_have_they_dont (dim 7)",
          _covered_ask is not None and "declared" in _covered_ask["you"], str(_covered_ask))
    check("every ask links to the review it came from (F-23 -> dim 7)",
          bool(_asks_rows) and all(r["source"].startswith("https://www.reddit.com/r/")
                                   for r in _asks_rows),
          str(sorted({r["source"] for r in _asks_rows})))

    # --- F-16: the three exports, stateless and deterministic --------------
    _params = {"you": str(_fid_confirmed), "competitors": str(_comp_id)}
    _md = client.get("/api/export/markdown", params=_params)
    _js = client.get("/api/export/json", params=_params)
    _cv = client.get("/api/export/csv", params=_params)
    check("all three exports answer 200 (F-16)",
          _md.status_code == _js.status_code == _cv.status_code == 200,
          f"{_md.status_code}/{_js.status_code}/{_cv.status_code}")
    _labels = [cmp.BAND_LABELS[b] for b in
               (cmp.BAND_YOU_HAVE, cmp.BAND_THEY_HAVE, cmp.BAND_BOTH, cmp.BAND_ASKED_FOR)]
    check("Markdown has the four groups incl. the demand group (F-16)",
          all(f"## {label}" in _md.text for label in _labels),
          str([label for label in _labels if f"## {label}" not in _md.text]))
    _js_data = json.loads(_js.text)
    check("JSON is re-processable: {you, them, rows} with the right row keys (F-16)",
          set(_js_data) >= {"you", "them", "rows"} and isinstance(_js_data["rows"], list)
          and all({"dimension", "you", "them", "source", "band"} <= set(r)
                  for r in _js_data["rows"]),
          str(sorted(_js_data)))
    check("JSON 'you' is the ONE founder record the caller named (F-16 / no leak)",
          _js_data["you"]["name"] == "Loom-note"
          and _js_data["you"]["founder_app_id"] == _fid_confirmed,
          str(_js_data["you"].get("name")))
    _csv_rows = list(csv.reader(io.StringIO(_cv.text)))
    check("CSV has the exact columns band, dimension, you, them, source_url, captured_at (F-16)",
          _csv_rows[0] == ["band", "dimension", "you", "them", "source_url", "captured_at"],
          str(_csv_rows[0]))
    check("CSV carries asked_for as a band value (F-16)",
          any(rw[0] == "asked_for" for rw in _csv_rows[1:]),
          str(sorted({rw[0] for rw in _csv_rows[1:]})))
    check("re-running an export with the same inputs gives the same bytes (F-16)",
          _md.text == client.get("/api/export/markdown", params=_params).text
          and _js.text == client.get("/api/export/json", params=_params).text
          and _cv.text == client.get("/api/export/csv", params=_params).text,
          "markdown/json/csv all byte-identical across two calls")
    check("an unknown export format is refused (F-16)",
          client.get("/api/export/pdf", params=_params).status_code == 404, "404")
    check("an export never triggers a capture (F-16 — stateless, pure read)",
          not any(j.get("kind") == "capture" and j.get("key") == capture.key_for(_orphan_id)
                  for j in seeder.JOBS.values()),
          "no capture job for the export-only competitor")

    # --- F-17: the slug endpoint and its collision rule ---------------------
    _known = client.get("/api/startups/acme-notes")
    check("a known product resolves by slug (F-17)",
          _known.status_code == 200
          and cmp.slugify(_known.json()["resolved_name"]) == "acme-notes",
          f"{_known.status_code} "
          f"{_known.json().get('resolved_name') if _known.status_code == 200 else ''}")
    check("an unknown slug is a clean 404 (F-17)",
          client.get("/api/startups/this-slug-does-not-exist-zzz").status_code == 404, "404")

    _dup_verified = insert_startup("Dup Group Co", "https://dup-a.example", verified=1)
    insert_startup("Dup Group Co", "https://dup-b.example", verified=0)
    _dup_resp = client.get("/api/startups/dup-group-co")
    check("a duplicate-name group resolves deterministically: verified first (F-17)",
          _dup_resp.status_code == 200
          and _dup_resp.json()["resolved_id"] == _dup_verified
          and len(_dup_resp.json()["duplicate_group"]) == 2,
          f"got={_dup_resp.json().get('resolved_id') if _dup_resp.status_code == 200 else None} "
          f"expected={_dup_verified}")
    _duo_a = insert_startup("Duo Unverified", "https://duo-a.example", verified=0)
    insert_startup("Duo Unverified", "https://duo-b.example", verified=0)
    _duo_resp = client.get("/api/startups/duo-unverified")
    check("with no verified row the lowest id wins (F-17)",
          _duo_resp.status_code == 200 and _duo_resp.json()["resolved_id"] == _duo_a,
          str(_duo_resp.json().get("resolved_id")))

    # --- F-21: explicit, claim-free trust badges ----------------------------
    _badge_stale = insert_startup("Badge Stale Co", "https://badge-stale.example")
    _conn = db.connect()
    try:
        _conn.execute(
            "UPDATE startups SET verified = 1, verified_at = '2026-01-01 00:00:00', "
            "status = 'active', check_failures = 0, "
            "last_checked = datetime('now', '-200 days') WHERE id = ?", (_badge_stale,))
        _conn.commit()
    finally:
        _conn.close()
    _stale = client.get("/api/startups/badge-stale-co").json()
    check("a stale last_checked reads machine_verified=false while admin_verified stays true (F-21)",
          _stale["machine_verified"] is False and _stale["admin_verified"] is True,
          f"machine={_stale['machine_verified']} admin={_stale['admin_verified']} "
          f"at={_stale['machine_verified_at']}")
    _badge_fresh = insert_startup("Badge Fresh Co", "https://badge-fresh.example")
    _conn = db.connect()
    try:
        _conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now'), status = 'active', "
            "check_failures = 0, last_checked = datetime('now') WHERE id = ?", (_badge_fresh,))
        _conn.commit()
    finally:
        _conn.close()
    _fresh = client.get("/api/startups/badge-fresh-co").json()
    check("a fresh check reads machine_verified=true (F-21)",
          _fresh["machine_verified"] is True, str(_fresh["machine_verified"]))
    check("the badges are explicit fields, never inferred from a raw timestamp (F-21)",
          {"admin_verified", "admin_verified_at", "machine_verified", "machine_verified_at"}
          <= set(_fresh),
          str(sorted(set(_fresh) & {"admin_verified", "admin_verified_at",
                                    "machine_verified", "machine_verified_at"})))
    check("no badge is emitted inside a claim/row cell (F-21 / §8.1)",
          all(not ({"admin_verified", "machine_verified"} & set(r)) for r in table["rows"])
          and "machine verified" not in _md.text.lower()
          and "admin verified" not in _md.text.lower(),
          "badges live on the record payload only")

    # --- F-22 wiring: a never-captured competitor gets queued, not a table --
    _jit_id = insert_startup("Jit Wiring Co", SITE_JIT)
    _queued = client.post("/api/compare",
                          json={"you": {"id": _fid_confirmed}, "competitors": [{"id": _jit_id}]})
    check("a never-captured competitor returns the queued/retry state (F-22)",
          _queued.status_code == 200
          and _queued.json().get("state") in ("queued", "in_progress")
          and bool(_queued.json().get("message")) and "both_have" not in _queued.json(),
          f"{_queued.status_code}: {_queued.json().get('state')} / "
          f"{_queued.json().get('message')}")
    wait_capture_job(_jit_id)
    _served = client.post("/api/compare",
                          json={"you": {"id": _fid_confirmed}, "competitors": [{"id": _jit_id}]})
    check("once captured, the same call returns the table (F-15/F-22)",
          _served.status_code == 200 and "both_have" in _served.json(),
          f"{_served.status_code}: {list(_served.json())[:4]}")

# ===========================================================================
# F-18 — search classification & match reasons
# ===========================================================================
print("\n--- F-18: search classification, match reasons and the pure-read posture ---")
TOKEN_WORD = "zorblat"
insert_startup("Zorblat", "https://zorblat-exact.example")
insert_startup("Zorblat Notes", "https://zorblat-name.example")
insert_startup("Tagline Zorb Co", "https://zorblat-tag.example",
               tagline="A zorblat for teams that write together")
insert_startup("Desc Zorb Co", "https://zorblat-desc.example",
               description="The zorblat keeps every note in one place.")
insert_startup("Cat Zorb Co", "https://zorblat-cat.example", category="zorblat")
insert_startup("Zorblit", "https://zorblat-fuzzy.example", stars=99999)
insert_startup("Zorblat Dead", "https://zorblat-dead.example", status="dead")
insert_startup("Zorblat Pivoted", "https://zorblat-piv.example", status="pivoted")
insert_startup("Obsidian", "https://obsidian.example")

with TestClient(api) as client:
    _obs = client.get("/api/search", params={"q": "Obsidian"})
    _payload = _obs.json()
    check("the search endpoint answers 200 (F-18)", _obs.status_code == 200, str(_obs.status_code))
    check("a product name returns that product as result #1 (F-18)",
          bool(_payload) and _payload[0]["name"] == "Obsidian",
          f"#1={[r['name'] for r in _payload[:1]]}")
    check("…with reason == 'Exact name match' (F-18)",
          bool(_payload) and _payload[0]["reason"] == search_mod.REASON_EXACT_NAME,
          repr(_payload[0]["reason"] if _payload else None))

    _conn = db.connect()
    try:
        _rows = [dict(r) for r in _conn.execute("SELECT * FROM startups").fetchall()]
    finally:
        _conn.close()
    _hits = search_mod.classify_rows(_rows, TOKEN_WORD)
    _live_hits = [h for h in _hits if h.row["status"] not in ("dead", "pivoted")]
    _rungs = [h.rung for h in _live_hits]
    check("the classified rungs are non-decreasing (ladder order holds) (F-18)",
          all(a <= b for a, b in zip(_rungs, _rungs[1:])), f"rungs={_rungs}")
    _live = client.get("/api/search", params={"q": TOKEN_WORD}).json()
    check("the endpoint returns the classifier's order verbatim (F-18)",
          [r["name"] for r in _live] == [h.row["name"] for h in _hits],
          "endpoint order == classify_rows order")
    _seq = [h.row["name"] for h in _live_hits
            if h.row["name"].startswith(("Zorblat", "Tagline", "Desc", "Cat"))]
    check("the fixtures come back in ladder order (exact -> name -> tagline -> desc -> category)",
          _seq == ["Zorblat", "Zorblat Notes", "Tagline Zorb Co", "Desc Zorb Co", "Cat Zorb Co"],
          str(_seq))
    check("a row only the fuzzy rung can reach lands on the fuzzy rung (F-18)",
          any(h.rung == search_mod.RUNG_FUZZY and h.row["name"] == "Zorblit" for h in _hits),
          "Zorblit -> fuzzy")
    _reasons = {r["reason"] for r in _live}
    check("every reason is one of the frozen vocabulary strings (F-18)",
          _reasons <= set(search_mod.REASONS),
          str(sorted(_reasons - set(search_mod.REASONS))))
    check("no reason is empty, a number, a code or an internal rung name (F-18)",
          all(r == r.strip() and r and not any(ch.isdigit() for ch in r)
              and "_" not in r and "rung" not in r.lower() for r in _reasons),
          str(sorted(_reasons)))
    check("the vocabulary is frozen at the eight plan strings (F-18)",
          len(search_mod.REASONS) == 8
          and {search_mod.REASON_EXACT_NAME, search_mod.REASON_PROBLEM,
               search_mod.REASON_AUDIENCE} <= set(search_mod.REASONS),
          str(search_mod.REASONS))

    check("dead AND pivoted rows sort last under an otherwise equal match (F-18)",
          [r["name"] for r in _live][-2:] == ["Zorblat Dead", "Zorblat Pivoted"],
          str([r["name"] for r in _live][-2:]))
    check("the tombstones are still returned, never hidden or deleted (F-18)",
          {r["name"] for r in _live} >= {"Zorblat Dead", "Zorblat Pivoted"},
          "both present in the payload")
    check("stars are a tie-break only — a 0-star exact-name hit beats a 99999-star fuzzy one",
          _live[0]["name"] == "Zorblat", f"#1={_live[0]['name']}")

    _no_q = client.get("/api/search")
    check("no q at all -> 200 with an empty list (documented contract)",
          _no_q.status_code == 200 and _no_q.json() == [], f"{_no_q.status_code} {_no_q.json()!r}")
    check("q= (empty) -> 200 with an empty list",
          client.get("/api/search", params={"q": ""}).json() == [], "[]")
    check("q=<whitespace> -> 200 with an empty list",
          client.get("/api/search", params={"q": "   "}).json() == [], "[]")
    for _meta in ("%", "_", "%%", "__"):
        _res = client.get("/api/search", params={"q": _meta})
        check(f"q={_meta!r} returns nothing rather than everything (F-18)",
              _res.status_code == 200 and _res.json() == [],
              f"{_res.status_code} {len(_res.json())} rows")

    _never_id = insert_startup("Nevercaptured Co", "https://never-captured.example")
    _ev_before = int(ev.count_for_startup(db.connect(), _never_id).get("feature", 0))
    client.get("/api/search", params={"q": "nevercaptured"})
    client.get("/api/search", params={"q": TOKEN_WORD})
    _ev_after = int(ev.count_for_startup(db.connect(), _never_id).get("feature", 0))
    _cap_jobs = [j for j in seeder.JOBS.values()
                 if j.get("kind") == "capture" and j.get("key") == capture.key_for(_never_id)]
    check("a search writes no evidence row (F-18)", _ev_before == _ev_after == 0,
          f"{_ev_before} -> {_ev_after}")
    check("a search queues no capture job for a never-captured competitor (F-22 contrast)",
          not _cap_jobs, f"capture jobs for the competitor: {len(_cap_jobs)}")
    _real_start_capture = capture.start_capture

    def _tripwire(*_a, **_k):
        raise AssertionError("search called capture.start_capture — search must stay a pure read")

    capture.start_capture = _tripwire
    try:
        _trip = client.get("/api/search", params={"q": TOKEN_WORD})
        _tripped = None
    except AssertionError as exc:
        _trip, _tripped = None, str(exc)
    finally:
        capture.start_capture = _real_start_capture
    check("a search never calls capture.start_capture (unlike /api/compare) (F-18)",
          _tripped is None and _trip.status_code == 200,
          _tripped or f"{_trip.status_code}, no capture attempted")

    insert_startup("Keyword Pop Co", "https://kw-pop.example",
                   features_json=json.dumps(["kwonlycapability"]))
    insert_startup("Keyword Empty Co", "https://kw-empty.example")
    _kw = client.get("/api/search", params={"q": "kwonlycapability"}).json()
    check("the keyword rung matches the populated row and skips the NULL one (data-aware)",
          len(_kw) == 1 and _kw[0]["name"] == "Keyword Pop Co",
          f"{len(_kw)} hit(s): {[r['name'] for r in _kw]}")
    check("a term that appears nowhere returns no rows at all (F-18)",
          client.get("/api/search", params={"q": "zzzznosuchwordzzzz"}).json() == [], "[]")

# ===========================================================================
# F-22 — just-in-time capture: one job per competitor, cached inside the window
# ===========================================================================
print("\n--- F-22: one job per competitor, in-flight retry, the 7-day window ---")
_jit_conc = insert_startup("Jit Concurrent Co", SITE_JIT + "-two")
FIXTURE[SITE_JIT + "-two"] = (200, HOMEPAGE_HTML.replace("acme.example",
                                                         "jit-compare.example-two"))
FIXTURE[SITE_JIT + "-two" + "/pricing"] = (200, PRICING_HTML)
FIXTURE[SITE_JIT + "-two" + "/docs"] = (200, DOCS_HTML)

_release = threading.Event()
_started = threading.Event()
_real_teardown = capture.capture_teardown


def _blocking_teardown(startup_id, **kwargs):
    _started.set()
    _release.wait(10)
    return {"state": "captured", "startup_id": startup_id}


capture.capture_teardown = _blocking_teardown
try:
    _first = capture.start_capture(_jit_conc)
    _began = _started.wait(5)
    _second = capture.start_capture(_jit_conc)
    _jobs = [j for j in seeder.JOBS.values()
             if j.get("kind") == "capture" and j.get("key") == capture.key_for(_jit_conc)]
    check("two concurrent captures of one competitor produce exactly one job (F-22)",
          _began and len(_jobs) == 1 and _first["state"] == "queued",
          f"jobs={len(_jobs)} first={_first['state']} second={_second['state']}")
    check("an in-flight capture returns the explicit retry state, not a partial teardown (F-22)",
          _second["state"] == "in_progress" and _second["message"] == capture.CAPTURE_IN_PROGRESS,
          str(_second))
    _release.set()
    _deadline = time.time() + 5
    while time.time() < _deadline and not all(j["status"] in ("done", "failed") for j in _jobs):
        time.sleep(0.02)
    check("the capture job completes and records its result (F-22)",
          bool(_jobs) and _jobs[0]["status"] == "done"
          and _jobs[0]["result"]["state"] == "captured",
          str(_jobs[0]["status"] if _jobs else None))
finally:
    _release.set()
    capture.capture_teardown = _real_teardown

_cached = capture.start_capture(_comp_id)
check("a request inside the 7-day window is served from cache (F-22)",
      _cached["state"] == "cached" and bool(_cached.get("captured_at")), str(_cached))

_stale_cap_id = insert_startup("Stale Capture Co", SITE_JIT + "-three")
FIXTURE[SITE_JIT + "-three"] = (200, HOMEPAGE_HTML.replace("acme.example",
                                                           "jit-compare.example-three"))
FIXTURE[SITE_JIT + "-three" + "/pricing"] = (200, PRICING_HTML)
FIXTURE[SITE_JIT + "-three" + "/docs"] = (200, DOCS_HTML)
capture.capture_teardown(_stale_cap_id, fetcher=fake_fetch,
                         llm_fn=lambda brief: TEARDOWN_FIXTURE)
_conn = db.connect()
try:
    _conn.execute(
        "UPDATE evidence SET captured_at = datetime('now', '-30 days') "
        "WHERE startup_id = ? AND evidence_type IN "
        "('feature','pricing','positioning','negative','review')", (_stale_cap_id,))
    _conn.execute("UPDATE startups SET pricing_captured_at = datetime('now', '-30 days') "
                  "WHERE id = ?", (_stale_cap_id,))
    _conn.commit()
finally:
    _conn.close()
capture.capture_teardown = lambda startup_id, **kw: {"state": "captured", "startup_id": startup_id}
try:
    _stale = capture.start_capture(_stale_cap_id)
    check("a request outside the window re-captures (F-22)",
          _stale["state"] in ("queued", "in_progress"), str(_stale))
finally:
    wait_capture_job(_stale_cap_id)
    capture.capture_teardown = _real_teardown
check("the freshness window is 7 days, the same rhythm as VERIFY_AUTO_STALE_DAYS (F-22)",
      config.CAPTURE_STALE_DAYS == 7,
      f"CAPTURE_STALE_DAYS={config.CAPTURE_STALE_DAYS} (VERIFY_AUTO_STALE_DAYS is pinned to "
      f"{config.VERIFY_AUTO_STALE_DAYS} for this run to keep the network out of the suite)")
check("a capture for an unknown competitor is an explicit not_found (F-22)",
      capture.start_capture(99999999)["state"] == "not_found", "not_found")

with TestClient(api) as client:
    check("there is no public capture-job endpoint (F-22 — job payloads are admin-gated)",
          client.get("/api/capture/status/anything").status_code == 404
          and client.get("/api/admin/capture/status/anything").status_code == 403,
          "public route absent; admin route 403 without a token")

# ===========================================================================
# §6 — the invariants that must not regress
# ===========================================================================
print("\n--- §6 invariants: auth, SSRF, LIKE-escape, rate limits, tri-state liveness ---")
_real_fetch_repo = gh_mod.fetch_repo


def _gh_404(url, **kwargs):
    raise ValueError("GitHub repo not found: test")


with TestClient(api) as client:
    # MUTATION_AUTH gates every write endpoint (the full 6-route matrix and the
    # failed-auth lockout are pinned by tests/smoke.py; here we pin that the gate
    # is live and that it is auth, not a dead route, that answers).
    _write_codes = {}
    for path, body in (
        ("/api/seed/github", {"github_url": "https://github.com/a/b"}),
        ("/api/seed/website", {"website_url": "https://example.com"}),
        ("/api/verify/run", None),
        ("/api/startups/1/verify", None),
        ("/api/startups/1/unverify", None),
        ("/api/startups/1/dead", None),
    ):
        r = client.post(path, json=body) if body else client.post(path)
        _write_codes[path] = r.status_code
    check("MUTATION_AUTH refuses every write endpoint without a token (403, not 404/200)",
          all(v == 403 for v in _write_codes.values()), str(_write_codes))
    check("the gate opens with the token (403 comes from auth, not a dead route)",
          client.post("/api/startups/999999/verify", headers=MUT).status_code == 404,
          "404 = auth passed, row absent")

    # SSRF guard: non-public targets are refused before any socket is opened.
    _blocked = {}
    for target in ("http://localhost:8020/", "http://127.0.0.1/", "http://[::1]/",
                   "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/",
                   "http://192.168.1.1/", "http://internal.local/", "file:///etc/passwd",
                   "gopher://example.com/"):
        try:
            netguard_mod.check_target(target)
            _blocked[target] = "ALLOWED"
        except netguard_mod.BlockedAddressError:
            _blocked[target] = "blocked"
        except Exception as exc:  # noqa: BLE001
            _blocked[target] = f"other:{type(exc).__name__}"
    check("netguard blocks loopback/private/link-local/metadata/non-http targets (SSRF guard)",
          all(v == "blocked" for v in _blocked.values()),
          str({k: v for k, v in _blocked.items() if v != "blocked"}) or "all 9 blocked")
    check("BlockedAddressError is a ValueError (existing 400/502 paths still catch it)",
          issubclass(netguard_mod.BlockedAddressError, ValueError))

    # LIKE metacharacters stay literal on the legacy list endpoint.
    _probe_id = insert_startup("LikeProbe", "https://likeprobe.example")
    check("q=% is a literal, not a match-everything wildcard (LIKE-escape)",
          client.get("/api/startups", params={"q": "%"}).json() == []
          and len(client.get("/api/startups", params={"q": "LikeProbe"}).json()) == 1,
          "q=% -> 0 rows, literal -> 1 row")
    check("q=_ is also literal (LIKE-escape)",
          client.get("/api/startups", params={"q": "_"}).json() == [], "0 rows")

    # Tri-state liveness: a bot wall is a skip (never a strike), a 404 is a
    # strike, and a human-verified row is never auto-flipped.
    _wall_id = insert_startup("BotWallCo", "https://botwall.example")
    _ver_id = insert_startup("VerifiedCo", "https://verifiedco.example")
    patch_startup(_ver_id, verified=1, verified_at="2026-01-01 00:00:00", check_failures=0)
    _real_check_url = verify.check_url_ok
    gh_mod.fetch_repo = _gh_404
    try:
        verify.check_url_ok = lambda url: (False, "HTTP 403", True)
        _j = client.post("/api/verify/run", headers=MUT).json()
        _jstat = wait_job(client, _j["job_id"])
        check("a 403 website check SKIPS — it never strikes (tri-state liveness)",
              _jstat["result"]["skipped"] >= 1 and row_of(_wall_id)["check_failures"] == 0,
              f"skipped={_jstat['result']['skipped']} cf={row_of(_wall_id)['check_failures']}")

        verify.check_url_ok = lambda url: (False, "HTTP 404", False)
        _j = client.post("/api/verify/run", headers=MUT).json()
        _jstat = wait_job(client, _j["job_id"])
        check("a 404 website check strikes — only 404/410 count (tri-state liveness)",
              _jstat["result"]["flagged"] >= 1 and row_of(_wall_id)["check_failures"] == 1,
              f"flagged={_jstat['result']['flagged']} cf={row_of(_wall_id)['check_failures']}")
        check("a verified row is never auto-flipped or struck (human gate outranks automation)",
              row_of(_ver_id)["status"] == "active" and row_of(_ver_id)["verified"] == 1
              and row_of(_ver_id)["check_failures"] == 0,
              f"status={row_of(_ver_id)['status']} verified={row_of(_ver_id)['verified']} "
              f"cf={row_of(_ver_id)['check_failures']}")

        # F-03 — verify_log is permanent: a >90-day-old row survives a pass.
        _conn = db.connect()
        try:
            _conn.execute(
                "INSERT INTO verify_log (startup_id, checked_at, website_ok, github_ok, notes) "
                "VALUES (?, datetime('now', '-200 days'), 1, NULL, 'aged audit row')",
                (_wall_id,))
            _conn.commit()
            _aged_before = _conn.execute(
                "SELECT COUNT(*) AS c FROM verify_log "
                "WHERE checked_at < datetime('now', '-90 days')").fetchone()["c"]
        finally:
            _conn.close()
        verify.check_url_ok = lambda url: (True, "HTTP 200", False)
        _j = client.post("/api/verify/run", headers=MUT).json()
        wait_job(client, _j["job_id"])
        _conn = db.connect()
        try:
            _aged_after = _conn.execute(
                "SELECT COUNT(*) AS c FROM verify_log "
                "WHERE checked_at < datetime('now', '-90 days')").fetchone()["c"]
            _recent = _conn.execute(
                "SELECT COUNT(*) AS c FROM verify_log WHERE notes = 'aged audit row'"
            ).fetchone()["c"]
        finally:
            _conn.close()
        check("a >90-day-old verify_log row survives a real pass (F-03 — no retention sweep)",
              _aged_before == 1 and _aged_after == 1 and _recent == 1,
              f"aged before={_aged_before} after={_aged_after} surviving row={_recent}")
    finally:
        verify.check_url_ok = _real_check_url
        gh_mod.fetch_repo = _real_fetch_repo

    # The human stamp is the only bulk writer: a pass leaves verified untouched.
    check("an automated pass never stamps verified=1 (the human gate is the only writer)",
          row_of(_probe_id)["verified"] == 0, f"verified={row_of(_probe_id)['verified']}")

    # Rate limiting: flipped on for this one check (the suite pins it off so a
    # fast run cannot trip it), then restored.
    _real_rate = config.RATE_LIMIT_ENABLED
    config.RATE_LIMIT_ENABLED = True
    try:
        main_mod._RATE.clear()
        _seen = [client.post("/api/startups/999999/dead", headers=MUT).status_code
                 for _ in range(65)]
        check("the per-IP sliding window returns 429 past the bucket limit (60/min)",
              _seen.count(429) > 0 and _seen[0] == 404,
              f"404s={_seen.count(404)} 429s={_seen.count(429)}")
        main_mod._RATE.clear()
        client.post("/api/startups/999999/dead", headers=MUT)
        _live_keys = len(main_mod._RATE)
        main_mod._evict_idle(main_mod._RATE, time.monotonic() + 3600, 60.0)
        check("rate-limiter keys are evicted once their window expires",
              _live_keys == 1 and len(main_mod._RATE) == 0,
              f"{_live_keys} key(s) during window, {len(main_mod._RATE)} after eviction")
    finally:
        config.RATE_LIMIT_ENABLED = _real_rate
        main_mod._RATE.clear()
        main_mod._FAILS.clear()

# ===========================================================================
# LLM gateways — the registry, the admin settings surface, runtime resolution
# ===========================================================================
print("\n--- LLM gateways: registry, admin settings, runtime resolution ---")
from app import gateways as gw_mod  # noqa: E402

_ENV_KEYS = ("OPENCODE_GO_API_KEY", "OPENCODE_ZEN_API_KEY", "OPENROUTER_API_KEY",
             "GEMINI_API_KEY", "GOOGLE_API_KEY", "COMMAND_CODE_API_KEY")
_saved_env = {k: os.environ.get(k) for k in (*_ENV_KEYS, "LLM_BASE_URL", "LLM_MODEL")}


def _clear_keys() -> None:
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


expect_base_urls = {
    "opencode-go": "https://opencode.ai/zen/go/v1",
    "opencode-zen": "https://opencode.ai/zen/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "command-code": "https://api.commandcode.ai/provider/v1",
}

try:
    _clear_keys()
    with TestClient(api) as client:
        check("the gateway settings surface is admin-gated",
              client.get("/api/admin/settings/gateways").status_code == 403,
              "403 without a token")
        listing = client.get("/api/admin/settings/gateways", headers=MUT).json()
        ids = [g["id"] for g in listing["gateways"]]
        check("all five requested gateways are registered",
              ids == list(expect_base_urls), str(ids))
        check("the base URLs are the ones each provider publishes",
              {g["id"]: g["default_base_url"] for g in listing["gateways"]} == expect_base_urls,
              str({g["id"]: g["default_base_url"] for g in listing["gateways"]}))
        check("every gateway is OpenAI-compatible: https, an env fallback and a docs link",
              all(g["default_base_url"].startswith("https://") and g["env_vars"]
                  and g["docs_url"] for g in listing["gateways"]),
              str([g["id"] for g in listing["gateways"] if not g["docs_url"]]))
        check("a gateway the operator has not touched reports ready=false, not an error",
              all(not g["ready"] for g in listing["gateways"]),
              "no keys in the environment")

        # --- the resolver: settings -> environment -> registry default --------
        check("with no key anywhere the resolver falls back to the default gateway",
              gw_mod.active_id() == "opencode-go", gw_mod.active_id())
        os.environ["GEMINI_API_KEY"] = "env-gemini-key-000000"
        check("a single env key steers the active gateway to that provider",
              gw_mod.active_id() == "gemini", gw_mod.active_id())
        check("an environment key is reported as env-sourced",
              gw_mod.public_view("gemini")["key_source"] == "env",
              gw_mod.public_view("gemini")["key_source"])

        stored = client.put(
            "/api/admin/settings/gateways/gemini",
            json={"api_key": "stored-gemini-key-abcdef", "model": "gemini-2.5-pro"},
            headers=MUT).json()
        check("a pasted key is stored and reported as settings-sourced (beats the env)",
              stored["has_key"] and stored["key_source"] == "settings"
              and gw_mod.resolve("gemini")["api_key"] == "stored-gemini-key-abcdef",
              f"source={stored['key_source']}")
        check("the response carries a 4-character hint, never the key",
              stored["key_hint"] == "\u2026cdef"
              and "stored-gemini-key-abcdef" not in json.dumps(stored),
              f"hint={stored['key_hint']!r}")
        check("no endpoint in the whole surface leaks a stored key",
              "stored-gemini-key-abcdef"
              not in client.get("/api/admin/settings/gateways", headers=MUT).text,
              "the list view is clean")

        # --- switching the active gateway ------------------------------------
        no_key = client.post("/api/admin/settings/gateways/active",
                             json={"gateway_id": "openrouter"}, headers=MUT)
        check("switching to a keyless gateway is refused with the reason (400)",
              no_key.status_code == 400 and "OPENROUTER_API_KEY" in no_key.json()["detail"],
              str(no_key.json().get("detail"))[:90])
        client.put("/api/admin/settings/gateways/openrouter",
                   json={"api_key": "sk-or-v1-000000000000"}, headers=MUT)
        no_model = client.post("/api/admin/settings/gateways/active",
                               json={"gateway_id": "openrouter"}, headers=MUT)
        check("a gateway with a key but no model is refused too (400)",
              no_model.status_code == 400 and "model" in no_model.json()["detail"],
              str(no_model.json().get("detail"))[:90])
        client.put("/api/admin/settings/gateways/openrouter",
                   json={"model": "openai/gpt-5"}, headers=MUT)
        switched = client.post("/api/admin/settings/gateways/active",
                               json={"gateway_id": "openrouter"}, headers=MUT)
        check("switching to a ready gateway takes effect immediately",
              switched.status_code == 200 and switched.json()["active"] == "openrouter"
              and switched.json()["effective"]["model"] == "openai/gpt-5",
              str(switched.json()["effective"]))
        check("switching needs no restart: resolve() reads the store per call",
              gw_mod.resolve()["gateway_id"] == "openrouter"
              and gw_mod.resolve()["base_url"] == "https://openrouter.ai/api/v1",
              gw_mod.resolve()["base_url"])
        check("an unknown gateway id is a 404, not a silent no-op",
              client.post("/api/admin/settings/gateways/active",
                          json={"gateway_id": "nope"}, headers=MUT).status_code == 404
              and client.get("/api/admin/settings/gateways/nope", headers=MUT).status_code == 404,
              "404 on both")

        # --- validation, clearing, and the file boundary ----------------------
        check("a non-http base URL is refused",
              client.put("/api/admin/settings/gateways/openrouter",
                         json={"base_url": "file:///etc/passwd"},
                         headers=MUT).status_code == 400, "400")
        check("a base URL carrying credentials is refused",
              client.put("/api/admin/settings/gateways/openrouter",
                         json={"base_url": "https://user:pw@host.example/v1"},
                         headers=MUT).status_code == 400, "400")
        check("a base URL with a query string is refused (a key could hide there)",
              client.put("/api/admin/settings/gateways/openrouter",
                         json={"base_url": "https://host.example/v1?key=abc"},
                         headers=MUT).status_code == 400, "400")
        trimmed = client.put("/api/admin/settings/gateways/openrouter",
                             json={"base_url": "https://openrouter.ai/api/v1/"},
                             headers=MUT).json()
        check("a trailing slash on a stored base URL is normalised away",
              trimmed["base_url"] == "https://openrouter.ai/api/v1",
              trimmed["base_url"])
        check("a request body with an invented field is refused, not ignored",
              client.put("/api/admin/settings/gateways/openrouter",
                         json={"api_ky": "oops"}, headers=MUT).status_code == 422, "422")
        client.put("/api/admin/settings/gateways/openrouter",
                   json={"api_key": ""}, headers=MUT)
        cleared = client.put("/api/admin/settings/gateways/openrouter",
                             json={"model": ""}, headers=MUT).json()
        check("clearing an override falls back to the environment, then the default",
              cleared["key_source"] == "none" and cleared["has_key"] is False
              and cleared["model"] == "",
              f"source={cleared['key_source']} model={cleared['model']!r}")
        after_clear = client.post("/api/admin/settings/gateways/active",
                                  json={"gateway_id": "openrouter"}, headers=MUT)
        check("a gateway whose key was cleared can no longer be made active",
              after_clear.status_code == 400, str(after_clear.status_code))
        check("resetting returns to the environment-described default gateway",
              (lambda: (_clear_keys(),
                        client.post("/api/admin/settings/gateways/active/reset",
                                    headers=MUT).json()["active"])[-1])() == "opencode-go",
              "back to OpenCode Go")

        check("the gateway settings live in their own file, not the archive or the founder store",
              str(config.SETTINGS_DB_PATH) not in (str(config.DB_PATH), str(config.FOUNDER_DB_PATH))
              and "gateway_settings" not in table_names(config.DB_PATH)
              and "gateway_settings" not in table_names(config.FOUNDER_DB_PATH),
              str(config.SETTINGS_DB_PATH.name))

        # --- the LLM client actually follows the setting (offline) -----------
        client.put("/api/admin/settings/gateways/openrouter",
                   json={"api_key": "sk-or-v1-wire-check-0001", "model": "openai/gpt-5"},
                   headers=MUT)
        client.post("/api/admin/settings/gateways/active",
                    json={"gateway_id": "openrouter"}, headers=MUT)
        sent: list[dict] = []

        class _StubResponse:
            status_code = 200
            text = ""

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": '{"name": "X"}'}}]}

        def _capture_post(url, **kwargs):
            sent.append({"url": url, **kwargs})
            return _StubResponse()

        _real_post = llm.httpx.post
        llm.httpx.post = _capture_post
        # The SSRF guard resolves the base URL's host, and the real URL here is a
        # public provider — this suite stays offline, so step the guard aside for
        # the URL-shape checks and exercise it for real a few checks below.
        _real_guard = gw_mod.guard_outbound
        gw_mod.guard_outbound = lambda url: None
        # The suite stubs llm.llm_json globally; restore the real one for this
        # check so the request the client actually builds is what gets asserted.
        llm.llm_json = _real_llm_json
        try:
            llm.llm_json("profile this")
        finally:
            llm.llm_json = fake_llm_json
            llm.httpx.post = _real_post
            gw_mod.guard_outbound = _real_guard
        _resolved = gw_mod.resolve()
        check("llm_json calls the ACTIVE gateway's base URL, not a hardcoded one",
              bool(sent) and sent[0]["url"]
              == f"{_resolved['base_url']}/chat/completions",
              str(sent[0]["url"] if sent else None))
        check("the key travels in the Authorization header, never in the URL",
              bool(sent) and sent[0]["headers"]["Authorization"]
              == f"Bearer {_resolved['api_key']}"
              and "?" not in sent[0]["url"],
              "header-only auth")
        check("the active gateway's model is what gets sent",
              bool(sent) and sent[0]["json"]["model"] == _resolved["model"],
              str(sent[0]["json"]["model"] if sent else None))
        _clear_keys()
        # Force the active gateway onto a keyless one through the store (set_active
        # refuses it on purpose — that refusal is asserted above), then read the
        # error the LLM client produces.
        gw_mod._app_setting(gw_mod.ACTIVE_KEY, "opencode-zen")
        _keyless_msg = ""
        try:
            llm._client_config()
        except RuntimeError as exc:
            _keyless_msg = str(exc)
        gw_mod._app_setting(gw_mod.ACTIVE_KEY, "")
        check("a gateway with no key fails loudly and names its env var",
              "OpenCode Zen" in _keyless_msg and "OPENCODE_ZEN_API_KEY" in _keyless_msg,
              _keyless_msg[:120] or "no error raised")

        # --- the test button is a result, never a 500, and never a network
        #     call when there is nothing to test -------------------------------
        _tripwire_calls: list = []
        _real_post2 = llm.httpx.post

        def _tripwire_post(url, **kwargs):
            _tripwire_calls.append(url)
            raise AssertionError("test_gateway made an outbound call with no key")

        llm.httpx.post = _tripwire_post
        try:
            keyless = client.post("/api/admin/settings/gateways/opencode-zen/test",
                                  headers=MUT)
        finally:
            llm.httpx.post = _real_post2
        check("testing a keyless gateway is a structured result, not a 500",
              keyless.status_code == 200 and keyless.json()["ok"] is False
              and "no API key" in keyless.json()["error"],
              str(keyless.json().get("error"))[:60])
        check("a keyless test never reaches the network",
              not _tripwire_calls, f"{len(_tripwire_calls)} outbound call(s)")
        check("testing an unknown gateway is a 404",
              client.post("/api/admin/settings/gateways/nope/test",
                          headers=MUT).status_code == 404, "404")

        # --- the SSRF guard on the outbound call ----------------------------
        # A gateway's base URL is admin-settable, so the request that carries a
        # stored key must not be able to reach a loopback / private / metadata
        # target. Both the Test button and llm_json go through one guard.
        _refused_without_flag = False
        try:
            gw_mod.guard_outbound("http://127.0.0.1:9/v1")
        except netguard_mod.BlockedAddressError:
            _refused_without_flag = True
        check("the guard refuses a loopback base URL by default",
              _refused_without_flag, "default posture is deny")

        _real_flag = config.ALLOW_PRIVATE_LLM_BASE
        _optin_ok = False
        config.ALLOW_PRIVATE_LLM_BASE = True
        try:
            gw_mod.guard_outbound("http://127.0.0.1:9/v1")   # must not raise
            _optin_ok = True
        except Exception:  # noqa: BLE001 — any raise means the opt-in did not work
            _optin_ok = False
        finally:
            config.ALLOW_PRIVATE_LLM_BASE = _real_flag
        check("ALLOW_PRIVATE_LLM_BASE=1 steps aside for a deliberately local model server",
              _optin_ok, "opt-in honoured, and only when set")

        _sockets: list = []
        _real_post3 = llm.httpx.post

        def _socket_tripwire(url, **kwargs):
            _sockets.append(url)
            raise AssertionError(f"the LLM path opened a socket to {url!r}")

        llm.httpx.post = _socket_tripwire
        try:
            client.put("/api/admin/settings/gateways/openrouter",
                       json={"api_key": "***", "base_url": "http://localhost:9/v1"},
                       headers=MUT)
            _blocked_test = client.post("/api/admin/settings/gateways/openrouter/test", headers=MUT)
            llm.llm_json = _real_llm_json
            gw_mod._app_setting(gw_mod.ACTIVE_KEY, "openrouter")
            _blocked_msg = ""
            try:
                llm.llm_json("profile this")
            except RuntimeError as exc:
                _blocked_msg = str(exc)
            finally:
                llm.llm_json = fake_llm_json
                gw_mod._app_setting(gw_mod.ACTIVE_KEY, "")
        finally:
            llm.httpx.post = _real_post3
        check("the Test button reports a blocked base URL as a result, not a 500",
              _blocked_test.status_code == 200 and _blocked_test.json()["ok"] is False
              and "SSRF guard" in _blocked_test.json()["error"],
              str(_blocked_test.json().get("error"))[:90])
        check("llm_json refuses the same target with a clear RuntimeError",
              "SSRF guard" in _blocked_msg, _blocked_msg[:90] or "no error raised")
        check("neither path opens a socket to the blocked target",
              not _sockets, f"{len(_sockets)} socket(s)")

        cleared = client.put("/api/admin/settings/gateways/openrouter",
                             json={"base_url": "", "api_key": ""}, headers=MUT).json()
        check("the override clears again and the gateway falls back to its default",
              cleared["base_url"] == cleared["default_base_url"],
              str(cleared["base_url"]))
finally:
    for _k, _v in _saved_env.items():
        if _v is None:
            os.environ.pop(_k, None)
        else:
            os.environ[_k] = _v

# ===========================================================================
print("\n" + "=" * 78)
_passed = _total - len(_fails)
if _fails:
    print(f"RESULT: {len(_fails)} FAILED -> {_fails}")
else:
    print("RESULT: ALL PASS")
print(f"TESTS: {_total} run, {_passed} passed, {len(_fails)} failed")
raise SystemExit(1 if _fails else 0)
