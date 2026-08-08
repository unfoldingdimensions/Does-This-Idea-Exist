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

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3023")
