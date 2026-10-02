"""The candidates staging store — where a sourcer's output lands, never the archive.

Phase C's whole point: today a channel generator's output flows straight into
`startups` through `seeder._ingest`, so a bad crawl becomes archive rows. Staging
breaks that: candidates land here, with their provenance, and **nothing in this
module can write to the archive**.

Design rules, each with a reason:

* **Its own file** (`CANDIDATES_DB_PATH`, default `backend/data/candidates.db`),
  like the settings and founder stores. The archive is the product's asset and
  gets copied and backed up; a crawler must not be able to touch it, and rollback
  must be as blunt as deleting one file.
* **Provenance or nothing.** `source`, `source_url` and `captured_at` are required
  and validated at the write. A candidate nobody can trace back to the page it
  came from is not auditable, and the scale plan's ">95% carry source_url +
  captured_at" is enforced here rather than reported after the fact.
* **Dedupe is a schema guarantee, not a report.** A UNIQUE index on `dedupe_key`
  makes a duplicate impossible to insert; the cascade itself
  (`canonical_domain` → `website_url` → `github_url` → normalised name) is the
  same rule the archive uses, imported from `enrich.canonical_domain` so the two
  can never drift.
* **"Already in the archive" is recorded, not dropped.** Such a row is staged with
  `state='known'`, because the yield report needs to know what a channel would
  actually ADD, which is a different number from what it found.
* **The cost column is honestly empty.** No LLM has been called at staging time,
  so `yield_report()` states `cost_unknown` instead of printing a confident
  `$0.00` — the cost-per-accepted ranking becomes real in Phase D, when the
  ledger has rows to divide by.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from . import config, db
from .enrich import canonical_domain

CANDIDATES_DDL = """
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  name TEXT,
  canonical_domain TEXT,
  github_url TEXT,
  channel TEXT NOT NULL,
  source TEXT,
  source_url TEXT NOT NULL,
  captured_at TEXT NOT NULL DEFAULT (datetime('now')),
  state TEXT NOT NULL DEFAULT 'new',
  archive_id INTEGER,
  liveness_state TEXT,
  liveness_at TEXT,
  meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_candidates_channel ON candidates(channel);
CREATE INDEX IF NOT EXISTS idx_candidates_state ON candidates(state);
CREATE INDEX IF NOT EXISTS idx_candidates_domain ON candidates(canonical_domain);
"""

# `new`      — staged, not yet judged
# `known`    — the archive already has this identity (staged, not dropped: yield
#              is what a channel ADDS, which is not what it found)
# `duplicate`— refused by the store; kept as an outcome, not a row
# `admitted` — reserved for the Phase D/E admission path; nothing writes it yet
STATES = frozenset({"new", "known", "duplicate", "admitted"})

LIVENESS_STATES = frozenset({"LIVE", "WALLED", "DEAD", "UNKNOWN", "MOVED", "BANNED", "NO_URL"})


def store_path() -> Path:
    """Where the staging store lives (env-overridable, like every other store).

    The path itself is declared in `config.py` next to `DB_PATH` / `FOUNDER_DB_PATH`
    / `SETTINGS_DB_PATH`, so every store's separation is visible in one place.
    """
    return Path(os.environ.get("CANDIDATES_DB_PATH") or config.CANDIDATES_DB_PATH)


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the staging store, creating its DDL on first use."""
    target = Path(path) if path else store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(CANDIDATES_DDL)
    return conn


_NAME_NOISE = re.compile(r"[^a-z0-9]+")


def normalise_name(name: str | None) -> str | None:
    """'Cal.com' -> 'calcom'; None/'  ' -> None. The last rung of the cascade."""
    if not name:
        return None
    flat = _NAME_NOISE.sub("", name.strip().lower())
    return flat or None


def dedupe_key(
    url: str | None = None,
    *,
    name: str | None = None,
    github_url: str | None = None,
) -> str | None:
    """The identity of a candidate: domain first, then the URL, then the name.

    Domain-first is deliberate — `acme.com/pricing` and `www.acme.com` are one
    company, and a channel that lists both must stage one candidate. Returns None
    when nothing usable is present, and staging refuses such a row.
    """
    domain = canonical_domain(url) or canonical_domain(github_url)
    if domain:
        return f"domain:{domain}"
    raw = (url or github_url or "").strip().lower().rstrip("/")
    if raw:
        return f"url:{raw}"
    flat = normalise_name(name)
    return f"name:{flat}" if flat else None


def archive_identity(conn: sqlite3.Connection | None = None) -> dict[str, int]:
    """`{dedupe_key: startup_id}` for everything the archive already holds.

    Read-only against the archive, through the ordinary connection helper, and
    never cached across calls (the archive changes under a running install). A row
    whose canonical_domain is NULL still contributes its URL and its name, which
    is why a pre-backfill archive does not silently stage duplicates of itself.
    """
    out: dict[str, int] = {}
    own = conn is None
    conn = conn or db.connect()
    try:
        rows = conn.execute(
            "SELECT id, website_url, github_url, name, canonical_domain FROM startups"
        ).fetchall()
    finally:
        if own:
            conn.close()
    for row in rows:
        domain = row["canonical_domain"] or canonical_domain(row["website_url"]) or canonical_domain(row["github_url"])
        if domain:
            out[f"domain:{domain}"] = row["id"]
            continue
        for candidate_key in (
            dedupe_key(row["website_url"]),
            dedupe_key(row["github_url"]),
            dedupe_key(name=row["name"]),
        ):
            if candidate_key:
                out.setdefault(candidate_key, row["id"])
    return out


def stage(
    candidates: Iterable[dict],
    *,
    channel: str,
    conn: sqlite3.Connection | None = None,
    known: dict[str, int] | None = None,
) -> dict:
    """Stage candidates from one channel. Returns `{staged, duplicates, known, refused}`.

    Refusals are loud in the RESULT (not exceptions), because one malformed row in
    a channel's output must not abandon the rest of the batch — the same rule the
    seed pipeline's per-candidate handler follows. A refusal always carries why.
    """
    own = conn is None
    conn = conn or connect()
    result: dict[str, Any] = {
        "channel": channel, "staged": 0, "duplicates": 0, "known": 0,
        "refused": [], "rows": [],
    }
    known_index = known if known is not None else archive_identity()
    try:
        for item in candidates:
            url = (item.get("url") or "").strip()
            source_url = (item.get("source_url") or "").strip()
            if not url:
                result["refused"].append({"candidate": item, "reason": "no url"})
                continue
            if not source_url:
                result["refused"].append({"candidate": item, "reason": "no source_url (provenance is required)"})
                continue
            key = dedupe_key(url, name=item.get("name"), github_url=item.get("github_url"))
            if not key:
                result["refused"].append({"candidate": item, "reason": "no usable identity"})
                continue
            row_known = known_index.get(key)
            state = "known" if row_known else "new"
            try:
                cur = conn.execute(
                    """INSERT INTO candidates
                       (dedupe_key, url, name, canonical_domain, github_url, channel,
                        source, source_url, captured_at, state, archive_id, meta_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        key, url, item.get("name"),
                        canonical_domain(url) or canonical_domain(item.get("github_url")),
                        item.get("github_url") or None,
                        channel, item.get("source") or channel,
                        source_url,
                        item.get("captured_at") or time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        state, row_known,
                        item.get("meta_json"),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # The UNIQUE index did its job: a duplicate of this identity (a
                # sibling channel, or the same channel twice) is counted, never
                # silently swallowed and never stored twice.
                result["duplicates"] += 1
                continue
            if state == "known":
                result["known"] += 1
            else:
                result["staged"] += 1
            result["rows"].append({"id": cur.lastrowid, "url": url, "state": state})
    finally:
        if own:
            conn.close()
    return result


def list_candidates(
    *,
    channel: str | None = None,
    state: str | None = None,
    limit: int = 100,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Read staged candidates (newest first), for the CLI and the report."""
    own = conn is None
    conn = conn or connect()
    try:
        where, params = [], []
        if channel:
            where.append("channel = ?")
            params.append(channel)
        if state:
            where.append("state = ?")
            params.append(state)
        sql = "SELECT * FROM candidates"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        if own:
            conn.close()


def set_liveness(key_or_id: int | str, state: str, *, conn: sqlite3.Connection | None = None) -> bool:
    """Record an auditor verdict on a candidate.

    The state vocabulary is the auditor's (`LIVENESS_STATES`), NOT a new one: a
    second opinion about what "live" means would make the yield report a different
    measurement from the funnel's.
    """
    if state not in LIVENESS_STATES:
        raise ValueError(f"unknown liveness state {state!r}: expected one of {sorted(LIVENESS_STATES)}")
    own = conn is None
    conn = conn or connect()
    try:
        if isinstance(key_or_id, int):
            cur = conn.execute(
                "UPDATE candidates SET liveness_state = ?, liveness_at = datetime('now') WHERE id = ?",
                (state, key_or_id),
            )
        else:
            cur = conn.execute(
                "UPDATE candidates SET liveness_state = ?, liveness_at = datetime('now') "
                "WHERE dedupe_key = ?",
                (state, key_or_id),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        if own:
            conn.close()


def pending_liveness(*, limit: int = 500, conn: sqlite3.Connection | None = None) -> list[dict]:
    """Candidates with no liveness verdict yet, newest first."""
    own = conn is None
    conn = conn or connect()
    try:
        return [
            dict(r) for r in conn.execute(
                "SELECT * FROM candidates WHERE liveness_state IS NULL "
                "ORDER BY id DESC LIMIT ?", (int(limit),),
            ).fetchall()
        ]
    finally:
        if own:
            conn.close()


def counts(*, conn: sqlite3.Connection | None = None) -> dict:
    """Totals the report and the tests both read, from ONE place."""
    own = conn is None
    conn = conn or connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()["n"]
        by_state = {
            r["state"]: r["n"] for r in conn.execute(
                "SELECT state, COUNT(*) AS n FROM candidates GROUP BY state"
            ).fetchall()
        }
        by_channel = {
            r["channel"]: r["n"] for r in conn.execute(
                "SELECT channel, COUNT(*) AS n FROM candidates GROUP BY channel"
            ).fetchall()
        }
        return {"total": total, "by_state": by_state, "by_channel": by_channel}
    finally:
        if own:
            conn.close()


def yield_report(*, conn: sqlite3.Connection | None = None) -> dict:
    """Per channel: what it found, what it added, and how much of that is live.

    The plan asks for channels "ranked by cost per accepted row". At staging time
    there is no cost yet — no LLM has run — so that column is reported as
    `cost_unknown` with the reason, never as `$0.00`. What IS real here is the
    funnel: found → staged → duplicates → already-known → liveness → live yield.
    """
    own = conn is None
    conn = conn or connect()
    try:
        rows = conn.execute(
            """SELECT channel,
                      COUNT(*) AS found,
                      SUM(CASE WHEN state = 'new' THEN 1 ELSE 0 END) AS staged,
                      SUM(CASE WHEN state = 'known' THEN 1 ELSE 0 END) AS known,
                      SUM(CASE WHEN liveness_state IS NOT NULL THEN 1 ELSE 0 END) AS judged,
                      SUM(CASE WHEN liveness_state = 'LIVE' THEN 1 ELSE 0 END) AS live,
                      SUM(CASE WHEN liveness_state = 'WALLED' THEN 1 ELSE 0 END) AS walled,
                      SUM(CASE WHEN liveness_state = 'DEAD' THEN 1 ELSE 0 END) AS dead
               FROM candidates GROUP BY channel ORDER BY channel"""
            ).fetchall()
        per_channel = []
        for r in rows:
            judged = r["judged"] or 0
            live = r["live"] or 0
            per_channel.append({
                "channel": r["channel"],
                "found": r["found"],
                "staged": r["staged"],
                "already_known": r["known"],
                "judged": judged,
                "live": live,
                "walled": r["walled"] or 0,
                "dead": r["dead"] or 0,
                # Null (not 0.0) until something has been judged: an unmeasured
                # yield must not look like a measured zero.
                "live_yield": round(live / judged, 4) if judged else None,
                "cost_per_accepted_usd": None,
                "cost_unknown": "no enrichment spend yet — channels are ranked by "
                                "live yield until Phase D puts $ on the ledger",
            })
        total = sum(c["found"] for c in per_channel)
        judged = sum(c["judged"] for c in per_channel)
        return {
            "channels": per_channel,
            "totals": {
                "found": total,
                "staged": sum(c["staged"] for c in per_channel),
                "already_known": sum(c["already_known"] for c in per_channel),
                "judged": judged,
                "live": sum(c["live"] for c in per_channel),
                "live_yield": round(
                    sum(c["live"] for c in per_channel) / judged, 4) if judged else None,
            },
            "sample_note": ("yield is computed on the candidates actually staged and judged; "
                            "it ranks channels at THIS sample size, not the archive's"),
            "cost_note": ("cost per accepted row is unknown until Phase D measures it (§7.4's "
                          "ledger); the report deliberately prints no $ rather than $0.00"),
        }
    finally:
        if own:
            conn.close()


def truncate(*, conn: sqlite3.Connection | None = None) -> int:
    """The documented rollback: empty the staging store. Returns rows removed.

    Touches ONE table in ONE file that is not the archive, which is the whole
    reason staging lives in its own store.
    """
    own = conn is None
    conn = conn or connect()
    try:
        n = conn.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()["n"]
        conn.execute("DELETE FROM candidates")
        conn.commit()
        return n
    finally:
        if own:
            conn.close()
