# Phase Ledger — IdeaExists implementation

**Purpose:** the single audit trail for backend-first gating. Every phase writes a row here; decisions about "can frontend start?" read only from this file.
**Rule:** Phases 6–8 may not be `running` while Phase 5 is not `PASS`.

| Phase | Status | Evidence (command + output summary) | Date |
|---|---|---|---|
| 0 — Onboarding & baseline | **PASS** | Docs read (implementation-plan, handoff, codebase-comprehension, reworked-revamp-plan, teardown-spec, gap-table-format, backend-checklist, phase-ledger). `npm test` → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed/0 failed). `backend\.venv\Scripts\python.exe scripts/phase0-baseline.py` → `[baseline] matches expected baseline` — **1,282 total / 1,278 verified / 0 dead / 57 github**; tables `jobs, sqlite_sequence, startups, verify_log`; last_checked 2026-09-04. No drift. Full output in §Phase 0 evidence below. | 2026-09-15 |
| 1 — Schema & evidence foundation | **PASS** | Migration verified on a **copy** of the live DB: `backend\.venv\Scripts\python.exe scripts\phase1-verify.py` → **RESULT: ALL PASS** (31 checks) — 1,282 rows before and after, 18 → 40 columns, all 22 teardown columns added incl. `app_store_url` / `play_store_url` / `date_source`, `founded` unchanged and never renamed, `evidence` table present with a NOT NULL `source_url`, second migration run added 0 columns (idempotent), every new column present in `enrich.UPDATABLE`, a 200-day-old `verify_log` row survived a real pass (F-03), and the F-04/F-05 branches behave (rdap / wayback / llm / unknown, machine_drafted stamped, human confirm flips it and a reuse refresh does not downgrade it). Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` (from `backend/`) → **RESULT: ALL PASS** (85 PASS / 0 FAIL); `npm test` with Node 24 first on PATH → **RESULT: ALL PASS**. Full output in §Phase 1 evidence below. | 2026-09-15 |
| 2 — Enrichment & teardown fields | pending | | |
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
| `backend/app/db.py` | `NEW_STARTUP_COLUMNS` (22 columns) is the single source of truth for both the fresh-DB `CREATE TABLE` and the new `migrate()`; `INIT_DB` now runs `executescript(SCHEMA)` + `migrate()`. Added the `evidence` table (F-02) and its `startup_id` index. |
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
- **Doc drift now stale, recorded not fixed** (the same rule Phase 0 applied): `docs/codebase-comprehension.md` §3 still says `verify_log` is “pruned to a 90-day window by the pass itself” and §10 lists the missing evidence/provenance model as technical debt. Both were accurate when written; F-01–F-03 supersede them. `docs/handoff.md` and the comprehension doc are Phase 9 clean-up material.
- **No `frontend/` file, no Phase 2 table, no `founded_at` rename.** `git diff --stat main` on this branch touches `backend/app/{db,enrich,verify}.py`, `scripts/phase1-verify.py` and `docs/phase-ledger.md` only.
- **Row status after this phase:** Phases 0–1 `PASS`; Phases 2–5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`.
