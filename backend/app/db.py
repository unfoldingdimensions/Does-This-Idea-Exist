"""SQLite storage (stdlib sqlite3, WAL). Schema v1 — additive changes only."""
import sqlite3
from pathlib import Path

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
"""


def connect() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def find_by_url(conn: sqlite3.Connection, website_url: str | None = None, github_url: str | None = None) -> sqlite3.Row | None:
    """Look up an existing startup by website or github URL (dedup for re-seeds)."""
    if website_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(website_url) = lower(?)", (website_url,)
        ).fetchone()
        if row:
            return row
    if github_url:
        row = conn.execute(
            "SELECT * FROM startups WHERE lower(github_url) = lower(?)", (github_url,)
        ).fetchone()
        if row:
            return row
    return None
