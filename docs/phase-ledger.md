# Phase Ledger — IdeaExists implementation

**Purpose:** the single audit trail for backend-first gating. Every phase writes a row here; decisions about "can frontend start?" read only from this file.
**Rule:** Phases 6–8 may not be `running` while Phase 5 is not `PASS`.

| Phase | Status | Evidence (command + output summary) | Date |
|---|---|---|---|
| 0 — Onboarding & baseline | **PASS** | Docs read (implementation-plan, handoff, codebase-comprehension, reworked-revamp-plan, teardown-spec, gap-table-format, backend-checklist, phase-ledger). `npm test` → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed/0 failed). `backend\.venv\Scripts\python.exe scripts/phase0-baseline.py` → `[baseline] matches expected baseline` — **1,282 total / 1,278 verified / 0 dead / 57 github**; tables `jobs, sqlite_sequence, startups, verify_log`; last_checked 2026-09-04. No drift. Full output in §Phase 0 evidence below. | 2026-09-15 |
| 1 — Schema & evidence foundation | **PASS** | Migration verified on a **copy** of the live DB: `backend\.venv\Scripts\python.exe scripts\phase1-verify.py` → **RESULT: ALL PASS** (31 checks) — 1,282 rows before and after, 18 → 40 columns, all 22 teardown columns added incl. `app_store_url` / `play_store_url` / `date_source`, `founded` unchanged and never renamed, `evidence` table present with a NOT NULL `source_url`, second migration run added 0 columns (idempotent), every new column present in `enrich.UPDATABLE`, a 200-day-old `verify_log` row survived a real pass (F-03), and the F-04/F-05 branches behave (rdap / wayback / llm / unknown, machine_drafted stamped, human confirm flips it and a reuse refresh does not downgrade it). Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` (from `backend/`) → **RESULT: ALL PASS** (85 PASS / 0 FAIL); `npm test` with Node 24 first on PATH → **RESULT: ALL PASS**. Full output in §Phase 1 evidence below. | 2026-09-15 |
| 2 — Enrichment & teardown fields | **PASS** | Branch `phase/02-enrichment-teardown-fields`, cut from Phase 1's branch and rebased onto `main` after #4 merged (see the note below). `backend\.venv\Scripts\python.exe scripts\phase2-verify.py` → **RESULT: ALL PASS** (70 checks, exit 0) on a copy of the live archive + a throwaway founder store, fetcher and both LLM prompts **stubbed**: a capture yields `features_json` with 6 items, 3 well-formed pricing plans (2 malformed rows dropped) with `pricing_captured_at` + `pricing_source_url`, a non-empty `positioning`, **one evidence row per feature / plan / free tier / positioning line / negative / review**, provenance `machine_drafted` until a human confirms. Negatives: every one traces to an **enumerating** page; a 404 on a guessed `/api` produces nothing; an unreadable page is `unknown` at confidence 0.1; a verdict-shaped LLM claim is rephrased and a duplicate of the deterministic probe is dropped. Founder app: all three paths draft (URL / form / agent-JSON), a form without 5–10 features → 400, malformed JSON → 400, unknown keys → 400, **nothing reaches the archive DB or `/api/startups` `/api/stats` `/api/categories`** (`1285 → 1285`), the compare guard refuses an unconfirmed app, link-less → `local_only` with **no opt-in offered**, link + opt-in → `pending` → approve → `archive_startup_id` set with the founder record still in its own file, and a rejection carries a readable note (a resubmission is a new row). JIT: two concurrent captures of one competitor → **exactly one job**, in-flight → explicit `capture in progress — retry`, inside 7 days → `cached`, outside → re-queued. Reviews: a 403 provider is a **skip**, every ask links to its review, no score of ours stored. Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` → **RESULT: ALL PASS**; `npm test` with Node 24 first on PATH → **RESULT: ALL PASS** (35 e2e passed / 0 failed). No `frontend/` file touched (asserted in the verifier). Full output in §Phase 2 evidence below.
| 3 — Comparison, gap table & export | pending | | |
| 4 — Search classification & match reasons | pending | | |
| 5 — Backend functional test gate | pending | | |
| 6 — Frontend implementation (blocked) | blocked | | |
| 7 — Frontend tests (blocked) | blocked | | |
| 8 — Full end-to-end test (blocked) | blocked | | |
| 9 — Handoff & close-out | pending | | |

**Baseline (recorded in Phase 0, 2026-09-15):** see the full evidence block below.

---

## Phase 0 evidence — onboarding & baseline (2026-09-15)

**Branch:** `phase/00-onboarding-baseline`, cut from `main` at `06cf858`. No application code was changed — this branch carries the ledger entry, and nothing else.

### Test baseline

Command: `npm test` (root `scripts/verify.mjs`; needs Node ≥23 first on PATH — AutoClaw's bundled Node 22 otherwise shadows the system Node 24):

```
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm test

[PASS] backend smoke (exit 0)              RESULT: ALL PASS
[PASS] frontend sort check (exit 0)        RESULT: ALL PASS
[PASS] frontend lint + build (exit 0)      ✓ Compiled successfully in 4.5s
[PASS] frontend e2e verification (exit 0)  TEST RESULTS: 35 PASSED, 0 FAILED

RESULT: ALL PASS
```

Zero `[FAIL]` lines in the full run. Fallback if the runner ever breaks on this machine: `cd backend` then `..\backend\.venv\Scripts\python.exe -m tests.smoke` (verified separately: exit 0, `RESULT: ALL PASS`).

### Data baseline

Command: `backend\.venv\Scripts\python.exe scripts\phase0-baseline.py` (read-only — opens the DB with `mode=ro` and cannot modify the archive):

```
[baseline] IdeaExists archive
  db_path      : E:\New-Personal-Projects\Does this Startup Exist\backend\data\ideasexist.db
  tables       : jobs, sqlite_sequence, startups, verify_log
  total        : 1282
  verified     : 1278
  dead         : 0
  website_url  : 1282
  github_url   : 57
  last_checked : 2026-09-04 15:04:08
  categories   : other 302 · ai 222 · finance 173 · health 165 · devtools 140 ·
                 productivity 109 · ecommerce 67 · media 49 · education 37 ·
                 social 14 · freelance 4
  sources      : website 1229 · github 53
[baseline] matches expected baseline (1282 / 1278 / 0 / 57)
```

**No drift.** The expected 1,282 filings / 1,278 verified / 0 dead / 57 with a GitHub repo is exactly what the archive reports.

### Notes recorded at Phase 0

- **Every spec file the phase prompts reference exists** — no missing documents.
- **One documentation inaccuracy found while measuring** (recorded here rather than fixed, since no product docs are changed in this phase): `docs/codebase-comprehension.md` §3 calls `startups` a “20-column” table; the live schema has **18** columns (`PRAGMA table_info(startups)`), which matches the column list printed in that same section. Nothing depends on it.
- **Row status after this phase:** Phase 0 `PASS`; Phases 1–5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`, per the rule at the top of this file.
- **Pre-Phase-0 repo hygiene** (completed before this branch, on `main`): the working tree was committed, planning/handover/working docs were untracked to local-only, and the Round 5 trust-model decisions were applied across the specs. `main` is at `06cf858` on both local and origin.

---

## Phase 1 evidence — schema & evidence foundation (2026-09-15)

**Branch:** `phase/01-schema-evidence-foundation`, cut from `main` at `6391ce6`. Backend only — nothing under `frontend/` was touched, and no Phase 2 table (`founder_apps`, `founder_submissions`, `FOUNDER_DB_PATH`) was created.

### Files changed

| File | Change |
|---|---|
| `backend/app/db.py` | `NEW_STARTUP_COLUMNS` (22 columns) is the single source of truth for both the fresh-DB `CREATE TABLE` and the new `migrate()`; `init_db()` now runs `executescript(SCHEMA)` + `migrate()`. Added the `evidence` table (F-02) and its `startup_id` index. |
| `backend/app/enrich.py` | `UPDATABLE` extended with all 22 new columns (the silent-drop trap); `stamp_provenance()` / `mark_human_confirmed()` / `GENERATED_TEXT_FIELDS` (F-05), applied in `_upsert` and both seed paths; `_resolve_founded()` records `date_source` at the three `seed_from_website` branches and the `reuse_profile` branch (F-04). |
| `backend/app/verify.py` | The 90-day `verify_log` retention `DELETE` is gone — the log is permanent (F-03). |
| `scripts/phase1-verify.py` | New exit-gate verifier (the evidence tool below). |
| `docs/phase-ledger.md` | This entry. |

### 1. Backup first — SQLite's own backup API, not a file copy

```
backend\.venv\Scripts\python.exe -c "import sqlite3; s=sqlite3.connect('backend/data/ideasexist.db'); d=sqlite3.connect('backend/data/ideasexist.db.bak-phase1'); s.backup(d); d.close(); s.close()"
```

Exit 0. `backend/data/ideasexist.db.bak-phase1` = 1,650,688 bytes (identical to the live file). Both files are under `backend/data/`, which is git-ignored, so neither is committed. The migration was then run against a **third** file copied from that backup — the live DB was never opened for writing.

### 2. Migration on a copy of the live DB

Command: `backend\.venv\Scripts\python.exe scripts\phase1-verify.py` → `EXIT=0`

```
[live] rows=1282 columns=18
[copy] before migration: rows=1282 columns=18
[PASS] row count unchanged by the migration (F-01) — 1282 -> 1282
[PASS] row count matches the Phase 0 baseline of 1,282 — 1282
[PASS] no column dropped or renamed — missing: []
[PASS] `founded` keeps its name (F-04 — rename rejected)
[PASS] `date_source` sits beside it (F-04)
[PASS] `app_store_url` present (F-19)
[PASS] `play_store_url` present (F-19)
[PASS] all 22 teardown columns added — missing: []
[PASS] first migration run actually added columns — added 22
[PASS] re-running the migration is a no-op (idempotent) — []
[PASS] no duplicate tables — {'startups': 1, 'evidence': 1, 'verify_log': 1, 'jobs': 1}
[PASS] evidence table exists (F-02)
[PASS] evidence has exactly the specified columns — ['id', 'startup_id', 'evidence_type', 'source_url', 'captured_at', 'claim', 'value', 'provenance', 'confidence', 'reviewed_at']
[PASS] evidence.source_url is NOT NULL (F-02) — notnull=1
[PASS] evidence.captured_at is NOT NULL and auto-filled (F-02) — datetime('now')
[PASS] a source-less evidence row is refused (F-02)
[PASS] every new column is in enrich.UPDATABLE — []
[PASS] no retention DELETE left in verify.py (F-03) — []
[PASS] the 200-day-old verify_log row survived the pass (F-03) — aged before=1 after=1 surviving row=1
[PASS] the pass still writes a new row per startup — verify_log rows=2
[PASS] verify job completed — done

RESULT: ALL PASS
```

The `PRAGMA table_info(startups)` dump from the same run — 40 columns, new ones appended, nothing renamed:

```
    0  id ... 17  updated_at TEXT notnull=1 default=datetime('now')
   18  entity_type            TEXT  notnull=0 default=None
   19  canonical_domain       TEXT  notnull=0 default=None
   20  aliases                TEXT  notnull=0 default=None
   21  problem_statement      TEXT  notnull=0 default=None
   22  target_users           TEXT  notnull=0 default=None
   23  product_url            TEXT  notnull=0 default=None
   24  docs_url               TEXT  notnull=0 default=None
   25  demo_url               TEXT  notnull=0 default=None
   26  app_store_url          TEXT  notnull=0 default=None
   27  play_store_url         TEXT  notnull=0 default=None
   28  pricing_json           TEXT  notnull=0 default=None
   29  pricing_captured_at    TEXT  notnull=0 default=None
   30  pricing_source_url     TEXT  notnull=0 default=None
   31  features_json          TEXT  notnull=0 default=None
   32  positioning            TEXT  notnull=0 default=None
   33  content_notes          TEXT  notnull=0 default=None
   34  activity_checked_at    TEXT  notnull=0 default=None
   35  activity_summary       TEXT  notnull=0 default=None
   36  last_human_reviewed_at TEXT  notnull=0 default=None
   37  review_notes           TEXT  notnull=0 default=None
   38  provenance             TEXT  notnull=0 default=None
   39  date_source            TEXT  notnull=0 default='unknown'
```

Sample migrated row (id=1, Obsidian): `founded='2020-05-08'`, `date_source='unknown'` (existing rows default to unknown — where the date came from was never recorded), `provenance=None`, 40 columns. **Existing values are untouched**: `founded` still holds the value it had before the migration.

### 3. F-04 / F-05 branch behaviour (stubbed, synthetic DB)

The same run exercises the three founded-date branches and the provenance stamp against a throwaway DB, so Phase 1 does not hand Phase 5 a code path that has never executed:

```
[PASS] RDAP-derived date is recorded as date_source='rdap' (F-04) — founded='1997-10-06' date_source='rdap'
[PASS] a fresh seed is stamped provenance='machine_drafted' (F-05) — machine_drafted
[PASS] a Wayback-derived date is recorded as date_source='wayback' (F-04) — founded='2019-03-04' date_source='wayback'
[PASS] an LLM-stated date is recorded as date_source='llm' (F-04) — founded='2015-06-01' date_source='llm'
[PASS] with no source the date stays NULL and date_source='unknown' (F-04) — founded=None date_source='unknown'
[PASS] a human confirm flips provenance to human_confirmed (F-05) — human_confirmed
[PASS] a reuse_profile refresh does not downgrade human_confirmed (F-05) — human_confirmed
[PASS] a reuse_profile refresh that learns nothing does not reset date_source (F-04) — date_source='rdap' founded='1997-10-06'
```

### 4. Test suites

```
cd backend
..\backend\.venv\Scripts\python.exe -m tests.smoke

RESULT: ALL PASS        (85 PASS lines, 0 FAIL lines, exit 0)
```

Root runner, all four suites (`npm test`, root `scripts/verify.mjs`, with Node 24 first on PATH — AutoClaw's bundled Node 22 otherwise shadows it):

```
[PASS] backend smoke (exit 0)              RESULT: ALL PASS
[PASS] frontend sort check (exit 0)        RESULT: ALL PASS
[PASS] frontend lint + build (exit 0)
[PASS] frontend e2e verification (exit 0)  TEST RESULTS: 35 PASSED, 0 FAILED

RESULT: ALL PASS
```

### Notes recorded at Phase 1

- **F-04 is backend-half-complete by design.** `date_source` is now recorded at every branch that produces a `founded` value in `seed_from_website` (plus the `reuse_profile` refresh). The display half — `startup-card.tsx`, `startup-detail.tsx` and the hardcoded `"2021"` fallback at `page.tsx:563` — is Phase 6 and stays out of this branch. GitHub seeds leave `date_source` at its `unknown` default on purpose: a repo's `created_at` is a code-hosting fact, not a founding date, and it is none of the classified sources.
- **F-05 enforcement point.** `_upsert` applies `stamp_provenance()` itself, so no generated text can reach the archive without a marker even if a future caller forgets; a marker already on a row is never downgraded by a metadata-only `reuse_profile` refresh. The human half (`mark_human_confirmed`) is deliberately **not** wired to the liveness approve gate — an Admin Verified stamp describes the business, not its marketing copy.
- **Doc drift caused by this phase — corrected in this branch.** Phase 1 falsified three statements in `docs/codebase-comprehension.md` (the doc a fresh agent reads to learn what the code *is*): §3 called `startups` a 20-column table and said `verify_log` is pruned to 90 days, and §10 listed the missing evidence/provenance model as technical debt. All three, plus the §11 consistency row on LLM prose, are now corrected in place and marked "Phase 1", with a note at the top of that document. (The `20-column` figure was independently wrong: the live schema has 18.) `docs/handoff.md` needed no change.
- **No `frontend/` file, no Phase 2 table, no `founded_at` rename.** `git diff --stat main` on this branch touches `backend/app/{db,enrich,verify}.py`, `scripts/phase1-verify.py` and `docs/phase-ledger.md` only.
- **Row status after this phase:** Phases 0–1 `PASS`; Phases 2–5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`.

---

## Phase 2 evidence — enrichment & teardown fields (2026-09-15)

**Branch:** `phase/02-enrichment-teardown-fields`. **Backend only** — no `frontend/` file was touched (the verifier asserts it: `git diff --name-only phase/01-schema-evidence-foundation..HEAD -- frontend` and `git status --porcelain -- frontend` are both empty).

**Deviation from the phase prompt, deliberate and flagged:** the prompt says to branch off `main`. At the time, Phase 1's PR (#4) was still open, so `main` did not contain the F-01–F-05/F-19 code this phase is told to build on (no teardown columns, no `evidence` table, no `enrich.UPDATABLE` extension); branching off `main` would have meant re-doing Phase 1 or building on a schema that does not exist. The Phase 2 branch was therefore cut from `phase/01-schema-evidence-foundation`.

**Resolved the same day:** #4 was merged into `main` first (rebase merge → `fb68f09`), then the Phase 2 branch was rebased onto the new `main` with `git rebase --onto origin/main 72838ee phase/02-enrichment-teardown-fields` — only the nine Phase 2 commits replay, no Phase 1 commit is duplicated, and `git diff HEAD~9 origin/main` is empty — force-pushed with `--force-with-lease`, and PR #5 was merged with a rebase merge → `7092482`. `main` is linear across both phases. `scripts/phase2-verify.py` and `tests.smoke` were re-run **on `main` after the merge**: `RESULT: ALL PASS` for both.

### Files changed

| File | Change |
|---|---|
| `backend/app/config.py` | `FOUNDER_DB_PATH` (its own file, mirrors `DB_PATH`), `CAPTURE_STALE_DAYS = 7`, `REVIEW_SOURCES` + `DEFAULT_REVIEW_SOURCES` (providers are config, not code). |
| `backend/app/db.py` | `table_ddl(name, extra)` so `startups` and `founder_apps` share one column shape from one source of truth; `connect_path()` so the founder store gets identical WAL/busy-timeout settings. |
| `backend/app/pages.py` | **New.** The page plan: homepage + `/pricing` + `/docs`, each through `netguard.safe_get`, each with an explicit `readable` / `unreadable` / `not_fetched` state and its own fetched_at/links. |
| `backend/app/llm.py` | `TEARDOWN_SYSTEM_PROMPT` + `llm_teardown()` + `teardown_brief()`; `llm_json()` gained a `system_prompt=` parameter (default unchanged, so the GitHub seed path keeps the identity prompt). |
| `backend/app/evidence.py` | **New.** The only evidence writer: `write_evidence` refuses a source-less claim by construction, `write_many`, `for_startup`, `count_for_startup`. Commits — an uncommitted row is a row that vanishes. |
| `backend/app/teardown.py` | **New.** Bounding (`clean_features` 5–10 or `[]`, `clean_plans` drops malformed rows, `clean_positioning` one capped line) + `write_teardown` (columns + one evidence row per claim, pricing stamps, unknowns recorded). |
| `backend/app/negatives.py` | **New.** Deterministic probes → `unknown` for unreadable enumerating pages → LLM negatives validated against readable enumerating URLs; guessed capability paths are never fetched; verdict-shaped claims are rephrased. |
| `backend/app/reviews.py` | **New.** `review_sources` providers, reddit-json + RSS parsers, tri-state fetch (403/429 = skip), deterministic classify + ask extraction, one evidence row per review, `asks_from_evidence` for Phase 3's dimension 7. No score anywhere. |
| `backend/app/capture.py` | **New.** `start_capture` (cached / queued / in_progress / not_found), `capture_teardown` (the callable), `run_capture_job`, freshness from the teardown evidence itself. |
| `backend/app/founder.py` | **New.** The founder store: `founder_apps` (same shape as `startups`), `founder_submissions` (§3.1 exactly), the three input paths, validation, the two gates, derived `archive_status`, approve/reject, `publish_to_archive` through `enrich._upsert`. |
| `backend/app/enrich.py` | `draft_from_page` / `draft_from_website` (one draft primitive, shared by the archive seed and the founder URL path), `values_from_record`, `mark_human_confirmed(..., table=)` with a whitelist, and the F-14 carve-out comment on the `reuse_profile` branch. |
| `backend/app/seeder.py` | A third job kind `capture` (own queue + worker, so a founder request never waits behind a 500-candidate seed); `try_enqueue_exclusive(job, key=…)` — kind-scoped by default, per-competitor for captures. |
| `backend/app/main.py` | 13 endpoints: `POST /api/founder-app`, `GET /api/founder-app/{id}`, `POST …/confirm`, `POST …/publish`, `GET /api/admin/founder/submissions`, `POST /api/admin/founder/submissions/{id}/approve|reject`, `POST /api/admin/capture/{id}`, `GET /api/admin/capture/status/{job_id}`; `admin_suggested()` now unions the founder store's pending submissions with the archive's rows. |
| `backend/tests/smoke.py` | `FOUNDER_DB_PATH` pinned into the throwaway temp dir, so a test run never writes `backend/data/founder.db`. |
| `backend/.env.example` | Documents `FOUNDER_DB_PATH`, `CAPTURE_STALE_DAYS`, `REVIEW_SOURCES`. |
| `scripts/phase2-verify.py` | **New.** The exit-gate verifier: 70 checks, stubbed fetcher + both LLM prompts, throwaway archive copy + throwaway founder store. |
| `docs/phase-ledger.md`, `docs/backend-checklist.md`, `docs/codebase-comprehension.md` | This entry, the F-06 correction, and the comprehension refresh. |

### 1. Exit gate — the real output

Command: `backend\.venv\Scripts\python.exe scripts\phase2-verify.py` → `EXIT=0`

It runs against `backend/data/ideasexist.db.phase2-test` (a **copy** made with SQLite's backup API) and `backend/data/founder.db.phase2-test` (a fresh throwaway file). The live archive and the live founder store are never opened for writing, and no test in the file touches the network.

```
==============================================================================
Phase 2 — enrichment & teardown fields: exit-gate verification
==============================================================================
[PASS] live archive present — E:\New-Personal-Projects\Does this Startup Exist\backend\data\ideasexist.db
[PASS] the verifier is pointed at a copy, not the live archive — …\ideasexist.db.phase2-test
[PASS] the verifier is pointed at a throwaway founder store — …\founder.db.phase2-test

--- capture: fixture site through a stubbed fetcher and LLM ---
[PASS] capture reports state=captured — captured
[PASS] features_json holds 5-10 items (F-06) — 6: ['local files', 'markdown notes', 'backlinks', 'graph view', 'sync (paid)', 'publish']
[PASS] pricing_json rows each carry a price and a period (F-07) — [{'name': 'Pro', 'price': '$8', 'period': 'monthly'}, {'name': 'Team', 'price': '$12', 'period': 'monthly'}, {'name': 'Enterprise', 'price': 'custom', 'period': 'annual'}]
[PASS] malformed plan rows are dropped, not stored half-formed (F-07) — ['Pro', 'Team', 'Enterprise']
[PASS] pricing_captured_at is stamped (F-07) — 2026-09-15 10:35:37
[PASS] pricing_source_url is stamped (F-07) — https://acme.example/pricing
[PASS] positioning is non-empty (F-08) — A private, local-first note app that links your thinking.
[PASS] one evidence row per feature, each with a source_url (F-06) — 6 rows for 6 features
[PASS] one evidence row per pricing plan + the free tier (F-07) — 4 rows for 3 plans + free tier
[PASS] the positioning line carries its source (F-08) — [{'id': 11, 'startup_id': 1296, 'evidence_type': 'positioning', 'source_url': 'https://acme.example', …}]
[PASS] provenance is machine_drafted until a human confirms (F-05) — machine_drafted
[PASS] every teardown evidence row is machine_drafted — ['machine_drafted']
[PASS] features with fewer than 5 supported items become unknown, never padded — []

--- negatives: deterministic first, LLM second, no verdicts ---
[PASS] a sourced negative traces to an enumerating page (F-09) — ['no self-host', 'no API', 'no mobile app', 'no real-time collaboration'] from ['https://acme.example', 'https://acme.example/docs', 'https://acme.example/pricing']
[PASS] no negative is derived from a guessed URL (F-09) — ['https://acme.example', 'https://acme.example/docs', 'https://acme.example/pricing']
[PASS] the LLM's negatives survive only when they trace to a page we read (F-09) — ['no self-host', 'no API', 'no mobile app', 'no real-time collaboration']
[PASS] a deterministic probe wins over the LLM's duplicate of the same fact (F-09) — ['no self-host', 'no API', 'no mobile app', 'no real-time collaboration']
[PASS] a verdict-shaped claim is rephrased into an observation (F-09) — ['no self-host', 'no API', 'no mobile app', 'no real-time collaboration']
[PASS] a 404 on a guessed URL produces nothing at all (F-09) — guessed-record probe returned None
[PASS] the page plan never fetches a guessed capability path — (('pricing', '/pricing'), ('docs', '/docs'))
[PASS] a negative with no enumerating source is refused, not stored — empty source and non-enumerating source both refused
[PASS] a retrieval failure is unknown with low confidence, never a negative (F-09) — 3 unknown row(s), conf=[0.1, 0.1, 0.1]
[PASS] an unreadable page still gets a source_url (the page we tried) — ['https://walled.example', 'https://walled.example/docs', 'https://walled.example/pricing']
[PASS] no pricing is stored when the pricing page could not be read (F-07) — pricing_json=None

--- reviews: what their users ask for, never a score ---
[PASS] one evidence row per review, source_url = the review permalink (F-23) — ['https://www.reddit.com/r/notes/comments/abc123/love_it/', 'https://www.reddit.com/r/notes/comments/def456/works_well/']
[PASS] a walled provider (403) is a skip, not a failure (F-23) — skipped=1 rows=2
[PASS] positive and negative are both classified (F-23) — ['negative', 'positive']
[PASS] no score, aggregate or NPS of our own is stored (F-23) — [['asks', 'classification'], ['asks', 'classification']]
[PASS] every extracted ask links to the review it came from (F-23) — [{'ask': 'Love it, but I wish it worked offline.', 'source_url': 'https://www.reddit.com/r/notes/comments/abc123/love_it/', …}]

--- founder app: three paths, two gates, containment ---
[PASS] URL path drafts the founder's app (F-10) — Acme Notes
[PASS] the URL path does not invent the founder's feature list (F-10) — []
[PASS] form path drafts a full teardown record (F-11) — ['local files', 'markdown notes', 'quick capture', 'backlinks', 'sync (paid)', 'publish']
[PASS] a form without 5-10 features is a clear 400 (F-11) — 400/400: features is required: 5-10 short capability strings (the gap table compares feature by feature)
[PASS] agent-JSON path drafts the founder's app (F-12) — 200
[PASS] malformed agent JSON is a 400 (F-12) — malformed agent JSON: Expecting property name enclosed in double quote
[PASS] unknown agent keys are a 400, never silently dropped (F-12) — unknown key(s) in agent payload: ['invented_field']
[PASS] nothing the founder path wrote reached the archive (F-20) — 1285 -> 1285
[PASS] no founder record appears in /api/startups (F-20) — []
[PASS] no founder record is counted by /api/stats (F-20) — 1285 vs 1285
[PASS] no founder record appears in /api/categories (F-20) — [{'category': 'other', 'count': 302}, …]
[PASS] the verify walk never sees the founder store (F-20) — list_suggested is archive-only
[PASS] the two stores are two files, each with its own schema (F-10/F-20) — founder_apps is absent from the archive; startups is absent from the founder store
[PASS] a link-less submission is comparison-only (F-20) — {'has_link': False, 'link': '', 'link_field': None}
[PASS] no consent question is asked when there is no link (F-20) — this app has no link (website / github / app store / play store) — it is comparison-only…
[PASS] the compare path refuses an unconfirmed founder app (F-13) — founder app 2 is not confirmed — confirm the draft before the gap table runs…
[PASS] confirm flips the record to human_confirmed (F-05/F-13) — human_confirmed confirmed_at=2026-09-15 10:35:37
[PASS] nothing is auto-confirmed by a draft (F-13) — all three drafts start unconfirmed
[PASS] ticking the opt-in creates a pending submission (F-13/F-24) — {'submitted': True, 'submission_id': 1, 'archive_status': 'pending', …}
[PASS] the admin queue unions founder submissions with the archive's rows (F-24) — 1 founder row(s) among 8 queue rows
[PASS] approval creates the archive row and links it (F-13/F-24) — archive_startup_id=1299 name=Founder Co
[PASS] the founder record keeps its own row — the archive got a twin, not the record (F-10) — archive 1285 -> 1286
[PASS] archive_status is derived from the newest submission (F-24) — approved
[PASS] a rejection carries a note the founder can read (F-24) — The site is behind a login, so nothing could be read.
[PASS] a rejection with no note is refused (F-24) — 400
[PASS] resubmitting after a rejection creates a NEW row, never an edit (F-24) — [(2, 'rejected'), (3, 'pending')]
[PASS] archive_status follows the newest submission (F-24) — pending

--- just-in-time capture: one job per competitor, cached for 7 days ---
[PASS] two concurrent captures of one competitor produce exactly one job (F-22) — jobs=1 first=queued second=in_progress
[PASS] an in-flight capture returns an explicit retry state, not a partial teardown (F-22) — {'state': 'in_progress', 'startup_id': 1300, 'message': 'capture in progress — retry'}
[PASS] the capture job completes and records its result (F-22) — done
[PASS] a request inside the 7-day window is served from cache (F-22) — {'state': 'cached', 'startup_id': 1296, 'captured_at': '2026-09-15 10:35:37', …}
[PASS] a request outside the window re-captures (F-22) — {'state': 'queued', 'startup_id': 1296, 'job_id': '8ee71480b3ea', …}
[PASS] the freshness window is 7 days, the same rhythm as VERIFY_AUTO_STALE_DAYS (F-22) — CAPTURE_STALE_DAYS=7 (VERIFY default is also 7; this run pins it to 0 to keep the network out of the test)

--- re-seed: dedup kept, teardown fields not lost ---
[PASS] a re-seed does not duplicate the row (F-14) — id 1296 -> 1296
[PASS] a re-seed keeps the teardown fields (F-14 carve-out) — features=True pricing=True
[PASS] a re-seed never downgrades human_confirmed (F-14 carve-out) — human_confirmed
[PASS] a unique-index collision is still a clear ValueError → 400 (F-14) — duplicate website_url refused
[PASS] no frontend/ file was touched in this phase — committed=[] working=[]

==============================================================================
RESULT: ALL PASS
```

### 2. Sample row dump (from the same run)

The dump runs after the aging check and the human-confirm check, which is why the pricing stamp is a month old and the provenance is `human_confirmed` rather than `machine_drafted`:

```
  startups.id            = 1296  (Acme Notes)
  features_json          = ["local files", "markdown notes", "backlinks", "graph view", "sync (paid)", "publish"]
  pricing_json           = {"free_tier": "Free up to 3 docs", "plans": [{"name": "Pro", "price": "$8", "period": "monthly"}, {"name": "Team", "price": "$12", "period": "monthly"}, {"name": "Enterprise", "price": "custom", "period": "annual"}]}
  pricing_captured_at    = 2026-08-16 10:35:38
  pricing_source_url     = https://acme.example/pricing
  positioning            = A private, local-first note app that links your thinking.
  provenance             = human_confirmed
  evidence rows:
    [feature    ] local files                                            conf=0.6 src=https://acme.example
    [feature    ] markdown notes                                         conf=0.6 src=https://acme.example
    [feature    ] backlinks                                              conf=0.6 src=https://acme.example
    [feature    ] graph view                                             conf=0.6 src=https://acme.example
    [feature    ] sync (paid)                                            conf=0.6 src=https://acme.example
    [feature    ] publish                                                conf=0.6 src=https://acme.example
    [pricing    ] Pro                                                    conf=0.7 src=https://acme.example/pricing
    [pricing    ] Team                                                   conf=0.7 src=https://acme.example/pricing
    [pricing    ] Enterprise                                             conf=0.7 src=https://acme.example/pricing
    [pricing    ] free_tier                                              conf=0.7 src=https://acme.example/pricing
    [positioning] A private, local-first note app that links your thin   conf=0.6 src=https://acme.example
    [negative   ] no self-host                                           conf=0.8 src=https://acme.example/pricing
    [negative   ] no API                                                 conf=0.8 src=https://acme.example/docs
    [negative   ] no mobile app                                          conf=0.8 src=https://acme.example
    [negative   ] no real-time collaboration                             conf=0.5 src=https://acme.example/docs
    [review     ] Love it, but I wish it worked offline                  conf=0.5 src=https://www.reddit.com/r/notes/comments/abc123/love_it/
    [review     ] Works well for our team                                conf=0.5 src=https://www.reddit.com/r/notes/comments/def456/works_well/
  founder_apps: id=2 name='Founder Co' source_kind=form provenance=human_confirmed confirmed_at=2026-09-15 10:35:37
  founder_submissions: [('approved', 1299, None)]
```

The three negatives at `conf=0.8` are the deterministic probes (the pricing page lists tiers and no self-host; the docs index lists no API section; the page's own links list no store link). `no real-time collaboration` at `conf=0.5` is the LLM's, kept because it cites `acme.example/docs`, a page we read. The `Malformed` and `HalfFormed` plans the stub returned are absent — dropped, not stored.

### 3. Test suites

```
cd backend
..\backend\.venv\Scripts\python.exe -m tests.smoke
RESULT: ALL PASS        (exit 0)
```

```
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm test
[PASS] backend smoke (exit 0)              RESULT: ALL PASS
[PASS] frontend sort check (exit 0)
[PASS] frontend lint + build (exit 0)
[PASS] frontend e2e verification (exit 0)  TEST RESULTS: 35 PASSED, 0 FAILED
RESULT: ALL PASS
```

### 4. Phase 3 wiring — the one line this phase owes

`POST /api/compare` starts the capture on the first founder request for a competitor and never before:

```python
state = capture.start_capture(competitor_id)   # cached | queued | in_progress | not_found
if state["state"] in ("queued", "in_progress"):
    return {"state": state["state"], "message": state["message"]}   # "capture in progress — retry"
# state == "cached": read the teardown fields the capture wrote
```

The callable and the job are tested here; no `/api/compare` route was added (that is Phase 3), and no public capture-job endpoint exists (job payloads carry error strings and fetched URLs — the admin-gated pair is `POST /api/admin/capture/{id}` / `GET /api/admin/capture/status/{job_id}`).

### 5. Notes recorded at Phase 2

- **The founder endpoints are deliberately not behind the admin token** (`POST /api/founder-app`, `…/confirm`, `…/publish`). They cannot write the archive — the approval path does that, and that one IS admin-gated — so the token would only stand between a founder and their own local draft. They are rate-limited (`20/min` per IP) like every other mutating route. If the owner prefers the archive's gate on them too, it is a two-line change.
- **A founder URL-path draft leaves `features_json` empty on purpose.** Spec §3 lists five fields for that path (name, tagline, category, description, founded), and the product must not invent the founder's own feature list — the confirm step's inline editing (Phase 6) is where those arrive. Until then the gap table will show `unknown` for feature rows against a URL-path app, which is the honest state. Phase 6 needs this to be visible, not silently filled.
- **The freshness anchor is the teardown evidence itself** (newest `feature`/`pricing`/`positioning`/`negative`/`review` row, with `pricing_captured_at` as a secondary signal). A capture that could read nothing writes no rows and therefore leaves no cache entry, so it is retried rather than mistaken for a fresh teardown.
- **A third job kind was added to the queue** (`capture`, its own worker) and `seeder.try_enqueue_exclusive` gained an optional `key`. The default scope is unchanged (kind-wide), so the verify/seed serialization semantics are exactly as they were; the capture's key is what makes "two concurrent requests, one job" true per competitor.
- **`evidence.write_evidence` commits.** Found while writing the gate: the first draft relied on the caller's commit and the rows silently disappeared when the connection closed — the teardown columns looked perfect and the evidence table was empty. Caught by the "one evidence row per feature" check, which is exactly the check that would have been skipped if the gate only asserted the visible fields.
- **Doc drift caused by this phase — corrected in this branch.** `docs/backend-checklist.md` F-06 said `seed_from_website`/`seed_from_github` populate `features_json`; Phase 2 (and Round 5's F-22) makes the just-in-time capture the writer, so F-06 now says so and points at F-22. `docs/codebase-comprehension.md` gained a Phase 2 note, the seven new modules, the founder store's two tables, the new endpoints, the capture paragraph in §4.4, the Phase 2 verifier in §7 and Reddit in the integration list.
### 6. Follow-up — the `publish` flag could never work (2026-09-15)

Found by an independent review after Phase 2 had already merged, so it is a follow-up commit rather than part of the original gate.

**What was wrong.** `FounderAppIn` accepted `publish: bool`, documented as "the CONSENT checkbox", and `create_founder_app` ran `founder.request_publish()` after the draft was written. Because the draft is written by that same request, `confirmed_at` is always NULL when the consent gate runs, so the `confirm the draft before publishing` guard fired on **every** such call — `publish=true` could not succeed. Worse, it failed *after* the row existed: a 400, which reads as "nothing happened", with a persisted draft behind it, so a client that retried accumulated orphan drafts (reproduced: two attempts → two rows).

**The fix.** `publish` is gone from the model, and consent is reachable only through `POST /api/founder-app/{id}/publish` — the flow the endpoint's own docstring already described. Rather than let an old client's `publish` key be silently ignored, `FounderAppIn` now carries `model_config = ConfigDict(extra="forbid")` plus a `mode="before"` validator that refuses the key with a message naming the call that does publish. Unknown top-level keys (typos) are refused too — F-12's rule, applied one level up.

**Gate check added.** `scripts/phase2-verify.py` gained four checks: the refusal is loud (422), the refusal names `founder-app/{id}/publish`, **the refused request writes no draft** (the partial-write property), and an unknown top-level key is refused as well. The original 70 checks exercised the two-step flow only — this is the check that would have caught it before the merge.

Re-verified after the change: `scripts/phase2-verify.py` → `RESULT: ALL PASS` (74 checks), backend smoke green.

- **Row status after this phase:** Phases 0–2 `PASS`; Phases 3–5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`.
