"""IdeaExists backend smoke test — in-process, no live server or network needed.

Run (from backend/, with the venv python):
    python -m tests.smoke

Uses a throwaway SQLite DB: DB_PATH env var is honored before app import.
Live LLM/GitHub seed paths are covered by manual runs — this suite pins the
API surface, schema bootstrap, error handling, and dedup upsert behavior.
"""
import os
import tempfile
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(_tmp.name) / "smoke.db")

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.enrich import _upsert  # noqa: E402
from app.main import app  # noqa: E402

fails: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


with TestClient(app) as client:
    check("health ok", client.get("/api/health").json().get("ok") is True)
    check("startups start empty", client.get("/api/startups").json() == [])
    check("categories start empty", client.get("/api/categories").json() == [])
    stats = client.get("/api/stats").json()
    check("stats zeroed", stats["total"] == 0 and stats["verified"] == 0, str(stats))
    check("mark-verify 404 on unknown", client.post("/api/startups/1/verify").status_code == 404)
    check("verify/run on empty", client.post("/api/verify/run").json()["checked"] == 0)

# Dedup upsert (network-free part of the seed paths)
conn = db.connect()
try:
    first = _upsert(
        conn,
        {"name": "Alpha", "tagline": "t1", "website_url": "https://example.com", "category": "other", "source": "website"},
        None,
    )
    existing = db.find_by_url(conn, website_url="https://example.com")
    second = _upsert(
        conn,
        {"name": "Alpha", "tagline": "t2", "website_url": "https://example.com", "category": "other", "source": "website"},
        existing,
    )
    check("upsert inserts", first["id"] == 1 and first["name"] == "Alpha", str(first))
    check("re-seed dedups (same id)", second["id"] == first["id"], f"{first['id']} vs {second['id']}")
    check("re-seed updates fields", second["tagline"] == "t2", second["tagline"])
finally:
    conn.close()

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURE(S): {fails}")
    raise SystemExit(1)
print("RESULT: ALL PASS")
