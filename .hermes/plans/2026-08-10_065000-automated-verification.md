# Automated Verification (keeping the manual gate) — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the weekly verification pass reliable and automatic (background job + fixed cron), while keeping the human status pill (Verified/Unverified/Dead) as the only thing that sets the verified stamp.

**Architecture:** Verification becomes a background job in the same serial queue as seeding (never runs in parallel with a seed). `POST /api/verify/run` enqueues and returns `{job_id}` immediately; a new `GET /api/verify/status/{job_id}` reports progress; the Hermes cron script polls instead of blocking on a 600s curl. GitHub rate limits (403/429) are counted as **skipped**, never failures — only a genuine 404 increments `check_failures`. The admin panel's existing "In progress" / "Recent runs" sections show verify jobs too, since they share the job shape.

**Tech Stack:** Python 3.11 stdlib + httpx (backend), existing `seeder.py` queue, existing `verify.py` logic, bash cron script (Hermes no_agent watchdog), Next.js frontend untouched except the verify button's poll flow.

**Manual verification stays as-is:** the status pill remains the only writer of `verified=1`/`verified_at`. Automation only feeds `check_failures`, `status='dead'`, and `verify_log`. This is the product's core promise ("checked by a human, not a crawler") and must not regress.

---

## Current Context (verified against code)

- `backend/app/verify.py` — `run_verification()` loops all startups synchronously: `check_url_ok` (HTTP 2xx/3xx), `check_github_ok` (via `gh.fetch_repo`), 3 consecutive failures → `status='dead'`, logs every check to `verify_log`. Returns `{checked, ok, flagged, dead_flipped}`.
- **Flaw 1:** `check_github_ok` catches rate-limit `RuntimeError` (403/429) and returns `False` → counted as a failure → can wrongly dead-flip healthy repos after 3 rate-limited runs. GitHub unauth limit is 60 req/hr; DB has 43 github_url entries.
- **Flaw 2:** the HTTP request blocks for the whole pass (247 sequential checks × up to 15s each) — can exceed any client timeout.
- Cron exists: Hermes job `fd5b6f0e3d08` "IdeaExists weekly verification", schedule `0 6 * * 1`, no_agent, script `~/AppData/Local/hermes/scripts/ideasexist-verify.sh` — curls `POST /api/verify/run` with `-m 600` (dies on long passes), prints JSON result. Last run: **error**.
- `verify_log` records everything; nothing reads it back (opportunity for a review surface).
- Seeder (`backend/app/seeder.py`) now has a serial queue: `JOBS` dict, `_QUEUE`, single `_worker` thread, `list_jobs()`, `queue_position`. Verify jobs can reuse this machinery with a `kind` field.
- Frontend: `page.tsx` `handleVerify` awaits `runVerification()` then toasts + reloads; `api.ts` `runVerification()` POSTs and returns the result JSON.
- No `GITHUB_TOKEN` in `backend/.env` (would raise the API limit to 5,000 req/hr).

## Proposed Approach

1. **Generalize the queue** (`seeder.py`): add a `kind` field to jobs (`"seed"` | `"verify"`); `_worker` dispatches `_run` by kind. Seed jobs keep `source` = SOURCES key; verify jobs get `source = "verify"` with the standard job fields (`total` = startup count, `ok` = alive, `skipped` = rate-limited/no-op, `failed` = flagged, `errors` = "name: reason" lines, `current` = startup being checked).
2. **`verify.py`**: split into `start_verification()` (validates + enqueues a verify job through `seeder`) and `run_verify_job(job)` (the existing loop, writing progress into the job dict + tri-state GitHub check). Add `get_verify_job(id)` passthrough.
3. **`main.py`**: `POST /api/verify/run` → `{"job_id": ...}` (202-style, no blocking); `GET /api/verify/status/{job_id}` → job dict (404 if unknown).
4. **Tri-state GitHub check**: `(ok, reason, skipped)` — 404/ValueError → failed; 403/429 → skipped (no `check_failures` bump); success/archived → ok.
5. **Cron script**: POST → parse `job_id` → poll `status` until done/failed (bounded ~30 min) → print summary. Silent when backend is off (unchanged). No more 600s curl death.
6. **Frontend**: `handleVerify` starts the job, polls status every 2s, toasts on completion (same pattern as admin panel). Footer/hero "last checked" already reflects completion via reload.
7. **Backend-start auto-run (optional, default on)**: on app startup, if `last_checked` is >7 days stale and `VERIFY_AUTO=1` (default in .env), enqueue a verify job automatically.

---

## Step-by-Step Plan

### Task 1: Generalize the seeder queue with a `kind` field

**Objective:** One serial queue serves both seeds and verify jobs; no two jobs (of any kind) run in parallel.

**Files:**
- Modify: `backend/app/seeder.py`

**Step 1:** Add `kind` to `start_job`'s job dict (`"kind": "seed"`) and to the `_run` dispatcher:
```python
def _run(job: dict) -> None:
    if job["kind"] == "verify":
        verify.run_verify_job(job)
        return
    ...existing seed loop...
```
(import `verify` lazily inside the branch to avoid a circular import — `verify.py` imports `db`/`gh` only, so a top-level import is fine if seeder is imported after verify; use a local import to be safe.)

**Step 2:** Add `enqueue_job(job: dict) -> None` used by both seed and verify paths (lock + append + notify). Refactor `start_job` to build the seed dict then call `enqueue_job`.

**Step 3:** `list_jobs()` and `_with_position` already generic — no change beyond the `kind` field flowing through.

**Step 4:** Verify with smoke: existing seed tests still pass; a verify job enqueued behind a running seed stays `queued` with `queue_position == 1` (extend the serial-queue test block).

**Step 5:** Commit — `refactor: seeder queue dispatches by job kind`

### Task 2: Tri-state GitHub check + verify job runner

**Objective:** `check_github_ok` distinguishes 404 (failure) from rate-limit (skipped); the verify loop writes progress into the job dict.

**Files:**
- Modify: `backend/app/verify.py`

**Step 1:** Change `check_github_ok(url) -> tuple[bool, str]` to `-> tuple[bool, str, bool]` (ok, note, skipped):
```python
except ValueError as exc:   # repo genuinely gone
    return False, str(exc)[:80], False
except RuntimeError as exc: # 403/429 rate limit or API error → skip, never fail
    return False, str(exc)[:80], True
except Exception as exc:
    return False, str(exc)[:80], False
```
Note: `gh.fetch_repo` raises `ValueError` on 404 and `RuntimeError` on 403/429 — perfect separation already.

**Step 2:** Add `run_verify_job(job)` — the existing `run_verification` loop, but:
- `job["total"] = len(rows)` upfront, `job["status"] = "running"`
- per row: `job["current"] = name`; bump `ok` / `skipped` / `failed`
- `failed` rows append `"name: reason"` to `job["errors"]`
- skipped rows do NOT increment `check_failures`
- on completion `job["status"] = "done"`, store `{checked, ok, skipped, flagged, dead_flipped}` into `job["result"]`
- keep `verify_log` writes unchanged

**Step 3:** Keep `run_verification()` as a thin sync wrapper for tests/back-compat (calls `run_verify_job` against a temp job dict).

**Step 4:** Extend smoke: monkeypatch `gh.fetch_repo` to raise `RuntimeError("rate limited")` → row's `check_failures` unchanged, job `skipped == 1`; raise `ValueError` → `failed == 1`, `check_failures` bumped.

**Step 5:** Commit — `feat: rate-limit-aware verify job with progress`

### Task 3: API endpoints — enqueue + status

**Objective:** `POST /api/verify/run` returns `{job_id}` immediately; `GET /api/verify/status/{job_id}` returns the job.

**Files:**
- Modify: `backend/app/main.py`

**Step 1:**
```python
@app.post("/api/verify/run")
def run_verification() -> dict:
    job_id = verify.start_verification()
    return {"job_id": job_id}

@app.get("/api/verify/status/{job_id}")
def verify_status(job_id: str) -> dict:
    job = verify.get_verify_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```
`start_verification()` validates there isn't already a running/queued verify job (fail loud with 409 if so — two verify passes in flight is a bug, not a feature).

**Step 2:** Update smoke: old `verify/run on empty` check → POST returns job_id, then poll status until done, assert `checked == 0`. Add: second concurrent verify POST → 409.

**Step 3:** Commit — `feat: async verify endpoints`

### Task 4: Fix the cron script (poll, don't block)

**Objective:** The weekly Hermes job reliably triggers a verify pass and reports the outcome.

**Files:**
- Modify: `C:\Users\ADMIN\AppData\Local\hermes\scripts\ideasexist-verify.sh`

**Step 1:** Rewrite: health check (silent exit 0 if backend off) → POST `/api/verify/run` → extract `job_id` → poll `/api/verify/status/$job_id` every 10s up to 30min → print human summary (`checked X · ok Y · skipped Z · flagged W · dead_flipped [...]`) → non-zero exit if status is `failed`.

**Step 2:** No jq dependency — parse with `sed`/`grep` on the JSON or a tiny python one-liner (python3 available in the venv; fall back to grep).

**Step 3:** Test locally: start backend, run the script by hand, confirm it prints the summary and exits 0. Stop backend, run again → silent exit 0.

**Step 4:** Commit — `fix: verify cron polls job status instead of blocking`

### Task 5: Frontend — poll the verify job

**Objective:** The footer button starts the job and toasts on completion (no hung request).

**Files:**
- Modify: `frontend/lib/api.ts` (`runVerification` → `startVerification` + `verificationStatus`)
- Modify: `frontend/lib/types.ts` (add `VerifyJob` type)
- Modify: `frontend/app/page.tsx` (`handleVerify` — start, poll 2s, toast, reload)

**Step 1:** api.ts:
```ts
export function startVerification(): Promise<{ job_id: string }> { ... POST ... }
export function verificationStatus(jobId: string): Promise<VerifyJob> { ... GET ... }
```

**Step 2:** page.tsx `handleVerify`: `startVerification()` → poll every 2s until terminal → toast `checked/ok/skipped/flagged` (fail-loud on `failed`) → `loadAll()`. Keep the button spinner while polling. Guard: prevent double-start while a verify is active (disable button).

**Step 3:** Verify live: click button → spinner → completion toast; both themes; detector `[]`; `npm test` ALL PASS.

**Step 4:** Commit — `feat: async verify button with progress`

### Task 6: Optional auto-run on stale data (backend start)

**Objective:** A truly set-and-forget local app: if `last_checked` is >7 days stale, kick a verify job at startup.

**Files:**
- Modify: `backend/app/config.py` (+`VERIFY_AUTO_STALE_DAYS`, default 7; 0 disables)
- Modify: `backend/app/main.py` (startup event → enqueue if stale)

**Step 1:** In the FastAPI startup handler: read `MAX(last_checked)`; if `VERIFY_AUTO_STALE_DAYS > 0` and stale, call `verify.start_verification()`; log loudly either way. Guard against enqueueing while a verify is already queued (start_verification's 409 logic returns gracefully on startup).

**Step 2:** Smoke: set stale in test DB, startup app, assert a verify job appears in `seeder.list_jobs()`.

**Step 3:** Commit — `feat: auto-verify when archive is stale`

### Task 7: Docs + review surface

**Objective:** Docs reflect the new behavior; flagged entries are visible somewhere.

**Files:**
- Modify: `PRODUCT.md` (weekly verification line → async job + rate-limit handling + auto-run)
- Modify: `DESIGN.md` (footer/admin notes if the admin panel shows verify jobs)
- Modify: `frontend/components/admin-panel.tsx` (if we want verify jobs listed in "Recent runs" — the job shape already fits; add `verify` to `SOURCE_LABELS`)

**Step 1:** Add `verify: "Verification"` to `SOURCE_LABELS` in admin-panel.tsx — verify jobs automatically appear in In progress / Recent runs with the existing UI (source badge + counts). Verify visually.

**Step 2:** Update PRODUCT.md/DESIGN.md wording (async, serialized with seeds, rate-limit skips, manual gate unchanged).

**Step 3:** Commit — `docs: automated verification + review surface`

---

## Files Likely to Change

| File | Change |
|---|---|
| `backend/app/seeder.py` | `kind` field, `enqueue_job`, `_run` dispatcher |
| `backend/app/verify.py` | tri-state github check, `start_verification`, `run_verify_job` |
| `backend/app/main.py` | async verify endpoints, startup auto-run |
| `backend/app/config.py` | `VERIFY_AUTO_STALE_DAYS` |
| `backend/tests/smoke.py` | async verify checks, rate-limit skip, 409, serialization |
| `frontend/lib/api.ts` | `startVerification`, `verificationStatus` |
| `frontend/lib/types.ts` | `VerifyJob` type |
| `frontend/app/page.tsx` | poll-based verify button |
| `frontend/components/admin-panel.tsx` | `verify` source label (verify jobs appear in queue UI) |
| `C:\Users\ADMIN\AppData\Local\hermes\scripts\ideasexist-verify.sh` | poll instead of block |
| `PRODUCT.md`, `DESIGN.md` | async + rate-limit + auto-run wording |

## Tests / Validation

- `python -m tests.smoke` — all existing + new checks PASS (throwaway DB): async verify on empty → `checked == 0`; concurrent verify → 409; rate-limit skip leaves `check_failures` untouched; 404 → failure bumps it; verify job queues behind a running seed.
- `npm test` — backend smoke + frontend lint/build ALL PASS.
- Detector (`detect.mjs --json`) → `[]` on all touched files.
- Cron script manual test: backend up → prints summary, exit 0; backend down → silent exit 0.
- Live browser: verify button spinner → completion toast; verify job visible in admin panel queue; no console errors; both themes.

## Risks / Tradeoffs

- **Two verify passes in flight** would double-hit GitHub's rate limit — prevented by the 409 guard and the serial queue.
- **Skipped ≠ failed** changes long-run behavior: rate-limited repos no longer accrue `check_failures`, so dead-flips become *more* conservative (only genuine 404s / dead links count). This is the correct fix but means the 3-strike clock only ticks on real evidence.
- **Cron script robustness**: polling for up to 30 min means the Hermes job runs long; the watchdog pattern already tolerates this (script stays silent when the backend is off). If the machine sleeps mid-pass, the verify job continues server-side; the script may report a timeout while the job actually completes — acceptable for a local tool, and the admin panel shows the real outcome.
- **Auto-run on startup** adds a network pass whenever the backend boots with stale data — could surprise during dev (LLM/server restarts). Mitigation: `VERIFY_AUTO_STALE_DAYS` default 7, documented, easily disabled.
- **Manual gate untouched**: verified stamp still only set by a human. No automation path writes `verified=1` — this is a hard invariant, asserted in smoke.

## Open Questions (RESOLVED — all defaults confirmed)

1. **Auto-run on backend start** — ✅ *Yes*, `VERIFY_AUTO_STALE_DAYS=7` (0 disables).
2. **Review surface** — ✅ *Admin panel "Recent runs" shows verify jobs*; no footer hint.
3. **GITHUB_TOKEN** — ✅ *Yes* — see "Getting a GitHub token" below.
4. **Weekly Hermes cron stays the trigger** — ✅ *Yes*; backend auto-run is additive.

### Getting a GitHub token (where to get it)

GitHub API unauth = 60 requests/hour. One verify pass checks 43 GitHub entries, so a single pass plus any seed work can brush the cap — and two passes in one hour blow past it. A token raises the limit to **5,000 requests/hour**.

1. Go to **https://github.com/settings/tokens** (needs to be logged in).
2. Click **Generate new token** → **Generate new token (classic)**.
3. Give it a name (e.g. "ideasexist-verify"), expiry (e.g. 1 year — no need for no-expiry).
4. **Scopes:** tick **`public_repo`** only (read access to public repos — all the seeder/verifier needs). Do *not* tick anything else; this token never writes.
5. Click **Generate token**, copy the `ghp_...` string immediately (GitHub shows it once).
6. Add to `backend/.env`:
   ```
   GITHUB_TOKEN=ghp_your_token_here
   ```
7. Restart the backend; confirm via `/api/health` (it reports `github_token: true`) or just run a verification.

Security note: treat it like a password — it's in `backend/.env`, which is git-ignored. If it ever leaks, revoke at the same URL.

---

## New Requirement (user-confirmed): Verification progress panel

**When "Run verification" is pressed manually, a panel opens with:**
- a progress bar,
- **Total** (startups to check),
- **Checked** with a live **(Verified / Unverified / Dead) breakdown** — i.e. of the entries checked so far, how many are currently Verified, how many Unverified, how many Dead,
- **Failed** count (checks that errored / link dead).

This extends Tasks 2/3/5. The verify job must track, per checked row: the entry's *current* verified/status state (for the breakdown) plus check success/failure (for Failed).

### Verify job breakdown fields (add to Task 2)

In `run_verify_job`, alongside `ok/skipped/failed`, maintain:
```python
job["breakdown"] = {"verified": 0, "unverified": 0, "dead": 0}
# per row, BEFORE the check — the entry's state at check time:
if row["status"] in ("dead", "pivoted"):
    job["breakdown"]["dead"] += 1
elif row["verified"] == 1:
    job["breakdown"]["verified"] += 1
else:
    job["breakdown"]["unverified"] += 1
```
`checked = job["done"]` (rows visited). `failed` stays the check-failure count.

### Task 5b: Verification progress panel (frontend)

**Files:**
- Modify: `frontend/components/verify-panel.tsx` (NEW — dialog with progress bar + breakdown)
- Modify: `frontend/app/page.tsx` (`handleVerify` opens the panel instead of a bare toast; polls; closes on completion with summary toast)

**Step 1:** `verify-panel.tsx` — a dialog (same glass-strong language as admin panel, `sm:max-w-md`) showing:
- progress bar (`done/total`),
- mono ledger lines: **Total N**, **Checked N/M** (with `Verified a · Unverified b · Dead c` live breakdown — the three status colors, colorblind-safe labels),
- **Failed N** (red, with expandable error list when > 0).

**Step 2:** page.tsx — `handleVerify`: `setVerifyPanel({open:true, jobId})` → poll `verificationStatus(jobId)` every 2s → update panel state → on terminal: keep panel open showing the final summary + a "Done" state (or auto-toast + close after 2s — user's pick), `loadAll()`.

**Step 3:** Verify live: press the footer button → panel opens with progress → breakdown ticks up → completes; failure case (backend off) → fail-loud. Both themes. Detector `[]`. `npm test` ALL PASS.

**Step 4:** Commit — `feat: verification progress panel with status breakdown`

---

## Execution Handoff

Plan complete — all open questions resolved, progress-panel requirement folded in. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Tasks: (1) queue `kind` dispatch, (2) tri-state GitHub check + breakdown fields, (3) async verify endpoints, (4) cron script fix, (5) frontend poll + **5b progress panel**, (6) auto-run on stale, (7) docs + admin verify label. Shall I proceed?

