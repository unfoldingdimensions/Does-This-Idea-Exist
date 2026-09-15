"""IdeaExists backend config — env-driven, defaults for local dev."""
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "ideasexist.db")))

# LLM: opencode.go (deepseek-v4-flash) — verified live 2026-08-09.
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

# Admin seeder gate: single owner token ("knows it's me"). Empty = admin disabled.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Security posture knobs. MUTATION_AUTH gates the status-flip / seed /
# verify-run endpoints behind the admin token. It defaults ON — fail closed.
# Set MUTATION_AUTH=0 only for a throwaway local instance; the app refuses to
# start with auth on and no ADMIN_TOKEN, so there is no silent-open state.
MUTATION_AUTH = os.getenv("MUTATION_AUTH", "1").strip().lower() in ("1", "true", "yes", "on")
# Per-IP sliding-window rate limiting on mutating + admin endpoints (default on).
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3023")

# Reverse-proxy trust for client-IP resolution. Handed to uvicorn as
# --forwarded-allow-ips so ITS ProxyHeadersMiddleware rewrites request.client
# (the rate limiter keys off that). Empty = trust nothing, which is the safe
# default: "*" would let any caller spoof X-Forwarded-For and walk past the
# per-IP limits entirely. Set it to the reverse proxy's address when hosting.
FORWARDED_ALLOW_IPS = os.getenv("FORWARDED_ALLOW_IPS", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
