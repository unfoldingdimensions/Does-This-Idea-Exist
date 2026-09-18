"""SQLite storage (stdlib sqlite3, WAL). Schema v1 — additive changes only."""
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from . import config

# --- F-01 additive migration: one source of truth -------------------------
# Canonical teardown column names live in docs/teardown-spec.md §5.1 (older
# plan documents spell some of them differently; §5.1 wins). Every column here
# is nullable TEXT, so `ALTER TABLE ... ADD COLUMN` is a metadata-only change:
# existing rows keep their values, nothing is dropped, nothing is rewritten.
#
# This tuple feeds BOTH the fresh-DB CREATE TABLE below and migrate(), so the
# two paths cannot drift. The same trap exists one level up in
# enrich.UPDATABLE — a column that is in the schema but missing from that
# tuple is silently dropped by _upsert, with no error and no warning — so
# scripts/phase1-verify.py asserts that this list and UPDATABLE agree.
#
# date_source is F-04 rather than F-01: WHERE a date came from was never
# recorded, so existing rows start at "unknown". Phase 6 stops the UI
# presenting an RDAP/Wayback date as a founding year (Notion is filed as
# 2000-11-01 when it was founded in 2013).
NEW_STARTUP_COLUMNS: tuple[tuple[str, str], ...] = (
    # identity & classification
    ("entity_type", "TEXT"),            # product | company | project | repository | domain | unknown
    ("canonical_domain", "TEXT"),
    ("aliases", "TEXT"),                # JSON list
    # the idea
    ("problem_statement", "TEXT"),
    ("target_users", "TEXT"),
    # product surface (URL definitions: docs/teardown-spec.md §5.3)
    ("product_url", "TEXT"),
    ("docs_url", "TEXT"),
    ("demo_url", "TEXT"),
    ("app_store_url", "TEXT"),          # F-19: iOS listing — also the mobile-app probe
    ("play_store_url", "TEXT"),         # F-19: Google Play listing
    # pricing, plan-by-plan, with its own capture stamps
    ("pricing_json", "TEXT"),
    ("pricing_captured_at", "TEXT"),
    ("pricing_source_url", "TEXT"),
    # teardown content
    ("features_json", "TEXT"),          # JSON flat list, 5-10 items
    ("positioning", "TEXT"),
    ("content_notes", "TEXT"),
    ("activity_checked_at", "TEXT"),
    ("activity_summary", "TEXT"),
    ("last_human_reviewed_at", "TEXT"),
    ("review_notes", "TEXT"),
    # provenance (F-05 / F-04)
    ("provenance", "TEXT"),             # machine_drafted | human_confirmed | sourced | unknown
    ("date_source", "TEXT DEFAULT 'unknown'"),  # llm | wayback | rdap | human | unknown
)

# --- approval provenance (scale-to-10k, 2026-09-18) -------------------------
# `verified` answers "is this row admitted to the archive".  It does NOT answer
# "who admitted it" - and until now the only answer was "a human", so the two
# questions collapsed into one flag and the Admin Verified badge could infer it.
#
# The funnel changes that: rows that pass the automated liveness gate are now
# admitted without a human seeing them.  If they were marked with `verified`
# alone they would each render "Admin Verified" - a badge claiming a human
# confirmed a business no human has ever looked at.  Badges must not lie
# (docs/teardown-spec.md §8.1), so admission provenance is recorded explicitly
# instead:
#
#   approval_source  'human' | 'machine'  (NULL = predates this column, i.e. human)
#   approved_by      'admin' | 'funnel:http' | 'funnel:render'
#   approval_note    optional free text for a rejection or re-check reason
#
# These are DELIBERATELY NOT in NEW_STARTUP_COLUMNS.  That tuple feeds
# enrich.UPDATABLE, so anything in it can be written by a seed/teardown upsert -
# and a re-seed silently resetting `approval_source` would turn a machine
# admission into an apparently human one.  Approval state is written only by
# verify.approve_suggested / verify.approve_machine, never by enrichment.
NEW_APPROVAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("approval_source", "TEXT"),        # human | machine | NULL (legacy => human)
    ("approved_by", "TEXT"),            # admin | funnel:http | funnel:render
    ("approval_note", "TEXT"),
)

_STARTUPS_BASE = """CREATE TABLE IF NOT EXISTS startups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  tagline TEXT,
  description TEXT,
  category TEXT,
  website_url TEXT,
  github_url TEXT,
  founded TEXT,
  stars INTEGER,
  language TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  verified INTEGER NOT NULL DEFAULT 0,
  verified_at TEXT,
  last_checked TEXT,
  check_failures INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))"""

# Fresh DB and upgraded DB both end up with the same column list: the CREATE
# statement above is the base, the teardown columns are appended from the one
# list the migration also reads.
def table_ddl(name: str, extra: tuple[tuple[str, str], ...] = ()) -> str:
    """DDL for a table with the archive's column shape.

    The founder store's `founder_apps` carries the SAME columns as `startups`
    (F-10) — that is what lets the gap table diff the two records like for like.
    Both are built here, from the same NEW_STARTUP_COLUMNS tuple that migrate()
    reads, so the founder store cannot quietly drift from the archive.
    """
    base = _STARTUPS_BASE.replace(
        "CREATE TABLE IF NOT EXISTS startups", f"CREATE TABLE IF NOT EXISTS {name}", 1
    )
    cols = tuple(NEW_STARTUP_COLUMNS) + tuple(extra)
    return base + "".join(f",\n  {col} {decl}" for col, decl in cols) + "\n);"


_STARTUPS_TABLE = table_ddl("startups")

SCHEMA = (
    _STARTUPS_TABLE
    + """
CREATE UNIQUE INDEX IF NOT EXISTS idx_startups_website ON startups(lower(website_url));
CREATE UNIQUE INDEX IF NOT EXISTS idx_startups_github ON startups(lower(github_url));
-- F-02: one row per claim, each with the source it came from. source_url and
-- captured_at are NOT NULL by design — evidence without a source is not
-- evidence, and the DB is the last line of defence behind the API's checks.
CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  startup_id INTEGER NOT NULL,
  evidence_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  captured_at TEXT NOT NULL DEFAULT (datetime('now')),
  claim TEXT,
  value TEXT,
  provenance TEXT,
  confidence REAL,
  reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_startup ON evidence(startup_id);
"""
    + """

CREATE TABLE IF NOT EXISTS verify_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  startup_id INTEGER NOT NULL,
  checked_at TEXT NOT NULL DEFAULT (datetime('now')),
  website_ok INTEGER,
  github_ok INTEGER,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  params_json TEXT,
  status TEXT NOT NULL,
  total INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0,
  ok INTEGER DEFAULT 0,
  skipped INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0,
  errors_json TEXT,
  ok_urls_json TEXT,
  skipped_urls_json TEXT,
  current TEXT,
  created_at REAL,
  started_at REAL,
  finished_at REAL,
  breakdown_json TEXT,
  result_json TEXT
);
"""
)


def connect_path(path) -> sqlite3.Connection:
    """A connection to another SQLite file, with this app's settings.

    The founder store is a separate file (config.FOUNDER_DB_PATH) on purpose
    (F-10/F-20). It gets the identical WAL + busy-timeout + row_factory setup so
    the two stores behave the same way rather than nearly the same way.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def connect() -> sqlite3.Connection:
    """The archive connection. Parallel workers (seed ∥ verify ∥ capture) are
    all writers — busy_timeout waits briefly for the other's commit instead of
    failing with "database is locked"."""
    return connect_path(config.DB_PATH)


def migrate(conn: sqlite3.Connection) -> list[str]:
    """F-01: bring an existing DB up to the current schema. Additive only.

    SQLite's ADD COLUMN with a constant (or NULL) default is a metadata write:
    rows are not rewritten and existing values are untouched. Idempotent by
    construction — PRAGMA table_info decides what is missing, so re-running
    adds nothing and returns []. Never DROP, never RENAME.

    Returns the names of the columns actually added, so a caller (or a test)
    can prove the first run was not a no-op and the second run was.

    Two lists are applied, and the split is load-bearing:

    * NEW_STARTUP_COLUMNS - the teardown/enrichment fields. Every one of them is
      also in enrich.UPDATABLE, and tests assert that parity (the silent-drop
      trap: a column in the schema but missing from UPDATABLE is dropped by
      _upsert with no error).
    * NEW_APPROVAL_COLUMNS - who admitted the row. These are deliberately NOT in
      UPDATABLE, so a re-seed can never overwrite an admission's provenance.

    Legacy rows keep approval_source NULL. That is not a gap to backfill: every
    row admitted before the funnel existed was admitted by a human, and NULL is
    read as exactly that (compare.badges), so no existing row is rewritten.
    """
    present = {row["name"] for row in conn.execute("PRAGMA table_info(startups)")}
    added: list[str] = []
    for name, decl in NEW_STARTUP_COLUMNS + NEW_APPROVAL_COLUMNS:
        if name in present:
            continue
        conn.execute(f"ALTER TABLE startups ADD COLUMN {name} {decl}")
        added.append(name)
    if added:
        conn.commit()
    return added


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)  # CREATE ... IF NOT EXISTS: fresh DBs get the full schema
        migrate(conn)               # existing DBs get the new columns; no-op on a fresh one
    finally:
        conn.close()


def normalize_url(url: str | None) -> str:
    """Canonical identity form for dedup: lowercase scheme+host, strip www.,
    default ports, trailing slashes, query strings and fragments.

    Paths stay case-sensitive (github.com/Owner/repo != github.com/owner/repo).
    """
    if not url:
        return ""
    u = url.strip()
    try:
        p = urlparse(u)
    except ValueError:
        return u.rstrip("/")
    host = (p.hostname or "").lower().removeprefix("www.")
    if p.scheme not in ("http", "https") or not host:
        return u.rstrip("/")
    # p.port raises (not returns None) for out-of-range ports like :99999 —
    # only urlparse() itself is guarded above.
    try:
        port_num = p.port
    except ValueError:
        return u.rstrip("/")
    port = ""
    if port_num and not (
        (p.scheme == "http" and port_num == 80) or (p.scheme == "https" and port_num == 443)
    ):
        port = f":{port_num}"
    return f"{p.scheme}://{host}{port}{p.path.rstrip('/')}"


def find_by_url(conn: sqlite3.Connection, website_url: str | None = None, github_url: str | None = None) -> sqlite3.Row | None:
    """Look up an existing startup by website or github URL (dedup for re-seeds).

    Exact-match first (unique index), then a normalized-equivalence fallback so
    `https://zoom.com` and `https://www.zoom.com/` resolve to the same row.
    """
    if website_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(website_url) = lower(?)", (website_url,)
        ).fetchone()
        if not row:
            n_ws = normalize_url(website_url)
            if n_ws:
                for candidate in conn.execute("SELECT * FROM startups WHERE website_url IS NOT NULL"):
                    if normalize_url(candidate["website_url"]) == n_ws:
                        return candidate
        elif row:
            return row
    if github_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(github_url) = lower(?)", (github_url,)
        ).fetchone()
        if not row:
            n_gh = normalize_url(github_url)
            if n_gh:
                for candidate in conn.execute("SELECT * FROM startups WHERE github_url IS NOT NULL"):
                    if normalize_url(candidate["github_url"]) == n_gh:
                        return candidate
        elif row:
            return row
    return None
