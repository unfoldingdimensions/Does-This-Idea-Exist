"""IdeaExists backend config — env-driven, defaults for local dev."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "ideasexist.db")))

# F-10 / F-20: the founder's own app lives in its OWN SQLite file, mirroring the
# DB_PATH pattern above — never in the archive. The separation is the property
# the split exists for: nothing in the founder store is ever listed, counted or
# searched by an archive endpoint. Hosting must exclude this file from backups
# (docs/teardown-spec.md §3.1) and the privacy copy is different per case.
FOUNDER_DB_PATH = Path(os.getenv("FOUNDER_DB_PATH", str(BASE_DIR / "data" / "founder.db")))

# LLM gateway settings (which provider is active, its key/model/base-URL
# overrides) live in their OWN file too, for the same reason the founder store
# does: they are SECRETS. The archive file gets copied, backed up and shared —
# the per-phase verifiers copy it around routinely — so an API key must never
# sit in it. See app/gateways.py.
SETTINGS_DB_PATH = Path(os.getenv("SETTINGS_DB_PATH", str(BASE_DIR / "data" / "settings.db")))

# LLM: the DEFAULT gateway is OpenCode Go (opencode.ai/zen/go/v1).
# These three values describe that gateway and nothing else — the other
# gateways (Zen, OpenRouter, Gemini, Command Code) are configured from the
# admin panel and stored in SETTINGS_DB_PATH, and app/gateways.py resolves which
# one is in effect at call time. With an empty settings store this is exactly
# the configuration the app has always run on.
#
# The gateway URL is operator config (backend/.env), never user input; parse
# it once here and reject anything that isn't a clean http(s) origin so a
# malformed value fails at boot instead of mid-enrichment.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1").rstrip("/")
_parsed_llm = urlparse(LLM_BASE_URL)
if _parsed_llm.scheme not in ("http", "https") or not _parsed_llm.hostname:
    raise RuntimeError(
        f"LLM_BASE_URL must be an http(s) origin, got {LLM_BASE_URL!r} — fix backend/.env"
    )
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
LLM_API_KEY = os.getenv("OPENCODE_GO_API_KEY", "")

# GitHub API: optional token for rate-limit headroom (unauth = 60 req/hr, plenty at this scale)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "") or None

# Auto-verify: kick a verification pass at startup if last_checked is older
# than this many days (0 disables). Set-and-forget for a local-first app.
VERIFY_AUTO_STALE_DAYS = int(os.getenv("VERIFY_AUTO_STALE_DAYS", "7"))

# F-22: a cached teardown is re-capturable after this many days. Deliberately the
# same number and the same clock as VERIFY_AUTO_STALE_DAYS — the product has ONE
# staleness rhythm, not two. Capture itself is just-in-time (first founder
# request), never on seed and never on approval.
CAPTURE_STALE_DAYS = int(os.getenv("CAPTURE_STALE_DAYS", "7"))

# F-23: review providers are CONFIG, not code — adding a platform is an edit
# here rather than a phase. Each entry is {name, kind, url_template} where
# {q} is replaced with the competitor's domain; kind is "reddit_json" or "rss".
# Reddit's public .json endpoints and RSS feeds are the fetchable ones. Walled
# platforms (G2, Capterra, Trustpilot) bot-wall datacenter traffic: a 403/429
# from one is a SKIP, never a failure or a strike (docs/teardown-spec.md §9).
DEFAULT_REVIEW_SOURCES: tuple[dict, ...] = (
    {
        "name": "reddit",
        "kind": "reddit_json",
        "url_template": "https://www.reddit.com/search.json?q={q}&sort=relevance&limit=25",
    },
    {
        "name": "reddit-rss",
        "kind": "rss",
        "url_template": "https://www.reddit.com/search.rss?q={q}&sort=relevance&limit=25",
    },
)


def _review_sources() -> tuple[dict, ...]:
    """REVIEW_SOURCES as JSON in the environment, else the defaults.

    A malformed value must not take the process down mid-capture (the app boots
    without it), so it falls back to the defaults — the loud failure here would
    cost more than it explains.
    """
    raw = os.getenv("REVIEW_SOURCES", "").strip()
    if not raw:
        return DEFAULT_REVIEW_SOURCES
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return DEFAULT_REVIEW_SOURCES
    if not isinstance(parsed, list):
        return DEFAULT_REVIEW_SOURCES
    return tuple(
        {"name": str(e.get("name") or ""), "kind": str(e.get("kind") or ""),
         "url_template": str(e.get("url_template") or "")}
        for e in parsed
        if isinstance(e, dict) and e.get("url_template")
    ) or DEFAULT_REVIEW_SOURCES


REVIEW_SOURCES = _review_sources()

# Admin seeder gate: single owner token ("knows it's me"). Empty = admin disabled.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Security posture knobs. MUTATION_AUTH gates the status-flip / seed /
# verify-run endpoints behind the admin token. It defaults ON — fail closed.
# Set MUTATION_AUTH=0 only for a throwaway local instance; the app refuses to
# start with auth on and no ADMIN_TOKEN, so there is no silent-open state.
MUTATION_AUTH = os.getenv("MUTATION_AUTH", "1").strip().lower() in ("1", "true", "yes", "on")
# Per-IP sliding-window rate limiting on mutating + admin endpoints (default on).
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")

# SSRF guard for the LLM gateway's outbound call — OFF by default.
# A gateway's base URL is settable through an admin endpoint now (app/gateways.py),
# not just an `.env` value, so the call that carries the API key gets the same
# netguard rule every page fetch gets: loopback, private, link-local, CGNAT and
# cloud-metadata targets are refused before a socket opens.
# Set this to 1 ONLY to reach a model server on your own machine (Ollama, LM Studio,
# vLLM on 127.0.0.1). It re-opens exactly the target class the guard closes.
ALLOW_PRIVATE_LLM_BASE = os.getenv("ALLOW_PRIVATE_LLM_BASE", "0").strip().lower() in ("1", "true", "yes", "on")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3023")

# Reverse-proxy trust for client-IP resolution. Handed to uvicorn as
# --forwarded-allow-ips so ITS ProxyHeadersMiddleware rewrites request.client
# (the rate limiter keys off that). Empty = trust nothing, which is the safe
# default: "*" would let any caller spoof X-Forwarded-For and walk past the
# per-IP limits entirely. Set it to the reverse proxy's address when hosting.
FORWARDED_ALLOW_IPS = os.getenv("FORWARDED_ALLOW_IPS", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
