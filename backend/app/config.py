"""IdeaExists backend config — env-driven, defaults for local dev."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "ideasexist.db")))

# LLM: opencode.go (deepseek-v4-flash) — verified live 2026-08-09
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
LLM_API_KEY = os.getenv("OPENCODE_GO_API_KEY", "")

# GitHub API: optional token for rate-limit headroom (unauth = 60 req/hr, plenty at this scale)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "") or None

# Auto-verify: kick a verification pass at startup if last_checked is older
# than this many days (0 disables). Set-and-forget for a local-first app.
VERIFY_AUTO_STALE_DAYS = int(os.getenv("VERIFY_AUTO_STALE_DAYS", "7"))

# Admin seeder gate: single owner token ("knows it's me"). Empty = admin disabled.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Security posture knobs (all additive — defaults preserve the local-first UX):
# MUTATION_AUTH=1 requires the admin token on the status-flip / seed / verify-run
# endpoints (default off = open, today's behavior). Hosting MUST set it to 1.
MUTATION_AUTH = os.getenv("MUTATION_AUTH", "").strip().lower() in ("1", "true", "yes", "on")
# Per-IP sliding-window rate limiting on mutating + admin endpoints (default on).
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3023")
