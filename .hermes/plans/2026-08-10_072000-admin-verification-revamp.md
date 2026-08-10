# Admin Panel Revamp: Seeding + Verification + Website Health Check

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fold verification into the admin panel as a vertical settings surface with three sections — **Seeding**, **Verification** (human gate / suggested queue), **Website Health Check** (automated pass with expandable output) — and add the **suggested-verified** workflow: the machine nominates alive-but-unverified entries, the human stamps them one-by-one or in bulk.

**Confirmed with user (2026-08-10):** "Everything that has been verified [by the automated run] comes up in the Verification section as suggested verified — entire list, scrollable, mark one-by-one or as a whole. Verification panel top shows the last complete verification date + number of websites verified at last run. Progress bar stays as implemented. Output for Already verified / Suggested verified / Failed — all expandable; Suggested + Failed rows have open-link and mark-verified buttons."

**Second round of decisions (2026-08-10, user):**
1. **NO footer "Run verification" button** — the admin panel is the only entry; verification starts from the Health Check section inside it.
2. **Every approval is behind the themed confirm popup** — both Mark-all and per-row Mark verified.
3. **Verified entries that fail a check appear in the Failed bucket** — as suggested.
4. **Sections: one open at a time** (accordion), **but seeding and verification run in parallel** — new seed jobs and verify jobs do NOT share a worker; they queue on separate kind-specific workers (seeds stay serial among themselves — contamination guard intact; verifies stay serial among themselves). See §6.
5. **Persistence — no data is lost on server restart**: jobs are written to a new `jobs` table as they progress and on completion; startup marks interrupted jobs `failed (interrupted)`. The Seeding section gets a **Seed summary** sub-tab and the Verification section a **Verification summary** sub-tab, both reading persisted history.
6. **New seeds appear in the suggested queue immediately** — the suggested query (`verified=0 AND status='active' AND check_failures=0`) already includes never-checked rows; they also show on the site as unverified as today.

---

## Design

### 1. Vertical settings panel (frontend)
- Admin dialog becomes a **stacked, collapsible section list** (accordion, one open at a time, chevron headers — existing glass/charcoal tokens):
  1. **Seeding** — existing seed form + queue ("In progress" + "Recent runs") unchanged.
  2. **Verification** — human-gate queue (see §3).
  3. **Website Health Check** — automated pass (see §4).
- Token gate stays: the whole panel unlocks with `ADMIN_TOKEN` (one paste, sessionStorage).
- Footer buttons become section shortcuts: **Admin panel** → opens at Seeding; **Run verification** → opens at Website Health Check (and auto-starts if no pass is active; re-attaches if one is).
- The standalone `verify-panel.tsx` dialog is **absorbed** into the Health Check section (progress bar + breakdown markup moves in; file deleted).

### 2. Backend: classify every checked row into three output buckets
`run_verify_job` gains per-entry classification (keeps the tri-state semantics from the last task — website dead OR github 404 = real failure; github rate-limit = skip, never a failure):

- **`failed`** — check failed (website dead or repo 404): `{name, url, reason}` list. A *verified* entry that now fails ALSO appears here (human must notice).
- **`already_verified`** — check passed AND `verified=1` at check time: `{name, url}` list.
- **`suggested`** — check passed AND `verified=0` at check time: `{name, url}` list (the nominations).
- github-skipped-but-website-ok → passes → lands in suggested/already per its verified state.

Job `result` becomes: `{checked, ok, flagged, skipped, dead_flipped, breakdown, already_verified[], suggested[], failed[]}`. `ok = already + suggested`.

### 3. Verification section (human gate)
- **Header line:** last complete verification date (`stats.last_checked`) + number of websites verified at last run (`stats.verified` — stamps only change via human action, so current count is the truthful "verified" number; date comes from the last completed automated pass). Both already exist on `/api/stats` — no new persistence needed.
- **Suggested-verified list** — live-computed (survives restarts, always current):
  `verified=0 AND status='active' AND check_failures=0` (alive, unstamped).
- Each row: name (truncate), external-link icon (opens `website_url`), **Mark verified** button.
- **Mark all** button at the top of the list → bulk-approves every suggested row (confirm dialog, themed — same pattern as the status pill).
- Actions refresh the list + the page's `loadAll()`.

### 4. Website Health Check section
- **Run verification** button (reuses the current flow: re-attach to `/api/verify/current` if active, else `POST /api/verify/run`), **same progress bar** (done/total · % · Verified/Unverified/Dead breakdown · current-check line · failed expander while running).
- On completion (or when a last job exists), render **three expandable buckets** from the job result:
  - **Already verified (N)** — read-only name list.
  - **Suggested verified (N)** — each row: open-link + **Mark verified**.
  - **Failed (N)** — each row: open-link + **Mark verified** (human overrides the machine — e.g. bot-blocked but actually alive).
- Buckets use the existing `SummaryRow` collapsible pattern; suggested list is scrollable (`max-h` + overflow).

### 5. Endpoints (additive)
| Endpoint | Auth | Behavior |
|---|---|---|
| `GET /api/verify/suggested` | admin | `[{id, name, website_url, github_url, category, last_checked}]` — alive + unverified (live DB query) |
| `POST /api/verify/approve` | admin | body `{ids?: number[], all?: true}` → stamps `verified=1, verified_at=now` on each; returns `{approved: n}`. `all` stamps every suggested row. |
| `GET /api/verify/current` | public | (exists) active verify job — Health Check re-attach |
| `/api/verify/run`, `/api/verify/status/{id}` | public | (exist) unchanged |
| `/api/startups/{id}/verify` | public | (exists) single-row human gate — unchanged, used by pill + rows |

- **Invariant:** automation never writes `verified=1`. The only writers are the human gate (`/verify`, `/approve`, pill). Asserted in smoke.

### 6. Parallel workers (seed ∥ verify, serial within kind)

Replace the single worker with two kind-scoped workers + queues:

```
_SEED_QUEUE / _SEED_COND / _seed_worker   → drains only kind="seed"
_VERIFY_QUEUE / _VERIFY_COND / _verify_worker → drains only kind="verify"
```

- `enqueue_job(job)` pushes onto the queue matching `job["kind"]` and notifies that worker. Seeds stay FIFO serial among themselves (no contamination); verifies stay serial among themselves; the two kinds run concurrently.
- **Verify must not hold a long write transaction** (that would block a concurrent seed): `run_verify_job` commits **per row** (283 tiny commits is fine — SQLite local).
- `db.connect()` gains `PRAGMA busy_timeout = 5000` so the two writers briefly wait instead of erroring "database is locked".
- `has_active_job(kind)` / `_with_position` / `list_jobs` updated for two queues (position = index within the job's own kind queue; `list_jobs` merges both, active first).
- `start_verification()` guard still checks `has_active_job("verify")` — no two verify passes in flight. Same for seeds (`has_active_job("seed")` — though queuing multiple seeds is allowed, they simply run one after the other; the guard exists to keep the UI honest, not to block queueing).

### 7. Job persistence (no data lost on restart)

- **New table `jobs`** (additive schema):
  ```sql
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
  ```
- `enqueue_job` INSERTs the row (status `queued`); the worker UPDATEs progress fields + `status` on terminal (and `current` during the run, throttled — every row for verify is fine locally).
- `list_jobs()` reads memory (live jobs) **merged with DB history** (completed jobs from previous runs / this run); memory wins for live jobs; DB rows fill the rest. `get_job()` falls back to the DB.
- **Startup recovery** (`lifespan`): any `jobs` row left `queued`/`running` is marked `failed` with `errors_json='interrupted by server restart'` — nothing is lost, nothing lies.
- **Seed summary sub-tab** (Seeding section): `list_jobs(kind="seed")` → per-run Fetched/All-exist/Failed rows (expandable, existing SummaryRow pattern) — persisted, survives restart.
- **Verification summary sub-tab** (Verification section): `list_jobs(kind="verify")` → per-run date + checked/ok/suggested/failed counts + expandable buckets from `result_json`.

### 8. Suggested-verified queue (live)

`GET /api/admin/verify/suggested` = `SELECT id, name, website_url, github_url, category, last_checked FROM startups WHERE verified = 0 AND status = 'active' AND check_failures = 0 ORDER BY name` — includes brand-new seeds (never checked) and passes; excluded: dead, already stamped, 1-2 strike failures.

---

## Step-by-Step Plan

### Task 1: Backend — two parallel workers + per-row verify commits + busy_timeout

**Files:** `backend/app/seeder.py`, `backend/app/verify.py`, `backend/app/db.py`

**Step 1:** `db.py` — add `PRAGMA busy_timeout=5000` to `connect()`.
**Step 2:** `seeder.py` — two queues/conds/workers; `enqueue_job` routes by kind; `_run` unchanged (already dispatches by kind); `_with_position`/`list_jobs`/`has_active_job` handle both queues.
**Step 3:** `verify.py` — `run_verify_job` commits per row (move `conn.commit()` inside the loop; drop the end-of-pass commit).
**Step 4:** Smoke: seed job and verify job **run concurrently** (start slow seed, then verify; assert verify's `started_at` < seed's `finished_at` — they overlap). Seeds still serialize: two seeds → second `queued`. Verify still serializes: second verify → 409.
**Step 5:** `git diff` review; detector `[]`; `npm test` backend smoke PASS.

### Task 2: Backend — bucket classification in `run_verify_job`

**File:** `backend/app/verify.py`

**Step 1:** In `run_verify_job`, after computing `failed`/`ok`, bucket the passed rows:
```python
if failed:
    job["failed"] += 1
    job["errors"].append(f"{row['name']}: {'; '.join(notes)}")
    job["failed_list"].append({"name": row["name"], "url": row["website_url"] or row["github_url"], "reason": "; ".join(notes)})
elif row["verified"] == 1:
    job["already_verified"].append({"name": row["name"], "url": row["website_url"] or row["github_url"]})
    job["ok"] += 1
else:
    job["suggested"].append({"name": row["name"], "url": row["website_url"] or row["github_url"]})
    job["ok"] += 1
```
(rate-limit-skip case stays `skipped` as before — `github_skipped_only`.)

**Step 2:** Init `already_verified`/`suggested`/`failed_list` in `start_verification()` job dict + `run_verification()` throwaway job; include all three in `job["result"]`.

**Step 3:** `git diff` review; detector `[]` on verify.py.

### Task 3: Backend — suggested + approve endpoints

**File:** `backend/app/main.py`, `backend/app/verify.py`

**Step 1:** `verify.py`:
```python
def list_suggested() -> list[dict]:
    conn = db.connect()
    rows = conn.execute(
        "SELECT id, name, website_url, github_url, category, last_checked FROM startups "
        "WHERE verified = 0 AND status = 'active' AND check_failures = 0 ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def approve_suggested(ids: list[int] | None = None, all_: bool = False) -> int:
    conn = db.connect()
    if all_:
        cur = conn.execute("UPDATE startups SET verified = 1, verified_at = datetime('now') WHERE verified = 0 AND status = 'active' AND check_failures = 0")
    else:
        cur = conn.execute(
            "UPDATE startups SET verified = 1, verified_at = datetime('now') WHERE id IN (%s)" % ",".join("?" * len(ids)),
            ids,
        )
    conn.commit()
    conn.close()
    return cur.rowcount
```

**Step 2:** `main.py` — admin-gated router additions. **Pydantic keyword note:** name the field `approve_all` (pydantic model field) and accept `{"approve_all": true, "ids": [...]}` — avoids the `all` keyword clash entirely.
```python
class ApproveIn(BaseModel):
    ids: list[int] | None = None
    approve_all: bool = False

@admin.get("/verify/suggested")
def admin_suggested() -> list[dict]:
    return verify.list_suggested()

@admin.post("/verify/approve")
def admin_approve(body: ApproveIn) -> dict:
    if body.approve_all:
        n = verify.approve_suggested(all_=True)
    elif body.ids:
        n = verify.approve_suggested(ids=body.ids)
    else:
        raise HTTPException(400, "Provide ids or approve_all=true")
    return {"approved": n}
```

**Step 3:** `git diff` review; detector `[]`.

### Task 4: Backend — job persistence (jobs table + startup recovery)

**Files:** `backend/app/db.py` (schema), `backend/app/seeder.py`, `backend/app/verify.py`, `backend/app/main.py` (lifespan recovery)

**Step 1:** `db.py` SCHEMA += `jobs` table (see §7). `init_db` creates it.

**Step 2:** `seeder.py`:
- `enqueue_job`: after appending to the in-memory queue, `INSERT` the job row (params/errors/urls/breakdown/result as JSON).
- Worker `_run`: on terminal, `UPDATE` the row with final status/counters/`result_json`/`finished_at`. During the run, `UPDATE current` + counters **every row** (throttle-free — local SQLite handles it; verify is ~283 rows).
- `list_jobs()`: merge in-memory live jobs with DB rows not present in memory (or whose memory copy is stale-terminal) — memory wins for live; DB fills history. `get_job()` falls back to DB.
- `_with_position` unchanged (uses the in-memory queue; DB jobs have `queue_position=None`).

**Step 3:** `main.py` `lifespan` → after `db.init_db()`: `UPDATE jobs SET status='failed', errors_json='interrupted by server restart' WHERE status IN ('queued','running')` (use seeder helper `recover_interrupted_jobs()`).

**Step 4:** Smoke: run a seed job → row exists in DB with `done>0`; simulate restart (fresh TestClient → lifespan recovery) → any queued/running rows are `failed (interrupted)`; `list_jobs` still returns DB history after a "restart" (new TestClient sees the old job).

**Step 5:** `git diff` review; detector `[]`.

### Task 5: Backend — smoke tests for suggested/approve/buckets/parallelism

**File:** `backend/tests/smoke.py` (extend the client4 verify block)

- suggested returns only alive+unverified rows (no verified, no dead, no check_failures>0); a brand-new seed (never checked) appears in suggested
- approve single id stamps exactly that row (verified=1, verified_at set)
- approve `approve_all=true` stamps every suggested row; count matches
- approve 403 without admin token
- job result buckets: seeded GhCorp row (website ok stubbed, github 404) → in `failed_list`; a verified row passing → `already_verified`; an unverified passing row → `suggested`; a verified row failing → in `failed_list` too
- **invariant:** verify pass alone never sets `verified=1` (checked rows keep verified=0 unless stamped)
- **parallelism (Task 1 step 4):** slow seed + verify overlap (`verify.started_at < seed.finished_at`); two seeds serialize (second `queued`); second verify → 409

### Task 6: Frontend — admin panel vertical sections (Seeding + shells)

**File:** `frontend/components/admin-panel.tsx`

**Step 1:** Replace the `Tabs` shell with a collapsible section list (chevron headers, one open at a time — `useState<SectionKey>("seed")`, AnimatePresence height fade or simple conditional). Section components:
- `<SeedSection>` — the existing seed form + queue, plus a **Seed summary** sub-tab (Task 8 data).
- `<VerificationSection>` — Task 7.
- `<HealthCheckSection>` — Task 8.

**Step 2:** `AdminPanel` accepts `initialSection?: "seed" | "verify" | "health"`. On `open` change, switch to `initialSection`.

**Step 3:** Keep token gate, `refreshJobs` polling, `onSeeded` — unchanged. Detector `[]`; lint/build pass.

### Task 7: Frontend — Verification section (suggested queue + summary sub-tab)

**File:** `frontend/components/admin-panel.tsx` (+ `frontend/lib/api.ts`, `frontend/lib/types.ts`)

**Step 1:** api.ts: `fetchSuggested() → GET /api/admin/verify/suggested`; `approveSuggested({ids?, approveAll?}) → POST /api/admin/verify/approve` (adminJson). types.ts: `SuggestedStartup {id, name, website_url, github_url, category, last_checked}`.

**Step 2:** Section markup:
- Header: "Last verification <date> · <N> verified" — from `fetchStats()` (fetch standalone).
- **Mark all** button (visible when list non-empty) → themed confirm dialog ("Approve all N suggested?") → `approveSuggested({approveAll:true})` → toast + refresh list + `onSeeded()`.
- Scrollable list (`max-h-72 overflow-y-auto`): each row = name (truncate) + external-link icon (anchor, `target="_blank" rel="noreferrer"`, `href=website_url || github_url`) + **Mark verified** button (per-row `approveSuggested({ids:[id]})` — **also behind the confirm dialog**, per user decision #2).
- Empty state: "Nothing to approve — the archive is fully verified or nothing's been checked yet."

**Step 3:** **Verification summary sub-tab** — `list_jobs` filtered `kind="verify"` → per-run: date + checked/ok/suggested/failed counts + expandable Already/Suggested/Failed buckets from `result_json` (persisted). Fetch on open + after any run.

**Step 4:** Fetch suggested on section open + after approve + after `onSeeded`. Detector `[]`; lint/build.

### Task 8: Frontend — Website Health Check section (absorb verify-panel)

**File:** `frontend/components/admin-panel.tsx` (absorb `verify-panel.tsx`, then delete it)

**Step 1:** Move the VerifyPanel markup into the section: run button, progress bar, done/total · %, Verified/Unverified/Dead breakdown, current-check line, running failures expander. Keep the poll + re-attach logic (`currentVerification` → poll → done).

**Step 2:** On terminal, render three expandable `SummaryRow` buckets from `job.result`:
- Already verified (N) — `already_verified` names.
- Suggested verified (N) — rows: name + open-link + **Mark verified** (calls `approveSuggested({ids:[id]})` — confirm dialog — then refresh suggested + `onSeeded`).
- Failed (N) — rows: name + reason (truncate, title attr) + open-link + **Mark verified**.

**Step 3:** Delete `frontend/components/verify-panel.tsx`; remove its import/usage from `page.tsx`. Detector `[]`; lint/build; `npm test` ALL PASS.

### Task 9: Frontend — remove footer Run-verification button + cleanup

**File:** `frontend/app/page.tsx`

**Step 1:** **Remove the footer "Run verification" button entirely** (user decision #1). Only the Admin panel gear remains; verification starts from the Health Check section inside the panel.
**Step 2:** `AdminPanel` gets `initialSection` state controlled from page.tsx (`useState<SectionKey>("seed")`); the gear button opens the panel at Seeding. No auto-start anywhere.
**Step 3:** Remove `verifyPanelOpen`/`VerifyPanel`/`handleVerify` state + dialog + imports from page.tsx (the run/poll logic moves into the Health Check section). Detector `[]`; lint/build; `npm test` ALL PASS.

### Task 10: Docs + final verification

- `PRODUCT.md`: admin panel section → three-section settings surface (Seeding + Seed summary / Verification + summary / Website Health Check); suggested-verified workflow; approve endpoints; parallel seed∥verify workers; job persistence.
- `DESIGN.md`: admin section → vertical collapsible sections (chevron headers, one open); external-link + mark-verified row pattern.
- Full sweep: `npm test` ALL PASS, detector `[]` on every touched file, both themes visually verified (panel sections, suggested list, buckets, confirm dialogs), parallel run live (seed + verify at once), restart persistence live (backend restart → summaries intact).

---

## Files Likely to Change

| File | Change |
|---|---|
| `backend/app/db.py` | `jobs` table (schema) |
| `backend/app/seeder.py` | two workers/queues, persistence (INSERT/UPDATE/recover/merge), `list_jobs` |
| `backend/app/verify.py` | buckets (already_verified/suggested/failed_list), per-row commits, `list_suggested`, `approve_suggested` |
| `backend/app/main.py` | admin `/verify/suggested` + `/verify/approve`; lifespan recovery |
| `backend/tests/smoke.py` | suggested/approve/bucket/invariant/parallelism/persistence checks |
| `frontend/components/admin-panel.tsx` | vertical sections; Verification + Health Check sections; summary sub-tabs |
| `frontend/components/verify-panel.tsx` | DELETED (absorbed) |
| `frontend/app/page.tsx` | remove footer Run-verification button + VerifyPanel |
| `frontend/lib/api.ts` | fetchSuggested, approveSuggested |
| `frontend/lib/types.ts` | SuggestedStartup |
| `PRODUCT.md`, `DESIGN.md` | docs sync |

---

## Risks & Guardrails

- **Pydantic `all` keyword** — avoided with `approve_all` field name (Task 3).
- **Parallel writers** — busy_timeout + WAL + per-row verify commits; smoke asserts overlap without lock errors.
- **"Verified at last run" semantics** — `stats.verified` is the live stamp count (stamps only change via human action, so it equals the count at the last run unless the user stamped since). `stats.last_checked` is the last completed automated pass. Both truthful; documented.
- **verified=1 stays human-only** — hard invariant, smoke-asserted. `approve` is admin-gated; the pill stays public.
- **Skipped (rate-limited) entries never land in failed** — they pass if the website is ok; a dead website + rate-limited github still fails (website is the real signal).
- **jobs table growth** — one row per run (seeds + weekly verify) — trivial size; no pruning needed.

---

## Open Questions (defaults chosen — confirm or override)

1. ~~Footer Run verification auto-starts~~ — **RESOLVED: no footer button at all.** Verification starts from the Health Check section.
2. **Mark-all approves the entire suggested list** behind a themed confirm — ✅ confirmed; per-row marks also get the confirm dialog.
3. **Verified entries that fail a check appear in the Failed bucket** — ✅ confirmed.
4. **Sections one-open-at-a-time accordion; seed ∥ verify run in parallel** — ✅ confirmed, backend supports it (two workers).

---

## Execution Handoff

Plan complete — all decisions folded in. Task order: (1) parallel workers + per-row commits, (2) buckets, (3) suggested/approve endpoints, (4) persistence, (5) backend smoke, (6) frontend section shells, (7) Verification queue + summary, (8) Health Check + absorb verify-panel, (9) footer cleanup, (10) docs + sweep. Shall I proceed?
