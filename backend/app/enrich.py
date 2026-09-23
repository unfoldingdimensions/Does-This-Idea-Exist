"""Seed orchestration: GitHub link → fetch + LLM profile → upsert.
Website → fetch homepage + Wayback date + LLM profile → upsert.
Re-seeding an existing URL UPDATES the entry (additive, never duplicates)."""
import json
import logging
import sqlite3
from urllib.parse import urlparse

from . import db, github as gh, llm, website as ws
from .liveness_rules import load_config as _lr_load_config, regdom as _lr_regdom

log = logging.getLogger("ideasexist")

# The columns _upsert_inner is allowed to write. It builds its INSERT/UPDATE
# column list from this tuple, so a column that exists in the schema but is
# missing here is SILENTLY DROPPED — no error, no warning, and the migration
# still looks correct. Every column in db.NEW_STARTUP_COLUMNS must be listed
# here (scripts/phase1-verify.py asserts the two agree).
UPDATABLE = [
    "name", "tagline", "description", "category", "website_url", "github_url",
    "founded", "stars", "language", "source",
    # --- F-01 teardown columns (all nullable; written as they are captured) ---
    "entity_type", "canonical_domain", "aliases",
    "problem_statement", "target_users",
    "product_url", "docs_url", "demo_url", "app_store_url", "play_store_url",
    "pricing_json", "pricing_captured_at", "pricing_source_url",
    "features_json", "positioning", "content_notes",
    "activity_checked_at", "activity_summary",
    "last_human_reviewed_at", "review_notes",
    # --- provenance (F-05) / founded-date provenance (F-04) ---
    "provenance", "date_source",
]

# LLM output bounds (L1 hardening): the evidence text is attacker-influenced
# (anyone can point a seed at their own site), so the LLM profile is untrusted
# input. Length caps keep the DB sane; the category whitelist mirrors the
# system prompt's enum and falls back to "other".
CATEGORIES = {
    "productivity", "ai", "devtools", "desktop", "freelance", "finance",
    "health", "education", "ecommerce", "social", "media", "other",
}
NAME_MAX, TAGLINE_MAX, DESCRIPTION_MAX = 120, 300, 4000

# --- F-05 provenance flags -------------------------------------------------
# Everything the model drafts is machine_drafted until a human confirms it;
# nothing generated may reach the archive without that marker.
MACHINE_DRAFTED = "machine_drafted"
HUMAN_CONFIRMED = "human_confirmed"
PROVENANCE_VALUES = (MACHINE_DRAFTED, HUMAN_CONFIRMED, "sourced", "unknown")

# The tables mark_human_confirmed may stamp. A whitelist, not a parameter: the
# table name goes into the SQL text, so it may never come from a caller.
CONFIRMABLE_TABLES = ("startups", "founder_apps")

# The fields the LLM drafts. `founded` is machine-derived too (LLM extraction,
# Wayback or RDAP) and is in the list because the app presents it as a fact.
GENERATED_TEXT_FIELDS = (
    "tagline", "description", "category", "features_json", "positioning", "founded",
)


def _existing_provenance(existing) -> str | None:
    """The provenance marker already on a row, or None. Defensive: a Row from
    a DB that predates the column must not raise mid-seed."""
    if existing is None:
        return None
    try:
        return existing["provenance"]
    except (IndexError, KeyError):
        return None


def stamp_provenance(values: dict, existing=None) -> dict:
    """F-05: mark a payload carrying LLM-drafted text as machine_drafted.

    Called by both seed paths and again inside _upsert as a safety net, so no
    generated text can be written without a marker. An explicit `provenance`
    in the payload always wins (a human-authored write), and a marker already
    on the row is never downgraded by a metadata-only refresh (reuse_profile,
    which rewrites `founded` from Wayback/RDAP and must not overwrite a
    human_confirmed row).
    """
    if not any(values.get(f) for f in GENERATED_TEXT_FIELDS):
        return values
    if values.get("provenance"):
        return values
    if _existing_provenance(existing):
        return values
    values["provenance"] = MACHINE_DRAFTED
    return values


def mark_human_confirmed(conn: sqlite3.Connection, startup_id: int, table: str = "startups") -> int:
    """F-05, human half: flip a machine-drafted row to human_confirmed.

    Phase 2 wires this to the founder-app confirm path (F-13) — which is why the
    table is selectable: the founder's record carries the same column shape and
    the same marker. It is deliberately NOT wired to the liveness approve gate
    (verify.approve_suggested): an Admin Verified stamp describes the business,
    not the accuracy of its marketing copy, and badges never attach to claims.
    """
    if table not in CONFIRMABLE_TABLES:
        raise ValueError(f"refusing to mark {table!r} human_confirmed")
    cur = conn.execute(
        f"UPDATE {table} SET provenance = ?, updated_at = datetime('now') WHERE id = ?",
        (HUMAN_CONFIRMED, startup_id),
    )
    conn.commit()
    return cur.rowcount


def _clean_profile(profile: dict) -> dict:
    """Bound and whitelist an LLM profile before it touches the DB."""
    return {
        "name": _text(profile.get("name"))[:NAME_MAX],
        "tagline": _text(profile.get("tagline"))[:TAGLINE_MAX],
        "description": _text(profile.get("description"))[:DESCRIPTION_MAX],
        "category": _category(profile.get("category")),
        "founded": profile.get("founded"),
    }


def _category(value) -> str:
    """Resolve the LLM's category against CATEGORIES; anything else → "other".

    The whitelist mirrors the system prompt's enum, but the model is free to
    ignore it and the evidence text is attacker-influenced (anyone can point a
    seed at their own site). Category also becomes a facet in the frontend
    filter bar, which assumes this fixed set.
    """
    cat = _text(value)[:40].lower()
    return cat if cat in CATEGORIES else "other"


def _http_url(raw: str | None) -> str:
    """Keep only http(s) URLs; return "" for anything else.

    GitHub's `homepage` is owner-controlled free text that lands in
    `website_url`, which the frontend renders straight into an href — a
    `javascript:` value there is a click-to-execute sink, and a bare
    `example.com` is a broken relative link. Bare hosts are common and
    legitimate in that field, so they get https:// rather than a rejection.
    """
    u = (raw or "").strip()
    if not u:
        return ""
    parsed = urlparse(u)
    if parsed.scheme:  # explicit scheme must be one we allow
        return u if parsed.scheme in ("http", "https") and parsed.hostname else ""
    return f"https://{u}" if urlparse(f"https://{u}").hostname else ""


def _text(value) -> str:
    """Coerce an LLM profile value to trimmed text.

    deepseek-v4-flash occasionally emits numbers for string fields
    ({"name": 2024}) — str() keeps the seed path alive instead of crashing
    on .strip(). None/empty → "" (falls through to the caller's fallback).
    """
    if value is None:
        return ""
    return str(value).strip()


def _build_evidence(parts: dict) -> str:
    return json.dumps({k: v for k, v in parts.items() if v}, ensure_ascii=False)


def draft_from_page(page: dict, domain: str, name_hint: str | None = None) -> dict:
    """Draft the identity profile from an ALREADY-fetched homepage.

    ONE place produces the website draft, so the founder's own app (F-10, the URL
    path) is drafted by exactly the primitive that drafts a competitor — same
    evidence, same prompt, same bounds. Returns the cleaned profile and the
    chosen name; the caller owns the DB writes.
    """
    evidence = _build_evidence({
        "page_title": page["title"],
        "meta_description": page["meta_description"],
        "homepage_text_excerpt": page["text"][:6000],
    })
    user = "Generate a startup profile from this website evidence:\n" + evidence
    if name_hint:
        user = f"The startup's name is: {name_hint}\n" + user
    profile = _clean_profile(llm.llm_json(user))
    name = _text(profile.get("name")) or _text(name_hint) or domain or ""
    if not name:
        raise RuntimeError("LLM returned no name")
    return {"page": page, "domain": domain, "profile": profile, "name": name}


def draft_from_website(website_url: str, name_hint: str | None = None) -> dict:
    """Fetch a homepage and draft the identity profile from it."""
    page = ws.fetch_homepage(website_url)
    return draft_from_page(page, urlparse(page["final_url"]).netloc, name_hint)


def values_from_record(record) -> dict:
    """An UPDATABLE-shaped values dict built from an existing record.

    Used by the founder-app approval to create the archive row THROUGH THE
    NORMAL WRITER (_upsert, with its dedup and its provenance stamp) instead of a
    second INSERT path that would drift. Only the columns that carry a value are
    copied — an empty field must not overwrite a real one on an existing row.
    """
    carried = (
        "name", "tagline", "description", "category", "website_url", "github_url",
        "founded", "date_source", "app_store_url", "play_store_url", "product_url",
        "docs_url", "demo_url", "problem_statement", "target_users",
        "features_json", "pricing_json", "pricing_captured_at", "positioning",
        "provenance",
    )
    values: dict = {}
    for key in carried:
        try:
            value = record[key]
        except (KeyError, IndexError, TypeError):
            continue
        if value is not None and value != "":
            values[key] = value
    values["source"] = "founder"
    return values


def _canonical_domain(url: str | None) -> str | None:
    """The registrable domain of a URL, or None when there is nothing usable.

    One writer, one shape: www-stripped, lowercased, suffix-aware
    (instance.app.github.dev -> github.dev). Written at intake and by the
    backfill so `db.find_by_url`'s unique index and the search ladder's
    exact-domain rung finally have a populated column to read — the column
    existed since the 40 -> 43 migration but NOTHING wrote it (measured
    2026-09-22: 1,258/1,258 rows NULL).
    """
    raw = (url or "").strip()
    if not raw:
        return None
    host = raw.split("://", 1)[1] if "://" in raw else raw
    host = host.split("/", 1)[0].split(":", 1)[0].strip()
    if not host or "." not in host:
        return None  # "localhost", "Probe Co" — not a domain
    try:
        return _lr_regdom(host, _lr_load_config(None)) or None
    except Exception:  # noqa: BLE001 — a weird host never blocks a filing
        return None


def seed_from_github(github_url: str, reuse_profile: bool = False) -> dict:
    repo = gh.fetch_repo(github_url)
    conn = db.connect()
    try:
        existing = db.find_by_url(conn, github_url=repo["html_url"])
        # homepage is untrusted repo-owner input — fall back to the repo URL if
        # it isn't a usable http(s) address.
        website_url = _http_url(repo["homepage"]) or f"https://github.com/{repo['full_name']}"
        if reuse_profile and existing:
            log.info(
                "reuse_profile: %s already exists (id=%s) — LLM skipped, metadata refreshed",
                repo["html_url"], existing["id"],
            )
            values = {
                "website_url": website_url,
                "github_url": repo["html_url"],
                "founded": repo["created_at"] or None,
                "canonical_domain": _canonical_domain(website_url),
                "stars": repo["stars"],
                "language": repo["language"],
                "source": "github",
            }
            return _upsert(conn, values, existing)
        evidence = _build_evidence({
            "repo_full_name": repo["full_name"],
            "repo_description": repo["description"],
            "topics": repo["topics"],
            "language": repo["language"],
            "stars": repo["stars"],
            "repo_created_at": repo["created_at"],
            "homepage": repo["homepage"],
        })
        profile = _clean_profile(
            llm.llm_json(
                "Generate a startup profile from this GitHub repo evidence:\n" + evidence
            )
        )
        name = _text(profile.get("name")) or _text(repo["name"]) or ""
        if not name:
            raise RuntimeError("LLM returned no name")
        values = {
            "name": name,
            "tagline": _text(profile.get("tagline")),
            "description": _text(profile.get("description")),
            "category": _text(profile.get("category")) or "other",
            "website_url": website_url,
            "github_url": repo["html_url"],
            "founded": repo["created_at"] or None,
            # date_source stays unset on purpose (F-04): a repo's created_at is
            # a code-hosting fact, not a founding date, and it is none of the
            # classified sources (llm/wayback/rdap/human) — the column keeps
            # its "unknown" default rather than claiming a provenance it has
            # not got.
            "canonical_domain": _canonical_domain(website_url),
            "stars": repo["stars"],
            "language": repo["language"],
            "source": "github",
        }
        return _upsert(conn, stamp_provenance(values), existing)
    finally:
        conn.close()


def seed_from_website(
    website_url: str, name_hint: str | None = None, reuse_profile: bool = False
) -> dict:
    page = ws.fetch_homepage(website_url)
    domain = urlparse(page["final_url"]).netloc
    conn = db.connect()
    try:
        existing = db.find_by_url(conn, website_url=page["final_url"])
        if reuse_profile and existing:
            log.info(
                "reuse_profile: %s already exists (id=%s) — LLM skipped, founded refreshed",
                page["final_url"], existing["id"],
            )
            # No LLM on this path, so the date can only come from Wayback or
            # RDAP — but its source is still recorded (F-04). When neither
            # answers, date_source is left alone rather than reset: an existing
            # row's recorded provenance must not be destroyed by a refresh
            # that learned nothing.
            found, date_source = _resolve_founded(domain, "")
            values = {
                "website_url": page["final_url"],
                "founded": found,
                "date_source": date_source if found else None,
                "canonical_domain": _canonical_domain(page["final_url"]),
                "source": "website",
            }
            # F-14 teardown carve-out (Phase 2). This payload carries metadata
            # only, and _upsert writes only the keys it is handed — so
            # features_json / pricing_json / positioning / the pricing stamps are
            # left standing rather than blanked, and stamp_provenance never
            # downgrades a human_confirmed marker. The teardown is not silently
            # LOST on a re-seed; because pricing decays, refreshing it is the JIT
            # capture's job (app/capture.py, 7-day window), not the seed's.
            return _upsert(conn, values, existing)
        draft = draft_from_page(page, domain, name_hint)
        # F-04: record WHICH branch produced the date — the three-branch
        # fallback used to throw that knowledge away.
        founded, date_source = _resolve_founded(domain, _text(draft["profile"].get("founded")))
        values = {
            "name": draft["name"],
            "tagline": _text(draft["profile"].get("tagline")),
            "description": _text(draft["profile"].get("description")),
            "category": _text(draft["profile"].get("category")) or "other",
            "website_url": page["final_url"],
            "github_url": None,
            "founded": founded,
            "date_source": date_source if founded else None,
            "canonical_domain": _canonical_domain(page["final_url"]),
            "stars": None,
            "language": None,
            "source": "website",
        }
        return _upsert(conn, stamp_provenance(values), existing)
    finally:
        conn.close()


def _resolve_founded(domain: str, llm_raw: str) -> tuple[str | None, str]:
    """Resolve `founded` and its `date_source` (F-04) from the three existing
    sources, in priority order:

      1. the LLM (the homepage states the date explicitly)            -> "llm"
      2. Wayback's first snapshot (when the site went live)           -> "wayback"
      3. RDAP domain registration (weakest: it can predate the
         company by decades — Notion's domain is 2000, the company 2013) -> "rdap"

    The seed path already knew which branch produced the date and threw that
    knowledge away; `date_source` is what lets Phase 6 stop presenting a
    domain-registration date as a founding year.
    """
    if llm_raw and llm_raw.lower() != "null":
        normalized = ws._normalize_date(llm_raw)
        if not normalized and len(llm_raw) == 4 and llm_raw.isdigit():
            normalized = llm_raw  # year only — honest, no fabricated month/day
        if normalized:
            return normalized, "llm"
    snapshot = ws.wayback_first_snapshot(domain)
    if snapshot:
        return snapshot, "wayback"
    registration = ws.rdap_registration_date(domain)
    if registration:
        return registration, "rdap"
    return None, "unknown"


def _upsert(conn: sqlite3.Connection, values: dict, existing) -> dict:
    """Insert or update a startup row. The returned dict carries `_inserted`
    (True when a new row was created) so the admin seeder can classify each
    candidate as new vs "all exist" (upsert refresh, LLM skipped).

    A unique-index collision (this row's website/github URL already filed
    under a DIFFERENT row) surfaces as a clear ValueError — the API answers
    400 and the seeder records a per-candidate failure instead of an
    IntegrityError leaking as a raw 502."""
    stamp_provenance(values, existing)  # F-05 safety net: no generated text without a marker
    try:
        return _upsert_inner(conn, values, existing)
    except sqlite3.IntegrityError as exc:
        url = values.get("website_url") or values.get("github_url") or ""
        raise ValueError(
            f"URL already filed under a different name ({url}) — dedupe merge "
            f"or edit the existing filing first: {exc}"
        ) from exc


def _upsert_inner(conn: sqlite3.Connection, values: dict, existing) -> dict:
    if existing:
        fields = [k for k in UPDATABLE if values.get(k) is not None]
        set_sql = ", ".join(f"{k} = ?" for k in fields) + ", updated_at = datetime('now')"
        conn.execute(f"UPDATE startups SET {set_sql} WHERE id = ?", [values[k] for k in fields] + [existing["id"]])
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (existing["id"],)).fetchone()
        result = dict(row)
        result["_inserted"] = False
        return result
    fields = [k for k in UPDATABLE if values.get(k) is not None]
    cols = ", ".join(fields)
    qmarks = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO startups ({cols}) VALUES ({qmarks})", [values[k] for k in fields]
    )
    conn.commit()
    row = conn.execute("SELECT * FROM startups WHERE id = ?", (cur.lastrowid,)).fetchone()
    result = dict(row)
    result["_inserted"] = True
    return result


def backfill_canonical_domains(conn: sqlite3.Connection) -> int:
    """Fill canonical_domain for rows admitted before anything wrote the column.

    Idempotent: only rows whose canonical_domain is NULL/'' are touched, so
    re-running (at boot, or ad hoc) is a no-op. Chunked commits so a 10k-row
    archive backfills without holding one long write lock (the verify pass's
    interleave rule). Returns the number of rows filled.

    This is the one-time backfill for the 1,258 rows the 2026-09-22 audit
    measured at 0% populated; every intake path now writes the column itself.
    """
    rows = conn.execute(
        "SELECT id, website_url, github_url FROM startups "
        "WHERE canonical_domain IS NULL OR canonical_domain = ''"
    ).fetchall()
    filled = 0
    for i in range(0, len(rows), 500):
        for row in rows[i:i + 500]:
            domain = _canonical_domain(row["website_url"] or row["github_url"])
            if domain:
                conn.execute(
                    "UPDATE startups SET canonical_domain = ? WHERE id = ?",
                    (domain, row["id"]),
                )
                filled += 1
        conn.commit()
    return filled
