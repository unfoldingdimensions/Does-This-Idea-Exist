"""Phase 1 exit-gate verifier — schema & evidence foundation (F-01 … F-05, F-19).

Read-only with respect to the live archive. It works on two throwaway copies:

  1. the migration pass runs against a copy of the live DB and checks that
     nothing moved (row count, exact column list, evidence table, idempotency);
  2. a synthetic DB proves F-03 — a verify_log row older than 90 days survives
     a verification pass now that the retention prune is gone.

Both copies live under backend/data/, which is git-ignored, and the live file
is never opened for writing.

Usage (from the repo root, venv python):
    backend\\.venv\\Scripts\\python.exe scripts\\phase1-verify.py
"""
import io
import re
import sqlite3
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATA = BACKEND / "data"
LIVE = DATA / "ideasexist.db"
BACKUP = DATA / "ideasexist.db.bak-phase1"
COPY = DATA / "ideasexist.db.phase1-test"
F03_DB = DATA / "ideasexist.db.phase1-f03"
SYNTH_DB = DATA / "ideasexist.db.phase1-f04"

sys.path.insert(0, str(BACKEND))

from app import config  # noqa: E402
from app import db  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def sqlite_backup(src: Path, dst: Path) -> None:
    """SQLite's own backup API, never a file copy: the archive is in WAL mode
    and a raw copy can miss writes still sitting in the -wal file."""
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


def read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def count_rows(path: Path) -> int:
    conn = read_only(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM startups").fetchone()[0]
    finally:
        conn.close()


def columns_of(path: Path, table: str = "startups") -> list[str]:
    conn = read_only(path)
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


def main() -> int:
    print("=" * 72)
    print("Phase 1 — schema & evidence foundation: exit-gate verification")
    print("=" * 72)

    # --- preconditions ---------------------------------------------------
    check("live DB present", LIVE.exists(), str(LIVE))
    check("WAL-safe backup present (F-01 safety)", BACKUP.exists(), str(BACKUP))
    if not LIVE.exists() or not BACKUP.exists():
        return 1

    live_cols = columns_of(LIVE)
    live_rows = count_rows(LIVE)
    print(f"\n[live] rows={live_rows} columns={len(live_cols)}")

    # --- 1. migrate a COPY (never the live file) -------------------------
    sqlite_backup(BACKUP, COPY)
    before_rows = count_rows(COPY)
    before_cols = columns_of(COPY)
    print(f"[copy] before migration: rows={before_rows} columns={len(before_cols)}")

    # Point the app's DB layer at the copy — connect() resolves config.DB_PATH
    # per call, so nothing else has to change.
    config.DB_PATH = COPY
    added_first = db.migrate(db.connect())
    added_second = db.migrate(db.connect())
    db.init_db()  # CREATE IF NOT EXISTS path on an already-migrated file

    after_rows = count_rows(COPY)
    after_cols = columns_of(COPY)

    check("row count unchanged by the migration (F-01)", after_rows == before_rows,
          f"{before_rows} -> {after_rows}")
    check("row count matches the Phase 0 baseline of 1,282", after_rows == 1282, str(after_rows))
    check("no column dropped or renamed", all(c in after_cols for c in before_cols),
          f"missing: {[c for c in before_cols if c not in after_cols]}")
    check("`founded` keeps its name (F-04 — rename rejected)",
          "founded" in after_cols and "founded_at" not in after_cols)
    check("`date_source` sits beside it (F-04)", "date_source" in after_cols)
    check("`app_store_url` present (F-19)", "app_store_url" in after_cols)
    check("`play_store_url` present (F-19)", "play_store_url" in after_cols)

    expected = [name for name, _ in db.NEW_STARTUP_COLUMNS]
    missing = [c for c in expected if c not in after_cols]
    check(f"all {len(expected)} teardown columns added", not missing, f"missing: {missing}")
    prov = [name for name, _ in db.NEW_APPROVAL_COLUMNS]
    check(f"all {len(prov)} admission-provenance columns added (scale-to-10k)",
          all(c in after_cols for c in prov),
          f"missing: {[c for c in prov if c not in after_cols]}")
    check("first migration run actually added columns",
          len(added_first) == len(expected) + len(prov), f"added {len(added_first)}")
    check("re-running the migration is a no-op (idempotent)", added_second == [], str(added_second))

    conn = sqlite3.connect(str(COPY))
    try:
        dupes = {t: conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = ?", (t,)).fetchone()[0]
                 for t in ("startups", "evidence", "verify_log", "jobs")}
    finally:
        conn.close()
    check("no duplicate tables", all(v == 1 for v in dupes.values()), str(dupes))

    # --- 2. the evidence table (F-02) ------------------------------------
    ev_cols = columns_of(COPY, "evidence")
    check("evidence table exists (F-02)", bool(ev_cols))
    check(
        "evidence has exactly the specified columns",
        ev_cols == ["id", "startup_id", "evidence_type", "source_url", "captured_at",
                    "claim", "value", "provenance", "confidence", "reviewed_at"],
        str(ev_cols),
    )
    conn = sqlite3.connect(str(COPY))
    try:
        info = {r[1]: r for r in conn.execute("PRAGMA table_info(evidence)")}
        captured_default = info["captured_at"][4]
        try:
            conn.execute("INSERT INTO evidence (startup_id, evidence_type, value) VALUES (1, 'feature', 'x')")
            sourceless_rejected = False
        except sqlite3.IntegrityError:
            sourceless_rejected = True
            conn.rollback()
    finally:
        conn.close()
    check("evidence.source_url is NOT NULL (F-02)", info["source_url"][3] == 1,
          f"notnull={info['source_url'][3]}")
    check("evidence.captured_at is NOT NULL and auto-filled (F-02)",
          info["captured_at"][3] == 1 and bool(captured_default), str(captured_default))
    check("a source-less evidence row is refused (F-02)", sourceless_rejected)

    # --- 3. UPDATABLE parity (the silent-drop trap) ----------------------
    from app import enrich  # noqa: E402

    missing_updatable = [c for c in expected if c not in enrich.UPDATABLE]
    check("every new column is in enrich.UPDATABLE", not missing_updatable, str(missing_updatable))
    # The mirror invariant (scale-to-10k): approval provenance must NOT be
    # enrichment-writable, or a re-seed could reset who admitted a row.
    clash = [c for c in prov if c in enrich.UPDATABLE]
    check("admission provenance is NOT enrichment-writable (scale-to-10k)",
          not clash, str(clash))

    # --- 4. F-03: verify_log is permanent --------------------------------
    src = io.open(BACKEND / "app" / "verify.py", encoding="utf-8").read()
    prune_lines = [ln.strip() for ln in src.splitlines() if re.search(r"DELETE FROM verify_log", ln)]
    check("no retention DELETE left in verify.py (F-03)", not prune_lines, str(prune_lines))

    for stale in (F03_DB, Path(str(F03_DB) + "-wal"), Path(str(F03_DB) + "-shm")):
        if stale.exists():
            stale.unlink()
    config.DB_PATH = F03_DB
    db.init_db()
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO startups (name, website_url, github_url, source) VALUES (?, NULL, NULL, 'website')",
            ("OldLogCorp",),
        )
        sid = conn.execute("SELECT id FROM startups").fetchone()["id"]
        # 200 days old — well past the old 90-day window. The row has no URLs,
        # so the pass makes no network calls and simply records a skip.
        conn.execute(
            "INSERT INTO verify_log (startup_id, checked_at, notes) "
            "VALUES (?, datetime('now', '-200 days'), 'pre-existing audit row')",
            (sid,),
        )
        conn.commit()
        aged_before = conn.execute(
            "SELECT COUNT(*) FROM verify_log WHERE checked_at < datetime('now', '-90 days')"
        ).fetchone()[0]
    finally:
        conn.close()

    from app import verify  # noqa: E402  (imports seeder lazily inside run_verify_job)

    job = {
        "id": uuid.uuid4().hex[:12], "kind": "verify", "source": "phase1-verify",
        "params": {}, "status": "running", "total": 0, "done": 0, "ok": 0,
        "skipped": 0, "failed": 0, "errors": [], "ok_urls": [], "skipped_urls": [],
        "current": "", "created_at": time.time(), "started_at": None,
        "finished_at": None, "breakdown": {"verified": 0, "unverified": 0, "dead": 0},
        "already_verified": [], "suggested": [], "failed_list": [], "result": None,
    }
    verify.run_verify_job(job)

    conn = read_only(F03_DB)
    try:
        survivors = conn.execute(
            "SELECT COUNT(*) FROM verify_log WHERE notes = 'pre-existing audit row'"
        ).fetchone()[0]
        aged_after = conn.execute(
            "SELECT COUNT(*) FROM verify_log WHERE checked_at < datetime('now', '-90 days')"
        ).fetchone()[0]
        total_log = conn.execute("SELECT COUNT(*) FROM verify_log").fetchone()[0]
    finally:
        conn.close()

    check("the 200-day-old verify_log row survived the pass (F-03)",
          aged_before == 1 and aged_after == 1 and survivors == 1,
          f"aged before={aged_before} after={aged_after} surviving row={survivors}")
    check("the pass still writes a new row per startup", total_log == 2, f"verify_log rows={total_log}")
    check("verify job completed", job["status"] == "done", str(job["status"]))

    # --- 5. F-04 / F-05 behaviour at the branches -------------------------
    # The three founded-date branches and the provenance stamp are exercised
    # here with stubs, on a synthetic DB, so Phase 1 does not hand Phase 5 a
    # code path that has never run.
    from app import enrich, llm, website  # noqa: E402

    for stale in (SYNTH_DB, Path(str(SYNTH_DB) + "-wal"), Path(str(SYNTH_DB) + "-shm")):
        if stale.exists():
            stale.unlink()
    config.DB_PATH = SYNTH_DB
    db.init_db()

    real_fetch = website.fetch_homepage
    real_wayback = website.wayback_first_snapshot
    real_rdap = website.rdap_registration_date
    real_llm = llm.llm_json

    def fake_page(url):
        return {"final_url": url, "title": "T", "meta_description": "M", "text": "body"}

    def make_llm(founded):
        return lambda user: {"name": "Synthetic", "tagline": "tg", "description": "desc",
                             "category": "ai", "founded": founded}

    def seed(url):
        return enrich.seed_from_website(url)

    try:
        website.fetch_homepage = fake_page

        # A. nothing from the LLM, nothing from Wayback -> RDAP
        llm.llm_json = make_llm("")
        website.wayback_first_snapshot = lambda d: None
        website.rdap_registration_date = lambda d: "1997-10-06"
        rdap_row = seed("https://rdap.example")
        check("RDAP-derived date is recorded as date_source='rdap' (F-04)",
              rdap_row["date_source"] == "rdap" and rdap_row["founded"] == "1997-10-06",
              f"founded={rdap_row['founded']!r} date_source={rdap_row['date_source']!r}")
        check("a fresh seed is stamped provenance='machine_drafted' (F-05)",
              rdap_row["provenance"] == enrich.MACHINE_DRAFTED, str(rdap_row["provenance"]))

        # B. Wayback wins over RDAP
        website.wayback_first_snapshot = lambda d: "2019-03-04"
        wb_row = seed("https://wayback.example")
        check("a Wayback-derived date is recorded as date_source='wayback' (F-04)",
              wb_row["date_source"] == "wayback" and wb_row["founded"] == "2019-03-04",
              f"founded={wb_row['founded']!r} date_source={wb_row['date_source']!r}")

        # C. the LLM wins over both
        llm.llm_json = make_llm("2015-06-01")
        llm_row = seed("https://llm.example")
        check("an LLM-stated date is recorded as date_source='llm' (F-04)",
              llm_row["date_source"] == "llm" and llm_row["founded"] == "2015-06-01",
              f"founded={llm_row['founded']!r} date_source={llm_row['date_source']!r}")

        # D. no source at all -> unknown, and no date invented
        llm.llm_json = make_llm("null")
        website.wayback_first_snapshot = lambda d: None
        website.rdap_registration_date = lambda d: None
        none_row = seed("https://nodate.example")
        check("with no source the date stays NULL and date_source='unknown' (F-04)",
              none_row["founded"] is None and none_row["date_source"] == "unknown",
              f"founded={none_row['founded']!r} date_source={none_row['date_source']!r}")

        # E. a human confirm flips the marker; a later reuse refresh keeps it
        conn = db.connect()
        try:
            enrich.mark_human_confirmed(conn, rdap_row["id"])
        finally:
            conn.close()
        conn = read_only(SYNTH_DB)
        try:
            confirmed = conn.execute("SELECT provenance FROM startups WHERE id = ?",
                                     (rdap_row["id"],)).fetchone()[0]
        finally:
            conn.close()
        check("a human confirm flips provenance to human_confirmed (F-05)",
              confirmed == enrich.HUMAN_CONFIRMED, str(confirmed))

        website.wayback_first_snapshot = lambda d: None
        website.rdap_registration_date = lambda d: None
        enrich.seed_from_website("https://rdap.example", reuse_profile=True)
        conn = read_only(SYNTH_DB)
        try:
            after = conn.execute("SELECT provenance, date_source, founded FROM startups WHERE id = ?",
                                 (rdap_row["id"],)).fetchone()
        finally:
            conn.close()
        check("a reuse_profile refresh does not downgrade human_confirmed (F-05)",
              after[0] == enrich.HUMAN_CONFIRMED, str(after[0]))
        check("a reuse_profile refresh that learns nothing does not reset date_source (F-04)",
              after[1] == "rdap" and after[2] == "1997-10-06", f"date_source={after[1]!r} founded={after[2]!r}")
    finally:
        website.fetch_homepage = real_fetch
        website.wayback_first_snapshot = real_wayback
        website.rdap_registration_date = real_rdap
        llm.llm_json = real_llm

    # --- evidence dump for the ledger ------------------------------------
    print("\n--- PRAGMA table_info(startups) on the migrated copy ---")
    conn = read_only(COPY)
    try:
        for row in conn.execute("PRAGMA table_info(startups)"):
            print(f"  {row[0]:>3}  {row[1]:<24} {row[2] or '':<8} notnull={row[3]} default={row[4]}")
    finally:
        conn.close()

    print("\n--- sample migrated row (id=1) ---")
    conn = read_only(COPY)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM startups ORDER BY id LIMIT 1").fetchone()
        for key in ("id", "name", "founded", "date_source", "provenance", "entity_type",
                    "app_store_url", "play_store_url", "features_json"):
            print(f"  {key:<18} = {row[key]!r}")
        print(f"  (row has {len(row.keys())} columns)")
    finally:
        conn.close()

    user_version = sqlite3.sqlite_version
    print(f"\n[info] sqlite {user_version}")
    print("\n" + "=" * 72)
    if failures:
        print(f"RESULT: {len(failures)} FAILED -> {failures}")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
