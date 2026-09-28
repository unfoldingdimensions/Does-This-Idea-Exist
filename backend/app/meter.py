"""LLM usage ledger — one row per ATTEMPT, so a $ figure is a measurement.

WHY THIS EXISTS
---------------
Scale plan §7.4 ("token accounting, $/row, concurrency cap, per-batch hard
budget") and Phase D, whose entire output is a measured $/row. Until this
module existed, `docs/llm-gateways.md` §6 said so in writing: "no usage/cost
accounting". The product spent tokens on every seed, enrich and teardown with
nothing recorded anywhere.

THE RULES THIS MODULE KEEPS
---------------------------
1. **`record()` never raises.** A ledger write must not fail an enrichment — but
   it must not be silent either. A failed write bumps a counter that the log,
   the admin panel and `failure_count()` surface. A quiet hole in a cost ledger
   is exactly the failure mode this module exists to close.
2. **Rows are per ATTEMPT, not per call.** `llm.llm_json` retries once and the
   provider bills both attempts; a per-call ledger would understate the bill by
   precisely what the retries cost.
3. **NULL means "not known", never zero.** A response with no `usage` block
   stores NULL tokens with `usage_missing=1`; a model with no rate stores NULL
   cost (see `prices`). Nothing is ever estimated into a number that looks
   measured — an invented figure is worse than a missing one.
4. **History is immutable.** Every row stores the rate it was priced with
   (`price_used`), so editing a rate changes future rows only.

`ts` is UTC (`datetime('now')`), like every other timestamp in this app.
"""
import logging
import sqlite3

from . import db

log = logging.getLogger("meter")

ATTEMPT_ROWS_DDL = """
CREATE TABLE IF NOT EXISTS llm_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  model TEXT,
  gateway_id TEXT,
  purpose TEXT,
  startup_id INTEGER,
  job_id TEXT,
  attempt INTEGER NOT NULL DEFAULT 1,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  cached_tokens INTEGER,
  total_tokens INTEGER,
  duration_ms INTEGER,
  ok INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  usage_missing INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL,
  price_used TEXT
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_ts ON llm_usage(ts);
CREATE INDEX IF NOT EXISTS idx_llm_usage_job ON llm_usage(job_id);
"""

# --- write-failure telemetry (rule 1) ---------------------------------------
_failures = 0
_last_failure: str | None = None


def failure_count() -> int:
    """How many usage rows failed to write since process start.

    Surfaced (never swallowed): the admin panel shows it, and a non-zero value
    means the spend numbers are a FLOOR, not the bill.
    """
    return _failures


def last_failure() -> str | None:
    """The most recent write failure's text, for the panel/log."""
    return _last_failure


def reset_failure_counter() -> None:
    """Test seam: clears the counters (they are process-global by design)."""
    global _failures, _last_failure
    _failures = 0
    _last_failure = None


def _sum_or_none(value):
    """SQL SUM() is NULL over zero rows — that is the honest answer, not 0."""
    return None if value is None else round(float(value), 6)


def record(
    *,
    model: str | None = None,
    gateway_id: str | None = None,
    purpose: str | None = None,
    startup_id: int | None = None,
    job_id: str | None = None,
    attempt: int = 1,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cached_tokens: int | None = None,
    total_tokens: int | None = None,
    duration_ms: int | None = None,
    ok: bool = False,
    error: str | None = None,
    usage_missing: int | bool = False,
    cost_usd: float | None = None,
    price_used: str | None = None,
) -> dict:
    """Append one attempt to the ledger. Returns {"recorded": bool, ...}.

    Never raises (rule 1). `total_tokens` is filled from prompt+completion when
    the provider did not send it and the parts are known; when nothing is known
    it stays NULL and `usage_missing` is set by the caller.
    """
    global _failures, _last_failure
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = int(prompt_tokens) + int(completion_tokens)
    try:
        conn = db.connect()
        try:
            conn.execute(
                """INSERT INTO llm_usage
                   (model, gateway_id, purpose, startup_id, job_id, attempt,
                    prompt_tokens, completion_tokens, cached_tokens, total_tokens,
                    duration_ms, ok, error, usage_missing, cost_usd, price_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model, gateway_id, purpose, startup_id, job_id, int(attempt or 1),
                    prompt_tokens, completion_tokens, cached_tokens, total_tokens,
                    duration_ms, 1 if ok else 0, error, 1 if usage_missing else 0,
                    cost_usd, price_used,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return {"recorded": True}
    except Exception as exc:  # noqa: BLE001 — a ledger write must not fail a call
        _failures += 1
        _last_failure = str(exc)
        log.warning("llm usage row NOT recorded: %s", exc)
        return {"recorded": False, "error": str(exc)}


def _where(since: str | None, job_id: str | None, purpose: str | None = None) -> tuple[str, list]:
    conds: list[str] = []
    params: list = []
    if since:
        conds.append("ts >= ?")
        params.append(since)
    if job_id is not None:
        conds.append("job_id = ?")
        params.append(job_id)
    if purpose is not None:
        conds.append("purpose = ?")
        params.append(purpose)
    return (" WHERE " + " AND ".join(conds) if conds else ""), params


def rows(
    limit: int = 100,
    since: str | None = None,
    job_id: str | None = None,
    purpose: str | None = None,
) -> list[dict]:
    """The raw ledger, newest first — what the panel's table shows."""
    where, params = _where(since, job_id, purpose)
    conn = db.connect()
    try:
        cur = conn.execute(
            f"SELECT * FROM llm_usage{where} ORDER BY id DESC LIMIT ?",
            [*params, int(limit)],
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def spend_usd(since: str | None = None, job_id: str | None = None) -> dict:
    """Total spend in a window, WITH its own completeness stated.

    `cost_complete` is False when any row in the window has a NULL cost (an
    unpriced model, or a call whose usage never arrived). A caller that prints
    the number without that flag is quoting a partial sum as a total.
    """
    where, params = _where(since, job_id)
    conn = db.connect()
    try:
        row = conn.execute(
            f"""SELECT COUNT(*) AS attempts,
                       SUM(cost_usd) AS cost,
                       SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) AS unpriced,
                       SUM(total_tokens) AS tokens,
                       SUM(CASE WHEN usage_missing = 1 THEN 1 ELSE 0 END) AS missing
                FROM llm_usage{where}""",
            params,
        ).fetchone()
    finally:
        conn.close()
    attempts = int(row["attempts"] or 0)
    unpriced = int(row["unpriced"] or 0)
    return {
        "attempts": attempts,
        "cost_usd": _sum_or_none(row["cost"]),
        "cost_complete": attempts > 0 and unpriced == 0,
        "unpriced_attempts": unpriced,
        "total_tokens": None if row["tokens"] is None else int(row["tokens"]),
        "usage_missing_attempts": int(row["missing"] or 0),
        "metering_failures": _failures,
    }


def totals(since: str | None = None) -> dict:
    """Spend + attempts + the metering-failure count for a window."""
    out = spend_usd(since=since)
    out["since"] = since
    return out


def by_purpose(since: str | None = None) -> list[dict]:
    """Attempts, tokens and spend grouped by what the call was for."""
    where, params = _where(since, None)
    conn = db.connect()
    try:
        cur = conn.execute(
            f"""SELECT COALESCE(purpose, 'unattributed') AS purpose,
                       COUNT(*) AS attempts,
                       SUM(ok) AS ok_attempts,
                       SUM(total_tokens) AS tokens,
                       SUM(cost_usd) AS cost,
                       SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) AS unpriced
                FROM llm_usage{where}
                GROUP BY COALESCE(purpose, 'unattributed')
                ORDER BY attempts DESC""",
            params,
        )
        return [
            {
                "purpose": r["purpose"],
                "attempts": int(r["attempts"] or 0),
                "ok_attempts": int(r["ok_attempts"] or 0),
                "total_tokens": None if r["tokens"] is None else int(r["tokens"]),
                "cost_usd": _sum_or_none(r["cost"]),
                "unpriced_attempts": int(r["unpriced"] or 0),
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def by_model(since: str | None = None) -> list[dict]:
    """Attempts, tokens and spend grouped by model — the rate table's audit."""
    where, params = _where(since, None)
    conn = db.connect()
    try:
        cur = conn.execute(
            f"""SELECT COALESCE(model, '(unknown)') AS model,
                       COUNT(*) AS attempts,
                       SUM(total_tokens) AS tokens,
                       SUM(cost_usd) AS cost,
                       SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) AS unpriced
                FROM llm_usage{where}
                GROUP BY COALESCE(model, '(unknown)')
                ORDER BY attempts DESC""",
            params,
        )
        return [
            {
                "model": r["model"],
                "attempts": int(r["attempts"] or 0),
                "total_tokens": None if r["tokens"] is None else int(r["tokens"]),
                "cost_usd": _sum_or_none(r["cost"]),
                "unpriced_attempts": int(r["unpriced"] or 0),
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def job_summary(job_id: str) -> dict:
    """The Phase D number: per-job tokens/row and $/row, with the caveats.

    `rows_touched` counts DISTINCT startup_ids, so a retried candidate does not
    inflate the row count and a per-row figure is not quietly divided by
    attempts instead of products.
    """
    conn = db.connect()
    try:
        row = conn.execute(
            """SELECT COUNT(*) AS attempts,
                      SUM(ok) AS ok_attempts,
                      SUM(CASE WHEN attempt > 1 THEN 1 ELSE 0 END) AS retried,
                      COUNT(DISTINCT CASE WHEN startup_id IS NOT NULL THEN startup_id END) AS rows_touched,
                      SUM(prompt_tokens) AS prompt_tokens,
                      SUM(completion_tokens) AS completion_tokens,
                      SUM(cached_tokens) AS cached_tokens,
                      SUM(total_tokens) AS total_tokens,
                      SUM(cost_usd) AS cost,
                      SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) AS unpriced,
                      SUM(CASE WHEN usage_missing = 1 THEN 1 ELSE 0 END) AS missing
               FROM llm_usage WHERE job_id = ?""",
            (job_id,),
        ).fetchone()
    finally:
        conn.close()

    attempts = int(row["attempts"] or 0)
    touched = int(row["rows_touched"] or 0)
    tokens = None if row["total_tokens"] is None else int(row["total_tokens"])
    cost = None if row["cost"] is None else round(float(row["cost"]), 6)
    return {
        "job_id": job_id,
        "attempts": attempts,
        "ok_attempts": int(row["ok_attempts"] or 0),
        "failed_attempts": attempts - int(row["ok_attempts"] or 0),
        "retried_attempts": int(row["retried"] or 0),
        "rows_touched": touched,
        "prompt_tokens": None if row["prompt_tokens"] is None else int(row["prompt_tokens"]),
        "completion_tokens": None if row["completion_tokens"] is None else int(row["completion_tokens"]),
        "cached_tokens": None if row["cached_tokens"] is None else int(row["cached_tokens"]),
        "total_tokens": tokens,
        "cost_usd": cost,
        "cost_complete": attempts > 0 and int(row["unpriced"] or 0) == 0,
        "unpriced_attempts": int(row["unpriced"] or 0),
        "usage_missing_attempts": int(row["missing"] or 0),
        "tokens_per_row": (tokens / touched) if (tokens is not None and touched) else None,
        "cost_per_row": (cost / touched) if (cost is not None and touched) else None,
        "metering_failures": _failures,
    }


def count(job_id: str | None = None) -> int:
    """How many ledger rows exist (optionally for one job)."""
    where, params = _where(None, job_id)
    conn = db.connect()
    try:
        return int(conn.execute(f"SELECT COUNT(*) AS c FROM llm_usage{where}", params).fetchone()["c"])
    finally:
        conn.close()


def table_present() -> bool:
    """True when the ledger table exists — a legacy DB that has not run
    init_db() yet answers False rather than raising (the ensure() guard)."""
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_usage'"
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()
