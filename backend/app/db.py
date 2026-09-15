"""SQLite storage (stdlib sqlite3, WAL). Schema v1 — additive changes only."""
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS startups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  tagline TEXT,
  description TEXT,
  category TEXT,
  website_url TEXT,
  github_url TEXT,
  founded TEXT,
  stars INTEGER,
  language TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  verified INTEGER NOT NULL DEFAULT 0,
  verified_at TEXT,
  last_checked TEXT,
  check_failures INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_startups_website ON startups(lower(website_url));
CREATE UNIQUE INDEX IF NOT EXISTS idx_startups_github ON startups(lower(github_url));
CREATE TABLE IF NOT EXISTS verify_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  startup_id INTEGER NOT NULL,
  checked_at TEXT NOT NULL DEFAULT (datetime('now')),
  website_ok INTEGER,
  github_ok INTEGER,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  params_json TEXT,
  status TEXT NOT NULL,
  total INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0,
  ok INTEGER DEFAULT 0,
  skipped INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0,
  errors_json TEXT,
  ok_urls_json TEXT,
  skipped_urls_json TEXT,
  current TEXT,
  created_at REAL,
  started_at REAL,
  finished_at REAL,
  breakdown_json TEXT,
  result_json TEXT
);
"""


def connect() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Parallel workers (seed ∥ verify) are both writers — wait briefly for the
    # other's commit instead of failing with "database is locked".
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def normalize_url(url: str | None) -> str:
    """Canonical identity form for dedup: lowercase scheme+host, strip www.,
    default ports, trailing slashes, query strings and fragments.

    Paths stay case-sensitive (github.com/Owner/repo != github.com/owner/repo).
    """
    if not url:
        return ""
    u = url.strip()
    try:
        p = urlparse(u)
    except ValueError:
        return u.rstrip("/")
    host = (p.hostname or "").lower().removeprefix("www.")
    if p.scheme not in ("http", "https") or not host:
        return u.rstrip("/")
    # p.port raises (not returns None) for out-of-range ports like :99999 —
    # only urlparse() itself is guarded above.
    try:
        port_num = p.port
    except ValueError:
        return u.rstrip("/")
    port = ""
    if port_num and not (
        (p.scheme == "http" and port_num == 80) or (p.scheme == "https" and port_num == 443)
    ):
        port = f":{port_num}"
    return f"{p.scheme}://{host}{port}{p.path.rstrip('/')}"


def find_by_url(conn: sqlite3.Connection, website_url: str | None = None, github_url: str | None = None) -> sqlite3.Row | None:
    """Look up an existing startup by website or github URL (dedup for re-seeds).

    Exact-match first (unique index), then a normalized-equivalence fallback so
    `https://zoom.com` and `https://www.zoom.com/` resolve to the same row.
    """
    if website_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(website_url) = lower(?)", (website_url,)
        ).fetchone()
        if not row:
            n_ws = normalize_url(website_url)
            if n_ws:
                for candidate in conn.execute("SELECT * FROM startups WHERE website_url IS NOT NULL"):
                    if normalize_url(candidate["website_url"]) == n_ws:
                        return candidate
        elif row:
            return row
    if github_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(github_url) = lower(?)", (github_url,)
        ).fetchone()
        if not row:
            n_gh = normalize_url(github_url)
            if n_gh:
                for candidate in conn.execute("SELECT * FROM startups WHERE github_url IS NOT NULL"):
                    if normalize_url(candidate["github_url"]) == n_gh:
                        return candidate
        elif row:
            return row
    return None
