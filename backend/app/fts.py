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
# v2 (2026-09-23): indexed columns grew from 6 to the ladder's NINE free-text
# fields + website_url — task 4's parity work proved the 6-column index is NOT
# a candidate superset of the ladder (positioning/features_json/
# problem_statement/target_users admissions were invisible to it).
FTS_SCHEMA_VERSION = 2

# The columns indexed, in FTS column order: the search ladder's nine free-text
# fields (search.py's _FREE_TEXT_FIELDS — keep in sync) plus website_url and
# canonical_domain so a domain query narrows through the index too.
FTS_COLUMNS = (
    "name",
    "aliases",
    "tagline",
    "description",
    "problem_statement",
    "target_users",
    "category",
    "positioning",
    "features_json",
    "website_url",
    "canonical_domain",
)

# The candidate ceiling. bm25's job is to cut 10k rows to something the ladder
# can classify in ~milliseconds; 500 is 5% of the scale target and far above
# any query's plausible true matches. Ladder ordering then picks the winners.
SEARCH_CANDIDATE_CAP = 500

# Above this many distinct words in a term's fuzzy length-band, the per-term
# ratio scan costs more than the linear scan would — give up and let the
# caller fall back (correct, just linear). Measured on the 1,258-row archive:
# bands are ~3-5k words and scan in ~20-30 ms; 60k distinct band words implies
# an archive far past the 10k scale target.
_FUZZY_SCAN_LIMIT = 60_000

# The word-table tokenizer reads these columns — the ladder's nine free-text
# fields (its admission surface) — so the word table covers every field a
# query term can be admitted through.
_WORD_COLS = (
    "name",
    "aliases",
    "tagline",
    "description",
    "problem_statement",
    "target_users",
    "category",
    "positioning",
    "features_json",
)

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

# Word-table sync. sx_words(col) (app/udf.py) emits the SAME lowercase word
# runs the ladder's _WORD_RE produces; json_each walks them. DISTINCT rows
# into app_search_word(word, startup_id) — the raw-word inverted table the
# candidate generator queries. Triggers (not writers) keep it exact, the same
# one-writer-shape rule as the FTS index itself.
_WORD_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS app_search_word (
  word TEXT NOT NULL,
  startup_id INTEGER NOT NULL,
  PRIMARY KEY (word, startup_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_app_search_word_id ON app_search_word(startup_id);
"""

_WORD_SELECTS = [f"SELECT value FROM json_each(sx_words(new.{c}))"
                 for c in _WORD_COLS]
_WORD_UNION = " UNION ".join(_WORD_SELECTS)

_WORD_TRIGGERS = (
    ("app_search_word_ai", "AFTER INSERT ON startups",
     f"INSERT INTO app_search_word (word, startup_id) "
     f"SELECT DISTINCT j.value, new.id FROM ({_WORD_UNION}) j"),
    ("app_search_word_ad", "AFTER DELETE ON startups",
     "DELETE FROM app_search_word WHERE startup_id = old.id"),
    ("app_search_word_au", "AFTER UPDATE ON startups",
     "DELETE FROM app_search_word WHERE startup_id = new.id;"
     f"INSERT INTO app_search_word (word, startup_id) "
     f"SELECT DISTINCT j.value, new.id FROM ({_WORD_UNION}) j"),
)


def _fts_ddl() -> str:
    cols = ", ".join(FTS_COLUMNS)
    return (
        f"CREATE VIRTUAL TABLE IF NOT EXISTS startups_fts USING fts5("
        f"{cols}, content='startups', content_rowid='id', tokenize='porter unicode61'"
        f");"
        # The porter-stemmed vocabulary side-table. Kept for introspection/
        # stats (and future bm25-only paths); the ladder-parity candidate
        # generator does NOT read it — stemming loses mid-word admissions
        # (probe 2026-09-23: 'base' is inside 'databasely' but not inside
        # stem('databasely')='databas'), so parity queries the RAW word table.
        "CREATE VIRTUAL TABLE IF NOT EXISTS startups_vocab "
        "USING fts5vocab(startups_fts, row);"
    )


def _trigger_sql(kind: str, when: str, body: str) -> str:
    cols = ", ".join(FTS_COLUMNS)
    new = "new.id, " + ", ".join(f"new.{c}" for c in FTS_COLUMNS)
    old = ", ".join(f"old.{c}" for c in FTS_COLUMNS)
    word_cols = ", ".join(_WORD_COLS)
    stmt = body.format(cols=cols, new=new, old=old, word_cols=word_cols)
    # probe-verified: a doubled ';' before END is a syntax error in trigger
    # bodies (sqlite3 executescript allows it elsewhere, triggers do not) —
    # so bodies must NOT end with their own semicolon.
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
        conn.executescript(_WORD_TABLE_DDL)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
        for name, when, body in _TRIGGERS:
            conn.executescript(_trigger_sql(name, when, body))
        for name, when, body in _WORD_TRIGGERS:
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
    """Rebuild BOTH structures from startups: the FTS index ('delete-all'
    first — probe-verified: bare 'delete' does NOT clear an external-content
    index) and the raw-word table (plain DELETE + re-seed through the same
    sx_words tokenizer the triggers use). NOT committed here — ensure()
    commits around it."""
    conn.execute("INSERT INTO startups_fts(startups_fts) VALUES('delete-all')")
    cols = ", ".join(FTS_COLUMNS)
    conn.execute(
        f"INSERT INTO startups_fts(rowid, {cols}) SELECT id, {cols} FROM startups")
    conn.execute("DELETE FROM app_search_word")
    word_union = " UNION ".join(
        f"SELECT j.value AS value, s.id AS id FROM startups s, json_each(sx_words(s.{c})) j"
        for c in _WORD_COLS
    )
    conn.execute(
        "INSERT INTO app_search_word (word, startup_id) "
        f"SELECT DISTINCT value, id FROM ({word_union})")


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

    NOTE (task 4): this answers "which rows contain these TOKENS". It is a
    filter over indexed text, not a superset of the ladder's admissions — the
    ladder also admits prefix/mid-word/fuzzy hits (see candidate_ids), so
    /api/search must NOT gate on this function alone.
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


def _admitting_words(conn: sqlite3.Connection, term: str) -> list[str] | None:
    """Distinct indexed words that could produce a ladder admission for `term`.

    Soundness (the ladder's own bands, search._distance):
      exact 0.0   -> word == term
      prefix 0.05 -> word startswith term (len >= 3)
      mid-word 0.10 -> word contains term (len >= 4) [startswith covered above]
      fuzzy <= 0.3 -> SequenceMatcher ratio(term, word) >= 0.7, |len diff| <= 2
                      (the ladder itself skips wider pairs)
    The SQL pass pulls exact/prefix/substring/length-band candidates cheaply;
    only the fuzzy band gets ratio-tested in Python, bounded by the ladder's
    own length window and _FUZZY_SCAN_LIMIT. None (None) means "the band is
    too large to scan — fall back to the linear path".
    """
    like = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    length = len(term)
    fuzzy_lo, fuzzy_hi = length - 2, length + 2
    rows = conn.execute(
        "SELECT DISTINCT word FROM app_search_word "
        "WHERE word = ? "
        "   OR (length(word) >= ? AND word LIKE ? ESCAPE '\\')"
        "   OR (length(word) >= ? AND instr(word, ?) > 0)"
        "   OR (length(word) BETWEEN ? AND ?)",
        (term, max(length - 2, 3), f"{like}%", 4, term, fuzzy_lo, fuzzy_hi),
    ).fetchall()
    words = [r["word"] for r in rows]
    band = [w for w in words if abs(len(w) - length) <= 2]
    if len(band) > _FUZZY_SCAN_LIMIT:
        return None
    if length >= 3:
        from .search import _ratio
        close = [w for w in band if 1.0 - _ratio(term, w) <= 0.3]
    else:
        close = []
    # prefix/mid-word admissions: the word CONTAINS the term (the ladder's
    # 'term in field.text' path); exact word match is the 0.0 case ('ai' at
    # len 2 is exact-or-nothing — the ladder's bands all floor at len 3).
    contains = [w for w in words if w == term or (length >= 3 and term in w)]
    return list(set(contains) | set(close))


def candidate_ids(conn: sqlite3.Connection, terms: list[str],
                  cap: int = SEARCH_CANDIDATE_CAP) -> list[int]:
    """Row ids that could POSSIBLY pass the ladder's gate for `terms`.

    Parity contract (task 4): returns a SUPERSET of every row the ladder's
    gate admits — token hits AND prefix/mid-word hits AND fuzzy-typo hits —
    so the ladder classifying only these candidates returns byte-identical
    results to the linear scan (up to the cap, see below).

    Mechanism: every ladder admission runs through word-level distances
    (search._distance), so a row can only be admitted if it contains a word
    "close" to a query term under one of the ladder's four bands. The raw
    word table (app_search_word, filled by the sx_words triggers — the
    ladder's OWN token shape) makes "rows holding word W" an indexed lookup,
    and _admitting_words computes the exact admitting-word set per term.
    The AND gate is a set intersection across terms.

    Returns [] (caller falls back to the linear scan — identical results,
    just slower) when: the index is unavailable; a term admits nothing; a
    band is too large to scan; or the candidate set exceeds `cap`. The cap
    is a SAFETY VALVE: correctness never depends on it, only speed does.
    """
    usable = [t for t in terms if t and t.strip()]
    if not usable:
        return []
    try:
        if not available(conn):
            return []
        per_term: list[set[int]] = []
        for term in usable:
            wanted = _admitting_words(conn, term)
            if wanted is None:
                return []  # fuzzy band too big -> linear scan
            if not wanted:
                return []  # this term cannot admit anything -> gate fails
            ph = ",".join("?" * len(wanted))
            rs = conn.execute(
                "SELECT DISTINCT startup_id FROM app_search_word "
                f"WHERE word IN ({ph})",
                tuple(sorted(wanted)),
            ).fetchall()
            if len(rs) > cap:
                return []  # too broad for the ladder to classify quickly -> linear scan
            per_term.append({r["startup_id"] for r in rs})
        acc = per_term[0]
        for s in per_term[1:]:
            acc &= s
        if len(acc) > cap:
            return []
        return sorted(acc)
    except Exception:  # noqa: BLE001 — any word-table problem reads as "no fast path"
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
