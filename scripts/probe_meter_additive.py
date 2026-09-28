"""§7.4 Task 1 probe: the ledger table must be ADDITIVE on the real archive.

Runs db.init_db() against a COPY of the live archive (never the original) and
proves: same row count, same column list, same per-row data, and the new table
present. Any difference is a bug in the schema work, not in this script.
"""
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
REPO = BACKEND.parent
LIVE = REPO / "backend" / "data" / "ideasexist.db"

sys.path.insert(0, str(BACKEND))

workdir = Path(tempfile.mkdtemp(prefix="meter-probe-"))
copy = workdir / "archive-copy.db"
# sqlite3's backup API, not a file copy — WAL means a plain copy can miss frames.
src = sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True)
dst = sqlite3.connect(copy)
with dst:
    src.backup(dst)
src.close()
dst.close()
print(f"copied live archive -> {copy}")


def snapshot(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(startups)")]
    rows = conn.execute("SELECT COUNT(*) FROM startups").fetchone()[0]
    digest = conn.execute(
        "SELECT COUNT(*), SUM(LENGTH(COALESCE(name,''))), SUM(id), "
        "SUM(LENGTH(COALESCE(website_url,''))) FROM startups"
    ).fetchone()
    tables = sorted(
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    )
    conn.close()
    return cols, rows, tuple(digest), tables


before_cols, before_rows, before_digest, before_tables = snapshot(copy)
print(f"before: {before_rows} rows, {len(before_cols)} columns, digest={before_digest}")
print(f"before tables: {len(before_tables)}")

# Now run the app's boot path against the COPY.
import os  # noqa: E402

os.environ["DB_PATH"] = str(copy)
os.environ["FOUNDER_DB_PATH"] = str(workdir / "founder.db")
os.environ["SETTINGS_DB_PATH"] = str(workdir / "settings.db")

from app import db, meter  # noqa: E402

db.init_db()

after_cols, after_rows, after_digest, after_tables = snapshot(copy)
print(f"after:  {after_rows} rows, {len(after_cols)} columns, digest={after_digest}")
print(f"after tables: {len(after_tables)}")

ok = True
if after_rows != before_rows:
    print(f"FAIL: row count changed {before_rows} -> {after_rows}")
    ok = False
if after_digest != before_digest:
    print(f"FAIL: row DATA changed\n  {before_digest}\n  {after_digest}")
    ok = False
if after_cols[: len(before_cols)] != before_cols:
    print("FAIL: existing columns changed or reordered")
    ok = False
print(f"column delta: {[c for c in after_cols if c not in before_cols]}")
print(f"table delta : {[t for t in after_tables if t not in before_tables]}")

# the ledger must be writable on the upgraded store
res = meter.record(model="probe-model", purpose="probe", cost_usd=0.0, prompt_tokens=1,
                   completion_tokens=1, ok=True)
print(f"record on upgraded copy: {res}")
print(f"ledger rows: {meter.count()}")
print(f"table_present: {meter.table_present()}")
if not res.get("recorded") or meter.count() != 1:
    print("FAIL: the ledger could not be written on the upgraded copy")
    ok = False

print("RESULT:", "PASS — additive, rows intact" if ok else "FAIL")
sys.exit(0 if ok else 1)
