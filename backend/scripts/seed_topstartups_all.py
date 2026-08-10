"""Seed ALL topstartups.io sites directly — bypasses the 500-cap admin API.

Runs the backend's own topstartups producer + ingest pipeline in-process
against the local DB (same code path as the API job, just uncapped and
standalone — no server needed). Fail-loud per entry, checkpoint-resumable:
re-running skips URLs already processed, and reuse_profile skips the LLM for
entries already on file.

Run (from backend/, with the venv python):
    .venv/Scripts/python.exe scripts/seed_topstartups_all.py
"""
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app import config, seeder  # noqa: E402

CHECKPOINT = config.BASE_DIR / "data" / "topstartups_checkpoint.json"
ERRORS = config.BASE_DIR / "data" / "topstartups_errors.txt"
LOG = config.BASE_DIR / "data" / "topstartups_seed.log"


def main() -> int:
    done: set[str] = set()
    if CHECKPOINT.exists():
        done = set(json.loads(CHECKPOINT.read_text(encoding="utf-8")))
    print(f"resume: {len(done)} URLs already processed", flush=True)

    ok = failed = skipped = 0
    errors: list[str] = []
    t0 = time.time()

    with open(LOG, "a", encoding="utf-8") as logf:
        for candidate in seeder._topstartups({}):
            url = candidate[0] if isinstance(candidate, tuple) else candidate
            if url in done:
                skipped += 1
                continue
            try:
                seeder._ingest(candidate, {"reuse_profile": True})
                ok += 1
                logf.write(f"OK   {url}\n")
            except Exception as exc:  # noqa: BLE001 — per-entry failure is data, not a crash
                failed += 1
                errors.append(f"{candidate}: {exc}")
                logf.write(f"FAIL {candidate}: {exc}\n")
            done.add(url)
            if (ok + failed) % 10 == 0:
                CHECKPOINT.write_text(json.dumps(sorted(done)), encoding="utf-8")
                elapsed = max(time.time() - t0, 0.001)
                rate = (ok + failed) / elapsed
                remaining = 1259 - len(done)
                eta_h = remaining / rate / 3600 if rate else 0
                print(
                    f"[{time.strftime('%H:%M:%S')}] {ok + failed + skipped} seen · "
                    f"{ok} ok · {failed} failed · {rate:.2f}/s · ETA {eta_h:.1f}h",
                    flush=True,
                )

    CHECKPOINT.write_text(json.dumps(sorted(done)), encoding="utf-8")
    if errors:
        ERRORS.write_text("\n".join(errors), encoding="utf-8")
    print(f"\nDONE: {ok} ok, {failed} failed, {skipped} skipped (see {ERRORS.name} for failures)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
