"""FTS5 index over the archive (Phase P, scale-plan §7.2) — a fast candidate
generator for /api/search, never a new ranker.

THE CONTRACT (decided 2026-09-22, .hermes/plans/2026-09-22_phase-p-paging-fts5.md):

  * bm25 narrows the archive to a candidate set (cap SEARCH_CANDIDATE_CAP);
    the EXISTING ladder in app/search.py then classifies, orders and assigns
    its frozen F-18 reasons. bm25 is a filter, not a ranker.
  * The index is an OPTIMISATION, never a dependency: `available()` False
    (missing table, old sqlite, corrupt index) means callers fall back to the
    linear scan and users see identical results — just slower. Nothing in the
    product requires this table to exist.
  * Sync is trigger-based (external-content table), so writes to `startups`
    stay in the index with no hook in any writer. A version marker decides
    between trust-the-triggers and rebuild: bump FTS_SCHEMA_VERSION when the
    column set or tokenizer changes and every boot after a deploy rebuilds
    once, cheaply.

WHY EXTERNAL CONTENT: the `startups` row is the single source of truth (the
archive holds ~40 columns; indexing all of them would duplicate the DB). The
FTS table stores only rowid->doc mapping; content is read back from startups.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger("ideasexist.fts")

# Bump when the indexed column set or tokenizer changes: every boot after the
# deploy rebuilds once (a few seconds at 10k rows), then trusts triggers again.
FTS_SCHEMA_VERSION = 1

# The columns indexed, in FTS column order. Deliberately the same free-text
# fields the search ladder reads (search.py's field map) plus canonical_domain
# (populated as of 2026-09-22) so a domain query narrows through the index.
FTS_COLUMNS = ("name", "tagline", "description", "category", "aliases", "canonical_domain")

# The candidate ceiling. bm25's job is to cut 10k rows to something the ladder
# can classify in ~milliseconds; 500 is 5% of the scale target and far above
# any query's plausible true matches. Ladder ordering then picks the winners.
SEARCH_CANDIDATE_CAP = 500

_TRIGGERS = (
    ("startups_fts_ai", "AFTER INSERT ON startups",
     "INSERT INTO startups_fts(rowid, {cols}) VALUES ({new})"),
    ("startups_fts_ad", "AFTER DELETE ON startups",
     "INSERT INTO startups_fts(startups_fts, rowid, {cols}) "
     "VALUES('delete', old.id, {old})"),
    ("startups_fts_au", "AFTER UPDATE ON startups",
     "INSERT INTO startups_fts(startups_fts, rowid, {cols}) "
     "VALUES('delete', old.id, {old});"
     "INSERT INTO startups_fts(rowid, {cols}) VALUES ({new})"),
)


def _fts_ddl() -> str:
    cols = ", ".join(FTS_COLUMNS)
    return (
        f"CREATE VIRTUAL TABLE IF NOT EXISTS startups_fts USING fts5("
        f"{cols}, content='startups', content_rowid='id', tokenize='porter unicode61'"
        f");"
    )


def _trigger_sql(kind: str, when: str, body: str) -> str:
    cols = ", ".join(FTS_COLUMNS)
    new = "new.id, " + ", ".join(f"new.{c}" for c in FTS_COLUMNS)
    old = ", ".join(f"old.{c}" for c in FTS_COLUMNS)
    stmt = body.format(cols=cols, new=new, old=old)
    return f"CREATE TRIGGER IF NOT EXISTS {kind} {when} BEGIN {stmt}; END;"


def available(conn: sqlite3.Connection) -> bool:
    """True when this sqlite build has FTS5 AND the index exists and is
    queryable. Cheap enough to call per request; a corrupt index reads as
    unavailable, which sends the caller to the linear path (never a 500)."""
    try:
        conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='startups_fts'").fetchone()
        conn.execute("SELECT count(*) FROM startups_fts LIMIT 1").fetchone()
        return True
    except Exception:  # noqa: BLE001 — no FTS5 module, no table, corrupt index
        return False


def version_ok(conn: sqlite3.Connection) -> bool:
    """True when the stored schema marker matches FTS_SCHEMA_VERSION."""
    try:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = 'fts_schema_version'"
        ).fetchone()
    except Exception:  # noqa: BLE001 — no app_meta table yet
        return False
    if not row:
        return False
    try:
        return int(row["value"]) == FTS_SCHEMA_VERSION
    except (TypeError, ValueError):
        return False


def ensure(conn: sqlite3.Connection, *, force: bool = False) -> bool:
    """Create/upgrade the index. Returns True when a REBUILD ran.

    Idempotent and cheap in the steady state: table + triggers are
    IF NOT EXISTS, and the rebuild only happens when the version marker is
    missing/mismatched (a deploy bumped FTS_SCHEMA_VERSION) or `force` is set
    (the self-test path). Callers run this at boot; it commits once.
    """
    try:
        conn.executescript(_fts_ddl())
        conn.execute(
            "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
        for name, when, body in _TRIGGERS:
            conn.executescript(_trigger_sql(name, when, body))
        if force or not version_ok(conn):
            rebuild(conn)
            conn.execute(
                "INSERT INTO app_meta (key, value) VALUES ('fts_schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(FTS_SCHEMA_VERSION),))
            conn.commit()
            return True
        return False
    except Exception as exc:  # noqa: BLE001 — an FTS-less sqlite must not block boot
        log.warning("fts.ensure unavailable (%s); search stays on the linear scan", exc)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return False


def rebuild(conn: sqlite3.Connection) -> None:
    """Rebuild the index from startups. The 'delete-all' command clears the
    old mapping first (probe-verified: bare 'delete' does NOT clear an
    external-content index — 'delete-all' does), so a rebuild over a
    stale/ghost-ridden index is also the repair path. NOT committed here —
    ensure() commits around it."""
    conn.execute("INSERT INTO startups_fts(startups_fts) VALUES('delete-all')")
    cols = ", ".join(FTS_COLUMNS)
    conn.execute(
        f"INSERT INTO startups_fts(rowid, {cols}) SELECT id, {cols} FROM startups")


def _fts_query(term: str) -> str:
    """Make a user term safe inside an FTS5 MATCH expression.

    FTS5 query syntax gives special meaning to quotes, `*`, `(`, `:`, `-`,
    `AND`/`OR`/`NEAR`... A bare term would be a syntax error or, worse, an
    unintended filter. Wrapping in double quotes makes it a phrase of exactly
    that token; a trailing `*` (prefix search) is opt-in via the caller.
    """
    escaped = term.replace('"', '""')
    return f'"{escaped}"'


def search_ids(conn: sqlite3.Connection, terms: list[str],
               cap: int = SEARCH_CANDIDATE_CAP) -> list[int]:
    """Candidate ids for an AND over terms, best (bm25) first, capped.

    AND across terms mirrors the ladder's gate: every term must match
    somewhere in the row. Each term is a quoted phrase so user punctuation
    can never alter query structure; empty terms are ignored (a query with no
    terms has no candidates — the caller treats that as the empty-query
    contract).
    """
    usable = [t for t in terms if t and t.strip()]
    if not usable:
        return []
    match = " AND ".join(_fts_query(t) for t in usable)
    try:
        rows = conn.execute(
            "SELECT rowid FROM startups_fts WHERE startups_fts MATCH ? "
            "ORDER BY bm25(startups_fts) LIMIT ?",
            (match, cap),
        ).fetchall()
        return [r["rowid"] for r in rows]
    except Exception:  # noqa: BLE001 — a malformed MATCH reads as "no candidates"
        return []


def stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """A small health snapshot for tests and the admin panel."""
    try:
        rows = conn.execute("SELECT count(*) AS c FROM startups_fts").fetchone()["c"]
        archived = conn.execute("SELECT count(*) AS c FROM startups").fetchone()["c"]
        return {"available": True, "indexed": rows, "archive_rows": archived,
                "version": FTS_SCHEMA_VERSION}
    except Exception:  # noqa: BLE001
        return {"available": False, "indexed": 0, "archive_rows": 0,
                "version": FTS_SCHEMA_VERSION}


def _aliases_text(value: Any) -> str:
    """aliases is stored as a JSON list; the FTS row needs plain text."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return " ".join(str(v) for v in parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        return value
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return ""
