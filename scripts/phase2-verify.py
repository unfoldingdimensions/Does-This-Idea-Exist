"""Phase 2 exit-gate verifier — enrichment & teardown fields.

Covers: F-06 F-07 F-08 (features / pricing / positioning + evidence rows),
F-09 (the negatives rule), F-10 F-11 F-12 F-13 (the founder app: three paths and
the two gates), F-14 (the teardown carve-out on a re-seed), F-20 (containment),
F-22 (just-in-time capture), F-23 (reviews), F-24 (the submission lifecycle).

Safety, following the Phase 1 verifier's pattern:

  * the LIVE archive is never opened for writing — every check runs against a
    copy made with SQLite's own backup API (the archive is in WAL mode, so a raw
    file copy can miss writes still sitting in the -wal file);
  * the founder store is a fresh throwaway file, not backend/data/founder.db;
  * the fetcher and BOTH LLM prompts are stubbed, so nothing here touches the
    network (the page plan, the founder URL path and the review providers all go
    through the one stubbed fetcher).

Usage (from the repo root, venv python):
    backend\\.venv\\Scripts\\python.exe scripts\\phase2-verify.py
"""
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
ARCHIVE_COPY = DATA / "ideasexist.db.phase2-test"
FOUNDER_COPY = DATA / "founder.db.phase2-test"

SITE = "https://acme.example"
SITE_TWO = "https://acme-two.example"   # same shape, its own row (unique website index)
SITE_WALLED = "https://walled.example"
TOKEN = "phase2-verify-token"
AUTH = {"X-Admin-Token": TOKEN}

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
print("Phase 2 — enrichment & teardown fields: exit-gate verification")
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

from app import config, db, enrich  # noqa: E402
from app import capture, evidence as ev, founder, llm, negatives  # noqa: E402
from app import pages as pages_mod, reviews, seeder, teardown as td, verify  # noqa: E402
from app import website as ws_mod  # noqa: E402
from app.main import app as api  # noqa: E402

check("the verifier is pointed at a copy, not the live archive",
      str(config.DB_PATH).endswith("ideasexist.db.phase2-test"), str(config.DB_PATH))
check("the verifier is pointed at a throwaway founder store",
      str(config.FOUNDER_DB_PATH).endswith("founder.db.phase2-test"), str(config.FOUNDER_DB_PATH))

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
    # A second readable site, so the review checks own a row of their own (the
    # archive's unique index is on website_url, so fixtures cannot share one).
    SITE_TWO: (200, HOMEPAGE_HTML.replace("acme.example", "acme-two.example")),
    SITE_TWO + "/pricing": (200, PRICING_HTML),
    SITE_TWO + "/docs": (200, DOCS_HTML),
    # A site whose enumerating pages refuse us: 403 and an empty shell. Neither
    # may become a negative (F-09) — they become `unknown` at low confidence.
    SITE_WALLED: (200, HOMEPAGE_HTML.replace("acme.example", "walled.example")),
    SITE_WALLED + "/pricing": (403, "<html><body>Access denied</body></html>"),
    SITE_WALLED + "/docs": (200, ""),
}

REDDIT_BODY = json.dumps({
    "data": {"children": [
        {"data": {
            "title": "Love it, but I wish it worked offline",
            "selftext": "The local files are great. I wish it worked without internet on a plane.",
            "permalink": "/r/notes/comments/abc123/love_it/",
            "subreddit": "notes",
            "score": 98765,          # deliberately not stored anywhere
            "ups": 98764,
        }},
        {"data": {
            "title": "Works well for our team",
            "selftext": "We use it every day and it works well.",
            "permalink": "/r/notes/comments/def456/works_well/",
            "score": 98763,
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
    """The only way out to the network in this script: a lookup table."""
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
        {"name": "Malformed", "price": "", "period": "monthly"},   # dropped
        {"name": "HalfFormed", "price": "$3", "period": "whenever"},  # dropped
    ]},
    # One negative cites a page we read; one cites a GUESSED url that was never
    # fetched; one is phrased as our verdict. Only the first may survive.
    "negatives": [
        {"claim": "no real-time collaboration",
         "observed_on": SITE + "/docs", "why": "the docs index lists no collaboration section"},
        {"claim": "no offline mode",
         "observed_on": SITE + "/api", "why": "the guessed /api URL 404s"},
        {"claim": "Acme has no self-host tier",
         "observed_on": SITE + "/pricing", "why": "pricing page lists Free / Pro / Team"},
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


with TestClient(api) as client:
    # =====================================================================
    # 1. Capture against the fixture (F-06 / F-07 / F-08 + evidence rows)
    # =====================================================================
    print("\n--- capture: fixture site through a stubbed fetcher and LLM ---")
    target_id = insert_startup("Acme Notes", SITE)
    result = capture.capture_teardown(target_id, fetcher=fake_fetch, llm_fn=lambda brief: TEARDOWN_FIXTURE)
    row = row_of(target_id)
    features = json.loads(row["features_json"] or "[]")
    pricing = json.loads(row["pricing_json"] or "{}")
    plans = pricing.get("plans") or []
    rows = ev.for_startup(db.connect(), target_id)
    feat_rows = [r for r in rows if r["evidence_type"] == "feature"]
    price_rows = [r for r in rows if r["evidence_type"] == "pricing"]
    neg_rows = [r for r in rows if r["evidence_type"] == "negative"]
    pos_rows = [r for r in rows if r["evidence_type"] == "positioning"]

    check("capture reports state=captured", result.get("state") == "captured", str(result.get("state")))
    check("features_json holds 5-10 items (F-06)",
          5 <= len(features) <= 10, f"{len(features)}: {features}")
    check("pricing_json rows each carry a price and a period (F-07)",
          bool(plans) and all(p.get("price") and p.get("period") in td.PERIODS for p in plans),
          str(plans))
    check("malformed plan rows are dropped, not stored half-formed (F-07)",
          len(plans) == 3 and all(p["name"] not in ("Malformed", "HalfFormed") for p in plans),
          str([p["name"] for p in plans]))
    check("pricing_captured_at is stamped (F-07)", bool(row["pricing_captured_at"]),
          str(row["pricing_captured_at"]))
    check("pricing_source_url is stamped (F-07)",
          row["pricing_source_url"] == SITE + "/pricing", str(row["pricing_source_url"]))
    check("positioning is non-empty (F-08)", bool((row["positioning"] or "").strip()),
          str(row["positioning"]))
    check("one evidence row per feature, each with a source_url (F-06)",
          len(feat_rows) == len(features) and all(r["source_url"] for r in feat_rows),
          f"{len(feat_rows)} rows for {len(features)} features")
    check("one evidence row per pricing plan + the free tier (F-07)",
          len(price_rows) == len(plans) + 1 and all(r["source_url"] == SITE + "/pricing" for r in price_rows),
          f"{len(price_rows)} rows for {len(plans)} plans + free tier")
    check("the positioning line carries its source (F-08)",
          len(pos_rows) == 1 and pos_rows[0]["source_url"] == SITE, str(pos_rows))
    check("provenance is machine_drafted until a human confirms (F-05)",
          row["provenance"] == enrich.MACHINE_DRAFTED, str(row["provenance"]))
    check("every teardown evidence row is machine_drafted",
          all(r["provenance"] == "machine_drafted" for r in rows if r["evidence_type"] in
              ("feature", "pricing", "positioning", "negative", "review")),
          str(sorted({r["provenance"] for r in rows})))
    check("features with fewer than 5 supported items become unknown, never padded",
          td.clean_features(["only one", "and two"]) == [] and td.clean_features([]) == [],
          str(td.clean_features(["only one", "and two"])))

    # =====================================================================
    # 2. Negatives — the strict rule (F-09)
    # =====================================================================
    print("\n--- negatives: deterministic first, LLM second, no verdicts ---")
    neg_claims = [r["claim"] for r in neg_rows]
    neg_sources = {r["source_url"] for r in neg_rows}
    check("a sourced negative traces to an enumerating page (F-09)",
          "no self-host" in neg_claims and SITE + "/pricing" in neg_sources,
          f"{neg_claims} from {sorted(neg_sources)}")
    check("no negative is derived from a guessed URL (F-09)",
          not any("/api" in (s or "") for s in neg_sources)
          and "no offline mode" not in neg_claims,
          str(sorted(neg_sources)))
    check("the LLM's negatives survive only when they trace to a page we read (F-09)",
          "no real-time collaboration" in neg_claims and SITE + "/docs" in neg_sources,
          str(neg_claims))
    check("a deterministic probe wins over the LLM's duplicate of the same fact (F-09)",
          sum(1 for c in neg_claims if "self-host" in (c or "")) == 1, str(neg_claims))
    check("a verdict-shaped claim is rephrased into an observation (F-09)",
          all(not (c or "").lower().startswith(("acme has no", "they have no")) for c in neg_claims),
          str(neg_claims))
    guessed = {"role": "api", "url": SITE + "/api", "state": "unreadable",
               "http_status": 404, "reason": "HTTP 404"}
    check("a 404 on a guessed URL produces nothing at all (F-09)",
          negatives.probe_absence(guessed, "API", why="guessed", hints=negatives.API_HINTS) is None,
          "guessed-record probe returned None")
    check("the page plan never fetches a guessed capability path",
          all(path not in negatives.GUESSED_CAPABILITY_PATHS for _, path in pages_mod.PLAN),
          str(pages_mod.PLAN))
    check("a negative with no enumerating source is refused, not stored",
          negatives.validate({"claim": "no API", "observed_on": ""}, {}) is None
          and negatives.validate({"claim": "no API", "observed_on": SITE + "/api"},
                                 {r: {"role": r, "url": u, "state": "readable", "text": "x"}
                                  for r, u in (("pricing", SITE + "/pricing"),)}) is None,
          "empty source and non-enumerating source both refused")

    # a site whose enumerating pages refuse us: unknown, low confidence
    walled_id = insert_startup("Walled Notes", SITE_WALLED)
    walled = capture.capture_teardown(walled_id, fetcher=fake_fetch, llm_fn=lambda brief: TEARDOWN_FIXTURE)
    walled_rows = ev.for_startup(db.connect(), walled_id)
    walled_negs = [r for r in walled_rows if r["evidence_type"] == "negative"]
    unknowns = [r for r in walled_negs if (r["value"] or "") == "unknown"]
    check("a retrieval failure is unknown with low confidence, never a negative (F-09)",
          bool(unknowns) and all((r["confidence"] or 1) <= 0.1 for r in unknowns),
          f"{len(unknowns)} unknown row(s), conf={[r['confidence'] for r in unknowns]}")
    check("an unreadable page still gets a source_url (the page we tried)",
          all(r["source_url"] for r in walled_negs), str(sorted({r["source_url"] for r in walled_negs})))
    check("no pricing is stored when the pricing page could not be read (F-07)",
          not row_of(walled_id)["pricing_json"] and not row_of(walled_id)["pricing_captured_at"],
          f"pricing_json={row_of(walled_id)['pricing_json']!r}")

    # =====================================================================
    # 3. Reviews (F-23)
    # =====================================================================
    print("\n--- reviews: what their users ask for, never a score ---")
    review_target = insert_startup("Acme Notes Reviews", SITE_TWO)
    review_result = capture.capture_teardown(
        review_target, fetcher=fake_fetch, llm_fn=lambda brief: TEARDOWN_FIXTURE,
        sources=REVIEW_SOURCES)
    review_rows = ev.for_startup(db.connect(), review_target, "review")
    check("one evidence row per review, source_url = the review permalink (F-23)",
          len(review_rows) == 2 and all(r["source_url"].startswith("https://www.reddit.com/r/") for r in review_rows),
          str([r["source_url"] for r in review_rows]))
    check("a walled provider (403) is a skip, not a failure (F-23)",
          review_result.get("reviews_skipped") == 1 and len(review_rows) == 2,
          f"skipped={review_result.get('reviews_skipped')} rows={len(review_rows)}")
    values = [json.loads(r["value"] or "{}") for r in review_rows]
    check("positive and negative are both classified (F-23)",
          {v.get("classification") for v in values} == {"negative", "positive"},
          str([v.get("classification") for v in values]))
    check("no score, aggregate or NPS of our own is stored (F-23)",
          all(set(v) == {"classification", "asks"} for v in values)
          and not any("98765" in (r["value"] or "") for r in review_rows),
          str([sorted(v) for v in values]))
    asks = reviews.asks_from_evidence(db.connect(), review_target)
    check("every extracted ask links to the review it came from (F-23)",
          bool(asks) and all(a["source_url"].startswith("https://www.reddit.com/r/") for a in asks),
          str(asks[:2]))

    # =====================================================================
    # 4. The founder app: three paths, two gates, containment (F-10 … F-13, F-20)
    # =====================================================================
    print("\n--- founder app: three paths, two gates, containment ---")
    base_count = archive_count()
    form_payload = {
        "name": "Founder Co",
        "description": "A note app for solo makers.",
        "target_user": "solo makers who take notes",
        "category": "productivity",
        "features": ["local files", "markdown notes", "quick capture", "backlinks",
                     "sync (paid)", "publish"],
        "positioning": "Notes for solo makers.",
        "pricing": {"free_tier": "Free", "plans": [{"name": "Pro", "price": "$5", "period": "monthly"}]},
        "website_url": "https://founder.example",
    }

    url_app = client.post("/api/founder-app", json={"url": SITE}).json()
    check("URL path drafts the founder's app (F-10)",
          url_app.get("founder_app_id") and url_app["profile"]["name"] == "Acme Notes"
          and url_app.get("confirmed") is False, str(url_app.get("profile", {}).get("name")))
    check("the URL path does not invent the founder's feature list (F-10)",
          url_app["profile"]["features"] == [], str(url_app["profile"]["features"]))

    form_app = client.post("/api/founder-app", json=form_payload).json()
    check("form path drafts a full teardown record (F-11)",
          form_app.get("founder_app_id") and 5 <= len(form_app["profile"]["features"]) <= 10
          and form_app["profile"]["pricing"].get("plans"), str(form_app["profile"]["features"]))

    missing_features = client.post("/api/founder-app", json={**form_payload, "features": None})
    short_features = client.post("/api/founder-app", json={**form_payload, "features": ["a", "b", "c", "d"]})
    check("a form without 5-10 features is a clear 400 (F-11)",
          missing_features.status_code == 400 and "features" in missing_features.json()["detail"]
          and short_features.status_code == 400,
          f"{missing_features.status_code}/{short_features.status_code}: "
          f"{missing_features.json().get('detail')}")

    agent_payload = {
        "name": "Agent Co",
        "description": "Drafted by the founder's own agent.",
        "target_user": "teams that write",
        "category": "devtools",
        "features": ["local files", "public API", "webhooks", "search", "export", "themes"],
        "positioning": "Docs that stay in your repo.",
        "pricing": {"free_tier": "No free tier", "plans": [{"name": "Solo", "price": "$9", "period": "monthly"}]},
        "links": {"website": "https://agent.example", "app_store": "https://apps.apple.com/app/id12345",
                  "play_store": "", "github": ""},
    }
    agent_app = client.post("/api/founder-app", json={"agent_json": json.dumps(agent_payload)})
    check("agent-JSON path drafts the founder's app (F-12)",
          agent_app.status_code == 200 and agent_app.json()["profile"]["app_store_url"].startswith("https://apps.apple.com"),
          str(agent_app.status_code))
    malformed = client.post("/api/founder-app", json={"agent_json": "{not json,"})
    unknown = client.post("/api/founder-app", json={"agent_json": json.dumps({**agent_payload, "invented_field": 1})})
    check("malformed agent JSON is a 400 (F-12)",
          malformed.status_code == 400 and "malformed" in malformed.json()["detail"].lower(),
          str(malformed.json().get("detail"))[:70])
    check("unknown agent keys are a 400, never silently dropped (F-12)",
          unknown.status_code == 400 and "invented_field" in unknown.json()["detail"],
          str(unknown.json().get("detail"))[:90])

    check("nothing the founder path wrote reached the archive (F-20)",
          archive_count() == base_count, f"{base_count} -> {archive_count()}")
    listed = client.get("/api/startups").json()
    names = {r["name"] for r in listed}
    stats = client.get("/api/stats").json()
    cats = client.get("/api/categories").json()
    founder_names = {"Founder Co", "Agent Co", "Linkless Co", "Rejected Co"}
    check("no founder record appears in /api/startups (F-20)",
          not (founder_names & names), str(sorted(founder_names & names)))
    check("no founder record is counted by /api/stats (F-20)",
          stats["total"] == base_count, f"{stats['total']} vs {base_count}")
    check("no founder record appears in /api/categories (F-20)",
          not any(c["category"] == "devtools" and c["count"] > 0 and "Agent Co" in names for c in cats)
          and bool(cats), str(cats[:3]))
    check("the verify walk never sees the founder store (F-20)",
          not ({"Founder Co", "Agent Co"} & {s["name"] for s in verify.list_suggested()}),
          "list_suggested is archive-only")
    check("the two stores are two files, each with its own schema (F-10/F-20)",
          str(config.FOUNDER_DB_PATH) != str(config.DB_PATH)
          and not db.connect().execute(
              "SELECT name FROM sqlite_master WHERE name='founder_apps'").fetchone()
          and not founder.connect().execute(
              "SELECT name FROM sqlite_master WHERE name='startups'").fetchone(),
          "founder_apps is absent from the archive; startups is absent from the founder store")

    # eligibility gate — no link, no consent question
    linkless = client.post("/api/founder-app", json={**form_payload, "name": "Linkless Co",
                                                     "website_url": None}).json()
    check("a link-less submission is comparison-only (F-20)",
          linkless["publish_offered"] is False and linkless["archive_status"] == "local_only"
          and linkless["eligibility"]["has_link"] is False, str(linkless["eligibility"]))
    linkless_publish = client.post(f"/api/founder-app/{linkless['founder_app_id']}/publish")
    check("no consent question is asked when there is no link (F-20)",
          linkless_publish.status_code == 400 and "comparison-only" in linkless_publish.json()["detail"],
          str(linkless_publish.json().get("detail"))[:90])

    # confirm gate + compare guard
    fid = form_app["founder_app_id"]
    try:
        founder.assert_comparable(fid)
        refused = False
        detail = "it allowed an unconfirmed app"
    except ValueError as exc:
        refused = True
        detail = str(exc)[:80]
    check("the compare path refuses an unconfirmed founder app (F-13)", refused, detail)
    confirmed = client.post(f"/api/founder-app/{fid}/confirm").json()
    conn = founder.connect()
    prov = conn.execute("SELECT provenance, confirmed_at FROM founder_apps WHERE id = ?", (fid,)).fetchone()
    conn.close()
    check("confirm flips the record to human_confirmed (F-05/F-13)",
          confirmed["confirmed"] is True and prov["provenance"] == enrich.HUMAN_CONFIRMED
          and bool(prov["confirmed_at"]), f"{prov['provenance']} confirmed_at={prov['confirmed_at']}")
    check("nothing is auto-confirmed by a draft (F-13)",
          form_app["confirmed"] is False and url_app["confirmed"] is False
          and agent_app.json()["confirmed"] is False, "all three drafts start unconfirmed")

    # consent -> pending -> approve -> archive_startup_id
    published = client.post(f"/api/founder-app/{fid}/publish").json()
    check("ticking the opt-in creates a pending submission (F-13/F-24)",
          published["submitted"] is True and published["archive_status"] == "pending",
          str(published))
    queue = client.get("/api/admin/verify/suggested", headers=AUTH).json()
    in_queue = [r for r in queue if r.get("kind") == "founder_submission"]
    check("the admin queue unions founder submissions with the archive's rows (F-24)",
          any(r["founder_app_id"] == fid for r in in_queue) and any(r.get("kind") == "archive" for r in queue),
          f"{len(in_queue)} founder row(s) among {len(queue)} queue rows")
    submission_id = published["submission_id"]
    approved = client.post(f"/api/admin/founder/submissions/{submission_id}/approve", headers=AUTH).json()
    archive_id = approved["archive_startup_id"]
    archived = row_of(archive_id)
    check("approval creates the archive row and links it (F-13/F-24)",
          archived is not None and archived["name"] == "Founder Co",
          f"archive_startup_id={archive_id} name={archived['name'] if archived else None}")
    check("the founder record keeps its own row — the archive got a twin, not the record (F-10)",
          founder.get(fid)["id"] == fid and archive_count() == base_count + 1,
          f"archive {base_count} -> {archive_count()}")
    check("archive_status is derived from the newest submission (F-24)",
          founder.archive_status(fid) == "approved" and "archive_status" not in founder.get(fid),
          str(founder.archive_status(fid)))

    # rejection carries a note; a resubmission is a NEW row
    reject_app = client.post("/api/founder-app", json={**form_payload, "name": "Rejected Co"}).json()
    rid = reject_app["founder_app_id"]
    client.post(f"/api/founder-app/{rid}/confirm")
    first_sub = client.post(f"/api/founder-app/{rid}/publish").json()["submission_id"]
    rejected = client.post(f"/api/admin/founder/submissions/{first_sub}/reject",
                           json={"note": "The site is behind a login, so nothing could be read."},
                           headers=AUTH).json()
    check("a rejection carries a note the founder can read (F-24)",
          rejected["submission"]["status"] == "rejected"
          and "login" in (rejected["submission"]["note"] or ""),
          str(rejected["submission"]["note"])[:60])
    check("a rejection with no note is refused (F-24)",
          client.post(f"/api/admin/founder/submissions/{first_sub}/reject",
                      json={"note": "  "}, headers=AUTH).status_code == 400, "400")
    second_sub = client.post(f"/api/founder-app/{rid}/publish").json()["submission_id"]
    history = founder.decisions(rid)
    check("resubmitting after a rejection creates a NEW row, never an edit (F-24)",
          len(history) == 2 and [h["status"] for h in history] == ["rejected", "pending"]
          and first_sub != second_sub,
          str([(h["id"], h["status"]) for h in history]))
    check("archive_status follows the newest submission (F-24)",
          founder.archive_status(rid) == "pending", founder.archive_status(rid))

    # =====================================================================
    # 5. Just-in-time capture (F-22)
    # =====================================================================
    print("\n--- just-in-time capture: one job per competitor, cached for 7 days ---")
    jit_id = insert_startup("Jit Corp", "https://jit.example")
    release = threading.Event()
    started = threading.Event()
    real_capture_teardown = capture.capture_teardown

    def blocking_teardown(startup_id, **kwargs):
        started.set()
        release.wait(10)
        return {"state": "captured", "startup_id": startup_id}

    capture.capture_teardown = blocking_teardown
    try:
        first = capture.start_capture(jit_id)
        started_now = started.wait(5)
        second = capture.start_capture(jit_id)
        jobs = [j for j in seeder.JOBS.values()
                if j.get("kind") == "capture" and j.get("key") == capture.key_for(jit_id)]
        check("two concurrent captures of one competitor produce exactly one job (F-22)",
              started_now and len(jobs) == 1 and first["state"] == "queued",
              f"jobs={len(jobs)} first={first['state']} second={second['state']}")
        check("an in-flight capture returns an explicit retry state, not a partial teardown (F-22)",
              second["state"] == "in_progress" and second["message"] == capture.CAPTURE_IN_PROGRESS,
              str(second))
        release.set()
        deadline = time.time() + 5
        while time.time() < deadline and not all(
                j["status"] in ("done", "failed") for j in jobs):
            time.sleep(0.02)
        check("the capture job completes and records its result (F-22)",
              jobs and jobs[0]["status"] == "done" and jobs[0]["result"]["state"] == "captured",
              str(jobs[0]["status"] if jobs else None))
    finally:
        release.set()
        capture.capture_teardown = real_capture_teardown

    cached = capture.start_capture(target_id)
    check("a request inside the 7-day window is served from cache (F-22)",
          cached["state"] == "cached" and bool(cached.get("captured_at")), str(cached))

    conn = db.connect()
    conn.execute(
        "UPDATE evidence SET captured_at = datetime('now', '-30 days') "
        "WHERE startup_id = ? AND evidence_type IN ('feature','pricing','positioning','negative','review')",
        (target_id,),
    )
    # The pricing stamp is the second freshness signal, so it ages with the rest.
    conn.execute(
        "UPDATE startups SET pricing_captured_at = datetime('now', '-30 days') WHERE id = ?",
        (target_id,),
    )
    conn.commit()
    conn.close()
    capture.capture_teardown = lambda startup_id, **kwargs: {"state": "captured", "startup_id": startup_id}
    try:
        stale = capture.start_capture(target_id)
        check("a request outside the window re-captures (F-22)",
              stale["state"] in ("queued", "in_progress"), str(stale))
    finally:
        capture.capture_teardown = real_capture_teardown
    check("the freshness window is 7 days, the same rhythm as VERIFY_AUTO_STALE_DAYS (F-22)",
          config.CAPTURE_STALE_DAYS == 7,
          f"CAPTURE_STALE_DAYS={config.CAPTURE_STALE_DAYS} (VERIFY default is also 7; "
          f"this run pins it to {config.VERIFY_AUTO_STALE_DAYS} to keep the network out of the test)")

    # =====================================================================
    # 6. F-14 idempotency kept, with the teardown carve-out
    # =====================================================================
    print("\n--- re-seed: dedup kept, teardown fields not lost ---")
    before = row_of(target_id)
    enrich.seed_from_website(SITE, reuse_profile=True)
    after = row_of(target_id)
    check("a re-seed does not duplicate the row (F-14)",
          row_of(target_id)["id"] == before["id"] and archive_count() >= base_count,
          f"id {before['id']} -> {after['id']}")
    check("a re-seed keeps the teardown fields (F-14 carve-out)",
          after["features_json"] == before["features_json"]
          and after["pricing_json"] == before["pricing_json"]
          and after["positioning"] == before["positioning"]
          and after["pricing_captured_at"] == before["pricing_captured_at"],
          f"features={bool(after['features_json'])} pricing={bool(after['pricing_json'])}")
    conn = db.connect()
    try:
        enrich.mark_human_confirmed(conn, target_id)
    finally:
        conn.close()
    enrich.seed_from_website(SITE, reuse_profile=True)
    check("a re-seed never downgrades human_confirmed (F-14 carve-out)",
          row_of(target_id)["provenance"] == enrich.HUMAN_CONFIRMED,
          str(row_of(target_id)["provenance"]))

    conn = db.connect()
    try:
        try:
            enrich._upsert(conn, {"name": "Twin Co", "website_url": SITE, "source": "website"}, None)
            dedup_refused = False
        except ValueError as exc:
            dedup_refused = "already filed" in str(exc)
    finally:
        conn.close()
    check("a unique-index collision is still a clear ValueError → 400 (F-14)",
          dedup_refused, "duplicate website_url refused")

    # =====================================================================
    # 7. sample dump for the ledger
    # =====================================================================
    print("\n--- sample teardown row (the ledger's raw evidence) ---")
    print("  (this row was aged 30 days by the F-22 window check and human-confirmed by the")
    print("   F-14 check above, which is why pricing_captured_at is a month back and")
    print("   provenance reads human_confirmed rather than machine_drafted)")
    row = row_of(target_id)
    print(f"  startups.id            = {row['id']}  ({row['name']})")
    print(f"  features_json          = {row['features_json']}")
    print(f"  pricing_json           = {row['pricing_json']}")
    print(f"  pricing_captured_at    = {row['pricing_captured_at']}")
    print(f"  pricing_source_url     = {row['pricing_source_url']}")
    print(f"  positioning            = {row['positioning']}")
    print(f"  provenance             = {row['provenance']}")
    print("  evidence rows:")
    for r in ev.for_startup(db.connect(), target_id):
        print(f"    [{r['evidence_type']:<11}] {str(r['claim'])[:52]:<54} "
              f"conf={r['confidence']} src={r['source_url']}")
    frow = founder.get(fid)
    print(f"  founder_apps: id={frow['id']} name={frow['name']!r} source_kind={frow['source_kind']} "
          f"provenance={frow['provenance']} confirmed_at={frow['confirmed_at']}")
    print(f"  founder_submissions: {[(h['status'], h['archive_startup_id'], h['note']) for h in founder.decisions(fid)]}")

# --- 8. no frontend file touched -------------------------------------------
names = subprocess.run(
    ["git", "diff", "--name-only", "phase/01-schema-evidence-foundation..HEAD", "--", "frontend"],
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
