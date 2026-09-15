# Phase Ledger — IdeaExists implementation

**Purpose:** the single audit trail for backend-first gating. Every phase writes a row here; decisions about "can frontend start?" read only from this file.
**Rule:** Phases 6–8 may not be `running` while Phase 5 is not `PASS`.

| Phase | Status | Evidence (command + output summary) | Date |
|---|---|---|---|
| 0 — Onboarding & baseline | **PASS** | Docs read (implementation-plan, handoff, codebase-comprehension, reworked-revamp-plan, teardown-spec, gap-table-format, backend-checklist, phase-ledger). `npm test` → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed/0 failed). `backend\.venv\Scripts\python.exe scripts/phase0-baseline.py` → `[baseline] matches expected baseline` — **1,282 total / 1,278 verified / 0 dead / 57 github**; tables `jobs, sqlite_sequence, startups, verify_log`; last_checked 2026-09-04. No drift. Full output in §Phase 0 evidence below. | 2026-09-15 |
| 1 — Schema & evidence foundation | pending | | |
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
