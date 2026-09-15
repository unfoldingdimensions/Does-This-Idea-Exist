"""Phase 4 exit-gate verifier — search classification & match reasons.

Covers F-18: the ladder and its order, the frozen reason vocabulary, dead-last
ordering with stars as a tie-break only, multi-term AND with a worst-term score,
the documented empty-query contract, literal LIKE metacharacters, the pure-read
posture (a search never triggers a capture), the founder-store containment, the
data-awareness rule (an empty column never matches everything), and the
reachable-rung census on a copy of the real archive.

Safety, following the Phase 1/2/3 verifiers' pattern:

  * the LIVE archive is never opened for writing — every check runs against a
    copy made with SQLite's own backup API (the archive is in WAL mode, so a raw
    file copy can miss writes still sitting in the -wal file);
  * the founder store is a fresh throwaway file, not backend/data/founder.db;
  * nothing touches the network: search reads stored data only, and no fixture
    needs a fetcher or an LLM.

Usage (from the repo root, venv python):
    backend\\.venv\\Scripts\\python.exe scripts\\phase4-verify.py
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATA = BACKEND / "data"
LIVE = DATA / "ideasexist.db"
ARCHIVE_COPY = DATA / "ideasexist.db.phase4-test"
FOUNDER_COPY = DATA / "founder.db.phase4-test"

TOKEN = "phase4-token"

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
print("Phase 4 — search classification & match reasons: exit-gate verification")
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

from app import capture, config, db, evidence as ev, seeder  # noqa: E402
from app import search as search_mod  # noqa: E402
from app.main import app as api  # noqa: E402

check("the verifier is pointed at a copy, not the live archive",
      str(config.DB_PATH).endswith("ideasexist.db.phase4-test"), str(config.DB_PATH))
check("the verifier is pointed at a throwaway founder store",
      str(config.FOUNDER_DB_PATH).endswith("founder.db.phase4-test"), str(config.FOUNDER_DB_PATH))


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


def patch_startup(startup_id: int, **cols) -> None:
    conn = db.connect()
    try:
        sets = ", ".join(f"{k} = ?" for k in cols)
        conn.execute(f"UPDATE startups SET {sets} WHERE id = ?", (*cols.values(), startup_id))
        conn.commit()
    finally:
        conn.close()


def archive_rows() -> list[dict]:
    conn = db.connect()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM startups").fetchall()]
    finally:
        conn.close()


def archive_count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
    finally:
        conn.close()


# The tokens the fixtures share, so a single query exercises the whole ladder.
TOKEN_WORD = "zorblat"
DOMAIN = "zorblat.example"


def names_of(payload: list[dict]) -> list[str]:
    return [r["name"] for r in payload]


def reason_of(payload: list[dict], name: str) -> str | None:
    for r in payload:
        if r["name"] == name:
            return r["reason"]
    return None


with TestClient(api) as client:
    total = archive_count()
    print(f"\n[copy] rows={total} columns="
          f"{len([r for r in db.connect().execute('PRAGMA table_info(startups)')])}")

    # The rung census is taken from the PRISTINE copy, before any fixture is
    # inserted — a fixture must never inflate "what the live archive can match".
    _conn = db.connect()
    try:
        def _populated(col: str) -> int:
            return _conn.execute(
                f"SELECT COUNT(*) AS c FROM startups WHERE {col} IS NOT NULL AND TRIM({col}) <> ''"
            ).fetchone()["c"]

        CENSUS = [
            ("exact name", "name", _populated("name")),
            ("exact domain", "website_url (host)", _populated("website_url")),
            ("phrase / name", "name + aliases", _populated("name")),
            ("tagline", "tagline", _populated("tagline")),
            ("problem-description", "description", _populated("description")),
            ("  ↳ (future column)", "problem_statement", _populated("problem_statement")),
            ("  ↳ (future column)", "target_users", _populated("target_users")),
            ("category / keyword", "category", _populated("category")),
            ("  ↳ keyword half", "features_json", _populated("features_json")),
            ("  ↳ keyword half", "positioning", _populated("positioning")),
            ("fuzzy", "the AND gate over the same fields", total),
        ]
    finally:
        _conn.close()

    # =====================================================================
    # 1. Fixtures — one row per rung, all sharing one nonsense token
    # =====================================================================
    print("\n--- fixtures: a row for every rung of the ladder ---")
    fx_exact = insert_startup("Zorblat", "https://zorblat-exact.example")
    fx_name = insert_startup("Zorblat Notes", "https://zorblat-name.example")
    fx_tagline = insert_startup("Tagline Zorb Co", "https://zorblat-tag.example",
                               tagline="A zorblat for teams that write together")
    fx_desc = insert_startup("Desc Zorb Co", "https://zorblat-desc.example",
                             description="The zorblat keeps every note in one place.")
    fx_category = insert_startup("Cat Zorb Co", "https://zorblat-cat.example",
                                 category="zorblat")
    fx_fuzzy = insert_startup("Zorblit", "https://zorblat-fuzzy.example", stars=99999)
    fx_domain = insert_startup("Domain Zorb Co", f"https://{DOMAIN}")
    fx_audience = insert_startup("Audience Zorb Co", "https://zorblat-aud.example",
                                 target_users="zorblat")
    fx_dead = insert_startup("Zorblat Dead", "https://zorblat-dead.example", status="dead")
    fx_pivoted = insert_startup("Zorblat Pivoted", "https://zorblat-piv.example",
                                status="pivoted")
    check("the fixtures were inserted (6 live rungs + domain + audience + 2 tombstones)",
          all((fx_exact, fx_name, fx_tagline, fx_desc, fx_category, fx_fuzzy, fx_domain,
               fx_audience, fx_dead, fx_pivoted)),
          f"ids={[fx_exact, fx_name, fx_tagline, fx_desc, fx_category, fx_fuzzy, fx_domain, fx_audience, fx_dead, fx_pivoted]}")

    # =====================================================================
    # 2. Exact name first — on a REAL product name, not a fixture
    # =====================================================================
    print("\n--- exact name first, on a real product ---")
    obs = client.get("/api/search", params={"q": "Obsidian"})
    payload = obs.json()
    check("the endpoint answers 200 (F-18)", obs.status_code == 200, str(obs.status_code))
    check("a real product name returns that product as result #1 (F-18)",
          names_of(payload)[:1] == ["Obsidian"],
          f"#1={names_of(payload)[:1]}")
    check("…with reason == 'Exact name match' (F-18)",
          reason_of(payload, "Obsidian") == search_mod.REASON_EXACT_NAME,
          repr(reason_of(payload, "Obsidian")))
    check("exactly one row is an exact-name match for 'Obsidian'",
          sum(1 for r in payload if r["reason"] == search_mod.REASON_EXACT_NAME) == 1,
          str(sum(1 for r in payload if r["reason"] == search_mod.REASON_EXACT_NAME)))
    check("an exact-name hit never sorts below a fuzzy one (F-18)",
          payload[0]["reason"] == search_mod.REASON_EXACT_NAME
          and search_mod.REASON_EXACT_NAME not in [r["reason"] for r in payload[1:]],
          f"first={payload[0]['reason']!r} last={payload[-1]['reason']!r}")

    # =====================================================================
    # 3. The ladder — a query that matches at several rungs comes back in order
    # =====================================================================
    print("\n--- the ladder is ordered ---")
    rows = archive_rows()
    hits = search_mod.classify_rows(rows, TOKEN_WORD)
    rungs = [h.rung for h in hits if h.row["status"] not in ("dead", "pivoted")]
    check("the classified rungs are non-decreasing (ladder order holds)",
          all(a <= b for a, b in zip(rungs, rungs[1:])),
          f"rungs={rungs}")
    ladder_names = names_of(client.get("/api/search", params={"q": TOKEN_WORD}).json())
    check("the endpoint returns the classifier's order verbatim",
          ladder_names == [h.row["name"] for h in hits],
          "endpoint order == classify_rows order")

    live_hits = [h for h in hits if h.row["status"] not in ("dead", "pivoted")]
    seq = [h.row["name"] for h in live_hits
           if h.row["name"].startswith(("Zorblat", "Tagline", "Desc", "Cat"))]
    check("the fixtures come back in ladder order (exact → name → tagline → desc → category)",
          seq == ["Zorblat", "Zorblat Notes", "Tagline Zorb Co", "Desc Zorb Co", "Cat Zorb Co"],
          str(seq))
    check("a capability that only the fuzzy rung can reach lands on the fuzzy rung",
          any(h.rung == search_mod.RUNG_FUZZY and h.row["name"] == "Zorblit" for h in hits),
          str([(h.row["name"], search_mod.RUNG_NAMES[h.rung]) for h in hits
               if h.row["name"] in ("Zorblit",)]))

    # =====================================================================
    # 4. The reason vocabulary — every rung's honest string, and nothing else
    # =====================================================================
    print("\n--- the reason vocabulary is correct and stable ---")
    live = client.get("/api/search", params={"q": TOKEN_WORD}).json()
    domain_payload = client.get("/api/search", params={"q": DOMAIN}).json()
    expected = [
        ("exact name", "Zorblat", search_mod.REASON_EXACT_NAME),
        ("exact domain", "Domain Zorb Co", search_mod.REASON_EXACT_DOMAIN),
        ("phrase / name", "Zorblat Notes", search_mod.REASON_NAME),
        ("tagline", "Tagline Zorb Co", search_mod.REASON_TAGLINE),
        ("problem-description", "Desc Zorb Co", search_mod.REASON_PROBLEM),
        ("fuzzy", "Zorblit", search_mod.REASON_FUZZY),
    ]
    for rung_label, row_name, want in expected:
        pool = domain_payload if row_name == "Domain Zorb Co" else live
        got = reason_of(pool, row_name)
        check(f"rung '{rung_label}' emits {want!r}", got == want, f"got {got!r}")
    check("the category rung emits 'Same category'",
          reason_of(live, "Cat Zorb Co") == search_mod.REASON_CATEGORY,
          repr(reason_of(live, "Cat Zorb Co")))
    check("the audience field emits 'Same audience, different approach' "
          "(latent — nothing writes target_users today)",
          reason_of(live, "Audience Zorb Co") == search_mod.REASON_AUDIENCE,
          repr(reason_of(live, "Audience Zorb Co")))

    all_reasons = {r["reason"] for r in live} | {r["reason"] for r in domain_payload}
    check("every reason returned is one of the frozen vocabulary strings",
          all_reasons <= set(search_mod.REASONS),
          str(sorted(all_reasons - set(search_mod.REASONS))))
    check("no reason is empty, a number, a code or an internal rung name",
          all(r == r.strip() and r and not re.search(r"\d", r)
              and "_" not in r and "rung" not in r.lower()
              for r in all_reasons),
          str(sorted(all_reasons)))
    check("the plan's three verbatim examples are preserved exactly",
          {search_mod.REASON_EXACT_NAME, search_mod.REASON_PROBLEM,
           search_mod.REASON_AUDIENCE} <= set(search_mod.REASONS),
          "Exact name match / Similar problem description / Same audience, different approach")

    # =====================================================================
    # 5. Dead and pivoted rows sink — with an otherwise equal match
    # =====================================================================
    print("\n--- dead and pivoted sink to the bottom ---")
    tail = names_of(live)[-2:]
    check("dead AND pivoted rows sort last under an otherwise equal match",
          tail == ["Zorblat Dead", "Zorblat Pivoted"], str(tail))
    check("the tombstones are still returned, never hidden or deleted",
          {r["name"] for r in live} >= {"Zorblat Dead", "Zorblat Pivoted"},
          "both present in the payload")
    dead_hit = next(h for h in hits if h.row["name"] == "Zorblat Dead")
    live_hit = next(h for h in hits if h.row["name"] == "Zorblat")
    check("the tombstone has the same rung/score as the live row it sinks below",
          dead_hit.rung == search_mod.RUNG_NAME_PHRASE and dead_hit.score == live_hit.score,
          f"dead rung={search_mod.RUNG_NAMES[dead_hit.rung]} score={dead_hit.score} "
          f"live score={live_hit.score}")

    # =====================================================================
    # 6. Stars are a tie-break only
    # =====================================================================
    print("\n--- stars break ties, they never rank ---")
    check("a 0-star exact-name match beats a 99999-star fuzzy one (F-18)",
          names_of(live)[0] == "Zorblat" and reason_of(live, "Zorblit") == search_mod.REASON_FUZZY,
          f"#1={names_of(live)[0]} (stars=None) vs Zorblit (stars=99999, "
          f"{reason_of(live, 'Zorblit')!r})")

    # =====================================================================
    # 7. Multi-term AND + the worst-term score
    # =====================================================================
    print("\n--- multi-term AND, scored by the worst term ---")
    a_id = insert_startup("Both Tokens Co", "https://and-both.example",
                          description="quixzal and vortamine both appear here")
    insert_startup("Quixzal Only Co", "https://and-quix.example",
                   description="quixzal alone appears here")
    insert_startup("Vortamine Only Co", "https://and-vort.example",
                   description="vortamine alone appears here")
    two = client.get("/api/search", params={"q": "quixzal vortamine"}).json()
    check("a two-term query returns only rows matching BOTH terms (AND, not OR)",
          names_of(two) == ["Both Tokens Co"], str(names_of(two)))

    insert_startup("Mix Terms Co", "https://and-mix.example",
                   description="quixzal zorblit")
    mix_rows = archive_rows()
    mix_hits = [h for h in search_mod.classify_rows(mix_rows, "quixzal zorblat")
                if h.row["name"] == "Mix Terms Co"]
    check("a row matching one term exactly and the other fuzzily still matches",
          len(mix_hits) == 1, str(len(mix_hits)))
    mix = mix_hits[0]
    check("the score is the WORST term's, not the average "
          "(quixzal exact=0.0, zorblat→zorblit fuzzy≈0.14)",
          mix.score > 0.10 and mix.reason == search_mod.REASON_FUZZY,
          f"score={mix.score:.3f} (average would be ≈{mix.score / 2:.3f}) reason={mix.reason!r}")
    check("a row matching only one of the two terms is excluded",
          not any(h.row["name"] == "Quixzal Only Co"
                  for h in search_mod.classify_rows(mix_rows, "quixzal zorblat")),
          "Quixzal Only Co absent")

    # =====================================================================
    # 8. The empty-query contract (documented: 200 + [])
    # =====================================================================
    print("\n--- the empty-query contract ---")
    no_q = client.get("/api/search")
    empty = client.get("/api/search", params={"q": ""})
    blank = client.get("/api/search", params={"q": "   "})
    check("no q at all → 200 with an empty list (documented contract)",
          no_q.status_code == 200 and no_q.json() == [],
          f"{no_q.status_code} {no_q.json()!r}")
    check("q= (empty) → 200 with an empty list",
          empty.status_code == 200 and empty.json() == [],
          f"{empty.status_code} {empty.json()!r}")
    check("q=<whitespace> → 200 with an empty list",
          blank.status_code == 200 and blank.json() == [],
          f"{blank.status_code} {blank.json()!r}")
    check("the empty query never returns the whole archive",
          len(no_q.json()) != total and len(blank.json()) != total,
          f"0 vs {total} rows")

    # =====================================================================
    # 9. LIKE metacharacters stay literal
    # =====================================================================
    print("\n--- LIKE metacharacters stay literal ---")
    for meta in ("%", "_", "%%", "__"):
        res = client.get("/api/search", params={"q": meta})
        check(f"q={meta!r} returns nothing rather than everything (F-18)",
              res.status_code == 200 and res.json() == [],
              f"{res.status_code} {len(res.json())} rows")
    legacy = client.get("/api/startups", params={"q": "%"}).json()
    check("/api/startups?q=% stays literal (not everything) — the existing rule is untouched",
          len(legacy) < total and all(
              "%" in " ".join(str(r.get(k) or "") for k in ("name", "tagline", "description"))
              for r in legacy),
          f"{len(legacy)} of {total} (every hit really contains a '%')")
    check("/api/startups?q=_ stays literal", client.get("/api/startups", params={"q": "_"}).json() == [],
          "0 rows")

    # =====================================================================
    # 10. Search is a pure read — it never triggers a capture
    # =====================================================================
    print("\n--- search is a pure read (no capture, no evidence) ---")
    never_id = insert_startup("Nevercaptured Co", "https://never-captured.example")
    ev_before = int(ev.count_for_startup(db.connect(), never_id).get("feature", 0))
    jobs_before = len(seeder.JOBS)
    client.get("/api/search", params={"q": "nevercaptured"})
    client.get("/api/search", params={"q": "zorblat"})
    ev_after = int(ev.count_for_startup(db.connect(), never_id).get("feature", 0))
    queued = [j for j in seeder.JOBS.values()
              if j.get("kind") == "capture" and j.get("key") == capture.key_for(never_id)]
    check("a search writes no evidence row", ev_before == ev_after == 0, f"{ev_before} → {ev_after}")
    check("a search queues no capture job for a never-captured competitor (F-22 contrast)",
          not queued and len(seeder.JOBS) >= jobs_before,
          f"capture jobs for the competitor: {len(queued)}")
    # A tripwire, not an assertion about the code's intentions: if any future
    # edit wires the JIT capture into the search path, this search raises here.
    real_start_capture = capture.start_capture

    def _tripwire(*_args, **_kwargs):
        raise AssertionError("search called capture.start_capture — search must stay a pure read")

    capture.start_capture = _tripwire
    try:
        trip = client.get("/api/search", params={"q": "zorblat"})
        tripped = False
    except AssertionError as exc:
        trip, tripped = None, str(exc)
    finally:
        capture.start_capture = real_start_capture
    check("a search never calls capture.start_capture (unlike /api/compare) — tripwire armed",
          not tripped and trip.status_code == 200, tripped or f"{trip.status_code}, no capture attempted")

    # =====================================================================
    # 11. Data-awareness — an empty column must never match everything
    # =====================================================================
    print("\n--- data-awareness: the keyword rung skips empty rows ---")
    kw_id = insert_startup("Keyword Pop Co", "https://kw-pop.example",
                           features_json=json.dumps(["kwonlycapability"]))
    kw_empty = insert_startup("Keyword Empty Co", "https://kw-empty.example")
    kw_payload = client.get("/api/search", params={"q": "kwonlycapability"}).json()
    check("the keyword rung matches the row whose teardown field is populated",
          reason_of(kw_payload, "Keyword Pop Co") == search_mod.REASON_PROBLEM,
          repr(reason_of(kw_payload, "Keyword Pop Co")))
    check("the row with a NULL features_json is skipped, not matched (data-aware)",
          "Keyword Empty Co" not in names_of(kw_payload) and len(kw_payload) == 1,
          f"{len(kw_payload)} hit(s): {names_of(kw_payload)}")
    pos_id = insert_startup("Positioning Co", "https://pos.example",
                            positioning="Zorblat positioning line for teams")
    pos_payload = client.get("/api/search", params={"q": "zorblat"}).json()
    check("positioning is additional evidence for the keyword rung when present",
          reason_of(pos_payload, "Positioning Co") == search_mod.REASON_PROBLEM,
          repr(reason_of(pos_payload, "Positioning Co")))
    nowhere = client.get("/api/search", params={"q": "zzzznosuchwordzzzz"}).json()
    check("a term that appears nowhere returns no rows at all",
          nowhere == [], str(len(nowhere)))

    # =====================================================================
    # 12. No founder leak — the founder store is never searched
    # =====================================================================
    print("\n--- the founder store is never searched (F-20) ---")
    draft = client.post("/api/founder-app", json={
        "name": "Zorblat Founder Only",
        "description": "A founder draft that must never surface in search.",
        "target_user": "founders",
        "category": "productivity",
        "features": ["local files", "markdown notes", "quick capture", "backlinks", "publish"],
        "website_url": "https://founder-only.example",
    }).json()
    check("the founder draft was created in its own store (F-10)",
          draft.get("founder_app_id") and draft.get("profile", {}).get("name") == "Zorblat Founder Only",
          str(draft.get("founder_app_id")))
    leak = client.get("/api/search", params={"q": "zorblat"}).json()
    leak2 = client.get("/api/search", params={"q": "founder only"}).json()
    check("no founder-store record appears in a search result (F-20)",
          all("Zorblat Founder Only" not in names_of(p) for p in (leak, leak2)),
          f"{len(leak)} / {len(leak2)} hits, none from the founder store")
    check("search reads the archive file only (the founder store is a different file)",
          str(config.FOUNDER_DB_PATH) != str(config.DB_PATH),
          str(config.FOUNDER_DB_PATH.name))

    # =====================================================================
    # 13. Reachable rungs — the census the ledger must carry
    # =====================================================================
    print("\n--- reachable rungs, on a PRISTINE copy of the real archive ---")
    for rung, col, n in CENSUS:
        print(f"    {rung:<22} {col:<38} {n:>5} / {total}")
    live_rungs = [(r, n) for r, _c, n in CENSUS if not r.startswith("  ↳")]
    check("every live rung of the ladder can match rows today (none is a promise the UI cannot keep)",
          all(n > 0 for _r, n in live_rungs), str(live_rungs))
    unwritten = {c: n for _r, c, n in CENSUS if _r.startswith("  ↳")}
    check("problem_statement / target_users / features_json / positioning are all 0 today — "
          "no rung is built on a column nothing writes",
          all(n == 0 for n in unwritten.values()), str(unwritten))

    # =====================================================================
    # 14. Timing evidence (the honest ceiling marker)
    # =====================================================================
    print("\n--- timing over the whole archive (the ponytail marker, measured) ---")
    all_rows = archive_rows()
    for q in ("obsidian", "markdown", "note taking"):
        t0 = time.perf_counter()
        got = search_mod.classify_rows(all_rows, q)
        ms = (time.perf_counter() - t0) * 1000
        print(f"    q={q!r:<14} {len(got):>4} hit(s)   {ms:6.1f} ms")
        check(f"a full-archive search for {q!r} stays under 400 ms",
              ms < 400, f"{ms:.1f} ms over {len(all_rows)} rows")

    # =====================================================================
    # 15. Sample payload for the ledger
    # =====================================================================
    print("\n--- sample payload (the ledger's raw evidence) ---")
    for r in client.get("/api/search", params={"q": "zorblat"}).json():
        hit = next(h for h in search_mod.classify_rows(all_rows, "zorblat") if h.row["id"] == r["id"])
        print(f"    {r['name']:<22} rung={search_mod.RUNG_NAMES[hit.rung]:<20} "
              f"score={hit.score:.3f}  reason={r['reason']!r}")
    print(f"    row keys: {sorted(client.get('/api/search', params={'q': 'Obsidian'}).json()[0].keys())[:6]} … "
          f"plus 'reason'")

# --- 16. no frontend file touched -------------------------------------------
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
