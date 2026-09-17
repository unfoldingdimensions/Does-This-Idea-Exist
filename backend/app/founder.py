"""The founder's own app: its own store, two gates, and a submission lifecycle.

Nothing in this module writes the archive (F-20) except the admin APPROVAL path,
which is the archive's own writer by design. The founder store is a separate
SQLite file (`config.FOUNDER_DB_PATH`) and no archive endpoint reads it — that
separation is the property the file split exists for, and it is tested directly.

`founder_apps` carries the SAME column shape as `startups` (F-10) so the gap
table can diff the two records like for like, plus three bookkeeping columns
that are ours alone (`source_kind`, `input_json`, `confirmed_at`).

Two gates, deliberately not merged (docs/teardown-spec.md §3.1):

    eligibility  at least one verifiable link — website_url | github_url |
                 app_store_url | play_store_url. No link → comparison only,
                 `local_only`, and NO consent question is asked (nothing would
                 be published, so there is nothing to consent to).
    consent      the publish opt-in, offered only when a fetchable link exists.
                 Ticked → a `founder_submissions` row with status='pending',
                 routed into the same admin queue as competitors.

`archive_status` is DERIVED from the newest submission row (`local_only` when
there are none) — never stored on the founder record (F-24). A resubmission
after a rejection is a NEW row, so rejected → resubmitted → approved stays
auditable, the same posture as the permanent `verify_log` and the phase ledger.

Three input paths, one row shape:

    URL      reuses the website draft primitive (enrich.draft_from_website)
    form     name · description · target user · category · features (5-10,
             REQUIRED) · pricing · links incl. both store URLs
    agent    the structured JSON from docs/teardown-spec.md §3, extended with
             the links block — unknown keys are rejected, never ignored
"""
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import time

from . import config, db, enrich
from . import teardown as td

log = logging.getLogger("ideasexist")

MACHINE_DRAFTED = enrich.MACHINE_DRAFTED
HUMAN_CONFIRMED = enrich.HUMAN_CONFIRMED

# The eligibility links, in the order the error message and the response report
# them (F-20). Two store links count: a mobile-only product with no website is
# still eligible.
ELIGIBILITY_LINKS = ("website_url", "github_url", "app_store_url", "play_store_url")

# founder_apps extras — ours, never the archive's.
FOUNDER_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("source_kind", "TEXT"),     # url | form | agent_json
    ("input_json", "TEXT"),      # what the founder actually submitted (audit)
    ("confirmed_at", "TEXT"),    # the confirm-before-diff gate (F-13)
    # Per-draft access token (sha256 hex of a 256-bit secret). Stops sequential
    # id enumeration of other founders' drafts on a hosted instance: every
    # read/mutation of a draft requires its token (X-Founder-Token), which is
    # returned ONCE at creation and never stored or returned again. Rows that
    # predate this column (NULL) stay token-less — the documented local-upgrade
    # path, not a bypass for new rows.
    ("access_token_hash", "TEXT"),
)
_FOUNDER_COLUMNS = tuple(enrich.UPDATABLE) + tuple(name for name, _ in FOUNDER_EXTRA_COLUMNS)

SUBMISSION_STATUSES = ("pending", "approved", "rejected", "withdrawn")

# The agent-payload contract (docs/teardown-spec.md §3, + the links block).
AGENT_KEYS = {"name", "description", "target_user", "category", "features",
              "positioning", "pricing", "links"}
AGENT_LINK_KEYS = {"website", "app_store", "play_store", "github"}
AGENT_PRICING_KEYS = {"free_tier", "plans"}
AGENT_PLAN_KEYS = {"name", "price", "period"}

FORM_LINK_KEYS = {"website_url", "github_url", "app_store_url", "play_store_url"}

FOUNDER_SCHEMA = (
    db.table_ddl("founder_apps", extra=FOUNDER_EXTRA_COLUMNS)
    + """
-- F-24: every publish request and its outcome. Exactly the columns in
-- docs/teardown-spec.md §3.1. archive_status is DERIVED from the newest row
-- here rather than stored on founder_apps, so a rejected-then-resubmitted
-- request keeps its history and the approval carries the cross-store link.
CREATE TABLE IF NOT EXISTS founder_submissions (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  founder_app_id     INTEGER NOT NULL,
  submitted_at       TEXT NOT NULL,
  status             TEXT NOT NULL,
  archive_startup_id INTEGER,
  decided_at         TEXT,
  decided_by         TEXT,
  note               TEXT
);
CREATE INDEX IF NOT EXISTS idx_founder_submissions_app ON founder_submissions(founder_app_id);
"""
)


# --- store -----------------------------------------------------------------

def connect() -> sqlite3.Connection:
    """The founder store connection — its own file, same WAL settings."""
    return db.connect_path(config.FOUNDER_DB_PATH)


def init_founder_db() -> None:
    conn = connect()
    try:
        conn.executescript(FOUNDER_SCHEMA)
        conn.commit()
        # Additive migration for stores created before access_token_hash
        # existed: fresh DBs already have it via FOUNDER_SCHEMA, so this is a
        # no-op for them (PRAGMA decides, never DROP/RENAME).
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(founder_apps)")}
        if "access_token_hash" not in cols:
            conn.execute("ALTER TABLE founder_apps ADD COLUMN access_token_hash TEXT")
            conn.commit()
    finally:
        conn.close()


def mint_access_token() -> tuple[str, str]:
    """A new per-draft secret and its stored hash.

    Returns (plaintext, sha256-hex). The plaintext is returned to the founder
    ONCE in the creation response; only the hash is stored and it is never
    returned by any endpoint afterwards.
    """
    plaintext = secrets.token_urlsafe(32)
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return plaintext, digest


def verify_access_token(row, supplied: str | None) -> bool:
    """True when `supplied` matches the draft's stored token hash.

    Rows with no stored hash predate per-draft tokens (local-upgrade path) and
    are treated as public — see the column comment. A stored hash with a
    missing or wrong token is a refusal, compared with hmac.compare_digest.
    """
    try:
        expected = row["access_token_hash"]
    except (KeyError, IndexError, TypeError):
        return True
    if not expected:
        return True
    if not supplied:
        return False
    actual = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, expected)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def get(founder_app_id: int) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM founder_apps WHERE id = ?", (founder_app_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# --- validation -------------------------------------------------------------

def require_features(raw) -> list[str]:
    """The form's and the agent payload's shared rule: 5-10 capabilities.

    A loud error, not a silent padding or a silent truncation — the gap table
    compares feature by feature, and a founder who submitted three capabilities
    needs to know why the comparison is hollow.
    """
    if raw is None:
        raise ValueError(
            f"features is required: {td.FEATURES_MIN}-{td.FEATURES_MAX} short capability "
            "strings (the gap table compares feature by feature)"
        )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("features must be a list of short capability strings")
    items = [td._text(item) for item in raw]
    items = [item[: td.FEATURE_MAX_CHARS] for item in items if item]
    if len(items) < td.FEATURES_MIN:
        raise ValueError(
            f"features must list at least {td.FEATURES_MIN} capabilities (got {len(items)}); "
            "fewer than that makes the comparison hollow"
        )
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item.lower() in seen:
            continue
        seen.add(item.lower())
        deduped.append(item)
    return deduped[: td.FEATURES_MAX]


def _text(value) -> str:
    return td._text(value)


def _links(payload: dict, keys) -> dict:
    """Normalize the link fields: http(s) only, bare hosts get https://.

    `enrich._http_url` is the existing guard (it closes the click-to-execute hole
    in GitHub's owner-controlled homepage field); the founder's own links go
    through the same one.
    """
    out: dict = {}
    for key in keys:
        out[key] = enrich._http_url(payload.get(key))
    return out


def category_of(raw) -> str:
    return enrich._category(raw)


# --- writes -----------------------------------------------------------------

def _insert(values: dict) -> dict:
    unknown = [key for key in values if key not in _FOUNDER_COLUMNS]
    if unknown:
        raise ValueError(f"unknown founder_apps column(s): {sorted(unknown)}")
    cols = [key for key in _FOUNDER_COLUMNS if values.get(key) is not None]
    conn = connect()
    try:
        cur = conn.execute(
            f"INSERT INTO founder_apps ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [values[key] for key in cols],
        )
        conn.commit()
        row = conn.execute("SELECT * FROM founder_apps WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def create_from_url(url: str, name_hint: str | None = None) -> dict:
    """The URL path (F-10): the same website primitive that drafts a competitor."""
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")
    draft = enrich.draft_from_website(url, name_hint)  # raises ValueError/RuntimeError loudly
    profile = draft["profile"]
    founded, date_source = enrich._resolve_founded(draft["domain"], _text(profile.get("founded")))
    founder_token, token_hash = mint_access_token()
    values = {
        "name": draft["name"],
        "tagline": _text(profile.get("tagline")),
        "description": _text(profile.get("description")),
        "category": _text(profile.get("category")) or "other",
        "website_url": enrich._http_url(draft["page"]["final_url"]) or url,
        "founded": founded,
        "date_source": date_source if founded else None,
        # The identity profile only: features stay EMPTY for the founder to edit
        # in the confirm step. The URL path must not invent the founder's own
        # feature list — the gap table compares feature by feature and section 3
        # of the spec lists exactly these five fields for this path.
        "features_json": json.dumps([], ensure_ascii=False),
        "provenance": MACHINE_DRAFTED,
        "source": "founder",
        "source_kind": "url",
        "access_token_hash": token_hash,
        "input_json": json.dumps({"url": url, "name_hint": name_hint}),
    }
    return _draft_response(_insert(values), founder_token=founder_token)


def create_from_form(payload: dict) -> dict:
    """The form path (F-11): features are REQUIRED, 5-10."""
    payload = payload or {}
    name = _text(payload.get("name"))
    if not name:
        raise ValueError("name is required")
    features = require_features(payload.get("features"))
    links = _links(payload, FORM_LINK_KEYS)
    pricing = td.clean_pricing(payload.get("pricing"))
    founder_token, token_hash = mint_access_token()
    values = {
        "name": name[: enrich.NAME_MAX],
        "description": _text(payload.get("description"))[: enrich.DESCRIPTION_MAX],
        "target_users": _text(payload.get("target_user") or payload.get("target_users")),
        "category": category_of(payload.get("category")),
        "features_json": json.dumps(features, ensure_ascii=False),
        "positioning": td.clean_positioning(payload.get("positioning")),
        "pricing_json": json.dumps(pricing, ensure_ascii=False) if (pricing["plans"] or pricing["free_tier"]) else None,
        "pricing_captured_at": _now(),
        "provenance": MACHINE_DRAFTED,
        "source": "founder",
        "source_kind": "form",
        "access_token_hash": token_hash,
        "input_json": json.dumps({**{k: payload.get(k) for k in ("name", "description", "target_user", "category")},
                                  "features": features, "links": links}, ensure_ascii=False),
        **links,
    }
    return _draft_response(_insert(values), founder_token=founder_token)


def create_from_agent_json(payload) -> dict:
    """The agent-payload path (F-12).

    Strict on purpose: malformed JSON and UNKNOWN KEYS are 400s. Invented fields
    must not be silently accepted — an unrecognised key is either a typo or a
    field we do not support, and quietly dropping it makes the founder's own
    submission a lie about what we stored.
    """
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed agent JSON: {exc}") from exc
    else:
        parsed = payload
    if not isinstance(parsed, dict):
        raise ValueError("agent payload must be a JSON object")
    unknown = sorted(set(parsed) - AGENT_KEYS)
    if unknown:
        raise ValueError(f"unknown key(s) in agent payload: {unknown}")

    links_raw = parsed.get("links") or {}
    if not isinstance(links_raw, dict):
        raise ValueError("agent payload: links must be an object")
    unknown_links = sorted(set(links_raw) - AGENT_LINK_KEYS)
    if unknown_links:
        raise ValueError(f"unknown key(s) in links: {unknown_links}")

    pricing_raw = parsed.get("pricing") or {}
    if not isinstance(pricing_raw, dict):
        raise ValueError("agent payload: pricing must be an object")
    unknown_pricing = sorted(set(pricing_raw) - AGENT_PRICING_KEYS)
    if unknown_pricing:
        raise ValueError(f"unknown key(s) in pricing: {unknown_pricing}")
    for plan in pricing_raw.get("plans") or []:
        if isinstance(plan, dict) and set(plan) - AGENT_PLAN_KEYS:
            raise ValueError(f"unknown key(s) in a pricing plan: {sorted(set(plan) - AGENT_PLAN_KEYS)}")

    name = _text(parsed.get("name"))
    if not name:
        raise ValueError("agent payload: name is required")
    features = require_features(parsed.get("features"))
    pricing = td.clean_pricing(pricing_raw)
    # The agent block names the links website/app_store/play_store/github; the
    # columns are website_url/app_store_url/play_store_url/github_url.
    links = _links(
        {
            "website_url": links_raw.get("website"),
            "app_store_url": links_raw.get("app_store"),
            "play_store_url": links_raw.get("play_store"),
            "github_url": links_raw.get("github"),
        },
        FORM_LINK_KEYS,
    )
    founder_token, token_hash = mint_access_token()
    values = {
        "name": name[: enrich.NAME_MAX],
        "description": _text(parsed.get("description"))[: enrich.DESCRIPTION_MAX],
        "target_users": _text(parsed.get("target_user")),
        "category": category_of(parsed.get("category")),
        "features_json": json.dumps(features, ensure_ascii=False),
        "positioning": td.clean_positioning(parsed.get("positioning")),
        "pricing_json": json.dumps(pricing, ensure_ascii=False) if (pricing["plans"] or pricing["free_tier"]) else None,
        "pricing_captured_at": _now(),
        "provenance": MACHINE_DRAFTED,
        "source": "founder",
        "source_kind": "agent_json",
        "access_token_hash": token_hash,
        "input_json": json.dumps(parsed, ensure_ascii=False)[:20000],
        **links,
    }
    return _draft_response(_insert(values), founder_token=founder_token)


# --- gates ------------------------------------------------------------------

def eligibility(row) -> dict:
    """The eligibility gate (F-20): is there at least one real link?"""
    for key in ELIGIBILITY_LINKS:
        try:
            value = (row[key] or "").strip()
        except (KeyError, IndexError, TypeError):
            value = ""
        if value:
            return {"has_link": True, "link": value, "link_field": key}
    return {"has_link": False, "link": "", "link_field": None}


def archive_status(founder_app_id: int) -> str:
    """DERIVED from the newest submission row — never stored (F-24)."""
    conn = connect()
    try:
        row = conn.execute(
            "SELECT status FROM founder_submissions WHERE founder_app_id = ? ORDER BY id DESC LIMIT 1",
            (founder_app_id,),
        ).fetchone()
    finally:
        conn.close()
    return row["status"] if row else "local_only"


def newest_submission(founder_app_id: int) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM founder_submissions WHERE founder_app_id = ? ORDER BY id DESC LIMIT 1",
            (founder_app_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def profile_of(row) -> dict:
    """The founder record's teardown fields, in the shape Phase 3 diffs."""
    keys = ("name", "tagline", "description", "category", "website_url", "github_url",
            "app_store_url", "play_store_url", "features_json", "pricing_json",
            "pricing_captured_at", "positioning", "target_users")
    out: dict = {}
    for key in keys:
        try:
            out[key] = row[key]
        except (KeyError, IndexError, TypeError):
            continue
    try:
        out["features"] = json.loads(row["features_json"] or "[]")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        out["features"] = []
    try:
        out["pricing"] = json.loads(row["pricing_json"]) if row["pricing_json"] else {}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        out["pricing"] = {}
    return out


def _draft_response(row: dict, founder_token: str | None = None) -> dict:
    gates = eligibility(row)
    response = {
        "founder_app_id": row["id"],
        "profile": profile_of(row),
        "confirmed": bool(row.get("confirmed_at")),
        "source_kind": row.get("source_kind"),
        "eligibility": gates,
        # The consent question is only ever offered when there is something to
        # publish (F-20). Nothing is auto-confirmed and nothing is auto-queued.
        "publish_offered": gates["has_link"],
        "archive_status": archive_status(row["id"]),
        "submission": newest_submission(row["id"]),
    }
    # The per-draft secret, returned ONCE at creation. Reads, confirms and
    # publishes never include it — the founder's client stores it and sends it
    # back as X-Founder-Token.
    if founder_token is not None:
        response["founder_token"] = founder_token
    return response


def confirm(founder_app_id: int) -> dict:
    """F-13 confirm — the human half of F-05 for the founder's own record."""
    row = get(founder_app_id)
    if not row:
        raise ValueError(f"founder app {founder_app_id} not found")
    conn = connect()
    try:
        enrich.mark_human_confirmed(conn, founder_app_id, table="founder_apps")
        conn.execute(
            "UPDATE founder_apps SET confirmed_at = ?, updated_at = datetime('now') WHERE id = ?",
            (_now(), founder_app_id),
        )
        conn.commit()
    finally:
        conn.close()
    return _draft_response(get(founder_app_id) or row)


def assert_comparable(founder_app_id: int) -> dict:
    """The confirm-before-diff guard the compare path calls (Phase 3).

    The gap table never renders against an unconfirmed profile: an unconfirmed
    draft is the machine's guess at the founder's app, and diffing against a
    guess would make the comparison meaningless.
    """
    row = get(founder_app_id)
    if not row:
        raise ValueError(f"founder app {founder_app_id} not found")
    if not row.get("confirmed_at"):
        raise ValueError(
            f"founder app {founder_app_id} is not confirmed — confirm the draft before "
            "the gap table runs (confirm-before-diff)"
        )
    return row


# --- submissions ------------------------------------------------------------

def _insert_submission(founder_app_id: int, status: str, note: str | None = None) -> int:
    if status not in SUBMISSION_STATUSES:
        raise ValueError(f"unknown submission status {status!r}")
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO founder_submissions (founder_app_id, submitted_at, status, note) "
            "VALUES (?, ?, ?, ?)",
            (founder_app_id, _now(), status, note),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def request_publish(founder_app_id: int, publish: bool, note: str | None = None) -> dict:
    """The consent gate. Order matters: eligibility is checked BEFORE consent is
    even considered, because a link-less app is never offered the question."""
    row = get(founder_app_id)
    if not row:
        raise ValueError(f"founder app {founder_app_id} not found")
    if not publish:
        return {"submitted": False, "archive_status": archive_status(founder_app_id),
                "message": "not published — the app stays in the founder store"}
    gates = eligibility(row)
    if not gates["has_link"]:
        raise ValueError(
            "this app has no link (website / github / app store / play store) — it is "
            "comparison-only and can never enter the archive, so no consent question is asked (F-20)"
        )
    if not row.get("confirmed_at"):
        raise ValueError("confirm the draft before publishing — consent is not approval (F-13)")
    submission_id = _insert_submission(founder_app_id, "pending", note)
    return {
        "submitted": True,
        "submission_id": submission_id,
        "archive_status": "pending",
        "message": "submitted to the archive queue — the same admin gate as any competitor",
    }


def get_submission(submission_id: int) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM founder_submissions WHERE id = ?", (submission_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def pending_submissions() -> list[dict]:
    """Pending submissions, with the founder app's name/links for the queue."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT s.id AS submission_id, s.founder_app_id, s.submitted_at, s.status, "
            "       a.name, a.website_url, a.github_url, a.app_store_url, a.play_store_url, a.category "
            "FROM founder_submissions s JOIN founder_apps a ON a.id = s.founder_app_id "
            "WHERE s.status = 'pending' ORDER BY s.id"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def decisions(founder_app_id: int) -> list[dict]:
    """Full submission history — never rewritten, so a rejection stays visible."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM founder_submissions WHERE founder_app_id = ? ORDER BY id",
            (founder_app_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _decide(submission_id: int, status: str, *, decided_by: str, note: str | None,
            archive_startup_id: int | None = None) -> dict:
    conn = connect()
    try:
        cur = conn.execute(
            "UPDATE founder_submissions SET status = ?, decided_at = ?, decided_by = ?, "
            "note = ?, archive_startup_id = COALESCE(?, archive_startup_id) WHERE id = ?",
            (status, _now(), decided_by, note, archive_startup_id, submission_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"submission {submission_id} not found")
    finally:
        conn.close()
    return get_submission(submission_id) or {}


def publish_to_archive(founder_row) -> dict:
    """Create the archive row THROUGH THE NORMAL SEED WRITER.

    `enrich._upsert` is the one writer the seed paths use: it applies
    stamp_provenance (F-05) and turns a unique-index collision into a clear
    ValueError. Writing a second INSERT here would drift from it — and the dedup
    matters, because a founder whose site is already filed must link to the
    existing record rather than create a twin.
    """
    values = enrich.values_from_record(founder_row)
    if not values.get("name"):
        values["name"] = f"founder-app-{founder_row['id']}"
    conn = db.connect()
    try:
        existing = db.find_by_url(
            conn, website_url=values.get("website_url"), github_url=values.get("github_url")
        )
        return enrich._upsert(conn, values, existing)
    finally:
        conn.close()


def approve_submission(submission_id: int, *, decided_by: str = "admin", note: str | None = None) -> dict:
    """Admin approval: the archive row is created and linked (archive_startup_id)."""
    submission = get_submission(submission_id)
    if not submission:
        raise ValueError(f"submission {submission_id} not found")
    if submission["status"] != "pending":
        raise ValueError(f"submission {submission_id} is {submission['status']}, not pending")
    founder_row = get(submission["founder_app_id"])
    if not founder_row:
        raise ValueError(f"founder app {submission['founder_app_id']} not found")
    row = publish_to_archive(founder_row)
    decided = _decide(
        submission_id, "approved", decided_by=decided_by, note=note,
        archive_startup_id=int(row["id"]),
    )
    return {"submission": decided, "archive_startup_id": int(row["id"]),
            "archive_inserted": bool(row.get("_inserted"))}


def reject_submission(submission_id: int, note: str, *, decided_by: str = "admin") -> dict:
    """Rejection carries a note the founder can actually read — there are no
    accounts to notify, so the submission row IS the message."""
    if not (note or "").strip():
        raise ValueError("a rejection needs a note the founder can read")
    submission = get_submission(submission_id)
    if not submission:
        raise ValueError(f"submission {submission_id} not found")
    if submission["status"] != "pending":
        raise ValueError(f"submission {submission_id} is {submission['status']}, not pending")
    decided = _decide(submission_id, "rejected", decided_by=decided_by, note=note.strip())
    # A rejection leaves the founder record and its history intact: the next
    # attempt is a NEW submission row.
    return {"submission": decided, "archive_status": archive_status(submission["founder_app_id"])}


def evidence_for(founder_app_id: int) -> list[dict]:
    """The founder's own evidence rows, if any were written into the founder
    store. Kept here so Phase 3 does not reach across stores for them."""
    conn = connect()
    try:
        if not conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence'"
        ).fetchone():
            return []
        rows = conn.execute(
            "SELECT * FROM evidence WHERE startup_id = ? ORDER BY id", (founder_app_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
