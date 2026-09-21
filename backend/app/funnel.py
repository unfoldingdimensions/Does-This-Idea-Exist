"""Apply a completed liveness-funnel run to the archive: admit the clean
majority, queue the exceptions.

The funnel (`scripts/site_liveness_audit.py`) decides; this module executes.
Admission only — it NEVER deletes and NEVER dead-flips:

  * deletion stays with the tool's own `drop` command (fresh evidence at drop
    time, sqlite backup API, manifest before delete, --max-drop-fraction);
  * the three-strike dead-flip stays with the verify pass, which outranks the
    funnel — and `verify.approve_machine`'s own guard refuses dead rows anyway,
    so a stale run can never resurrect one.

Mapping (docs/liveness-funnel-plan.md, Sequence 1):

  LIVE + gate company/unverified   -> ADMIT via verify.approve_machine:
                                      approval_source='machine',
                                      approved_by='funnel:render' when the row
                                      carries rendered evidence else
                                      'funnel:http', approval_note = the receipt
                                      (run directory, state, gate, reason).
  LIVE + gate not_company/review   -> QUEUE (the company gate is not confident,
                                      so a human sees it)
  WALLED / UNKNOWN / MOVED / BANNED-> QUEUE (the §3.3 exception path)
  NO_URL                           -> QUEUE
  DEAD / REPURPOSED                -> IGNORED, reported in the response —
                                      removal is the drop tool's jurisdiction.

A run that predates the company gate (no `company_gate` field on any row) is
REFUSED: admitting without the gate's verdict would be guessing. Re-importing
the same run is a no-op — the admission guard only stamps verified=0 rows, so
the second pass reports everything as already admitted.
"""
from __future__ import annotations

import json
import os
from typing import Any

from . import db, verify

ADMIT_STATES = frozenset({"LIVE"})
QUEUE_STATES = frozenset({"WALLED", "UNKNOWN", "MOVED", "BANNED", "NO_URL"})
ADMIT_GATES = frozenset({"company", "unverified"})
QUEUE_GATES = frozenset({"not_company", "review"})

# states.json rows from a full-archive run; anything wildly larger is a wrong
# path, not a big archive (the tool refuses drops past 25% — this is the same
# instinct on the admission side).
MAX_ROWS = 100_000
# A bound on the FILE, before json.load ever sees it: 100k rows of the real
# writer's output is ~60 MB, so 128 MB rejects a wrong/huge file on size
# instead of parsing an attacker-supplied multi-gigabyte one first.
MAX_FILE_BYTES = 128_000_000
# SQLite's default bind-variable limit is 32766; chunked reads stay far under
# it so a full-archive run (100k rows) works in three queries instead of
# dying with "too many SQL variables" past the limit.
_CHUNK = 10_000


def import_run(run_dir: str, *, dry_run: bool = True) -> dict[str, Any]:
    """Execute (or, by default, plan) a run's admission decisions.

    `run_dir` is the operator's own local run directory — the tool prints it at
    the end of every audit; this is an admin-tokened endpoint for exactly that
    path. Raises FileNotFoundError for a missing run, ValueError for a run the
    funnel rules refuse.

    State file selection mirrors the tool's own `drop` command: when a render
    pass has run, states-merged.json is the better basis — its rows carry the
    rendered capture that settled the row (browser_evidence / evidence_mode)
    and the pre-render verdict (http_state / http_why). Importing states.json
    would ignore the renderer entirely: rows only visible to a browser land in
    the queue instead of being admitted, and every admission reads funnel:http.
    An explicit states.json is still honoured when it is all there is.
    """
    run_dir = os.path.abspath(run_dir)
    merged_path = os.path.join(run_dir, "states-merged.json")
    states_path = os.path.join(run_dir, "states.json")
    if os.path.isfile(merged_path):
        states_path = merged_path
    if not os.path.isfile(states_path):
        raise FileNotFoundError(f"no states.json under {run_dir}")
    # Parse defensively and bound the row count BEFORE materialising: a
    # multi-GB file is rejected on size, not after a full json.load of it.
    file_size = os.path.getsize(states_path)
    if file_size > MAX_FILE_BYTES:
        raise ValueError(
            f"states file is {file_size / 1e6:.0f} MB (cap {MAX_FILE_BYTES // 1_000_000} "
            f"MB) — that is not a funnel run, it is the wrong file")
    with open(states_path, encoding="utf-8") as fh:
        states = json.load(fh)
    if not isinstance(states, list) or not states:
        raise ValueError(f"{states_path} holds no rows")
    if len(states) > MAX_ROWS:
        raise ValueError(f"{len(states)} rows is not a funnel run (cap {MAX_ROWS})")
    # Provenance is optional (verify/report runs don't rewrite run.json), but a
    # run from before the company gate existed is refused, not guessed at.
    if not any("company_gate" in s for s in states):
        raise ValueError(
            "run predates the company gate (no company_gate field on any row); "
            "re-run `site_liveness_audit.py audit` with the current tool")
    run_meta: dict[str, Any] = {}
    run_json = os.path.join(run_dir, "run.json")
    if os.path.isfile(run_json):
        with open(run_json, encoding="utf-8") as fh:
            run_meta = json.load(fh)
        if not isinstance(run_meta, dict):
            run_meta = {}

    # Current DB state per id — read-only, in chunks. Two ceilings bite at
    # scale: SQLite's bind-variable limit (32766 by default — a 100k-row run
    # would otherwise die with "too many SQL variables"), and untyped JSON
    # (a `true` id is an int in Python; a 10**30 id overflows the binding).
    # Both are handled here so a big-but-legitimate run simply works and a
    # malformed one fails with a named error.
    ids: list[int] = []
    for s in states:
        sid = s.get("id")
        if isinstance(sid, bool):  # bool IS int in Python — exclude explicitly
            continue
        if isinstance(sid, int) and 0 < sid < 2**62:
            ids.append(sid)
    dbstate: dict[int, dict[str, Any]] = {}
    conn = db.connect()
    try:
        for start in range(0, len(ids), _CHUNK):
            chunk = ids[start:start + _CHUNK]
            placeholders = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT id, verified, status, check_failures FROM startups "
                f"WHERE id IN ({placeholders})", chunk).fetchall()
            for r in rows:
                dbstate[r["id"]] = dict(r)
    finally:
        conn.close()

    admits: list[dict[str, Any]] = []
    queued: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    unknown_ids: list[Any] = []
    already_admitted = 0
    for s in states:
        sid = s.get("id")
        if sid not in dbstate:
            unknown_ids.append(sid)
            continue
        gate = (s.get("company_gate") or "").strip().lower()
        entry = {
            "id": sid,
            "name": s.get("name", ""),
            "url": s.get("url", ""),
            "state": s.get("state", ""),
            "gate": gate,
            "why": (s.get("why") or "")[:160],
            # a merged state file carries the rendered capture that settled the
            # row; rendered evidence admits with a different stage name
            "rendered": bool(s.get("browser_evidence")),
        }
        if entry["state"] in ADMIT_STATES and gate in ADMIT_GATES:
            if dbstate[sid]["verified"] == 1:
                already_admitted += 1
            else:
                admits.append(entry)
        elif entry["state"] in ADMIT_STATES or entry["state"] in QUEUE_STATES \
                or gate in QUEUE_GATES:
            queued.append(entry)
        else:
            ignored.append(entry)  # DEAD / REPURPOSED: drop's jurisdiction

    admitted: list[int] = []
    if not dry_run:
        for entry in admits:
            by = "funnel:render" if entry["rendered"] else "funnel:http"
            note = (f"funnel run {os.path.basename(run_dir)}: state "
                    f"{entry['state']}, gate {entry['gate'] or '-'}; "
                    f"{entry['why'][:120]}")
            # The guard inside approve_machine is the real brake: verified=0,
            # status='active', check_failures=0 — a machine can never re-stamp,
            # resurrect, or admit a row on a failure strike.
            if verify.approve_machine([entry["id"]], by=by, note=note):
                admitted.append(entry["id"])

    return {
        "run": run_dir,
        "tool": run_meta.get("tool"),
        "run_generated_at": run_meta.get("generated_at"),
        "config_hash": run_meta.get("config_hash"),
        "states_file": os.path.basename(states_path),
        "total_rows": len(states),
        "dry_run": dry_run,
        "admit_eligible": len(admits),
        "already_admitted": already_admitted,
        "admitted": sorted(admitted),
        "queued": queued,
        "ignored": [{k: e[k] for k in ("id", "name", "state", "why")}
                    for e in ignored],
        "unknown_ids": unknown_ids,
    }
