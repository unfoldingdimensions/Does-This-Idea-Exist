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

ATTRIBUTION
-----------
The ledger knows WHICH row and job a call served only because the caller says
so: `with meter.attributing(job_id=..., purpose=...):`. Contexts nest and merge,
so the seeder can stamp the job while `enrich` stamps the purpose, and neither
has to know about the other. Unset means `unattributed` — visible as such, never
guessed.

`ts` is UTC (`datetime('now')`), like every other timestamp in this app.
"""
import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar

from . import db, gateways

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

# --- attribution (which row/job a call served) -------------------------------
# A ContextVar, not a parameter: llm_json's signature stays put, so the ~8
# existing call sites and the injected-llm_fn test seam keep working untouched.
_ATTRIBUTION: ContextVar[dict] = ContextVar("llm_attribution", default={})


@contextmanager
def attributing(
    *,
    purpose: str | None = None,
    startup_id: int | None = None,
    job_id: str | None = None,
    budget_usd: float | None = None,
):
    """Stamp the calls made inside this block. Contexts nest and merge.

        with meter.attributing(job_id=job["id"]):        # the seeder
            with meter.attributing(purpose="enrich:website"):   # enrich
                llm.llm_json(...)                        # both stamped

    Only the fields passed are set, so an inner block cannot erase an outer
    one's attribution by omission. `budget_usd` is a per-job override of the
    configured cap (§7.4 task 4) — the seeder passes its job's own limit here so
    the brake does not have to reach back into the job registry.
    """
    merged = dict(_ATTRIBUTION.get())
    if purpose is not None:
        merged["purpose"] = purpose
    if startup_id is not None:
        merged["startup_id"] = startup_id
    if job_id is not None:
        merged["job_id"] = job_id
    if budget_usd is not None:
        merged["budget_usd"] = budget_usd
    token = _ATTRIBUTION.set(merged)
    try:
        yield merged
    finally:
        _ATTRIBUTION.reset(token)


def current_attribution() -> dict:
    """What a call made right now would be stamped with (a copy)."""
    return dict(_ATTRIBUTION.get())


def usage_from_response(data) -> dict:
    """Pull token counts out of an OpenAI-compatible response. Never guesses.

    Returns {"prompt_tokens", "completion_tokens", "cached_tokens",
    "total_tokens", "missing"} where every count is None when the provider did
    not send it, and `missing` is True when no `usage` block arrived at all.

    Shapes handled, because this was written without a paid probe (the gateway's
    usage block is unverified — §7.4 Open Question 4):
      * `usage.prompt_tokens` / `completion_tokens` / `total_tokens` (OpenAI-compatible)
      * `usage.prompt_tokens_details.cached_tokens` (OpenAI/DeepSeek cache read)
      * `usage.prompt_cache_hit_tokens` (DeepSeek's older field name)
    A count that arrives as a string is coerced; anything unparseable is NULL,
    because 0 and "unknown" are different facts.
    """
    out = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
        "total_tokens": None,
        "missing": True,
    }
    if not isinstance(data, dict):
        return out
    usage = data.get("usage")
    if not isinstance(usage, dict) or not usage:
        return out

    def _int(value):
        if isinstance(value, bool) or value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    out["prompt_tokens"] = _int(usage.get("prompt_tokens"))
    out["completion_tokens"] = _int(usage.get("completion_tokens"))
    out["total_tokens"] = _int(usage.get("total_tokens"))
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        out["cached_tokens"] = _int(details.get("cached_tokens"))
    if out["cached_tokens"] is None:
        out["cached_tokens"] = _int(usage.get("prompt_cache_hit_tokens"))
    # "missing" means NO token count at all came back. A response with a usage
    # block but no prompt_tokens is a provider quirk, not a missing block: it is
    # recorded with whatever arrived, and the NULLs still block a cost figure.
    out["missing"] = all(
        out[k] is None for k in ("prompt_tokens", "completion_tokens", "total_tokens")
    )
    return out


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
    """SQL SUM() is NULL over zero rows — that is the honest answer, not 0.

    Rounded to 8 decimals to match `cost_of`'s precision: a single small call is
    ~$0.0001, and rounding a per-row figure to 6dp would report $0.000097 where
    the rate table says $0.00009666."""
    return None if value is None else round(float(value), 8)


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

    Attribution (`job_id`, `purpose`, `startup_id`) is the CALLER's to pass: this
    writer records what it is handed and never reads the ambient attribution
    context itself. `llm._record_attempt` is the place that context is read, so
    the record is always explicit at the point it is written.
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
    cost = _sum_or_none(row["cost"])
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


# --- the rate table ----------------------------------------------------------
# Where the $ comes from. A tiny editable table in the settings store (one JSON
# blob under one key), because prices change and code shouldn't have to.
#
# THE HONESTY RULES, in order of importance:
#   * An unknown model is UNPRICED (NULL cost) — never estimated, never zero.
#   * A call whose tokens are unknown is UNPRICED, whatever the model costs.
#   * Every row records the rate it used (`price_used`), so editing a rate
#     changes future rows only and an old figure stays reproducible.
#   * A $ figure from this table is the MARGINAL COST at published list prices,
#     not an invoice: a flat-rate subscription (OpenCode Go, $10/month) bills
#     nothing per token, and a provider discount, a batch tier or a routed
#     fallback will not appear here. The panel and the report say so.
RATES_KEY = "llm_rates"

# The published prices, cited. `as_of` is the date the page was read, and the
# source URL is stored per row so an operator can re-check it. Cache columns are
# per 1M tokens in USD: `cached_input` is what a cache READ costs (our calls
# only ever read) and `cached_write` is recorded when the provider publishes it.
DEFAULT_RATES_SOURCE = "https://opencode.ai/docs/zen"
DEFAULT_RATES_AS_OF = "2026-09-28"
DEFAULT_RATES: dict[str, dict] = {
    # OpenCode Zen's published table, transcribed 2026-09-28. The project's
    # default gateway (opencode-go) serves the same model ids.
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28, "cached_input": 0.028},
    "deepseek-v4-pro": {"input": 1.74, "output": 3.48, "cached_input": 0.145},
    "glm-5.3-flash": {"input": 0.15, "output": 0.50, "cached_input": 0.03},
    "glm-5.3": {"input": 1.40, "output": 4.40, "cached_input": 0.26},
    "kimi-k2.5": {"input": 0.60, "output": 3.00, "cached_input": 0.10},
    "qwen3.7-plus": {"input": 0.40, "output": 1.60, "cached_input": 0.04,
                     "cached_write": 0.50},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00, "cached_input": 0.30,
                          "cached_write": 3.75,
                          "notes": "the published <=200K-token tier only; the "
                                   ">200K tier is $6.00/$22.50/$0.60 and is NOT "
                                   "what this row prices"},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00, "cached_input": 0.15},
    # The Google gateway's own default model. Left UNPRICED on purpose: the
    # pricing page read on 2026-09-28 no longer names 2.5 Flash in its tables
    # (its Flash blocks are unnamed in the captured text), and a guessed rate is
    # exactly the fabricated number this module exists to prevent. Fill these two
    # numbers in from the console and every Gemini-routed call prices itself.
    "gemini-2.5-flash": {
        "input": None, "output": None, "cached_input": None,
        "source": "https://ai.google.dev/gemini-api/docs/pricing",
        "as_of": DEFAULT_RATES_AS_OF,
        "verified": False,
        "notes": "confirm the current 2.5 Flash input/output/cached rates in the "
                 "Google AI console, then edit this row (Admin -> Usage) — until "
                 "then Gemini calls are recorded unpriced, which is honest",
    },
}

_RATES_MEMO: dict = {"raw": None, "parsed": None}


def _rate_version(rates: dict) -> str:
    """A short stable id for a rate table, so a row can name the rates it used."""
    canonical = json.dumps(rates, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]


def _clean_rate_row(row: dict) -> dict:
    """Normalise one stored row; keep only the fields the pricer reads."""
    out = {}
    for field in ("input", "output", "cached_input", "cached_write"):
        value = row.get(field)
        if value is None or value == "":
            out[field] = None
        else:
            try:
                out[field] = float(value)
            except (TypeError, ValueError):
                out[field] = None
    for field in ("source", "as_of", "notes"):
        text = row.get(field)
        out[field] = (str(text).strip() or None) if text else None
    out["verified"] = bool(row.get("verified", True))
    return out


def _parse_stored(raw: str) -> dict | None:
    """The stored table, or None when there is none / it is unreadable.

    None is the answer for BOTH "never edited" and "the stored blob is junk":
    callers that ask for the effective table fall back to the built-ins either
    way, and `rates_source` reports the origin as built-in — because pricing off
    a table nobody can read would be worse than pricing off the cited defaults.
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("rate table is not an object")
        return {str(k): _clean_rate_row(v if isinstance(v, dict) else {})
                for k, v in parsed.items()}
    except Exception as exc:  # noqa: BLE001 — bad JSON must not break every call
        log.warning("stored rate table is unreadable (%s); using the built-ins", exc)
        return None


def load_rates(stored_only: bool = False) -> dict | None:
    """The active rate table: the operator's stored edits, else the built-ins.

    Defaults live in code (cited, dated) so pricing works on a fresh install
    without a boot-time write; `save_rates` persists an edit and from then on the
    stored table wins. `clear_rates()` removes the override.

    `stored_only=True` answers "has anyone edited this?" — the stored table, or
    **None** when nothing valid is stored (an empty dict is a deliberate "no
    rates", which is a different thing from "never edited").
    """
    raw = ""
    try:
        raw = gateways.get_setting(RATES_KEY)
    except Exception as exc:  # noqa: BLE001 — a settings read must not break pricing
        log.warning("rate table unreadable (%s); using built-ins", exc)
    stored = _parse_stored(raw)
    if stored_only:
        return stored
    if _RATES_MEMO["raw"] == raw and _RATES_MEMO["parsed"] is not None:
        return _RATES_MEMO["parsed"]
    effective = stored if stored is not None else _default_table()
    _RATES_MEMO.update({"raw": raw, "parsed": effective})
    return effective


def _default_table() -> dict:
    """The built-in table with the citation stamped onto EVERY row.

    The source and the date it was read are per-row, not global, because a table
    can mix providers (Zen's list prices for the coding models, Google's page for
    the Gemini one) and a figure without its source is not verifiable later.
    """
    out = {}
    for model, row in DEFAULT_RATES.items():
        clean = _clean_rate_row(row)
        clean["source"] = clean["source"] or DEFAULT_RATES_SOURCE
        clean["as_of"] = clean["as_of"] or DEFAULT_RATES_AS_OF
        out[model] = clean
    return out


def save_rates(rates: dict) -> dict:
    """Persist an edited rate table. Returns the stored form.

    Invalid JSON never gets in: every row is normalised first, and a rate that
    cannot be read as a number becomes NULL (unpriced) rather than 0 (free).
    """
    clean = {str(k): _clean_rate_row(v if isinstance(v, dict) else {})
             for k, v in (rates or {}).items()}
    payload = json.dumps(clean, sort_keys=True, indent=2)
    gateways.set_setting(RATES_KEY, payload)
    _RATES_MEMO.update({"raw": None, "parsed": None})
    return clean


def clear_rates() -> None:
    """Drop the stored override, returning to the cited built-in table."""
    gateways.set_setting(RATES_KEY, "")
    _RATES_MEMO.update({"raw": None, "parsed": None})


def rates_source(rates: dict | None = None) -> dict:
    """"builtin" or "stored", plus the version id — what a $ figure cites."""
    stored = load_rates(stored_only=True)
    table = load_rates() if rates is None else rates
    return {
        "origin": "stored" if stored is not None else "builtin",
        "version": _rate_version(table or {}),
        "models": len(table or {}),
        "as_of": _max_as_of(table or {}),
        "source": DEFAULT_RATES_SOURCE,
    }


def _max_as_of(table: dict) -> str | None:
    dates = [r.get("as_of") for r in table.values() if r.get("as_of")]
    return max(dates) if dates else None


def rate_for(model: str | None, rates: dict | None = None) -> dict | None:
    """The rate row for a model id, or None. Never invents one."""
    if not model:
        return None
    table = (load_rates() if rates is None else rates) or {}
    return table.get(str(model))


def cost_of(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_tokens: int | None = None,
    rates: dict | None = None,
) -> tuple[float | None, str]:
    """Price one attempt. Returns (cost_usd | None, price_used).

    `price_used` is "<model>@<version>" when the row was priced, and
    "unpriced:<reason>" when it was not — so a NULL cost always states WHY. The
    reasons are the facts a reader needs to fix it:

      unpriced:no-usage        the provider sent no token counts
      unpriced:no-rate         this model has no row in the rate table
      unpriced:empty-rate      the row exists but its rates are not filled in
      unpriced:no-cached-rate  cache hits happened and no cache rate is known
      unpriced:cached>prompt   the counts disagree (cache cannot exceed input)

    Cache accounting: `cached_tokens` are a SUBSET of `prompt_tokens` in the
    OpenAI-compatible APIs this app talks to, so cache reads are billed at the
    cache rate and the rest of the prompt at the input rate. Anything that does
    not fit that shape is left unpriced rather than billed wrongly.
    """
    table = (load_rates() if rates is None else rates) or {}
    version = _rate_version(table)
    if not model:
        return None, "unpriced:no-rate"
    if prompt_tokens is None or completion_tokens is None:
        return None, "unpriced:no-usage"
    row = table.get(str(model))
    if row is None:
        return None, "unpriced:no-rate"
    cached = int(cached_tokens or 0)
    if cached and row.get("cached_input") is None:
        return None, "unpriced:no-cached-rate"
    if cached > int(prompt_tokens):
        return None, "unpriced:cached>prompt"
    rate_in, rate_out = row.get("input"), row.get("output")
    if rate_in is None or rate_out is None:
        return None, "unpriced:empty-rate"
    billable_input = int(prompt_tokens) - cached
    cost = (
        (billable_input / 1_000_000) * rate_in
        + (cached / 1_000_000) * (row.get("cached_input") or 0)
        + (int(completion_tokens) / 1_000_000) * rate_out
    )
    return round(cost, 8), f"{model}@{version}"


def price_attempt(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_tokens: int | None = None,
    rates: dict | None = None,
) -> tuple[float | None, str]:
    """`cost_of` with the rate table read once and never raising — the form
    `llm`'s per-attempt recorder calls."""
    try:
        return cost_of(model, prompt_tokens, completion_tokens, cached_tokens, rates)
    except Exception as exc:  # noqa: BLE001 — pricing must not break a call either
        log.warning("pricing failed for %s (%s); recording unpriced", model, exc)
        return None, "unpriced:price-error"


# --- the pacemaker: a per-job budget that PARKS, not a suggestion ------------
# §7.4's "per-batch hard budget". The design rule from the user's answers: on
# breach the job PARKS at the next per-candidate boundary with everything already
# written left in place — it does not fail, roll back, or silently carry on.
#
# SCOPE IS PER JOB, and that is a decision, not an oversight: a call that belongs
# to no job is not braked by this, because the configured cap describes a batch.
# The panel shows spend for both, so an un-jobbed call is visible even though it
# is unbudgeted.
BUDGET_KEY = "llm_budget_usd"


class BudgetExceeded(RuntimeError):
    """The spend brake fired. Carries the numbers: "budget exceeded" with no
    figures is not actionable, and neither is a $ that hides what it covers.

    `kind` distinguishes WHY the batch stopped — "budget" (the cap was reached)
    from "metering" (the ledger could not be read, so the cap could not be
    checked). A job records it as `stop_reason`, so an operator never has to guess
    which of the two happened.
    """

    kind = "budget"

    def __init__(
        self,
        *,
        spend_usd: float | None,
        cap_usd: float,
        rate_version: str,
        job_id: str | None,
        scope: str = "job",
        cost_complete: bool = True,
    ):
        self.spend_usd = spend_usd
        self.cap_usd = cap_usd
        self.rate_version = rate_version
        self.job_id = job_id
        self.scope = scope
        self.cost_complete = cost_complete
        if spend_usd is None:
            detail = (f"the spend ledger could not be read, so a ${cap_usd:.4f} "
                      f"{scope} cap could not be checked")
        else:
            floor = "" if cost_complete else " (a FLOOR — this job has unpriced calls)"
            detail = (f"spent ${spend_usd:.4f}{floor} of a ${cap_usd:.4f} "
                      f"{scope} cap (rates {rate_version})")
        super().__init__(f"LLM spend brake stopped {scope} {job_id}: {detail}")


class LedgerUnreadable(BudgetExceeded):
    """The brake could not read the ledger, so it cannot prove the job is under
    its cap. It fails CLOSED and says so.

    Deliberately a BudgetExceeded: every caller that already stops a batch on the
    brake handles this with no extra wiring, and `kind` keeps the two cases
    distinguishable in the job's own record. Failing OPEN was the alternative and
    it is the wrong default for a guard rail — a brake that silently disables
    itself when its meter is unreadable is not a brake.
    """

    kind = "metering"

    def __init__(self, *, cap_usd: float, job_id: str | None, cause: str,
                 scope: str = "job"):
        self.cause = cause
        super().__init__(spend_usd=None, cap_usd=cap_usd, rate_version="unknown",
                         job_id=job_id, scope=scope, cost_complete=False)
        self.args = (f"{self.args[0]} — {cause}",)


def budget_setting() -> dict:
    """The configured per-job cap. Unset = unlimited = the pre-metering product."""
    raw = ""
    try:
        raw = (gateways.get_setting(BUDGET_KEY) or "").strip()
    except Exception as exc:  # noqa: BLE001 — a settings read must not break a call
        log.warning("budget setting unreadable (%s); treating it as unlimited", exc)
        return {"budget_usd": None, "raw": "", "source": "unreadable", "parse_error": str(exc)}
    if not raw:
        return {"budget_usd": None, "raw": "", "source": "unset", "parse_error": None}
    try:
        value = float(raw)
    except ValueError:
        # NOT silently unlimited-with-no-trace: the read endpoint reports it, so
        # an operator who typed "ten dollars" can see why nothing is braked.
        return {"budget_usd": None, "raw": raw, "source": "invalid",
                "parse_error": f"{raw!r} is not a number of USD"}
    if value < 0:
        return {"budget_usd": None, "raw": raw, "source": "invalid",
                "parse_error": "a budget cannot be negative"}
    return {"budget_usd": value, "raw": raw, "source": "setting", "parse_error": None}


def set_budget(value) -> dict:
    """Set the per-job cap; None or "" clears it. Raises ValueError on junk."""
    if value is None or value == "":
        gateways.set_setting(BUDGET_KEY, "")
        return budget_setting()
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"budget_usd must be a number of USD or null, got {value!r}") from None
    if number < 0:
        raise ValueError("budget_usd must be >= 0 (use null for unlimited)") from None
    gateways.set_setting(BUDGET_KEY, str(number))
    return budget_setting()


def effective_budget(job_budget=None) -> float | None:
    """The cap for this call: a job's own limit wins, else the setting."""
    if job_budget is not None and job_budget != "":
        try:
            value = float(job_budget)
        except (TypeError, ValueError):
            log.warning("job budget %r is not a number — falling back to the setting", job_budget)
        else:
            if value >= 0:
                return value
            log.warning("job budget %r is negative — falling back to the setting", job_budget)
    return budget_setting()["budget_usd"]


def budget_status(job_id: str | None = None, job_budget=None) -> dict:
    """Where the brake stands — what the admin endpoint and panel report.

    Never raises: an unreadable ledger (a store that has not been migrated yet,
    a locked file) is REPORTED as `ledger_error` with the spend left unknown,
    because a 500 on the panel tells the operator nothing and hides the state
    that actually needs attention.
    """
    where = current_attribution()
    resolved_job = job_id if job_id is not None else where.get("job_id")
    resolved_override = job_budget if job_budget is not None else where.get("budget_usd")
    setting = budget_setting()
    cap = effective_budget(resolved_override)
    ledger_error = None
    try:
        spend = spend_usd(job_id=resolved_job)
    except Exception as exc:  # noqa: BLE001 — reported, not raised (see docstring)
        spend = {}
        ledger_error = str(exc)
    cost = spend.get("cost_usd")
    rates = rates_source()
    return {
        "scope": "job",
        "job_id": resolved_job,
        # Which window the spend figure covers: a job's own ledger rows, or (with
        # no job in context) this install's whole history. Never blurred.
        "spend_window": "job" if resolved_job else "all-time",
        "ledger_error": ledger_error,
        "budget_usd": cap,
        "budget_source": ("job" if resolved_override is not None and cap is not None
                          else setting["source"]),
        "parse_error": setting["parse_error"],
        # A $ from a ledger with unpriced rows is a floor and says so. An EMPTY
        # window is not a floor — there is nothing there to be incomplete.
        "spend_usd": cost,
        "spend_is_floor": bool(spend.get("attempts")) and not bool(spend.get("cost_complete")),
        "attempts": spend.get("attempts"),
        "unpriced_attempts": spend.get("unpriced_attempts"),
        "remaining_usd": None if cap is None else round(max(0.0, cap - (cost or 0.0)), 8),
        "over_budget": None if cap is None else (cost or 0.0) >= cap,
        # Enforcement needs BOTH a cap and a job: this is a per-job brake.
        "enforced": bool(cap is not None and resolved_job),
        "rate_version": rates["version"],
        "rates_origin": rates["origin"],
    }


def check_budget(job_id: str | None = None, job_budget=None) -> None:
    """Raise BudgetExceeded if this job has spent its cap. Called before every
    attempt, so a retry cannot slip past a cap the first attempt just reached.

    Unlimited (the default) returns immediately — that path is pinned by a test
    to be byte-identical to the product before §7.4 existed.

    If the ledger cannot be READ, this raises LedgerUnreadable (a BudgetExceeded
    with kind="metering") rather than letting a raw sqlite3 error escape into
    llm_json, where it would be misreported as a failed LLM attempt. Fails closed:
    an unverifiable cap is not a satisfied cap.
    """
    where = current_attribution()
    resolved_job = job_id if job_id is not None else where.get("job_id")
    resolved_override = job_budget if job_budget is not None else where.get("budget_usd")
    cap = effective_budget(resolved_override)
    if cap is None or not resolved_job:
        return
    try:
        spend = spend_usd(job_id=resolved_job)
    except Exception as exc:  # noqa: BLE001 — a blind brake must stop, loudly
        log.error("spend ledger unreadable for job %s (%s) — stopping the batch", resolved_job, exc)
        raise LedgerUnreadable(cap_usd=cap, job_id=resolved_job, cause=str(exc)) from exc
    cost = spend.get("cost_usd") or 0.0
    if cost >= cap:
        raise BudgetExceeded(
            spend_usd=cost,
            cap_usd=cap,
            rate_version=rates_source()["version"],
            job_id=resolved_job,
            cost_complete=bool(spend.get("cost_complete")),
        )


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
