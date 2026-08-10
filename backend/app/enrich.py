"""Seed orchestration: GitHub link → fetch + LLM profile → upsert.
Website → fetch homepage + Wayback date + LLM profile → upsert.
Re-seeding an existing URL UPDATES the entry (additive, never duplicates)."""
import json
import logging
import sqlite3
from urllib.parse import urlparse

from . import db, github as gh, llm, website as ws

log = logging.getLogger("ideasexist")

UPDATABLE = [
    "name", "tagline", "description", "category", "website_url", "github_url",
    "founded", "stars", "language", "source",
]


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


def seed_from_github(github_url: str, reuse_profile: bool = False) -> dict:
    repo = gh.fetch_repo(github_url)
    conn = db.connect()
    try:
        existing = db.find_by_url(conn, github_url=repo["html_url"])
        website_url = (repo["homepage"] or "").strip() or f"https://github.com/{repo['full_name']}"
        if reuse_profile and existing:
            log.info(
                "reuse_profile: %s already exists (id=%s) — LLM skipped, metadata refreshed",
                repo["html_url"], existing["id"],
            )
            values = {
                "website_url": website_url,
                "github_url": repo["html_url"],
                "founded": repo["created_at"] or None,
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
        profile = llm.llm_json(
            "Generate a startup profile from this GitHub repo evidence:\n" + evidence
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
            "stars": repo["stars"],
            "language": repo["language"],
            "source": "github",
        }
        return _upsert(conn, values, existing)
    finally:
        conn.close()


def seed_from_website(
    website_url: str, name_hint: str | None = None, reuse_profile: bool = False
) -> dict:
    page = ws.fetch_homepage(website_url)
    domain = urlparse(page["final_url"]).netloc
    # founded priority: LLM (homepage states it explicitly) → Wayback first snapshot
    # (site went live — closest to product launch) → RDAP domain registration (weakest).
    founded = None
    conn = db.connect()
    try:
        existing = db.find_by_url(conn, website_url=page["final_url"])
        if reuse_profile and existing:
            log.info(
                "reuse_profile: %s already exists (id=%s) — LLM skipped, founded refreshed",
                page["final_url"], existing["id"],
            )
            values = {
                "website_url": page["final_url"],
                "founded": ws.wayback_first_snapshot(domain) or ws.rdap_registration_date(domain),
                "source": "website",
            }
            return _upsert(conn, values, existing)
        evidence = _build_evidence({
            "page_title": page["title"],
            "meta_description": page["meta_description"],
            "homepage_text_excerpt": page["text"][:6000],
        })
        user = "Generate a startup profile from this website evidence:\n" + evidence
        if name_hint:
            user = f"The startup's name is: {name_hint}\n" + user
        profile = llm.llm_json(user)
        name = _text(profile.get("name")) or _text(name_hint) or domain or ""
        if not name:
            raise RuntimeError("LLM returned no name")
        llm_founded_raw = _text(profile.get("founded"))
        if llm_founded_raw and llm_founded_raw.lower() != "null":
            founded = ws._normalize_date(llm_founded_raw)
            if not founded and len(llm_founded_raw) == 4 and llm_founded_raw.isdigit():
                founded = llm_founded_raw  # year only — honest, no fabricated month/day
        if not founded:
            founded = ws.wayback_first_snapshot(domain) or ws.rdap_registration_date(domain)
        values = {
            "name": name,
            "tagline": _text(profile.get("tagline")),
            "description": _text(profile.get("description")),
            "category": _text(profile.get("category")) or "other",
            "website_url": page["final_url"],
            "github_url": None,
            "founded": founded,
            "stars": None,
            "language": None,
            "source": "website",
        }
        return _upsert(conn, values, existing)
    finally:
        conn.close()


def _upsert(conn: sqlite3.Connection, values: dict, existing) -> dict:
    """Insert or update a startup row. The returned dict carries `_inserted`
    (True when a new row was created) so the admin seeder can classify each
    candidate as new vs "all exist" (upsert refresh, LLM skipped)."""
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
