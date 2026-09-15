"""Phase 3 exit-gate verifier — comparison, gap table & export.

Covers: F-15 (the gap table, five bands), F-16 (the three exports, stateless and
deterministic), F-17 (the stable slug endpoint and its collision rule), F-21 (the
two trust badges, explicit and claim-free), the F-13 compare guard, the F-22 JIT
wiring it triggers, and the posture that the founder store never leaks.

Safety, following the Phase 1/2 verifiers' pattern:

  * the LIVE archive is never opened for writing — every check runs against a
    copy made with SQLite's own backup API (the archive is in WAL mode, so a raw
    file copy can miss writes still sitting in the -wal file);
  * the founder store is a fresh throwaway file, not backend/data/founder.db;
  * the fetcher and BOTH LLM prompts are stubbed, so nothing touches the network.

Usage (from the repo root, venv python):
    backend\\.venv\\Scripts\\python.exe scripts\\phase3-verify.py
"""
import csv
import io
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATA = BACKEND / "data"
LIVE = DATA / "ideasexist.db"
ARCHIVE_COPY = DATA / "ideasexist.db.phase3-test"
FOUNDER_COPY = DATA / "founder.db.phase3-test"

SITE = "https://acme.example"
SITE_JIT = "https://jit-compare.example"
TOKEN = "phase3-admin-token"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def sqlite_backup(src: Path, dst: Path) -> None:
    """SQLite's own backup API, never a file copy (WAL mode)."""
    for stale in (dst, Path(str(dst) + "-wal"), Path(str(dst) + "-shm")):
        if stale.exists():
            stale.unlink()
    s = sqlite3.connect(str(src))
    d = sqlite3.connect(str(dst))
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def drop(path: Path) -> None:
    for stale in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if stale.exists():
            stale.unlink()


print("=" * 78)
print("Phase 3 — comparison, gap table & export: exit-gate verification")
print("=" * 78)

check("live archive present", LIVE.exists(), str(LIVE))
if not LIVE.exists():
    print("\nRESULT: 1 FAILED -> ['live archive present']")
    sys.exit(1)

# --- 0. throwaway copies + env BEFORE importing app (config reads env at import) ---
sqlite_backup(LIVE, ARCHIVE_COPY)
drop(FOUNDER_COPY)
os.environ["DB_PATH"] = str(ARCHIVE_COPY)
os.environ["FOUNDER_DB_PATH"] = str(FOUNDER_COPY)
os.environ["ADMIN_TOKEN"] = TOKEN
os.environ["MUTATION_AUTH"] = "1"
os.environ["RATE_LIMIT_ENABLED"] = "0"       # endpoint flakiness is not this phase's subject
os.environ["VERIFY_AUTO_STALE_DAYS"] = "0"   # no auto-verify pass running behind our back
os.environ.pop("REVIEW_SOURCES", None)

sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db  # noqa: E402
from app import capture, compare as cmp, evidence as ev, founder, llm, seeder  # noqa: E402
from app import website as ws_mod  # noqa: E402
from app.main import app as api  # noqa: E402

check("the verifier is pointed at a copy, not the live archive",
      str(config.DB_PATH).endswith("ideasexist.db.phase3-test"), str(config.DB_PATH))
check("the verifier is pointed at a throwaway founder store",
      str(config.FOUNDER_DB_PATH).endswith("founder.db.phase3-test"), str(config.FOUNDER_DB_PATH))

# --- stubs: one fetcher, one LLM, no network anywhere ---
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

FIXTURE: dict[str, tuple[int, str]] = {
    SITE: (200, HOMEPAGE_HTML),
    SITE + "/pricing": (200, PRICING_HTML),
    SITE + "/docs": (200, DOCS_HTML),
    SITE_JIT: (200, HOMEPAGE_HTML.replace("acme.example", "jit-compare.example")),
    SITE_JIT + "/pricing": (200, PRICING_HTML),
    SITE_JIT + "/docs": (200, DOCS_HTML),
}

# Two reviews, each with one clean ask: "native mobile app" (neither side covers)
# and "public API" (the founder's declared features cover it).
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
    ]}
})


class _Resp:
    def __init__(self, url, status, text, content_type="text/html"):
        self.url = url
        self.status_code = status
        self.text = text
        self.headers = {"content-type": content_type}


def fake_fetch(url, **kwargs):
    """The only way out to the network in this script: a lookup table."""
    if url.startswith("https://www.reddit.com/search"):
        return _Resp(url, 200, REDDIT_BODY, "application/json")
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
    ]},
    "negatives": [
        # A duplicate of the deterministic self-host probe — dropped.
        {"claim": "no self-host", "observed_on": SITE + "/pricing",
         "why": "pricing page lists no self-host tier"},
        # Cites a page we read and that enumerates -> survives.
        {"claim": "no real-time collaboration", "observed_on": SITE + "/docs",
         "why": "the docs index lists no collaboration section"},
        # A GUESSED url that was never fetched -> dropped by validate().
        {"claim": "no offline mode", "observed_on": SITE + "/api",
         "why": "the guessed /api URL 404s"},
    ],
}

IDENTITY_FIXTURE = {
    "name": "Acme Notes",
    "tagline": "local-first notes for small teams",
    "description": "Acme Notes is a private note app for small teams.",
    "category": "productivity",
    "founded": None,
}


def fake_llm_json(user_content, max_tokens=8000, timeout=180.0, system_prompt=None):
    if system_prompt == llm.TEARDOWN_SYSTEM_PROMPT:
        return json.loads(json.dumps(TEARDOWN_FIXTURE))
    return dict(IDENTITY_FIXTURE)


llm.llm_json = fake_llm_json
ws_mod.wayback_first_snapshot = lambda domain: None
ws_mod.rdap_registration_date = lambda domain: None
import app.netguard as netguard_mod  # noqa: E402

netguard_mod.safe_get = fake_fetch


def insert_startup(name: str, website_url: str, **cols) -> int:
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


def row_of(startup_id: int):
    conn = db.connect()
    try:
        return conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
    finally:
        conn.close()


def row_of_fid(founder_app_id: int):
    """The founder record, read back from the founder store."""
    return founder.get(founder_app_id)


def archive_count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
    finally:
        conn.close()


def find(table: dict, band: str, dimension=None, you_has=None):
    for r in table.get(band) or []:
        if dimension and r["dimension"] != dimension:
            continue
        if you_has and you_has not in r["you"].lower():
            continue
        return r
    return None


def wait_capture_job(startup_id: int, timeout: float = 8.0):
    """Wait for the capture job keyed to a competitor to leave the queue."""
    key = capture.key_for(startup_id)
    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = [j for j in seeder.JOBS.values()
                if j.get("kind") == "capture" and j.get("key") == key]
        if jobs and all(j["status"] in ("done", "failed") for j in jobs):
            return jobs
        time.sleep(0.03)
    return []


with TestClient(api) as client:
    base_count = archive_count()

    # =====================================================================
    # 1. Build the fixtures: a captured competitor and a confirmed founder app
    # =====================================================================
    print("\n--- fixtures: one captured competitor, one confirmed founder app ---")
    comp_id = insert_startup("Acme Notes", SITE)
    capture.capture_teardown(comp_id, fetcher=fake_fetch,
                             llm_fn=lambda brief: TEARDOWN_FIXTURE)
    comp_neg_rows = ev.for_startup(db.connect(), comp_id, "negative")
    check("the competitor fixture carries a real captured teardown",
          bool(ev.count_for_startup(db.connect(), comp_id).get("feature")),
          str(ev.count_for_startup(db.connect(), comp_id)))

    form_payload = {
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
    draft = client.post("/api/founder-app", json=form_payload).json()
    fid = draft["founder_app_id"]
    check("the founder draft starts unconfirmed (F-13)", draft["confirmed"] is False, str(draft["confirmed"]))

    # =====================================================================
    # 2. F-13 — compare refuses an unconfirmed founder app, explicitly
    # =====================================================================
    print("\n--- F-13: the gap table never runs against an unconfirmed draft ---")
    unconfirmed = client.post("/api/compare", json={"you": {"id": fid},
                                                    "competitors": [{"id": comp_id}]})
    detail = unconfirmed.json().get("detail")
    check("compare refuses an unconfirmed app with an explicit not-confirmed state (F-13)",
          unconfirmed.status_code == 409 and isinstance(detail, dict)
          and detail.get("state") == "not_confirmed" and "confirm" in detail.get("message", ""),
          f"{unconfirmed.status_code}: {detail}")

    client.post(f"/api/founder-app/{fid}/confirm")

    # =====================================================================
    # 3. F-15 — the gap table bands
    # =====================================================================
    print("\n--- F-15: the five bands, correct for the fixture ---")
    resp = client.post("/api/compare", json={"you": {"id": fid}, "competitors": [{"id": comp_id}]})
    check("compare returns the table once the competitor is cached (F-15/F-22)",
          resp.status_code == 200 and "you_have_they_dont" in resp.json(),
          f"{resp.status_code}")
    table = resp.json()

    you_only = find(table, cmp.BAND_YOU_HAVE, cmp.DIM_FEATURES, you_has="public api")
    check("a capability only 'you' have lands in you_have_they_dont (F-15)",
          you_only is not None and you_only["source"], str(you_only))
    check("…and that edge traces to the competitor's enumerating page (F-09/F-15)",
          you_only is not None and you_only["source"] == SITE + "/docs",
          str(you_only and you_only["source"]))

    them_only = find(table, cmp.BAND_THEY_HAVE, cmp.DIM_FEATURES, you_has="not offered")
    check("a capability only 'they' have lands in they_have_you_dont (F-15)",
          them_only is not None and them_only["source"], str(them_only))

    both = None
    for r in table[cmp.BAND_BOTH]:
        if r["dimension"] == cmp.DIM_FEATURES and "markdown" in r["them"].lower():
            both = r
    check("a capability both have lands in both_have (F-15)", both is not None and both["source"],
          str(both))

    # No data on either side -> unknown: a you-only capability against a
    # competitor with no teardown at all.
    bare_id = insert_startup("Bare Compare Co", "https://bare-compare.example")
    conn = db.connect()
    try:
        bare_table = cmp.build_table(row_of_fid(fid), [row_of(bare_id)], conn)
    finally:
        conn.close()
    unknown_feature = find(bare_table, cmp.BAND_UNKNOWN, cmp.DIM_FEATURES, you_has="public api")
    check("missing data on either side is shown as unknown, never scored (F-15)",
          unknown_feature is not None and unknown_feature["them"].lower().startswith("unknown"),
          str(unknown_feature))
    check("the activity row is unknown — the 'you' side has no liveness signal (dim 6)",
          all(r["band"] == cmp.BAND_UNKNOWN for r in table["rows"]
              if r["dimension"] == cmp.DIM_ACTIVITY),
          str([r["band"] for r in table["rows"] if r["dimension"] == cmp.DIM_ACTIVITY]))

    # =====================================================================
    # 4. Cell rules — sourced or unknown; no verdicts; negatives enumerated
    # =====================================================================
    print("\n--- cell rules: every 'they' cell sourced, negatives enumerated ---")
    sourced_bands = (cmp.BAND_YOU_HAVE, cmp.BAND_THEY_HAVE, cmp.BAND_BOTH, cmp.BAND_ASKED_FOR)
    unsourced = [(r["band"], r["dimension"]) for r in table["rows"]
                 if r["band"] in sourced_bands and not r["source"]]
    check("every non-unknown 'they' cell carries a source (cell rule 1)", not unsourced, str(unsourced))
    check("every row is exactly {dimension, band, you, them, source, captured_at}",
          all(set(r) == {"dimension", "band", "you", "them", "source", "captured_at"}
              for r in table["rows"]),
          str(sorted({k for r in table["rows"] for k in r})))
    check("no verdict line is emitted (cell rule 5 / §8.3)",
          not any(w in json.dumps(table).lower() for w in ("you should", "you will beat", "recommend")),
          "no 'you should'/'you will beat'/'recommend' anywhere")

    dim5 = [r for r in table["rows"] if r["dimension"] == cmp.DIM_DOESNT_DO]
    check("the negative list only contains observations that trace to an enumerating page (F-09)",
          bool(dim5) and all(r["source"] for r in dim5)
          and not any("/api" in r["source"] or "/self-host" in r["source"] for r in dim5),
          str(sorted({r["source"] for r in dim5})))
    check("a sourced negative whose capability you cover is an edge (dim 5)",
          find(table, cmp.BAND_YOU_HAVE, cmp.DIM_DOESNT_DO) is not None,
          str(find(table, cmp.BAND_YOU_HAVE, cmp.DIM_DOESNT_DO)))

    # An unsourced "doesn't do" cell renders unknown, never "no".
    orphan_id = insert_startup("Orphan Negative Co", "https://orphan-neg.example")
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO evidence (startup_id, evidence_type, source_url, captured_at, "
            "claim, value, provenance, confidence) VALUES (?,?,?,?,?,?,?,?)",
            (orphan_id, "negative", "", "2026-09-15 00:00:00", "no self-host",
             "observed: x", "machine_drafted", 0.8),
        )
        conn.commit()
        orphan_table = cmp.build_table(row_of_fid(fid), [row_of(orphan_id)], conn)
    finally:
        conn.close()
    orphan_row = next((r for r in orphan_table["rows"]
                       if r["dimension"] == cmp.DIM_DOESNT_DO), None)
    check("an unsourced doesn't-do cell renders unknown, never 'no' (cell rule 2)",
          orphan_row is not None and orphan_row["band"] == cmp.BAND_UNKNOWN
          and orphan_row["them"].lower().startswith("unknown"),
          str(orphan_row))

    # =====================================================================
    # 5. Dimension 7 — asks
    # =====================================================================
    print("\n--- dimension 7: what their users ask for (from reviews) ---")
    asks_rows = [r for r in table["rows"] if r["dimension"] == cmp.DIM_ASKS]
    check("a reviewer ask neither side covers lands in asked_for (dim 7)",
          find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS) is not None
          and "reviewer" in find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS)["them"],
          str(find(table, cmp.BAND_ASKED_FOR, cmp.DIM_ASKS)))
    covered_ask = find(table, cmp.BAND_YOU_HAVE, cmp.DIM_ASKS)
    check("the same ask, when your declared features cover it, lands in you_have_they_dont (dim 7)",
          covered_ask is not None and "declared" in covered_ask["you"],
          str(covered_ask))
    check("every ask links to the review it came from (F-23 → dim 7)",
          bool(asks_rows) and all(r["source"].startswith("https://www.reddit.com/r/") for r in asks_rows),
          str(sorted({r["source"] for r in asks_rows})))

    # =====================================================================
    # 6. F-16 — the three exports, stateless and deterministic
    # =====================================================================
    print("\n--- F-16: markdown / json / csv, stateless and deterministic ---")
    params = {"you": str(fid), "competitors": str(comp_id)}
    md = client.get("/api/export/markdown", params=params)
    js = client.get("/api/export/json", params=params)
    cv = client.get("/api/export/csv", params=params)
    check("all three exports answer 200 (F-16)",
          md.status_code == js.status_code == cv.status_code == 200,
          f"{md.status_code}/{js.status_code}/{cv.status_code}")

    md_text = md.text
    labels = [cmp.BAND_LABELS[b] for b in
              (cmp.BAND_YOU_HAVE, cmp.BAND_THEY_HAVE, cmp.BAND_BOTH, cmp.BAND_ASKED_FOR)]
    check("Markdown has the four groups incl. the demand group (F-16)",
          all(f"## {label}" in md_text for label in labels),
          str([label for label in labels if f"## {label}" not in md_text]))

    js_data = json.loads(js.text)
    check("JSON is re-processable: {you, them, rows} with the right row keys (F-16)",
          set(js_data) >= {"you", "them", "rows"} and isinstance(js_data["rows"], list)
          and all({"dimension", "you", "them", "source", "band"} <= set(r) for r in js_data["rows"]),
          str(sorted(js_data)))
    check("JSON 'you' is the ONE founder record the caller named (F-16 / no leak)",
          js_data["you"]["name"] == "Loom-note" and js_data["you"]["founder_app_id"] == fid,
          str(js_data["you"].get("name")))

    csv_rows = list(csv.reader(io.StringIO(cv.text)))
    check("CSV has the exact columns band, dimension, you, them, source_url, captured_at (F-16)",
          csv_rows[0] == ["band", "dimension", "you", "them", "source_url", "captured_at"],
          str(csv_rows[0]))
    check("CSV carries asked_for as a band value (F-16)",
          any(rw[0] == "asked_for" for rw in csv_rows[1:]),
          str(sorted({rw[0] for rw in csv_rows[1:]})))

    md2 = client.get("/api/export/markdown", params=params).text
    js2 = client.get("/api/export/json", params=params).text
    cv2 = client.get("/api/export/csv", params=params).text
    check("re-running an export with the same inputs gives the same bytes (F-16 stateless+deterministic)",
          md.text == md2 and js.text == js2 and cv.text == cv2,
          "markdown/json/csv all byte-identical across two calls")

    # =====================================================================
    # 7. F-17 — the slug endpoint and its collision rule
    # =====================================================================
    print("\n--- F-17: the stable slug endpoint ---")
    known = client.get("/api/startups/acme-notes")
    check("a known product resolves by slug (F-17)",
          known.status_code == 200
          and cmp.slugify(known.json()["resolved_name"]) == "acme-notes",
          f"{known.status_code} {known.json().get('resolved_name') if known.status_code == 200 else ''}")
    missing = client.get("/api/startups/this-slug-does-not-exist-zzz")
    check("an unknown slug is a clean 404 (F-17)", missing.status_code == 404, str(missing.status_code))

    # A REAL duplicate group from the archive copy, resolved deterministically.
    conn = db.connect()
    try:
        groups: dict[str, list] = {}
        for r in conn.execute("SELECT id, name, verified FROM startups").fetchall():
            groups.setdefault(cmp.slugify(r["name"]), []).append(dict(r))
    finally:
        conn.close()
    dup_slug = next((s for s, rows in groups.items() if len(rows) > 1 and s), None)
    dup_rows = groups.get(dup_slug or "", [])
    expected = min(dup_rows, key=lambda r: (0 if r["verified"] == 1 else 1, r["id"])) if dup_rows else None
    dup_resp = client.get(f"/api/startups/{dup_slug}") if dup_slug else None
    check("a real same-name group resolves deterministically: verified first, then lowest id (F-17)",
          dup_resp is not None and dup_resp.status_code == 200
          and dup_resp.json()["resolved_id"] == expected["id"]
          and len(dup_resp.json()["duplicate_group"]) == len(dup_rows),
          f"slug={dup_slug} got={dup_resp.json()['resolved_id'] if dup_resp and dup_resp.status_code == 200 else None} "
          f"expected={expected['id'] if expected else None} group={len(dup_rows)}")

    # =====================================================================
    # 8. F-21 — explicit, claim-free trust badges
    # =====================================================================
    print("\n--- F-21: admin_verified / machine_verified are explicit fields ---")
    stale_id = insert_startup("Badge Stale Co", "https://badge-stale.example")
    conn = db.connect()
    try:
        conn.execute(
            "UPDATE startups SET verified = 1, verified_at = '2026-01-01 00:00:00', "
            "status = 'active', check_failures = 0, "
            "last_checked = datetime('now', '-200 days') WHERE id = ?", (stale_id,),
        )
        conn.commit()
    finally:
        conn.close()
    stale = client.get("/api/startups/badge-stale-co").json()
    check("a stale last_checked reads machine_verified=false while admin_verified stays true (F-21)",
          stale["machine_verified"] is False and stale["admin_verified"] is True,
          f"machine={stale['machine_verified']} admin={stale['admin_verified']} at={stale['machine_verified_at']}")

    fresh_id = insert_startup("Badge Fresh Co", "https://badge-fresh.example")
    conn = db.connect()
    try:
        conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now'), status = 'active', "
            "check_failures = 0, last_checked = datetime('now') WHERE id = ?", (fresh_id,),
        )
        conn.commit()
    finally:
        conn.close()
    fresh = client.get("/api/startups/badge-fresh-co").json()
    check("a fresh check reads machine_verified=true (F-21)", fresh["machine_verified"] is True, str(fresh["machine_verified"]))
    check("the badges are explicit fields, never inferred from a raw timestamp (F-21)",
          {"admin_verified", "admin_verified_at", "machine_verified", "machine_verified_at"} <= set(fresh),
          str(sorted(set(fresh) & {"admin_verified", "admin_verified_at", "machine_verified", "machine_verified_at"})))
    check("no badge is emitted inside a claim/row cell (F-21 / §8.1)",
          all(not ({"admin_verified", "machine_verified"} & set(r)) for r in table["rows"])
          and "machine verified" not in md_text.lower() and "admin verified" not in md_text.lower(),
          "badges live on the record payload only")

    # =====================================================================
    # 9. The founder store never leaks into the archive surface
    # =====================================================================
    print("\n--- no founder leak: archive endpoints never see the founder store ---")
    listed = client.get("/api/startups").json()
    names = {r["name"] for r in listed}
    stats = client.get("/api/stats").json()
    cats = client.get("/api/categories").json()
    check("no founder record appears in /api/startups", "Loom-note" not in names, str("Loom-note" in names))
    check("no founder record is counted by /api/stats", stats["total"] == archive_count(),
          f"{stats['total']} vs {archive_count()}")
    check("no founder record appears in /api/categories",
          not any(c["category"] == "productivity" and c["count"] == 0 for c in cats) and bool(cats),
          str(cats[:2]))
    check("the two stores are two files, each with its own schema (F-10/F-20)",
          str(config.FOUNDER_DB_PATH) != str(config.DB_PATH)
          and not db.connect().execute(
              "SELECT name FROM sqlite_master WHERE name='founder_apps'").fetchone()
          and not founder.connect().execute(
              "SELECT name FROM sqlite_master WHERE name='startups'").fetchone(),
          "founder_apps absent from the archive; startups absent from the founder store")

    # =====================================================================
    # 10. F-22 — the JIT wiring the compare endpoint triggers
    # =====================================================================
    print("\n--- F-22: /api/compare triggers the just-in-time capture ---")
    jit_id = insert_startup("Jit Compare Co", SITE_JIT)
    queued = client.post("/api/compare", json={"you": {"id": fid}, "competitors": [{"id": jit_id}]})
    check("a never-captured competitor returns the queued/retry state, not a partial teardown (F-22)",
          queued.status_code == 200 and queued.json().get("state") in ("queued", "in_progress")
          and bool(queued.json().get("message")) and "both_have" not in queued.json(),
          f"{queued.status_code}: {queued.json().get('state')} / {queued.json().get('message')}")
    wait_capture_job(jit_id)
    served = client.post("/api/compare", json={"you": {"id": fid}, "competitors": [{"id": jit_id}]})
    check("once captured, the same call returns the table (F-22)",
          served.status_code == 200 and "both_have" in served.json(),
          f"{served.status_code}: {list(served.json())[:4]}")

    # two concurrent requests, one job (the callable the endpoint wires)
    conc_id = insert_startup("Jit Concurrent Co", SITE_JIT + "-two")
    FIXTURE[SITE_JIT + "-two"] = (200, HOMEPAGE_HTML.replace("acme.example", "jit-compare.example-two"))
    FIXTURE[SITE_JIT + "-two" + "/pricing"] = (200, PRICING_HTML)
    FIXTURE[SITE_JIT + "-two" + "/docs"] = (200, DOCS_HTML)
    release = threading.Event()
    started = threading.Event()
    real_teardown = capture.capture_teardown

    def blocking_teardown(startup_id, **kwargs):
        started.set()
        release.wait(10)
        return {"state": "captured", "startup_id": startup_id}

    capture.capture_teardown = blocking_teardown
    try:
        first = capture.start_capture(conc_id)
        began = started.wait(5)
        second = capture.start_capture(conc_id)
        jobs = [j for j in seeder.JOBS.values()
                if j.get("kind") == "capture" and j.get("key") == capture.key_for(conc_id)]
        check("two concurrent captures of one competitor produce exactly one job (F-22)",
              began and len(jobs) == 1 and first["state"] == "queued",
              f"jobs={len(jobs)} first={first['state']} second={second['state']}")
        check("an in-flight capture returns an explicit retry state (F-22)",
              second["state"] == "in_progress" and second["message"] == capture.CAPTURE_IN_PROGRESS,
              str(second))
        release.set()
        deadline = time.time() + 5
        while time.time() < deadline and not all(j["status"] in ("done", "failed") for j in jobs):
            time.sleep(0.02)
    finally:
        release.set()
        capture.capture_teardown = real_teardown

    # =====================================================================
    # 11. sample dump for the ledger
    # =====================================================================
    print("\n--- sample gap table (the ledger's raw evidence) ---")
    print(f"  you  = {table['you']['name']}  (founder_app_id={fid})")
    print(f"  them = {[c['name'] for c in table['competitors']]}")
    for band in cmp.BANDS:
        rows = table[band]
        print(f"  [{band}] {len(rows)} row(s)")
        for r in rows[:3]:
            print(f"     {r['dimension']:<24} you={r['you'][:34]:<36} them={r['them'][:36]:<38} "
                  f"src={r['source'][:40]}")
    print(f"  negative evidence rows for the competitor: "
          f"{[(r['claim'], r['source_url']) for r in comp_neg_rows]}")
    print("  markdown export (head):")
    for line in md_text.splitlines()[:12]:
        print(f"    {line}")

# --- 12. no frontend file touched -------------------------------------------
names = subprocess.run(
    ["git", "diff", "--name-only", "main..HEAD", "--", "frontend"],
    cwd=str(ROOT), capture_output=True, text=True,
).stdout.split()
dirty = subprocess.run(
    ["git", "status", "--porcelain", "--", "frontend"],
    cwd=str(ROOT), capture_output=True, text=True,
).stdout.split()
check("no frontend/ file was touched in this phase", not names and not dirty,
      f"committed={names} working={dirty}")

print("\n" + "=" * 78)
if failures:
    print(f"RESULT: {len(failures)} FAILED -> {failures}")
    sys.exit(1)
print("RESULT: ALL PASS")
sys.exit(0)
