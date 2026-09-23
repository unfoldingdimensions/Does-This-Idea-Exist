"""IdeaExists API — FastAPI backend (:8020)."""
import asyncio
import hmac
import logging
import sys
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import config

# Log stream must tolerate non-Latin-1 text before anything writes to it. The
# archive is international (startup names in any script) and our own notes carry
# symbols like the star in "repo ok, 12★" — on a legacy Windows console
# (cp1252) encoding those raises inside the log handler and the line is lost.
# UTF-8 with replacement is the one place to fix it for every caller.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Logging is configured HERE, ahead of the sibling imports below, because
# importing `seeder` starts its worker threads — anything logged during that
# import would fall through to Python's lastResort handler (bare stderr, no
# timestamp, no level) if basicConfig ran later.
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    stream=sys.stdout,
)

from . import capture, compare as compare_mod, db, enrich, evidence as evidence_mod, founder, fts, funnel, gateways, search as search_mod, seeder, verify  # noqa: E402

log = logging.getLogger("ideasexist")

AUTO_VERIFY_INTERVAL_S = 86_400  # 24h


def _check_auth_config() -> None:
    """Fail fast on the one config combination that bricks the app silently:
    auth on with no token means every write endpoint 403s forever and the logs
    say nothing about why. Refuse to start instead of serving a dead API."""
    if config.MUTATION_AUTH and not config.ADMIN_TOKEN:
        raise RuntimeError(
            "MUTATION_AUTH is on but ADMIN_TOKEN is empty — every write endpoint "
            "would reject every request. Set ADMIN_TOKEN in the environment, or "
            "set MUTATION_AUTH=0 for an intentionally open local instance."
        )


async def _auto_verify_loop() -> None:
    """Re-check staleness every 24h (the boot check happens in `lifespan`).

    Weekly liveness IS the product, and this is its only trigger inside a
    long-running process: the previous boot-only call meant a container that
    never restarts never re-verified. `start_verification` already refuses a
    second in-flight pass, so an overlapping manual run is a no-op here.
    """
    while True:
        await asyncio.sleep(AUTO_VERIFY_INTERVAL_S)
        try:
            await asyncio.to_thread(_maybe_auto_verify)  # sqlite off the event loop
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — a bad tick must not kill the loop
            log.exception("auto-verify tick failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_auth_config()
    db.init_db()
    # canonical_domain backfill (2026-09-22): the column existed since the 43-col
    # migration but nothing wrote it (1,258/1,258 NULL). Every intake path now
    # writes it; this one-time pass fills the rows admitted before that. Idempotent
    # and chunked — a fully-populated archive makes it a single indexed SELECT.
    try:
        _conn = db.connect()
        try:
            _filled = enrich.backfill_canonical_domains(_conn)
            # Phase P: the FTS index (a candidate generator for /api/search).
            # ensure() is a no-op in the steady state; it rebuilds only when the
            # schema version moved (a deploy) or the index is missing. A build
            # without FTS5 logs and keeps the linear scan.
            _rebuilt = fts.ensure(_conn)
            if _rebuilt:
                log.info("fts index rebuilt (schema version %s)", fts.FTS_SCHEMA_VERSION)
        finally:
            _conn.close()
        if _filled:
            log.info("canonical_domain backfill: %d rows filled", _filled)
    except Exception as exc:  # noqa: BLE001 — a backfill failure must not block boot
        log.warning("canonical_domain/fts boot step skipped: %s", exc)
    # F-10: the founder store is its own file and its own schema. Creating it at
    # boot (not lazily on first write) means a broken FOUNDER_DB_PATH fails here,
    # loudly, instead of on a founder's first request.
    founder.init_founder_db()
    # Same reasoning for the LLM gateway settings (which provider is active, and
    # its key/model overrides): its own file, created at boot so a broken
    # SETTINGS_DB_PATH fails here rather than on the first seed.
    gateways.init_settings_db()
    seeder.recover_interrupted_jobs()  # restart recovery: queued/running → failed(interrupted)
    log.info(
        "starting: mutation_auth=%s rate_limit=%s admin=%s",
        config.MUTATION_AUTH, config.RATE_LIMIT_ENABLED, bool(config.ADMIN_TOKEN),
    )
    # Boot check runs synchronously: by the time the app serves its first
    # request, an overdue archive already has its pass queued. The loop then
    # only handles the recurring ticks.
    _maybe_auto_verify()
    verify_task = asyncio.create_task(_auto_verify_loop())
    try:
        yield
    finally:
        verify_task.cancel()


def _maybe_auto_verify() -> None:
    """Set-and-forget: if the archive hasn't been checked recently (or at all),
    enqueue a verification pass. Fails quietly on any guard — the 24h loop
    above and the manual button are the triggers."""
    days = config.VERIFY_AUTO_STALE_DAYS
    if days <= 0:
        return
    conn = db.connect()
    try:
        # Stale = never checked, or last check older than the threshold.
        stale = conn.execute(
            "SELECT COUNT(*) AS c FROM startups "
            "WHERE last_checked IS NULL OR last_checked < datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()["c"]
    finally:
        conn.close()
    if stale == 0:
        return
    try:
        job_id = verify.start_verification()
    except RuntimeError:
        return  # a pass is already queued/running — nothing to do
    log.info("auto-verify: %s stale entries → verify job %s", stale, job_id)


app = FastAPI(title="IdeaExists API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # FRONTEND_ORIGIN may be a comma-separated list (e.g. both the
    # localhost: and 127.0.0.1: spellings of the dev frontend).
    allow_origins=[o.strip() for o in config.FRONTEND_ORIGIN.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token", "X-Founder-Token"],
)
# /api/startups returns the whole archive on every page load (the frontend
# filters client-side). Measured at 1,292 rows: 950 KiB raw -> 225 KiB gzipped
# (4.2x, not the "roughly 10x" this comment once claimed — description prose
# doesn't compress well). JSON.parse ~1ms; ~3-5MB memory. The real cost curve
# is client-side Fuse search (linear in rows; ~22ms/term at 1,292), so the
# pleasant ceiling is ~3,000 rows — see LIST_LIMIT_DEFAULT.
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """Minimal security headers on every API response (additive)."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    return resp


# --- Rate limiting: per-IP sliding window on mutating/admin endpoints ---
_RATE: dict[tuple[str, str], deque] = defaultdict(deque)
_RATE_LOCK = threading.Lock()


def rate_limited(bucket: str, limit: int, window_s: float = 60.0):
    """FastAPI dependency — at most `limit` requests per IP per window.

    Guards the token gate (brute force), the mutating endpoints (abuse / cost
    burn) and the heavy-read endpoints (full-archive scan floods). Public reads
    get a generous bucket (120/min) — humans never notice, scrapers do.
    """

    def dep(request: Request) -> None:
        if not config.RATE_LIMIT_ENABLED:
            return
        key = (bucket, request.client.host if request.client else "unknown")
        now = time.monotonic()
        with _RATE_LOCK:
            q = _RATE[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(status_code=429, detail="Too many requests — slow down a little")
            q.append(now)
            _evict_idle(_RATE, now, window_s)

    return dep


def _evict_idle(store: dict, now: float, window_s: float) -> None:
    """Drop keys whose window has fully expired.

    Without this the per-IP dicts grow forever: entries are trimmed inside
    their window but the key itself is never removed, so every distinct source
    IP leaks a dict entry for the life of the process. Caller holds the lock.

    ponytail: full sweep per request, O(active IPs in the window) — fine at
    this scale. If the key count ever gets large, sweep every Nth call instead.
    """
    stale = [k for k, q in store.items() if not q or now - q[-1] > window_s]
    for k in stale:
        del store[k]


# --- Failed-auth lockout: counts *failed* admin-token checks per IP so a
# brute-force guesser burns quota, while legitimate (successful) usage and
# read polling are never throttled. ---
_FAILS: dict[tuple[str, str], deque] = defaultdict(deque)
_FAILS_LOCK = threading.Lock()


def _note_failed_auth(request: Request, bucket: str = "admin", limit: int = 10, window_s: float = 60.0) -> None:
    if not config.RATE_LIMIT_ENABLED:
        return
    key = (bucket, request.client.host if request.client else "unknown")
    now = time.monotonic()
    with _FAILS_LOCK:
        q = _FAILS[key]
        while q and now - q[0] > window_s:
            q.popleft()
        q.append(now)
        over = len(q) > limit
        _evict_idle(_FAILS, now, window_s)
        if over:
            raise HTTPException(status_code=429, detail="Too many failed attempts — try again later")


class GithubSeedIn(BaseModel):
    # Length caps are DoS hygiene, not validation: over-long values are 422s
    # instead of oversized fetch targets / DB writes downstream.
    github_url: str = Field(max_length=2000)


class WebsiteSeedIn(BaseModel):
    website_url: str = Field(max_length=2000)
    name: str | None = Field(default=None, max_length=120)


class SeedIn(BaseModel):
    source: str = Field(max_length=64)
    params: dict = {}


class FounderAppIn(BaseModel):
    """The founder's own app — three input shapes, one endpoint.

    URL   `url` (plus an optional `name_hint`) → the website draft primitive.
    Form  the flat fields below, with `features` REQUIRED (5-10, F-11).
    Agent `agent_json` (pasted text) or `agent` (already-parsed object), the
          shape in docs/teardown-spec.md §3 plus the links block (F-12).

    Consent is NOT a field here: publishing runs through
    `POST /api/founder-app/{id}/publish`, after a confirm (F-13). A `publish`
    key is refused rather than ignored — see `_no_publish_flag` — so no client
    can believe it published something it did not. Nothing is auto-confirmed.
    """

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _no_publish_flag(cls, data):
        """`publish` was accepted on this endpoint until 2026-09-15 and could
        never succeed: the draft is created in this same request, so it is
        never confirmed by the time the consent gate runs — every such call
        answered 400 *after* writing the row, which is a partial write dressed
        as a no-op, and a retrying client wrote a second draft. Consent is its
        own call now, and an old client is told exactly that instead of being
        silently ignored."""
        if isinstance(data, dict) and "publish" in data:
            raise ValueError(
                "publish is not accepted here — create the draft, confirm it, then "
                "POST /api/founder-app/{id}/publish"
            )
        return data

    url: str | None = Field(default=None, max_length=2000)
    name_hint: str | None = Field(default=None, max_length=120)
    agent_json: str | None = Field(default=None, max_length=20000)
    agent: dict | None = None
    # form path
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    target_user: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=40)
    features: list[str] | None = Field(default=None, max_length=20)
    positioning: str | None = Field(default=None, max_length=1000)
    pricing: dict | None = None
    website_url: str | None = Field(default=None, max_length=2000)
    github_url: str | None = Field(default=None, max_length=2000)
    app_store_url: str | None = Field(default=None, max_length=2000)
    play_store_url: str | None = Field(default=None, max_length=2000)


class RejectIn(BaseModel):
    note: str = Field(max_length=2000)


class GatewaySettingsIn(BaseModel):
    """A partial patch of one gateway's stored settings.

    Omitting a field leaves it alone; sending it as `null` (or `""`) CLEARS the
    override so it falls back to the environment and then the registry default.
    That distinction is why this model does not simply default every field to
    None — the endpoint reads `model_dump(exclude_unset=True)`.
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)


class ActiveGatewayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gateway_id: str = Field(max_length=64)


class CompareIn(BaseModel):
    """`{you: {...}, competitors: [...]}` (F-15).

    The sides are NAMED rather than passed as one flat id list: the `you` record
    lives in the founder store (`FOUNDER_DB_PATH`) and the competitors in the
    archive, so a bare `id=7` is ambiguous across the two files.  Each reference
    may be an id, a slug, or a `{id|slug|...}` object; the resolver accepts both.
    """

    you: Any = None
    competitors: list[Any] = []


def require_admin(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    """Owner gate: ADMIN_TOKEN from the environment — fails loudly (403), never
    silently. Failed attempts are counted per IP (10/min) so brute-forcing the
    token is throttled to a crawl."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(403, "Admin disabled — set ADMIN_TOKEN in backend/.env")
    # compare_digest requires ASCII-only str inputs — Starlette decodes header
    # bytes as latin-1, so a non-ASCII token would raise TypeError (500)
    # instead of the intended 403. Compare as bytes.
    supplied = (x_admin_token or "").encode("utf-8", "surrogateescape")
    expected = config.ADMIN_TOKEN.encode("utf-8")
    if not x_admin_token or not hmac.compare_digest(supplied, expected):
        _note_failed_auth(request)
        raise HTTPException(403, "Invalid admin token")


def require_mutation_auth(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    """Mutations stay open by default (local-first UX — the status pill and Add
    dialog work without unlocking admin). When MUTATION_AUTH=1 they demand the
    same admin token as the admin router. Hosting MUST set MUTATION_AUTH=1."""
    if not config.MUTATION_AUTH:
        return
    require_admin(request, x_admin_token)


def check_founder_token(founder_row, x_founder_token: str | None) -> None:
    """Per-draft ownership gate: the draft's creation response carried a
    one-time `founder_token`, and every later read/mutation of that draft must
    present it as `X-Founder-Token`.

    Without this, sequential integer ids are enumerable — anyone could read
    another founder's draft, submission history and rejection notes, or run
    paid (LLM/fetch) comparisons against it. Drafts created before per-draft
    tokens existed carry no hash and stay accessible (local-upgrade path)."""
    if founder_row is None:
        return
    if founder.verify_access_token(founder_row, x_founder_token):
        return
    raise HTTPException(403, "Invalid founder token for this draft")


def _sanitized_502(exc: Exception, what: str) -> HTTPException:
    """Upstream (fetch/LLM/provider) failures become a generic 502.

    The provider's own text can carry internal URLs, key hints or attacker
    reflection — it belongs in the server log (for the operator) rather than
    in a response body (for any caller). Input-guidance 400s are unaffected:
    those are our own words, not upstream text.
    """
    log.warning("%s failed: %s", what, exc)
    return HTTPException(
        status_code=502,
        detail=f"{what} failed — check the URL and try again",
    )


admin = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


@admin.get("/check", dependencies=[Depends(rate_limited("admin_check", 20, 60))])
def admin_check() -> dict:
    return {"ok": True}


@admin.post("/seed", dependencies=[Depends(rate_limited("admin_seed", 20, 60))])
def start_seed(body: SeedIn) -> dict:
    try:
        job_id = seeder.start_job(body.source, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id}


@admin.get("/seed/status/{job_id}")
def seed_status(job_id: str) -> dict:
    job = seeder.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@admin.get("/seed/jobs")
def seed_jobs() -> list[dict]:
    """Every seed job — active first (running, then queued), then finished.
    The panel re-attaches to live progress on open via this list."""
    return seeder.list_jobs()


class ApproveIn(BaseModel):
    ids: list[int] | None = Field(default=None, max_length=1000)
    approve_all: bool = False
    created_after: str | None = Field(default=None, max_length=32)
    created_before: str | None = Field(default=None, max_length=32)


class FunnelImportIn(BaseModel):
    """The `run` field is a server-local directory produced by the audit tool.

    Deliberately NOT an arbitrary path: funnel runs are directories the tool
    writes beside the repo (default `./liveness-out`, or the operator's
    --out root), and this API is how the operator hands one to the app. The
    validators refuse anything else — absolute paths outside the repo, `..`
    escapes, and Windows UNC device/`\\host\share` paths — because an
    unconstrained path would let the server probe arbitrary filesystem
    locations and, on Windows, authenticate to an attacker-chosen SMB host
    (NetNTLMv2 coercion). Import by copying the run under the repo first.
    """

    run: str = Field(min_length=1, max_length=1000)
    dry_run: bool = True
    # Sequence 4: an explicit operator override for a run whose recorded QA
    # false-approval rate breaches the budget. Only meaningful when actually
    # applying (dry_run=false); validated below so a nonsense combination
    # (dry-run + override) is rejected rather than silently ignored.
    allow_qa_breach: bool = False

    @model_validator(mode="after")
    def _run_must_be_local(self) -> "FunnelImportIn":
        from .funnel import run_dir_is_importable  # local import, no cycle

        problems = run_dir_is_importable(self.run)
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @model_validator(mode="after")
    def _override_needs_apply(self) -> "FunnelImportIn":
        if self.allow_qa_breach and self.dry_run:
            raise ValueError(
                "allow_qa_breach only applies with dry_run=false — a dry-run "
                "plan is never blocked by the budget, so there is nothing to "
                "override")
        return self



@admin.post("/funnel/import", dependencies=[Depends(rate_limited("funnel_import", 10, 60))])
def admin_funnel_import(body: FunnelImportIn) -> dict:
    """Apply a completed liveness-funnel run (`scripts/site_liveness_audit.py
    audit --out ...`): ADMIT the clean LIVE majority via the machine stamp
    (verify.approve_machine — approval_source='machine', the stage that admitted
    it in approved_by, and the run + reason as the approval_note receipt), QUEUE
    the exception rows (walled / unknown / moved / banned / non-company / free
    host) for the human path, and IGNORE dead/repurposed rows — removal stays
    with the tool's own `drop` command and its brakes.

    Admission only: this endpoint never deletes and never dead-flips. Dry-run is
    the default and reports what WOULD match the admission guard. Re-importing a
    run is a no-op (the guard only stamps verified=0 rows).
    """
    try:
        return funnel.import_run(
            body.run, dry_run=body.dry_run, allow_qa_breach=body.allow_qa_breach)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@admin.get("/verify/suggested")
def admin_suggested() -> list[dict]:
    """Human-approval queue — entries the automated check considers alive (or
    never checked) that no human has stamped yet, UNIONED with the founder
    store's pending submissions (F-24).

    `verify.list_suggested()` reads the archive only; a submission living in
    another FILE does not appear there on its own, so the union happens here.
    Every row carries `kind` so the panel can render the two differently and
    post a decision to the right endpoint.
    """
    rows = [{**row, "kind": "archive"} for row in verify.list_suggested()]
    for sub in founder.pending_submissions():
        rows.append(
            {
                "kind": "founder_submission",
                "id": sub["submission_id"],
                "submission_id": sub["submission_id"],
                "founder_app_id": sub["founder_app_id"],
                "name": sub["name"],
                "website_url": sub["website_url"],
                "github_url": sub["github_url"],
                "app_store_url": sub["app_store_url"],
                "play_store_url": sub["play_store_url"],
                "category": sub["category"],
                "last_checked": None,
                "created_at": sub["submitted_at"],
            }
        )
    return rows


@admin.post("/verify/approve", dependencies=[Depends(rate_limited("approve", 60, 60))])
def admin_approve(body: ApproveIn) -> dict:
    """Bulk human gate: stamp verified=1 on the given ids, every suggested
    row, or every suggested row in a created_at window (the batch boundary
    for "approve this seed run"). One of three writers of verified=1 (this, the single-row
    /verify endpoint, and verify.approve_machine) —
    only this path and the single-row
    endpoint stamp approval_source='human'; a machine admission is stamped
    'machine' and compare.badges withholds Admin Verified from it."""
    if body.approve_all:
        n = verify.approve_suggested(approve_all=True)
    elif body.ids:
        n = verify.approve_suggested(ids=body.ids)
    elif body.created_after or body.created_before:
        n = verify.approve_suggested(
            created_after=body.created_after, created_before=body.created_before
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide ids, approve_all=true, or a created_after/created_before window",
        )
    return {"approved": n}


# --- founder submissions: the same admin gate as competitors (F-24) ---
@admin.get("/founder/submissions")
def admin_founder_submissions() -> dict:
    """Pending publish requests from the founder store. Admin-gated: the payload
    carries the founder's own draft, which is nobody else's business."""
    return {"pending": founder.pending_submissions()}


@admin.post("/founder/submissions/{submission_id}/approve", dependencies=[Depends(rate_limited("founder_decide", 60, 60))])
def admin_founder_approve(submission_id: int) -> dict:
    """Approve a publish request: the archive row is created through the normal
    seed writer and its id is recorded as the cross-store link."""
    if not founder.get_submission(submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")
    try:
        return founder.approve_submission(submission_id, decided_by="admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin.post("/founder/submissions/{submission_id}/reject", dependencies=[Depends(rate_limited("founder_decide", 60, 60))])
def admin_founder_reject(submission_id: int, body: RejectIn) -> dict:
    """Reject with a note the founder can read. A resubmission is a new row."""
    if not founder.get_submission(submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")
    try:
        return founder.reject_submission(submission_id, body.note, decided_by="admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- LLM gateways: which provider the backend calls, and with which key -----
# The registry lives in app/gateways.py; these routes are the admin panel's view
# of it. Two invariants hold across all of them, and they are the reason the
# routes exist in this shape:
#
#   * a stored key is WRITE-ONLY — responses carry `has_key`, `key_source` and a
#     4-character `key_hint`, never the value;
#   * the secret never travels in a URL or a log line (see gateways.py).
@admin.get("/settings/gateways", dependencies=[Depends(rate_limited("settings_read", 60, 60))])
def admin_gateways() -> dict:
    """Every known gateway, what the operator has overridden, and what is in
    effect right now. This is the panel's settings screen."""
    return gateways.list_gateways()


@admin.get("/settings/gateways/{gateway_id}")
def admin_gateway(gateway_id: str) -> dict:
    try:
        return gateways.public_view(gateway_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin.put(
    "/settings/gateways/{gateway_id}",
    dependencies=[Depends(rate_limited("settings_write", 30, 60))],
)
def admin_update_gateway(gateway_id: str, body: GatewaySettingsIn) -> dict:
    """Patch one gateway: paste a key, override the model or base URL, or clear
    an override. Nothing here takes effect on the archive until the gateway is
    made active — or immediately, if it already is."""
    payload = body.model_dump(exclude_unset=True)
    kwargs = {key: payload[key] for key in ("api_key", "model", "base_url")
              if key in payload}
    try:
        return gateways.update_gateway(gateway_id, **kwargs)
    except ValueError as exc:
        detail = str(exc)
        status = 404 if detail.startswith("unknown gateway") else 400
        raise HTTPException(status_code=status, detail=detail) from exc


@admin.post(
    "/settings/gateways/active",
    dependencies=[Depends(rate_limited("settings_write", 30, 60))],
)
def admin_set_active_gateway(body: ActiveGatewayIn) -> dict:
    """Switch the gateway every LLM call uses (seeds AND teardown captures).

    Refused with a 400 when the chosen gateway has no usable key or model:
    making it active would silently break every seed and capture, and a loud
    refusal before the switch is worth more than a broken product after it.
    """
    try:
        return gateways.set_active(body.gateway_id)
    except ValueError as exc:
        detail = str(exc)
        status = 404 if detail.startswith("unknown gateway") else 400
        raise HTTPException(status_code=status, detail=detail) from exc


@admin.post(
    "/settings/gateways/active/reset",
    dependencies=[Depends(rate_limited("settings_write", 30, 60))],
)
def admin_reset_active_gateway() -> dict:
    """Go back to the gateway `backend/.env` describes."""
    return gateways.clear_active()


@admin.post(
    "/settings/gateways/{gateway_id}/test",
    dependencies=[Depends(rate_limited("gateway_test", 10, 60))],
)
def admin_test_gateway(gateway_id: str) -> dict:
    """One real, tiny completion against a gateway — the panel's "Test" button.

    Works on a gateway that is NOT active, so a key can be checked before it is
    switched in. Never raises: a bad key, a wrong model or an unreachable host
    all come back as `ok: false` with the provider's own text, because that is
    the information the operator actually needs.
    """
    try:
        gateways.public_view(gateway_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return gateways.test_gateway(gateway_id)


# --- just-in-time capture (F-22): admin-gated, because a job payload carries
# error strings and fetched URLs. There is deliberately no PUBLIC job endpoint.
@admin.post("/capture/{startup_id}", dependencies=[Depends(rate_limited("capture", 30, 60))])
def admin_start_capture(startup_id: int) -> dict:
    """Trigger a capture by hand (the panel's button; Phase 3 wires the founder
    request). Idempotent inside the freshness window and while one is in flight."""
    state = capture.start_capture(startup_id)
    if state.get("state") == "not_found":
        raise HTTPException(status_code=404, detail="Startup not found")
    return state


@admin.get("/capture/status/{job_id}")
def admin_capture_status(job_id: str) -> dict:
    job = capture.get_capture_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "llm_model": config.LLM_MODEL,
        "db": config.DB_PATH.name,
    }


# The client holds everything and filters client-side (Fuse). The knee where
# that architecture stops feeling instant is ~3,000 rows (measured: 22ms/term
# at 1,292, 35ms at 2,500, 70ms at 5,000 on desktop) — so the default ceiling
# sits at the knee, with MAX as an explicit opt-in. When the limit bites, the
# response is truncated with HTTP 200: the frontend detects it via
# startups.length < /api/stats.total and banners it (search/filters only cover
# the rows shown).
# ponytail: when the archive outgrows ~3,000 rows, move SEARCH server-side
# (SQLite FTS5 + bm25) — not offset pagination, which the directory UX doesn't
# need. This marker shows up in /ponytail-debt.
LIST_LIMIT_DEFAULT, LIST_LIMIT_MAX = 3000, 5000


def _like_escape(term: str) -> str:
    """Escape LIKE metacharacters so a search term matches literally.

    The value is already parameterized (no injection), but LIKE still
    interprets its wildcards: `q=%` would return the entire table and
    `%a%a%a…` is a cheap scan amplifier.
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/api/startups")
def list_startups(
    category: str | None = Query(default=None, max_length=40),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(LIST_LIMIT_DEFAULT, ge=1, le=LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    response: Response = None,  # type: ignore[assignment]
    _rl: None = Depends(rate_limited("read", 120, 60)),
) -> list[dict]:
    """The archive. The frontend pulls this once and filters client-side, so
    the default limit is a growth ceiling rather than real pagination: once
    the row count passes LIST_LIMIT_DEFAULT the response is truncated (still
    HTTP 200) and the frontend detects it against /api/stats. Tombstones sink
    first — both 'dead' AND 'pivoted' — so truncation never promotes them.

    SHAPE CONTRACT (pinned by a functional test): a bare JSON list. The Phase P
    envelope lives on /api/startups/page — this endpoint is deliberately left
    untouched so every existing consumer keeps working. The only addition is
    the X-Total-Count header (harmless, additive).
    """
    rows, total = _archive_page(category=category, q=q, limit=limit, offset=offset)
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return rows


def _archive_page(
    *, category: str | None, q: str | None, limit: int, offset: int,
    year: str | None = None, status: str | None = None,
) -> tuple[list[dict], int]:
    """One query builder for BOTH list endpoints, so they cannot drift.

    Returns (rows, total) where total is the filtered-row count (the envelope's
    `total`, and the X-Total-Count header). Tombstones sink first — both 'dead'
    AND 'pivoted' — so any window of the paging order leads with live rows.
    """
    conn = db.connect()
    try:
        conds: list[str] = []
        params: list = []
        if category:
            conds.append("category = ?")
            params.append(category)
        if q:
            conds.append(
                "(name LIKE ? ESCAPE '\\' OR tagline LIKE ? ESCAPE '\\' "
                "OR description LIKE ? ESCAPE '\\')"
            )
            params += [f"%{_like_escape(q)}%"] * 3
        if year:
            conds.append("founded LIKE ? ESCAPE '\\'")  # year prefix: "2024" -> "2024%"
            params.append(f"{_like_escape(year)}%")
        if status:
            conds.append("status = ?")
            params.append(status)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        order = (" CASE status WHEN 'dead' THEN 1 WHEN 'pivoted' THEN 1 ELSE 0 END,"
                 " name COLLATE NOCASE")
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM startups{where}", params).fetchone()["c"]
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM startups{where} ORDER BY{order} LIMIT ? OFFSET ?",
            [*params, limit, offset]).fetchall()]
        return rows, total
    finally:
        conn.close()


@app.get("/api/startups/page")
def list_startups_page(
    category: str | None = Query(default=None, max_length=40),
    q: str | None = Query(default=None, max_length=200),
    year: str | None = Query(default=None, min_length=4, max_length=10),
    status: str | None = Query(default=None, pattern="^(active|verified|unverified|dead|pivoted)$"),
    limit: int = Query(300, ge=1, le=LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    _rl: None = Depends(rate_limited("read", 120, 60)),
) -> dict:
    """The paged archive (Phase P, scale-plan §7.1): an explicit envelope
    instead of a truncation a client has to detect.

    {total, limit, offset, rows} — `total` is the FILTERED row count, so a
    pager renders exact page counts per facet combination, and offset+limit
    walks the full set with stable ordering (tombstones sink). `year` filters
    on the founded-year prefix and `status` on the row status — the facets the
    home page applies client-side today, exposed server-side so Phase P's
    frontend window can move them behind this endpoint later without a new
    contract.

    Additive by design: /api/startups is untouched (shape pinned by a test);
    this endpoint is the only one a pager needs.
    """
    rows, total = _archive_page(
        category=category, q=q, year=year, status=status, limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "rows": rows}


@app.get("/api/search")
def search(
    q: str | None = Query(
        default=None,
        max_length=200,
        description="free-text query; split into words, all of which must match",
    ),
    limit: int = Query(LIST_LIMIT_DEFAULT, ge=1, le=LIST_LIMIT_MAX),
    _rl: None = Depends(rate_limited("read", 120, 60)),
) -> list[dict]:
    """Classified search with a per-result reason (F-18).

    The server-side escape hatch for the client-side Fuse path (which stays as
    it is — Phase 6 switches to this endpoint without changing what a user
    sees). Ordered by the plan's ladder: exact name → exact domain →
    phrase/name → tagline → problem-description → category/keyword → fuzzy,
    with dead/pivoted rows last and stars as a tie-break only. See
    `app/search.py` for the ladder's mapping onto the columns that exist today,
    the frozen reason vocabulary and the divergences from lib/search.ts.

    EMPTY-QUERY CONTRACT (documented + tested): a missing, blank, whitespace-only
    or punctuation-only `q` (`%`, `_`) returns 200 with an EMPTY list. It is not
    an error (the UI clears the box without a banner), it is never the whole
    archive, and it is not an accident of a LIKE '%%' — the query is split into
    word terms and a query with no terms has nothing to match. A distinct 4xx
    was the alternative; the empty shape was chosen so "no query" and "no
    matches" are the same, harmless state for a live search box.

    LIKE-ESCAPE: this route builds no SQL at all, so a metacharacter cannot
    become a wildcard by construction. `/api/startups` keeps its own
    `_like_escape` (that path still uses LIKE) and is untouched.

    PURE READ: unlike `/api/compare`, a search never triggers the JIT capture
    (F-22). It reads stored data only — a search that fetched pages and called
    the LLM would be slow, non-deterministic and expensive on every keystroke.

    ponytail: linear scan in Python (app.search). Pleasant to ~3,000 rows, the
    same knee as the client path (LIST_LIMIT_DEFAULT); FTS5 + bm25 is the next
    step when the archive outgrows it, not a bigger scan.
    """
    if not search_mod.query_terms(q):
        return []  # the documented empty-query contract
    conn = db.connect()
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM startups").fetchall()]
    finally:
        conn.close()
    # Archive rows only — the founder store is a different file and is never
    # read here (F-20).
    return search_mod.rank(rows, q, limit=limit)


@app.get("/api/categories")
def categories(_rl: None = Depends(rate_limited("read", 120, 60))) -> list[dict]:
    conn = db.connect()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT category, COUNT(*) AS count FROM startups GROUP BY category ORDER BY count DESC"
            ).fetchall()
        ]
    finally:
        conn.close()


@app.post("/api/seed/github", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("seed_url", 20, 60))])
def seed_github(body: GithubSeedIn) -> dict:
    try:
        return enrich.seed_from_github(body.github_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — upstream text stays in the server log, never in the response
        raise _sanitized_502(exc, "GitHub seed") from exc


@app.post("/api/seed/website", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("seed_url", 20, 60))])
def seed_website(body: WebsiteSeedIn) -> dict:
    try:
        return enrich.seed_from_website(body.website_url, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _sanitized_502(exc, "Website seed") from exc


@app.post("/api/founder-app", dependencies=[Depends(rate_limited("founder_app_create", 10, 60))])
def create_founder_app(body: FounderAppIn) -> dict:
    """Draft the founder's own app into the FOUNDER store (F-10/F-11/F-12).

    Deliberately NOT behind the admin token: this path cannot write the archive
    (F-20), so the token that guards archive mutations would only stand between
    a founder and their own local draft. It is rate-limited all the same — and
    creation is limited tighter (10/min) than confirm/publish, because the URL
    path triggers an outbound fetch plus an LLM call on every hit.

    Nothing is auto-confirmed. Consent is a separate call —
    `POST /api/founder-app/{id}/publish` — because the eligibility rule is
    evaluated first and a link-less app is never even asked (F-20).
    """
    try:
        if body.agent_json or body.agent is not None:
            result = founder.create_from_agent_json(body.agent_json or body.agent)
        elif body.url:
            result = founder.create_from_url(body.url, body.name_hint)
        else:
            result = founder.create_from_form(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — a fetch/LLM failure on the URL path
        raise _sanitized_502(exc, "Founder draft") from exc
    return result


@app.get("/api/founder-app/{founder_app_id}")
def get_founder_app(founder_app_id: int, x_founder_token: str | None = Header(default=None)) -> dict:
    """The founder's own draft, plus the two gates and the derived
    `archive_status`. Local read — there are no accounts, so there is no
    notification: the status is what makes a rejected request visible.

    Gated by the draft's own token (X-Founder-Token, issued once at creation):
    sequential ids must not be enumerable into other founders' drafts."""
    row = founder.get(founder_app_id)
    if not row:
        raise HTTPException(status_code=404, detail="Founder app not found")
    check_founder_token(row, x_founder_token)
    gates = founder.eligibility(row)
    return {
        "founder_app_id": row["id"],
        "profile": founder.profile_of(row),
        "confirmed": bool(row.get("confirmed_at")),
        "source_kind": row.get("source_kind"),
        "eligibility": gates,
        "publish_offered": gates["has_link"],
        "archive_status": founder.archive_status(row["id"]),
        "submission": founder.newest_submission(row["id"]),
        "submissions": founder.decisions(row["id"]),
    }


@app.post("/api/founder-app/{founder_app_id}/confirm", dependencies=[Depends(rate_limited("founder_app", 20, 60))])
def confirm_founder_app(founder_app_id: int, x_founder_token: str | None = Header(default=None)) -> dict:
    """The confirm-before-diff gate (F-13): flips the draft to human_confirmed
    (F-05's human half) so the gap table may run against it. Publishing stays a
    separate decision."""
    row = founder.get(founder_app_id)
    if not row:
        raise HTTPException(status_code=404, detail="Founder app not found")
    check_founder_token(row, x_founder_token)
    try:
        return founder.confirm(founder_app_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/founder-app/{founder_app_id}/publish", dependencies=[Depends(rate_limited("founder_app", 20, 60))])
def publish_founder_app(founder_app_id: int, x_founder_token: str | None = Header(default=None)) -> dict:
    """The consent gate on its own (the checkbox ticked after a confirm).

    Eligibility first: no link means comparison-only, and no consent question is
    asked at all (F-20).
    """
    row = founder.get(founder_app_id)
    if not row:
        raise HTTPException(status_code=404, detail="Founder app not found")
    check_founder_token(row, x_founder_token)
    try:
        return founder.request_publish(founder_app_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/verify/run", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("verify_run", 10, 60))])
def run_verification() -> dict:
    """Enqueue a verification pass — returns immediately with a job_id; poll
    /api/verify/status/{job_id} for progress. Serialized on the seed queue."""
    try:
        job_id = verify.start_verification()
    except RuntimeError as exc:  # a verify pass is already queued/running
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": job_id}


@admin.get("/verify/status/{job_id}")
def verify_status(job_id: str) -> dict:
    """Admin-gated: the job payload carries error strings and seeded URLs."""
    job = verify.get_verify_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@admin.get("/verify/current")
def verify_current() -> dict | None:
    """The active (queued/running) verification job, or None. Lets the panel
    re-attach to a pass already in flight (scheduler-triggered or from an
    earlier click) instead of starting a second one.

    Admin-gated: this walks the whole jobs table and JSON-parses every row, and
    the payload leaks job errors + seeded URLs. Only the panel consumes it.
    """
    return verify.get_active_verify_job()


@app.post("/api/startups/{startup_id}/verify", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_verified(startup_id: int) -> dict:
    """Human gate: confirm a startup exists → verified badge + verified_at.

    Also revives a filed entry: a human confirming a dead site is alive
    un-files it (status back to 'active') and RESETS the strike counter —
    human judgment outranks automation (a revive is a fresh start, not a
    continuation of the old streak).
    """
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now'), "
            "status = 'active', check_failures = 0, "
            "approval_source = 'human', approved_by = 'admin' WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.post("/api/startups/{startup_id}/unverify", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_unverified(startup_id: int) -> dict:
    """Human gate: revoke the verified stamp → back to unverified (active)."""
    conn = db.connect()
    try:
        cur = conn.execute(
            # Clear the provenance with the stamp: a withdrawn admission must not
            # leave a stale 'human'/'machine' marker behind for the badges to read.
            "UPDATE startups SET verified = 0, verified_at = NULL, status = 'active', "
            "approval_source = NULL, approved_by = NULL WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.post("/api/startups/{startup_id}/dead", dependencies=[Depends(require_mutation_auth), Depends(rate_limited("mutate", 60, 60))])
def mark_dead(startup_id: int) -> dict:
    """Human gate: file as dead — checked and gone. Filed, never deleted."""
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE startups SET status = 'dead', verified = 0, verified_at = NULL WHERE id = ?",
            (startup_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Startup not found")
        conn.commit()
        row = conn.execute("SELECT * FROM startups WHERE id = ?", (startup_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.get("/api/stats")
def stats(_rl: None = Depends(rate_limited("read", 120, 60))) -> dict:
    conn = db.connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) AS c FROM startups WHERE verified = 1").fetchone()["c"]
        dead = conn.execute("SELECT COUNT(*) AS c FROM startups WHERE status = 'dead'").fetchone()["c"]
        last = conn.execute("SELECT MAX(last_checked) AS m FROM startups").fetchone()["m"]
        return {"total": total, "verified": verified, "dead": dead, "last_checked": last}
    finally:
        conn.close()


# --- Phase 3: comparison, gap table, exports and the stable slug endpoint ----
# The cross-store diff runs in Python (compare.py): the two sides live in two
# different files and the band logic is not expressible as SQL.  These routes
# read the founder store only for the ONE founder record the caller named — the
# archive endpoints above are untouched and never learn the founder store exists.


def _resolve_you_or_4xx(ref, x_founder_token: str | None = None) -> dict:
    fid = compare_mod.founder_ref_to_id(ref)
    if fid is None:
        raise HTTPException(
            status_code=400,
            detail="'you' must name a founder app (founder id, or its name slug)",
        )
    row = founder.get(fid)
    if not row:
        raise HTTPException(status_code=404, detail=f"founder app {fid} not found")
    # The `you` side is the founder's own draft — comparing or exporting
    # against someone else's draft (and triggering a paid JIT capture for it)
    # must require that draft's token, same as reading it.
    check_founder_token(row, x_founder_token)
    return row


def _assert_confirmed(founder_row) -> None:
    """F-13: the gap table never runs against an unconfirmed draft.  Surfaced as
    an explicit state, never a generic 500 or a silently empty table."""
    try:
        founder.assert_comparable(founder_row["id"])
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"state": "not_confirmed", "message": str(exc)},
        ) from exc


def _resolve_competitors(refs) -> list:
    refs = list(refs or [])
    if not refs:
        raise HTTPException(status_code=400, detail="at least one competitor is required")
    if len(refs) > compare_mod.MAX_COMPETITORS:
        raise HTTPException(
            status_code=400,
            detail=f"at most {compare_mod.MAX_COMPETITORS} competitors are allowed",
        )
    conn = db.connect()
    try:
        rows = []
        for ref in refs:
            row = compare_mod.resolve_startup(conn, ref)
            if not row:
                raise HTTPException(status_code=404, detail=f"competitor not found: {ref!r}")
            rows.append(row)
    finally:
        conn.close()
    return rows


def _split_refs(values) -> list[str]:
    """Accept `?competitors=a&competitors=b` and `?competitors=a,b` alike."""
    out: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _capture_or_retry(competitor_rows):
    """JIT capture (F-22), the wiring Phase 2 left open: the first founder
    request for a competitor triggers the capture.  Until it lands the caller
    gets the explicit queued/in-progress state and retries — never a partial
    teardown.  Returns a retry payload dict, or None when every competitor is
    served from cache and the table may be built."""
    for row in competitor_rows:
        state = capture.start_capture(row["id"])
        if state.get("state") in ("queued", "in_progress"):
            return {
                "state": state["state"],
                "message": state.get("message"),
                "startup_id": state.get("startup_id"),
            }
    return None


@app.post("/api/compare", dependencies=[Depends(rate_limited("compare", 60, 60))])
def api_compare(body: CompareIn, x_founder_token: str | None = Header(default=None)) -> dict:
    """The gap table (F-15): refuse an unconfirmed `you`, capture any competitor
    whose teardown is missing or stale, then diff the two stores in Python."""
    you_row = _resolve_you_or_4xx(body.you, x_founder_token)
    _assert_confirmed(you_row)
    competitor_rows = _resolve_competitors(body.competitors)
    retry = _capture_or_retry(competitor_rows)
    if retry:
        retry["you"] = {"founder_app_id": int(you_row["id"]), "name": you_row["name"]}
        retry["competitors"] = [{"id": int(r["id"]), "name": r["name"]} for r in competitor_rows]
        return retry
    conn = db.connect()
    try:
        return compare_mod.build_table(you_row, competitor_rows, conn)
    finally:
        conn.close()


@app.get("/api/export/{fmt}")
def api_export(
    fmt: str,
    you: str = Query(..., description="founder app id or name slug", max_length=200),
    competitors: list[str] = Query(default=[], description="competitor id/slug, repeatable or comma-separated", max_length=200),
    x_founder_token: str | None = Header(default=None),
    _rl: None = Depends(rate_limited("export", 60, 60)),
) -> Response:
    """The three exports (F-16), shapes in `docs/gap-table-format.md` §5.

    Stateless: same inputs as `/api/compare`, recomputed here with no stored
    "last comparison", so one founder's comparison can never be read back by
    another request and re-running with the same inputs yields the same bytes.
    Pure reads — an export never triggers a capture (that is the compare path's
    side effect), so it stays deterministic.
    """
    fmt_key = (fmt or "").lower()
    if fmt_key not in compare_mod.EXPORT_FORMATS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown export format {fmt!r}; use one of {', '.join(compare_mod.EXPORT_FORMATS)}",
        )
    you_row = _resolve_you_or_4xx(you, x_founder_token)
    _assert_confirmed(you_row)
    competitor_rows = _resolve_competitors(_split_refs(competitors))
    conn = db.connect()
    try:
        table = compare_mod.build_table(you_row, competitor_rows, conn)
    finally:
        conn.close()
    text, media_type = compare_mod.render(fmt_key, table)
    return Response(
        content=text,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="gap-table.{fmt_key}"'},
    )


@app.get("/api/startups/{slug}")
def get_startup_by_slug(slug: str, _rl: None = Depends(rate_limited("read", 120, 60))) -> dict:
    """The stable per-product endpoint (F-17) the frontend's `/products/<slug>`
    route calls.  A same-name collision resolves deterministically (human-verified
    first, then the lowest id) and the payload names the row it got; the two trust
    badges are explicit fields (F-21), never inferred from a timestamp.

    The payload also carries this row's `evidence` rows.  A negative claim is an
    observation about a page (F-09, spec §8.2), so the dossier can only render a
    sourced "doesn't do" list if it can read the source URL and capture date
    behind each one.  They are attached here rather than denormalised into a
    column: `evidence` is append-only and the single writer is
    `evidence.write_evidence`, so a column would be a second copy that drifts.
    Every row carries `source_url` + `captured_at` by construction (F-02), which
    is exactly what the cell rule requires.  `evidence` is always a list — an
    uncaptured record gets `[]`, never a missing key.
    """
    conn = db.connect()
    try:
        row, candidates = compare_mod.resolve_startup_slug(conn, slug)
        if not row:
            raise HTTPException(status_code=404, detail=f"no product with slug {slug!r}")
        payload = compare_mod.startup_payload(row, candidates)
        payload["evidence"] = evidence_mod.for_startup(conn, int(row["id"]))
        return payload
    finally:
        conn.close()


# Admin router is defined above; include after all routes so it resolves at import time.
app.include_router(admin)
