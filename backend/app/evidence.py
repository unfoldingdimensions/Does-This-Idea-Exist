"""Evidence rows — one place that writes them, so the rule is structural.

"Evidence without a source is not evidence" is F-02's whole point, and the
`evidence` table enforces it at the DB layer with `source_url NOT NULL`. This
module enforces it one level earlier, by CONSTRUCTION: `write_evidence` refuses a
source-less claim with a clear error instead of letting it reach a NOT NULL
constraint mid-seed (or, worse, get swallowed by a caller's broad except). Every
teardown writer goes through here rather than building INSERTs of its own, so a
future caller cannot forget the rule — there is no other way to write a row.

`confidence` carries the retrieval-vs-assertion distinction (F-09): an
observation about a page we READ is real evidence; a page we could not read
yields `unknown` at low confidence, never a negative.
"""
import sqlite3
from typing import Iterable

# F-02's closed vocabulary. Anything else is a bug in the caller, and a typo
# would otherwise sit in the DB looking like a legitimate type forever.
EVIDENCE_TYPES = (
    "feature",
    "pricing",
    "positioning",
    "negative",
    "review",
    "repo_created",
    "homepage_claim",
    "wayback_first",
    "reachability",
    "curator_confirmation",
)


class SourceRequiredError(ValueError):
    """A claim was written without the page it came from."""


def write_evidence(
    conn: sqlite3.Connection,
    startup_id: int,
    evidence_type: str,
    source_url: str,
    *,
    claim: str | None = None,
    value: str | None = None,
    provenance: str | None = None,
    confidence: float | None = None,
    captured_at: str | None = None,
    commit: bool = True,
) -> int:
    """Insert one evidence row and return its id.

    `source_url` is positional and mandatory: a caller that has no source has no
    claim to write, and that is exactly the rule we want to be unable to bypass.

    It COMMITS by default. A row written inside a transaction the caller never
    closes is a row that silently disappears when the connection closes — which
    is exactly how a teardown can look complete while its evidence is gone.
    """
    if not source_url or not str(source_url).strip():
        raise SourceRequiredError(
            f"refusing to write a '{evidence_type}' row for startup {startup_id} "
            "without a source_url — evidence without a source is not evidence (F-02)"
        )
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unknown evidence_type {evidence_type!r}; allowed: {EVIDENCE_TYPES}")
    cols = ["startup_id", "evidence_type", "source_url", "claim", "value", "provenance", "confidence"]
    vals: list = [startup_id, evidence_type, str(source_url).strip(), claim, value, provenance, confidence]
    if captured_at:
        cols.append("captured_at")
        vals.append(captured_at)
    cur = conn.execute(
        f"INSERT INTO evidence ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        vals,
    )
    if commit:
        conn.commit()
    return int(cur.lastrowid)


def write_many(conn: sqlite3.Connection, startup_id: int, rows: Iterable[dict]) -> int:
    """Insert a batch of evidence dicts (same keys as write_evidence). Returns
    how many rows were written; the first source-less row refuses the batch.

    One commit for the batch — still a commit, for the same reason as above.
    """
    written = 0
    for row in rows:
        write_evidence(
            conn,
            startup_id,
            row["evidence_type"],
            row["source_url"],
            claim=row.get("claim"),
            value=row.get("value"),
            provenance=row.get("provenance"),
            confidence=row.get("confidence"),
            captured_at=row.get("captured_at"),
            commit=False,
        )
        written += 1
    if written:
        conn.commit()
    return written


def for_startup(conn: sqlite3.Connection, startup_id: int, evidence_type: str | None = None) -> list[dict]:
    """Read a startup's evidence back — used by the verifier and by Phase 3's
    dimension 7 (review rows), which consumes them rather than re-fetching."""
    sql = "SELECT * FROM evidence WHERE startup_id = ?"
    params: list = [startup_id]
    if evidence_type:
        sql += " AND evidence_type = ?"
        params.append(evidence_type)
    return [dict(r) for r in conn.execute(sql + " ORDER BY id", params).fetchall()]


def count_for_startup(conn: sqlite3.Connection, startup_id: int) -> dict[str, int]:
    rows = conn.execute(
        "SELECT evidence_type, COUNT(*) AS c FROM evidence WHERE startup_id = ? GROUP BY evidence_type",
        (startup_id,),
    ).fetchall()
    return {r["evidence_type"]: r["c"] for r in rows}
