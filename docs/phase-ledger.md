# Phase Ledger — IdeaExists implementation

**Purpose:** the single audit trail for backend-first gating. Every phase writes a row here; decisions about "can frontend start?" read only from this file.
**Rule:** Phases 6–8 may not be `running` while Phase 5 is not `PASS`.

| Phase | Status | Evidence (command + output summary) | Date |
|---|---|---|---|
| 0 — Onboarding & baseline | **PASS** | Docs read (implementation-plan, handoff, codebase-comprehension, reworked-revamp-plan, teardown-spec, gap-table-format, backend-checklist, phase-ledger). `npm test` → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed/0 failed). `backend\.venv\Scripts\python.exe scripts/phase0-baseline.py` → `[baseline] matches expected baseline` — **1,282 total / 1,278 verified / 0 dead / 57 github**; tables `jobs, sqlite_sequence, startups, verify_log`; last_checked 2026-09-04. No drift. Full output in §Phase 0 evidence below. | 2026-09-15 |
| 1 — Schema & evidence foundation | **PASS** | Migration verified on a **copy** of the live DB: `backend\.venv\Scripts\python.exe scripts\phase1-verify.py` → **RESULT: ALL PASS** (31 checks) — 1,282 rows before and after, 18 → 40 columns, all 22 teardown columns added incl. `app_store_url` / `play_store_url` / `date_source`, `founded` unchanged and never renamed, `evidence` table present with a NOT NULL `source_url`, second migration run added 0 columns (idempotent), every new column present in `enrich.UPDATABLE`, a 200-day-old `verify_log` row survived a real pass (F-03), and the F-04/F-05 branches behave (rdap / wayback / llm / unknown, machine_drafted stamped, human confirm flips it and a reuse refresh does not downgrade it). Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` (from `backend/`) → **RESULT: ALL PASS** (85 PASS / 0 FAIL); `npm test` with Node 24 first on PATH → **RESULT: ALL PASS**. Full output in §Phase 1 evidence below. | 2026-09-15 |
| 2 — Enrichment & teardown fields | **PASS** | Branch `phase/02-enrichment-teardown-fields`, cut from Phase 1's branch and rebased onto `main` after #4 merged (see the note below). `backend\.venv\Scripts\python.exe scripts\phase2-verify.py` → **RESULT: ALL PASS** (70 checks, exit 0) on a copy of the live archive + a throwaway founder store, fetcher and both LLM prompts **stubbed**: a capture yields `features_json` with 6 items, 3 well-formed pricing plans (2 malformed rows dropped) with `pricing_captured_at` + `pricing_source_url`, a non-empty `positioning`, **one evidence row per feature / plan / free tier / positioning line / negative / review**, provenance `machine_drafted` until a human confirms. Negatives: every one traces to an **enumerating** page; a 404 on a guessed `/api` produces nothing; an unreadable page is `unknown` at confidence 0.1; a verdict-shaped LLM claim is rephrased and a duplicate of the deterministic probe is dropped. Founder app: all three paths draft (URL / form / agent-JSON), a form without 5–10 features → 400, malformed JSON → 400, unknown keys → 400, **nothing reaches the archive DB or `/api/startups` `/api/stats` `/api/categories`** (`1285 → 1285`), the compare guard refuses an unconfirmed app, link-less → `local_only` with **no opt-in offered**, link + opt-in → `pending` → approve → `archive_startup_id` set with the founder record still in its own file, and a rejection carries a readable note (a resubmission is a new row). JIT: two concurrent captures of one competitor → **exactly one job**, in-flight → explicit `capture in progress — retry`, inside 7 days → `cached`, outside → re-queued. Reviews: a 403 provider is a **skip**, every ask links to its review, no score of ours stored. Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` → **RESULT: ALL PASS**; `npm test` with Node 24 first on PATH → **RESULT: ALL PASS** (35 e2e passed / 0 failed). No `frontend/` file touched (asserted in the verifier). Full output in §Phase 2 evidence below.
| 3 — Comparison, gap table & export | **PASS** | Branch `phase/03-comparison-gap-export`, cut from `main` at `d41fdd0`. `backend\.venv\Scripts\python.exe scripts\phase3-verify.py` → **RESULT: ALL PASS** (45 checks at the gate; **47** after the §5 follow-up, still ALL PASS) on a copy of the live archive + a throwaway founder store, fetcher and both LLM prompts **stubbed**: the five bands are correct for a fixture (you-only → `you_have_they_dont`, they-only → `they_have_you_dont`, both → `both_have`, no data on either side → `unknown`); every non-`unknown` "they" cell carries a source; an unsourced "doesn't do" cell renders `unknown` (never "no") and only observations that trace to an enumerating page enter the negative list; dimension 7 sends an ask your features cover to `you_have_they_dont` and an uncovered one to `asked_for`, each linked to its review; compare refuses an unconfirmed founder app with an explicit `409 not_confirmed` state (F-13); the JIT wiring queues a capture on the first founder request (F-22), serves the table once it is cached, and two concurrent calls still collapse into **one** job; all three exports parse and re-run **byte-identical** (stateless + deterministic), and CSV carries `asked_for` as a band value; a known slug resolves, an unknown slug 404s, and the real `cal-com` duplicate group resolves deterministically (human-verified first, then lowest id); a stale `last_checked` reads `machine_verified=false` while `admin_verified` stays true, and no badge appears in a claim cell; the founder store never reaches `/api/startups` / `/api/stats` / `/api/categories`. Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` (from `backend/`) → **RESULT: ALL PASS** (85 PASS / 0 FAIL); `npm test` with Node 24 first on PATH → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed / 0 failed). No `frontend/` file touched (asserted in the verifier). Full output in §Phase 3 evidence below. | 2026-09-15 |
| 4 — Search classification & match reasons | **PASS** | Branch `phase/04-search-classification`, cut from `main` at `e92b1a8`. `backend\.venv\Scripts\python.exe scripts\phase4-verify.py` → **RESULT: ALL PASS** (58 checks, exit 0) on a copy of the live archive + a throwaway founder store, with **no fetcher and no LLM at all** (a search reads stored data only): a real product name returns as result **#1** with `reason == "Exact name match"` (Obsidian, exactly one exact-name hit); a query matching at every rung returns non-decreasing rungs `[0, 2, 3, 4, 4, 5, 6]` and the fixtures come back exact → name → tagline → description → category → fuzzy; every one of the **eight frozen reason strings** is emitted (including the latent "Same audience, different approach", which no column writes today); dead **and** pivoted rows sort last under an otherwise equal match and are still returned; a **0-star exact-name match beats a 99999-star fuzzy one**; a two-term query returns **only** rows matching both and scores by the **worst** term (0.143, not the 0.071 average); the empty-query contract (no `q`, `q=`, `q=<blank>`) is **200 + `[]`**; `q=%` and `q=_` return **0 rows**, and `/api/startups?q=%` is still literal (40 of 1,282 — every hit really contains a `%`); a search writes no evidence row and queues no capture job, and a tripwire proves it never calls `capture.start_capture` (the F-22 contrast with `/api/compare`); no founder-store record appears in a search result; the keyword rung matches a fixture with `features_json` populated and **skips** the row where it is NULL (data-awareness); and the reachable-rung census is recorded below. Suites: `..\backend\.venv\Scripts\python.exe -m tests.smoke` (from `backend/`) → **RESULT: ALL PASS** (85 PASS / 0 FAIL); `npm test` with Node 24 first on PATH → **RESULT: ALL PASS** (backend smoke exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed / 0 failed). No `frontend/` file touched (asserted in the verifier). Full output in §Phase 4 evidence below. | 2026-09-16 |
| 5 — Backend functional test gate | **PASS** | Branch `phase/05-backend-functional-gate`, cut from `main` at `850c6e9`. Backend only — no `frontend/` file touched. New: `backend/tests/functional.py`, one self-contained suite over **F-01–F-24 + the §6 invariants** (187 checks) with its own throwaway archive + founder store and the fetcher, both LLM prompts and both date sources stubbed: `cd backend` then `..\backend\.venv\Scripts\python.exe -m tests.functional` → **`RESULT: ALL PASS`** — `TESTS: 187 run, 187 passed, 0 failed` (exit 0, ~2.8 s; identical across four consecutive runs). Wired into `scripts\verify.mjs` directly after the smoke suite, so `npm test` now runs **five** steps → **`RESULT: ALL PASS`** (backend smoke exit 0 · backend functional exit 0 · frontend sort check exit 0 · frontend lint+build exit 0 · e2e 35 passed / 0 failed). **Traceability table F-01–F-24 → test → PASS below.** Real-backend smoke against the **real** archive: WAL-safe backup to `ideasexist.db.bak-phase5` first, then the first boot since Phase 1 → **18 → 40 columns and the `evidence` table appearing, 1,282 rows before and after**; `GET /api/health`, `/api/stats`, `/api/categories`, `/api/search?q=obsidian`, `/api/startups/obsidian` all answered with real data; a real founder app (`Phase 5 Smoke App`, confirmed) plus a real JIT capture of **Obsidian** (6.0 s, page plan fetched) → 3 sourced negative evidence rows written, with `features_json`/`pricing_json`/`positioning` left **unknown** because the LLM gateway answered **401** for the configured `OPENCODE_GO_API_KEY` — recorded honestly, not hidden (see §Phase 5 evidence 4). All four `scripts/phaseN-verify.py` re-run on this branch → **`RESULT: ALL PASS`** (31 / 74 / 47 / 59 checks); `phase4-verify.py` needed its rung-census assertion repaired against the now-real captured state (recorded below). Full output in §Phase 5 evidence below. | 2026-09-16 |
| 6 — Frontend implementation | pending | Unblocked by the Phase 5 `PASS` above (this row moved `blocked` → `pending` in the same commit as the Phase 5 row). | |
| 7 — Frontend tests | pending | Unblocked by the Phase 5 `PASS` above. | |
| 8 — Full end-to-end test | pending | Unblocked by the Phase 5 `PASS` above. | |
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
---

## Phase 3 evidence — comparison, gap table & export (2026-09-15)

**Branch:** `phase/03-comparison-gap-export`, cut from `main` at `d41fdd0`. Backend only — nothing under `frontend/` was touched (asserted in the verifier by a `git diff`/`git status` check on that path).

### Files changed

| File | Change |
|---|---|
| `backend/app/compare.py` | **New.** The whole comparison engine: the slug rule and its collision resolution (F-17), the explicit trust badges (F-21), the two sides gathered from their two stores, the seven-dimension cross-store diff and the five bands (`docs/gap-table-format.md`), and the three export renderers (F-16). |
| `backend/app/main.py` | `POST /api/compare` (F-15, with the F-13 guard and the F-22 JIT wiring), `GET /api/export/{markdown\|json\|csv}` (F-16), `GET /api/startups/{slug}` (F-17). |
| `scripts/phase3-verify.py` | **New.** The exit-gate verifier (the evidence tool below). |
| `docs/codebase-comprehension.md` | §4.2 HTTP surface, §7 harness, §9 "what is missing" — corrected for what Phase 3 falsified (see the doc-drift note). |
| `docs/phase-ledger.md` | This entry. |

No new tables, no new columns (the badges are derived, per F-21).

### 1. The exit gate — comparison, gap table & export

Command (from the repo root, venv python): `backend\.venv\Scripts\python.exe scripts\phase3-verify.py` → **`EXIT=0`**. Every check on a copy of the live archive (SQLite's backup API — WAL mode) plus a throwaway founder store, with the fetcher and both LLM prompts **stubbed**, so nothing touched the network or the live files.

```
[PASS] a capability only 'you' have lands in you_have_they_dont (F-15) — {'dimension': 'Features', 'band': 'you_have_they_dont', 'you': 'public API', 'them': 'no — no API (Acme Notes)', 'source': 'https://acme.example/docs', 'captured_at': '...'}
[PASS] a capability only 'they' have lands in they_have_you_dont (F-15) — {'you': 'not offered', 'them': 'backlinks (Acme Notes)', 'source': 'https://acme.example'}
[PASS] a capability both have lands in both_have (F-15) — {'you': 'markdown notes', 'them': 'markdown notes (Acme Notes)'}
[PASS] missing data on either side is shown as unknown, never scored (F-15) — {'you': 'public API', 'them': 'unknown — no teardown captured', 'source': ''}
[PASS] every non-unknown 'they' cell carries a source (cell rule 1) — []
[PASS] an unsourced doesn't-do cell renders unknown, never 'no' (cell rule 2) — {'dimension': "What it doesn't do", 'band': 'unknown', 'them': 'unknown — could not read the page (Orphan Negative Co)'}
[PASS] the negative list only contains observations that trace to an enumerating page (F-09) — ['https://acme.example', 'https://acme.example/docs', 'https://acme.example/pricing']
[PASS] a reviewer ask neither side covers lands in asked_for (dim 7) — {'band': 'asked_for', 'source': 'https://www.reddit.com/r/notes/comments/aaa1/needs_mobile/'}
[PASS] the same ask, when your declared features cover it, lands in you_have_they_dont (dim 7) — {'you': 'yes — declared: public API', 'source': 'https://www.reddit.com/r/notes/comments/bbb2/api/'}
[PASS] compare refuses an unconfirmed app with an explicit not-confirmed state (F-13) — 409: {'state': 'not_confirmed', 'message': 'founder app 1 is not confirmed — confirm the draft before the gap table runs (confirm-before-diff)'}
[PASS] Markdown has the four groups incl. the demand group (F-16) — []
[PASS] CSV has the exact columns band, dimension, you, them, source_url, captured_at (F-16)
[PASS] CSV carries asked_for as a band value (F-16) — ['asked_for', 'both_have', 'they_have_you_dont', 'unknown', 'you_have_they_dont']
[PASS] re-running an export with the same inputs gives the same bytes (F-16 stateless+deterministic)
[PASS] a real same-name group resolves deterministically: verified first, then lowest id (F-17) — slug=cal-com got=5 expected=5 group=2
[PASS] a stale last_checked reads machine_verified=false while admin_verified stays true (F-21)
[PASS] a fresh check reads machine_verified=true (F-21)
[PASS] no badge is emitted inside a claim/row cell (F-21 / §8.1)
[PASS] no founder record appears in /api/startups / is counted by /api/stats / appears in /api/categories
[PASS] a never-captured competitor returns the queued/retry state, not a partial teardown (F-22) — 200: queued / capture queued
[PASS] once captured, the same call returns the table (F-22)
[PASS] two concurrent captures of one competitor produce exactly one job (F-22) — jobs=1 first=queued second=in_progress
[PASS] no frontend/ file was touched in this phase — committed=[] working=[]

RESULT: ALL PASS
```

45 checks, 0 failed.

### 2. Sample gap table (the ledger's raw evidence)

`you` = the founder's confirmed app **Loom-note** (an online-first note app with an API and collaboration); `them` = the captured competitor **Acme Notes** (a local-first note app). Bands from the run:

| Band | Rows | Example |
|---|---|---|
| `you_have_they_dont` (6) | Features ×3, What it doesn't do ×2, What their users ask for ×1 | `public API` → *no — no API* (source `acme.example/docs`) |
| `they_have_you_dont` (6) | Pricing ×2, Features ×3, … | `Team $12/monthly` (source `acme.example/pricing`) |
| `both_have` (7) | Pricing ×1, Free tier ×1, Features ×2, Positioning ×1, What it doesn't do ×2 | `Pro $7/monthly` vs `Pro $8/monthly` |
| `unknown` (1) | Activity / liveness ×1 | `you=n/a` — the founder side has no liveness signal |
| `asked_for` (1) | What their users ask for ×1 | `native mobile app` — 2 reviewers asked (source `reddit.com/r/notes/...`) |

The competitor's negative evidence rows (the "doesn't do" list), every one traced to a page that enumerates:

```
('no self-host',                 'https://acme.example/pricing')
('no API',                       'https://acme.example/docs')
('no mobile app',                'https://acme.example')
('no real-time collaboration',   'https://acme.example/docs')
```

Markdown export (head):

```
# Gap table — Loom-note vs Acme Notes
_You: Loom-note. Competitor(s): Acme Notes._
## You have — they don't
| Dimension | You | Competitor | Source |
|---|---|---|---|
| Features | public API | no — no API (Acme Notes) | https://acme.example/docs (captured 2026-09-15 ...) |
| Features | real-time collaboration | no — no real-time collaboration (Acme Notes) | https://acme.example/docs (captured ...) |
| Features | export | not in their feature list (Acme Notes) | https://acme.example (captured ...) |
| What it doesn't do | yes — declared: public API | no API (Acme Notes) | https://acme.example/docs (captured ...) |
```

### 3. The two suites (unchanged, still green)

- `cd backend` then `..\backend\.venv\Scripts\python.exe -m tests.smoke` → **`RESULT: ALL PASS`** (85 `[PASS]` / 0 `[FAIL]`, exit 0).
- `$env:PATH = "C:\Program Files\nodejs;" + $env:PATH` then `npm test` (Node 24 first on PATH; AutoClaw's bundled Node 22 otherwise shadows it) → **`RESULT: ALL PASS`**:

```
[PASS] backend smoke (exit 0)              RESULT: ALL PASS
[PASS] frontend sort check (exit 0)        RESULT: ALL PASS
[PASS] frontend lint + build (exit 0)      ✓ Compiled successfully
[PASS] frontend e2e verification (exit 0)  TEST RESULTS: 35 PASSED, 0 FAILED
RESULT: ALL PASS
```

### 4. Notes recorded at Phase 3

- **The compare guard, the JIT wiring and the diff, in that order.** `POST /api/compare` resolves the `you` founder record, then calls `founder.assert_comparable` **before anything else** (F-13): an unconfirmed draft is a 409 `{"state": "not_confirmed"}` with the message, never a generic 500 and never a silently empty table. Only then does it trigger the capture (F-22) — the ledger's one open line, now wired — and only when every competitor is `cached` does it build the table.
- **The exports are deliberately not the compare path.** They take the same named inputs as query parameters and recompute from stored data; they **never** trigger a capture. That is what makes "re-running an export with the same inputs gives the same bytes" true, and it is why the export has no retry state: an export of a competitor with no teardown renders `unknown` rows rather than a job.
- **`both_have` carries parity, including parity of absence.** The spec has no "neither side has it" band. A *sourced* negative whose capability you also lack is therefore placed in `both_have` (no differentiation), while a negative whose capability you **do** cover is a real edge in `you_have_they_dont`. An unsourced (or `unknown`-valued) negative is placed in `unknown` — the cell reads "unknown", never "no" (cell rule 2). This is the one place the five bands needed a judgement call; it is written down here so it is not re-litigated silently.
- **Capability-level matching is a short, reviewable alias table** (`compare.CAPABILITY_ALIASES`), not a fuzzy matcher: an unlisted variant stays its own row, which is the honest failure mode (a spurious merge would hide a real gap). "markdown" == "Markdown" needs no entry; "offline mode" == "local files" == "work without internet" is one entry, shared by the feature rows and dimension 7.
- **`machine_verified`'s window falls back to `CAPTURE_STALE_DAYS` when `VERIFY_AUTO_STALE_DAYS` is 0.** Found while writing the gate: with auto-verify disabled for a throwaway instance the naive window made the badge read false for every row. The fallback keeps the badge meaningful (a stale check still reads false) without a second config knob.
- **Doc drift caused by this phase — corrected in this branch.** `docs/codebase-comprehension.md` §9 said there was "no side-by-side comparison, no export, and no stable URL for a single product". Phase 3 closes the *backend* half of that, so §9 now carries the correction and names what is still missing (the frontend view, the `/products/<slug>` route, search-with-reasons). §4.2 gains the three new routes and §7 gains the Phase 3 verifier.
### 5. Follow-up — the feature-source union (2026-09-16)

Found by an independent review of this branch **before it was merged**, so it lands inside Phase 3 rather than as a post-merge fix.

**What was wrong — in principle, not in the normal path.** `compare.them_side()` built a competitor's feature set from its `feature` **evidence rows**, and consulted `features_json` only when there were **no** evidence rows at all (`if not features:`). The two sources were never reconciled, so if they ever disagreed the table **under-reported** the competitor's features — and under-reporting flips a parity row into a *"you have — they don't"* edge. That is a false edge in the founder's favour, fabricated with a plausible-looking source attached: precisely the failure the product calls its strictest rule.

**Why the normal path never hits it.** One capture writes both — `features_json` and one evidence row per feature, features and pricing together — so in practice they agree, which is why this took a review rather than the gate to surface: the gate's fixture comes from the real capture path and is therefore always consistent by construction.

**The fix.** The two sources are **unioned**: a capability present in *either* counts as present, and an evidence row still supplies the provenance whenever both carry the same capability. The failure mode becomes parity / `unknown` instead of an invented edge.

**Gate check added.** `scripts/phase3-verify.py` 45 → **47 checks**: a capability injected into `features_json` alone must still count as present (and must not be reported as "not in their feature list"), and the existing capability's evidence source must survive the merge unchanged.

Re-verified after the change: `scripts/phase3-verify.py` → **RESULT: ALL PASS** (47 checks, exit 0); backend smoke green.

- **Row status after this phase:** Phases 0–3 `PASS`; Phases 4–5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`.
---

## Phase 4 evidence — search classification & match reasons (2026-09-16)

**Branch:** `phase/04-search-classification`, cut from `main` at `e92b1a8`. Backend only — nothing under `frontend/` was touched (asserted in the verifier by a `git diff`/`git status` check on that path). Search is a pure read, so the verifier installs **no fetch stub and no LLM stub**: every check runs against stored data.

### Files changed

| File | Change |
|---|---|
| `backend/app/search.py` | **New.** The classifier: the frozen reason vocabulary, the ladder mapped onto the columns that exist today (with the measured census in the module docstring), the word-term AND gate, the distance model (0.0 exact word / 0.05 prefix / 0.10 mid-word / 1−ratio fuzzy, matching at ≤ the client's own Fuse threshold 0.3), the ordering key (dead → rung → worst-term score → stars → name → id) and the two documented divergences from `lib/search.ts`. |
| `backend/app/main.py` | `GET /api/search` (F-18) — the documented empty-query contract, the additive/read-only posture, and the `?limit=` ceiling that mirrors `LIST_LIMIT_DEFAULT`. |
| `scripts/phase4-verify.py` | **New.** The exit-gate verifier (the evidence tool below), 58 checks. |
| `docs/backend-checklist.md` | F-18 now records the two decisions it left open (the empty-query contract and the frozen vocabulary). |
| `docs/codebase-comprehension.md` | §4.2 read surface, §7 harness, §9 "what is missing" — corrected for what Phase 4 falsified (see the doc-drift note). |
| `docs/phase-ledger.md` | This entry. |

No new tables, no new columns, no schema change.

### 1. The exit gate — the real output

Command (from the repo root, venv python): `backend\.venv\Scripts\python.exe scripts\phase4-verify.py` → **`EXIT=0`**. Every check runs against a copy of the live archive (SQLite's backup API — WAL mode) plus a fresh throwaway founder store.

```
[copy] rows=1282 columns=40

--- fixtures: a row for every rung of the ladder ---
[PASS] the fixtures were inserted (6 live rungs + domain + audience + 2 tombstones) — ids=[1296, …, 1305]

--- exact name first, on a real product ---
[PASS] the endpoint answers 200 (F-18) — 200
[PASS] a real product name returns that product as result #1 (F-18) — #1=['Obsidian']
[PASS] …with reason == 'Exact name match' (F-18) — 'Exact name match'
[PASS] exactly one row is an exact-name match for 'Obsidian' — 1
[PASS] an exact-name hit never sorts below a fuzzy one (F-18) — first='Exact name match' last='Similar to your search'

--- the ladder is ordered ---
[PASS] the classified rungs are non-decreasing (ladder order holds) — rungs=[0, 2, 3, 4, 4, 5, 6]
[PASS] the endpoint returns the classifier's order verbatim — endpoint order == classify_rows order
[PASS] the fixtures come back in ladder order (exact → name → tagline → desc → category) — ['Zorblat', 'Zorblat Notes', 'Tagline Zorb Co', 'Desc Zorb Co', 'Cat Zorb Co']
[PASS] a capability that only the fuzzy rung can reach lands on the fuzzy rung — [('Zorblit', 'fuzzy')]

--- the reason vocabulary is correct and stable ---
[PASS] rung 'exact name' emits 'Exact name match' — got 'Exact name match'
[PASS] rung 'exact domain' emits 'Exact domain match' — got 'Exact domain match'
[PASS] rung 'phrase / name' emits 'Name contains your search' — got 'Name contains your search'
[PASS] rung 'tagline' emits 'Tagline mentions it' — got 'Tagline mentions it'
[PASS] rung 'problem-description' emits 'Similar problem description' — got 'Similar problem description'
[PASS] rung 'fuzzy' emits 'Similar to your search' — got 'Similar to your search'
[PASS] the category rung emits 'Same category' — 'Same category'
[PASS] the audience field emits 'Same audience, different approach' (latent — nothing writes target_users today) — 'Same audience, different approach'
[PASS] every reason returned is one of the frozen vocabulary strings — []
[PASS] no reason is empty, a number, a code or an internal rung name — [8 strings, all clean]
[PASS] the plan's three verbatim examples are preserved exactly

--- dead and pivoted sink to the bottom ---
[PASS] dead AND pivoted rows sort last under an otherwise equal match — ['Zorblat Dead', 'Zorblat Pivoted']
[PASS] the tombstones are still returned, never hidden or deleted — both present in the payload
[PASS] the tombstone has the same rung/score as the live row it sinks below — dead rung=phrase/name score=0.0 live score=0.0

--- stars break ties, they never rank ---
[PASS] a 0-star exact-name match beats a 99999-star fuzzy one (F-18) — #1=Zorblat (stars=None) vs Zorblit (stars=99999, 'Similar to your search')

--- multi-term AND, scored by the worst term ---
[PASS] a two-term query returns only rows matching BOTH terms (AND, not OR) — ['Both Tokens Co']
[PASS] a row matching one term exactly and the other fuzzily still matches — 1
[PASS] the score is the WORST term's, not the average (quixzal exact=0.0, zorblat→zorblit fuzzy≈0.14) — score=0.143 (average would be ≈0.071) reason='Similar to your search'
[PASS] a row matching only one of the two terms is excluded — Quixzal Only Co absent

--- the empty-query contract ---
[PASS] no q at all → 200 with an empty list (documented contract) — 200 []
[PASS] q= (empty) → 200 with an empty list — 200 []
[PASS] q=<whitespace> → 200 with an empty list — 200 []
[PASS] the empty query never returns the whole archive — 0 vs 1282 rows

--- LIKE metacharacters stay literal ---
[PASS] q='%' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='_' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='%%' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='__' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] /api/startups?q=% stays literal (not everything) — the existing rule is untouched — 40 of 1282 (every hit really contains a '%')
[PASS] /api/startups?q=_ stays literal — 0 rows

--- search is a pure read (no capture, no evidence) ---
[PASS] a search writes no evidence row — 0 → 0
[PASS] a search queues no capture job for a never-captured competitor (F-22 contrast) — capture jobs for the competitor: 0
[PASS] a search never calls capture.start_capture (unlike /api/compare) — tripwire armed — 200, no capture attempted

--- data-awareness: the keyword rung skips empty rows ---
[PASS] the keyword rung matches the row whose teardown field is populated — 'Similar problem description'
[PASS] the row with a NULL features_json is skipped, not matched (data-aware) — 1 hit(s): ['Keyword Pop Co']
[PASS] positioning is additional evidence for the keyword rung when present — 'Similar problem description'
[PASS] a term that appears nowhere returns no rows at all — 0

--- the founder store is never searched (F-20) ---
[PASS] the founder draft was created in its own store (F-10) — 1
[PASS] no founder-store record appears in a search result (F-20) — 11 / 1 hits, none from the founder store
[PASS] search reads the archive file only (the founder store is a different file) — founder.db.phase4-test

--- timing over the whole archive (the ponytail marker, measured) ---
[PASS] a full-archive search for 'obsidian' stays under 400 ms — 28.6 ms over 1300 rows
[PASS] a full-archive search for 'markdown' stays under 400 ms — 71.8 ms over 1300 rows
[PASS] a full-archive search for 'note taking' stays under 400 ms — 95.6 ms over 1300 rows

[PASS] no frontend/ file was touched in this phase — committed=[] working=[]

RESULT: ALL PASS
```

58 checks, 0 failed. (The fixture rows live only in the throwaway copy, which is why the timing pass reports 1,300 rows.)

### 2. Reachable rungs — the census this phase owes the ledger

Counted on a **pristine** copy of the real archive, *before* any fixture is inserted, so nothing here is inflated by the test data (1,282 rows):

| Rung | Matches on | Rows it can match today |
|---|---|---|
| exact name | `name` | 1,282 / 1,282 |
| exact domain | `website_url` (host) | 1,282 / 1,282 |
| phrase / name | `name` + `aliases` | 1,282 / 1,282 |
| tagline | `tagline` | 1,256 / 1,282 |
| problem-description | `description` | 1,258 / 1,282 |
| ↳ (future column) | `problem_statement` | **0 / 1,282** |
| ↳ (future column) | `target_users` | **0 / 1,282** |
| category / keyword | `category` | 1,282 / 1,282 |
| ↳ keyword half | `features_json` | **0 / 1,282** |
| ↳ keyword half | `positioning` | **0 / 1,282** |
| fuzzy | the AND gate over the same fields | 1,282 / 1,282 |

**Every live rung can match rows today; no rung is built on a column nothing writes.** The four zero rows are exactly the ones the phase prompt named: `problem_statement` and `target_users` are written by no phase, and `features_json`/`positioning` arrive only with a JIT capture (F-22) — no competitor has been captured on the live archive yet. They are *additional evidence* inside rungs that are already live (`description`, `category`), never the rung itself, so the ladder cannot degrade into a promise the UI cannot keep. `canonical_domain` is likewise empty, which is why the exact-domain rung reads the host of `website_url`.

### 3. Sample payload (the ledger's raw evidence)

`GET /api/search?q=zorblat` on the copy, with the fixture rows (the same output the verifier prints):

```
Zorblat                rung=exact name           score=0.000  reason='Exact name match'
Zorblat Notes          rung=phrase/name          score=0.000  reason='Name contains your search'
Tagline Zorb Co        rung=tagline              score=0.000  reason='Tagline mentions it'
Audience Zorb Co       rung=problem-description  score=0.000  reason='Same audience, different approach'
Desc Zorb Co           rung=problem-description  score=0.000  reason='Similar problem description'
Cat Zorb Co            rung=category/keyword     score=0.000  reason='Same category'
Positioning Co         rung=category/keyword     score=0.000  reason='Similar problem description'
Zorblit                rung=fuzzy                score=0.143  reason='Similar to your search'
Zorblat Dead           rung=phrase/name          score=0.000  reason='Name contains your search'   <- dead, sinks
Zorblat Pivoted        rung=phrase/name          score=0.000  reason='Name contains your search'   <- pivoted, sinks
```

On the untouched live archive, `q=Obsidian` returns `#1 = Obsidian (Exact name match)` and `q=obsidian.md` returns exactly one row, reason `Exact domain match`; `q=markdown` returns two rows (`Obsidian`, `iA Writer`), both `Tagline mentions it`.

### 4. Test suites

```
cd backend
..\backend\.venv\Scripts\python.exe -m tests.smoke
RESULT: ALL PASS        (85 PASS / 0 FAIL, exit 0)
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

The smoke suite's pinned LIKE test still reads `q=% returned 0 of 12; literal returned 1` — the list endpoint's escape is untouched.

### 5. Notes recorded at Phase 4

- **The empty-query contract: 200 + `[]`.** The plan left the choice open ("an empty result with a stable shape, or an explicit 4xx"). The empty shape was chosen because the endpoint is a live search box: "no query" and "no matches" are then the same harmless state, the UI needs no special case, and the shape is stable. It is an explicit early return, never an accident of a `LIKE '%%'` — there is no SQL in the search path at all, so a metacharacter cannot become a wildcard by construction.
- **Queries are split into WORD terms, and that is also what makes `q=%` and `q=_` return nothing.** A query with no word terms (blank, whitespace, `%`, `_`, `%%`, `__`) has nothing to match and returns the empty contract. `q=%` therefore returns 0 rows here — while `/api/startups?q=%` keeps its own behaviour (a literal `%`, which on this archive matches 40 rows that really do contain one). Both are "literal, never a wildcard"; the search endpoint is simply stricter about what counts as a term.
- **The ladder maps onto columns that exist — `problem_statement`/`target_users` get no rung of their own.** A rung built on them would match zero rows forever. They are extra fields *inside* the problem rung, which is live on `description` (1,258 rows) today. The audience field keeps its frozen reason ("Same audience, different approach"), so the day a later phase starts writing `target_users` the copy already exists and the verifier already pins it.
- **One judgement call, written down so it is not re-litigated silently: the keyword half of the category/keyword rung emits "Similar problem description".** The vocabulary has no "keyword" string, and "Same category" would be false for a hit inside `features_json`/`positioning`. Those two fields are the product's own description of what it does, so the plan's own verbatim fragment is the closest true statement. The rung's *other* half (an exact `category` match) emits "Same category" as expected, and the rung is reachable either way.
- **Documented divergences from `lib/search.ts`** (the invariants — exact name first, dead/pivoted last, stars as a tie-break only, AND-across-terms with a worst-term score — are identical):
  1. the client ranks purely by Fuse score, so a strong fuzzy hit could outrank a weak phrase hit; this endpoint ranks by **rung first** (the ladder is the product requirement) and uses the score only to order within a rung;
  2. a 1–2 character term matches only a whole word here ("ai" matches the word *ai*, not the *ai* inside *email*), because a binary substring rule on one character matches most of the archive.
  The client path is untouched and stays for a small archive, as the plan requires.
- **`search.py` builds no SQL and no LIKE pattern.** That is the honest way to satisfy "a metacharacter stays literal", and it is why the module says so explicitly: any future edit that reaches for `LIKE` re-introduces the degenerate-rung risk the prompt warns about.
- **Performance is the honest linear scan, and the marker is kept.** 28–96 ms per full-archive query at 1,282–1,300 rows (measured, printed by the gate) — the same knee as the client path (`LIST_LIMIT_DEFAULT = 3000`). The `ponytail:` note in both `search.py` and the route names FTS5 + bm25 as the next step, not a bigger scan.
- **Doc drift caused by this phase — corrected in this branch.** `docs/codebase-comprehension.md` §9 (and §11's premise "Search relevance needs classification, not just ranking") described a gap whose *backend* half this phase closes: §9 now carries the Phase 4 correction and names what is still missing (the frontend that renders the reasons). §4.2 gains the route, §7 gains the Phase 4 verifier, and `docs/backend-checklist.md` F-18 records the two decisions it had left open. No other product doc was falsified.

- **Row status after Phase 4:** Phases 0–4 `PASS`; Phase 5 `pending`; Phases 6–8 stay `blocked` — the frontend remains blocked until Phase 5 is `PASS`. (Superseded by the Phase 5 section below.)

---

## Phase 5 evidence — backend functional test gate (2026-09-16)

**Branch:** `phase/05-backend-functional-gate`, cut from `main` at `850c6e9`. **Backend only** — no `frontend/` file was touched (`git diff --name-only main..HEAD -- frontend` is empty, and each of the four phase verifiers re-asserts it). This phase adds **no product feature**; it adds one suite, one runner step, one repaired verifier assertion and this entry.

**Who ran it:** the AutoClaw agent for this repo (`does-this-startup-exist`, session `agent:does-this-startup-exist:893c5a2e`) on `DESKTOP-KV8OEKP`; venv Python 3.11.15, Node 24.19.0 first on `PATH`. **Date: 2026-09-16.**

### Files changed

| File | Change |
|---|---|
| `backend/tests/functional.py` | **New.** The consolidated suite: F-01–F-24 + the §6 invariants, 187 checks, self-contained (own throwaway archive + founder store inside one temp dir; fetcher, both LLM prompts, Wayback and RDAP all stubbed; no network, never the live file). Mirrors `tests/smoke.py`'s discipline; prints `[PASS]`/`[FAIL]`, a `RESULT:` line and `TESTS: n run, n passed, n failed`; exits non-zero on any failure. |
| `scripts/verify.mjs` | One new step, `backend functional (Phase 5 gate)`, placed directly after the backend smoke suite. A comment records why the four `phaseN-verify.py` scripts are **not** wired in instead: they need the live archive and its Phase 1 backup, which a checkout on another machine will not have. |
| `scripts/phase4-verify.py` | The rung-census assertion repaired against the now-real captured state (see §Phase 5 evidence 7). |
| `docs/codebase-comprehension.md` | §7's runner line corrected: `npm test` runs **five** suites, not four. A Phase 5 note added at the top; the correction marked inline. |
| `docs/backend-checklist.md` | §7 gains the Phase 5 completion marker and the command that produces the evidence. |
| `docs/phase-ledger.md` | This entry, the Phase 5 row set to `PASS`, and Phases 6–8 moved `blocked` → `pending` **in the same commit**. |

No table, column, endpoint or product behaviour changed.

### 1. The consolidated suite — the real output

Command (from `backend/`):

```
..\backend\.venv\Scripts\python.exe -m tests.functional
```

```
==============================================================================
IdeaExists backend functional suite — Phase 5 gate
==============================================================================
[PASS] a legacy-shaped archive starts at the recorded 18 base columns (F-01) — 18 columns
[PASS] the migration knows exactly 22 new teardown columns (F-01) — 22
[PASS] the migration takes the archive 18 -> 40 columns (F-01) — 18 -> 40
[PASS] no column is dropped or renamed by the migration (F-01) — missing: []
[PASS] `founded` keeps its name (F-04 — the rename is rejected) — founded=True founded_at=False
[PASS] `date_source` sits beside `founded` (F-04)
[PASS] the two store-link columns are added (F-19)
[PASS] the first migration run really adds all 22 columns (F-01) — added 22
[PASS] the migration executes only ADD COLUMN — no DROP, no RENAME (F-01) — 23 statement(s): 1 PRAGMA table_info + 22 ALTER, nothing destructive
[PASS] re-running the migration is a no-op (idempotent) (F-01) — []
[PASS] existing rows survive the migration (F-01) — 2 rows
[PASS] a legacy `founded` value is untouched by the migration (F-01/F-04) — 2020-05-08
[PASS] existing rows default date_source to 'unknown' (F-04) — unknown
[PASS] the `evidence` table exists after the migration (F-02) — ['evidence', 'jobs', 'sqlite_sequence', 'startups', 'verify_log']
[PASS] evidence has exactly the specified columns (F-02) — ['id', 'startup_id', 'evidence_type', 'source_url', 'captured_at', 'claim', 'value', 'provenance', 'confidence', 'reviewed_at']
[PASS] evidence.source_url is NOT NULL (F-02) — notnull=1
[PASS] evidence.captured_at is NOT NULL (F-02) — notnull=1
[PASS] a source-less evidence row is refused by the writer (F-02) — SourceRequiredError
[PASS] a source-less evidence row is refused by the DB too (F-02) — NOT NULL constraint
[PASS] evidence.captured_at is auto-filled (F-02) — 2026-09-16 09:12:21
[PASS] every new column is in enrich.UPDATABLE (F-01 — the silent-drop trap) — []
[PASS] every UPDATABLE name is a real archive column (F-01) — []
[PASS] app_store_url / play_store_url are writable through the normal writer (F-19)
[PASS] an LLM-stated date is recorded as date_source='llm' (F-04) — ('2015-06-01', 'llm')
[PASS] a Wayback-derived date is recorded as date_source='wayback' (F-04) — ('2019-03-04', 'wayback')
[PASS] an RDAP-derived date is recorded as date_source='rdap' (F-04) — ('1997-10-06', 'rdap')
[PASS] with no source the date stays NULL and date_source='unknown' (F-04) — (None, 'unknown')
[PASS] date_source is one of the frozen values (F-04) — unknown
[PASS] a fresh seed is stamped provenance='machine_drafted' (F-05) — machine_drafted
[PASS] the seeded row carries date_source='unknown' when nothing stated a date (F-04/F-05) — unknown
[PASS] a human confirm flips provenance to human_confirmed (F-05) — human_confirmed
[PASS] a reuse_profile refresh does not downgrade human_confirmed (F-05) — human_confirmed
[PASS] mark_human_confirmed refuses a table outside its whitelist (F-05) — jobs refused
[PASS] a capture reports state=captured (F-06) — captured
[PASS] features_json holds 5-10 items (F-06) — 6: ['local files', 'markdown notes', 'backlinks', 'graph view', 'sync (paid)', 'publish']
[PASS] fewer than 5 supported features become unknown, never padded (F-06) — []
[PASS] more than 10 features are capped, not stored raw (F-06) — 10
[PASS] one evidence row per feature, each with a source_url (F-06) — 6 rows for 6 features
[PASS] pricing rows each carry a price and a period (F-07) — [{'name': 'Pro', 'price': '$8', 'period': 'monthly'}, {'name': 'Team', 'price': '$12', 'period': 'monthly'}, {'name': 'Enterprise', 'price': 'custom', 'period': 'annual'}]
[PASS] malformed plan rows are dropped, not stored half-formed (F-07) — ['Pro', 'Team', 'Enterprise']
[PASS] pricing_captured_at is stamped (F-07) — 2026-09-16 09:12:21
[PASS] pricing_source_url is stamped (F-07) — https://acme.example/pricing
[PASS] the free tier is captured as its own claim (F-07) — Free up to 3 docs
[PASS] one evidence row per pricing plan + the free tier (F-07) — 4 rows for 3 plans + free tier
[PASS] positioning is non-empty (F-08) — A private, local-first note app that links your thinking.
[PASS] the positioning line carries its source (F-08)
[PASS] provenance is machine_drafted until a human confirms (F-05/F-08) — machine_drafted
[PASS] every teardown evidence row is machine_drafted (F-05) — ['machine_drafted']
[PASS] teardown evidence is unknown rather than invented when a page is unreadable (F-06) — every evidence row carries a confidence
[PASS] a sourced negative traces to an enumerating page (F-09) — ['no self-host', 'no API', 'no mobile app', 'no real-time collaboration'] from ['https://acme.example', 'https://acme.example/docs', 'https://acme.example/pricing']
[PASS] no negative is derived from a guessed URL (F-09)
[PASS] the LLM's negatives survive only when they trace to a page we read (F-09)
[PASS] a deterministic probe wins over the LLM's duplicate of the same fact (F-09)
[PASS] a verdict-shaped claim is rephrased into an observation (F-09)
[PASS] a 404 on a guessed URL produces nothing at all (F-09) — guessed-record probe returned None
[PASS] the page plan never fetches a guessed capability path (F-09) — (('pricing', '/pricing'), ('docs', '/docs'))
[PASS] a negative with no enumerating source is refused, not stored (F-09) — empty source and non-enumerating source both refused
[PASS] a retrieval failure is unknown with low confidence, never a negative (F-09) — 3 unknown row(s), conf=[0.1, 0.1, 0.1]
[PASS] an unreadable page still gets a source_url (the page we tried) (F-09) — ['https://walled.example', 'https://walled.example/docs', 'https://walled.example/pricing']
[PASS] no pricing is stored when the pricing page could not be read (F-07) — pricing_json=None
[PASS] one evidence row per review, source_url = the review permalink (F-23) — 3 permalinks
[PASS] a walled provider (403) is a skip, not a failure (F-23) — skipped=1 rows=3
[PASS] positive and negative are both classified (F-23) — ['negative', 'negative', 'positive']
[PASS] no score, aggregate or NPS of our own is stored (F-23) — [['asks', 'classification'], ['asks', 'classification'], ['asks', 'classification']]
[PASS] every extracted ask links to the review it came from (F-23)
[PASS] every review evidence row is machine_drafted (F-05/F-23) — ['machine_drafted']
[PASS] URL path drafts the founder's app (F-10) — Acme Notes
[PASS] the URL path does not invent the founder's feature list (F-10) — []
[PASS] form path drafts a full teardown record (F-11) — ['local files', 'markdown notes', 'public API', 'real-time collaboration', 'export']
[PASS] a form without 5-10 features is a clear 400 (F-11) — 400/400
[PASS] agent-JSON path drafts the founder's app (F-12) — 200
[PASS] malformed agent JSON is a 400 (F-12) — malformed agent JSON: Expecting property name enclosed in double quote
[PASS] unknown agent keys are a 400, never silently dropped (F-12) — unknown key(s) in agent payload: ['invented_field']
[PASS] nothing the founder path wrote reached the archive (F-20) — 7 -> 7
[PASS] no founder record appears in /api/startups (F-20) — []
[PASS] no founder record is counted by /api/stats (F-20) — 7 vs 7
[PASS] no founder record appears in /api/categories and the facets still answer (F-20)
[PASS] the verify walk never sees the founder store (F-20) — list_suggested is archive-only
[PASS] the two stores are two files, each with its own schema (F-10/F-20)
[PASS] a link-less submission is comparison-only (F-20) — {'has_link': False, 'link': '', 'link_field': None}
[PASS] no consent question is asked when there is no link (F-20)
[PASS] a store-only link satisfies eligibility (F-19/F-20) — link_field=play_store_url
[PASS] the compare path refuses an unconfirmed founder app (F-13) — assert_comparable raised
[PASS] the endpoint refuses an unconfirmed app with an explicit 409 not_confirmed (F-13) — 409: {'state': 'not_confirmed', 'message': 'founder app 6 is not confirmed — confirm the draft before the gap table runs (confirm-before-diff)'}
[PASS] confirm flips the record to human_confirmed (F-05/F-13) — human_confirmed at=2026-09-16 09:12:22
[PASS] nothing is auto-confirmed by a draft (F-13) — all three drafts start unconfirmed
[PASS] a `publish` key on the create endpoint is refused, not ignored (F-13) — HTTP 422
[PASS] the refusal names the call that does publish (F-13)
[PASS] the refused request wrote no draft (F-13 — no partial write to retry) — 6 -> 6
[PASS] an unknown top-level key is refused too (F-12's rule, one level up) — HTTP 422
[PASS] ticking the opt-in creates a pending submission (F-13/F-24) — {'submitted': True, 'submission_id': 1, 'archive_status': 'pending'}
[PASS] the admin queue unions founder submissions with the archive's rows (F-24) — 1 founder row(s) among 7 queue rows
[PASS] approval creates the archive row and links it (F-13/F-24) — archive_startup_id=8 name=Loom-note
[PASS] the founder record keeps its own row — the archive got a twin (F-10) — archive 7 -> 8
[PASS] archive_status is derived from the newest submission (F-24) — approved
[PASS] a rejection carries a note the founder can read (F-24) — The site is behind a login, so nothing could be read.
[PASS] a rejection with no note is refused (F-24) — 400
[PASS] resubmitting after a rejection creates a NEW row, never an edit (F-24) — [(2, 'rejected'), (3, 'pending')]
[PASS] archive_status follows the newest submission (F-24) — pending
[PASS] the founder draft is readable back from its own endpoint (F-10) — GET /api/founder-app/{id}
[PASS] a re-seed does not duplicate the row (F-14) — id 5 -> 5
[PASS] a re-seed keeps the teardown fields (F-14 carve-out) — features=True pricing=True
[PASS] a re-seed never downgrades human_confirmed (F-14 carve-out) — human_confirmed
[PASS] a unique-index collision is still a clear ValueError -> 400 (F-14) — duplicate website_url refused
[PASS] compare refuses a `you` it cannot resolve (F-13/F-15) — unresolvable 'you'
[PASS] compare returns the table for a confirmed founder app (F-15/F-22) — 200
[PASS] a capability only 'you' have lands in you_have_they_dont (F-15) — public API vs 'no — no API (Acme Notes)' src=https://acme.example/docs
[PASS] that edge traces to the competitor's enumerating page (F-09/F-15) — https://acme.example/docs
[PASS] a capability only 'they' have lands in they_have_you_dont (F-15)
[PASS] a capability both have lands in both_have (F-15)
[PASS] every band is present in the payload (F-15) — ['you_have_they_dont', 'they_have_you_dont', 'both_have', 'unknown', 'asked_for']
[PASS] missing data is shown as unknown, never scored (F-15) — None
[PASS] the activity row is unknown — the 'you' side has no liveness signal (dim 6) — ['unknown']
[PASS] every non-unknown 'they' cell carries a source (cell rule 1) — []
[PASS] every row is exactly {dimension, band, you, them, source, captured_at}
[PASS] no verdict line is emitted (cell rule 5)
[PASS] a negative is only rendered from an enumerating page (F-09/F-15)
[PASS] a negative whose capability you cover is an edge (dim 5) — 'yes — declared: public API' vs 'no API (Acme Notes)'
[PASS] an unsourced doesn't-do cell renders unknown, never 'no' (cell rule 2)
[PASS] a reviewer ask neither side covers lands in asked_for (dim 7)
[PASS] the same ask, when your declared features cover it, lands in you_have_they_dont (dim 7)
[PASS] every ask links to the review it came from (F-23 -> dim 7)
[PASS] all three exports answer 200 (F-16) — 200/200/200
[PASS] Markdown has the four groups incl. the demand group (F-16) — []
[PASS] JSON is re-processable: {you, them, rows} with the right row keys (F-16) — ['rows', 'them', 'you']
[PASS] JSON 'you' is the ONE founder record the caller named (F-16 / no leak) — Loom-note
[PASS] CSV has the exact columns band, dimension, you, them, source_url, captured_at (F-16)
[PASS] CSV carries asked_for as a band value (F-16) — ['asked_for', 'both_have', 'they_have_you_dont', 'unknown', 'you_have_they_dont']
[PASS] re-running an export with the same inputs gives the same bytes (F-16)
[PASS] an unknown export format is refused (F-16) — 404
[PASS] an export never triggers a capture (F-16 — stateless, pure read)
[PASS] a known product resolves by slug (F-17) — 200 Acme Notes
[PASS] an unknown slug is a clean 404 (F-17) — 404
[PASS] a duplicate-name group resolves deterministically: verified first (F-17) — got=10 expected=10
[PASS] with no verified row the lowest id wins (F-17) — 12
[PASS] a stale last_checked reads machine_verified=false while admin_verified stays true (F-21) — machine=False admin=True
[PASS] a fresh check reads machine_verified=true (F-21) — True
[PASS] the badges are explicit fields, never inferred from a raw timestamp (F-21)
[PASS] no badge is emitted inside a claim/row cell (F-21 / §8.1)
[PASS] a never-captured competitor returns the queued/retry state (F-22) — 200: queued / capture queued
[PASS] once captured, the same call returns the table (F-15/F-22) — 200
[PASS] the search endpoint answers 200 (F-18) — 200
[PASS] a product name returns that product as result #1 (F-18) — #1=['Obsidian']
[PASS] …with reason == 'Exact name match' (F-18) — 'Exact name match'
[PASS] the classified rungs are non-decreasing (ladder order holds) (F-18) — rungs=[0, 2, 3, 4, 5, 6]
[PASS] the endpoint returns the classifier's order verbatim (F-18)
[PASS] the fixtures come back in ladder order (exact -> name -> tagline -> desc -> category) — ['Zorblat', 'Zorblat Notes', 'Tagline Zorb Co', 'Desc Zorb Co', 'Cat Zorb Co']
[PASS] a row only the fuzzy rung can reach lands on the fuzzy rung (F-18) — Zorblit -> fuzzy
[PASS] every reason is one of the frozen vocabulary strings (F-18) — []
[PASS] no reason is empty, a number, a code or an internal rung name (F-18)
[PASS] the vocabulary is frozen at the eight plan strings (F-18)
[PASS] dead AND pivoted rows sort last under an otherwise equal match (F-18) — ['Zorblat Dead', 'Zorblat Pivoted']
[PASS] the tombstones are still returned, never hidden or deleted (F-18)
[PASS] stars are a tie-break only — a 0-star exact-name hit beats a 99999-star fuzzy one — #1=Zorblat
[PASS] no q at all -> 200 with an empty list (documented contract) — 200 []
[PASS] q= (empty) -> 200 with an empty list — []
[PASS] q=<whitespace> -> 200 with an empty list — []
[PASS] q='%' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='_' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='%%' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] q='__' returns nothing rather than everything (F-18) — 200 0 rows
[PASS] a search writes no evidence row (F-18) — 0 -> 0
[PASS] a search queues no capture job for a never-captured competitor (F-22 contrast) — capture jobs for the competitor: 0
[PASS] a search never calls capture.start_capture (unlike /api/compare) (F-18) — 200, no capture attempted
[PASS] the keyword rung matches the populated row and skips the NULL one (data-aware) — 1 hit(s): ['Keyword Pop Co']
[PASS] a term that appears nowhere returns no rows at all (F-18) — []
[PASS] two concurrent captures of one competitor produce exactly one job (F-22) — jobs=1 first=queued second=in_progress
[PASS] an in-flight capture returns the explicit retry state, not a partial teardown (F-22) — message='capture in progress — retry'
[PASS] the capture job completes and records its result (F-22) — done
[PASS] a request inside the 7-day window is served from cache (F-22)
[PASS] a request outside the window re-captures (F-22) — queued
[PASS] the freshness window is 7 days, the same rhythm as VERIFY_AUTO_STALE_DAYS (F-22) — CAPTURE_STALE_DAYS=7
[PASS] a capture for an unknown competitor is an explicit not_found (F-22) — not_found
[PASS] there is no public capture-job endpoint (F-22 — job payloads are admin-gated)
[PASS] MUTATION_AUTH refuses every write endpoint without a token (403, not 404/200)
[PASS] the gate opens with the token (403 comes from auth, not a dead route) — 404
[PASS] netguard blocks loopback/private/link-local/metadata/non-http targets (SSRF guard) — all 9 blocked
[PASS] BlockedAddressError is a ValueError (existing 400/502 paths still catch it)
[PASS] q=% is a literal, not a match-everything wildcard (LIKE-escape) — q=% -> 0 rows, literal -> 1 row
[PASS] q=_ is also literal (LIKE-escape) — 0 rows
[PASS] a 403 website check SKIPS — it never strikes (tri-state liveness) — cf=0
[PASS] a 404 website check strikes — only 404/410 count (tri-state liveness) — cf=1
[PASS] a verified row is never auto-flipped or struck (human gate outranks automation)
[PASS] a >90-day-old verify_log row survives a real pass (F-03 — no retention sweep) — aged before=1 after=1 surviving row=1
[PASS] an automated pass never stamps verified=1 (the human gate is the only writer)
[PASS] the per-IP sliding window returns 429 past the bucket limit (60/min) — 404s=60 429s=5
[PASS] rate-limiter keys are evicted once their window expires — 1 key(s) during window, 0 after eviction

==============================================================================
RESULT: ALL PASS
TESTS: 187 run, 187 passed, 0 failed
```

187 checks, 0 failed, exit 0, **~2.8 s**. Four consecutive runs produced the identical summary (no ordering, thread-timing or wall-clock dependence).

### 2. The traceability table — F-01–F-24 → the check that proves it → PASS

Every row below is proven by `backend/tests/functional.py` unless the row says otherwise.

| Item | The check that proves it | Result |
|---|---|---|
| **F-01** Additive migration | A legacy 18-column archive is built and migrated: 18 → 40 columns, no column dropped or renamed, existing rows and their `founded` value untouched, the second `migrate()` returns `[]`; a SQL **trace** of the run shows 22 `ALTER TABLE … ADD COLUMN` statements and nothing destructive; every `db.NEW_STARTUP_COLUMNS` entry is in `enrich.UPDATABLE` (the silent-drop trap) and every `UPDATABLE` name is a real column | PASS |
| **F-02** Evidence table | `evidence` exists with exactly the 10 specified columns; `source_url` / `captured_at` NOT NULL; `write_evidence` refuses a source-less claim (`SourceRequiredError`) and a raw INSERT is refused by the constraint; `captured_at` auto-fills | PASS |
| **F-03** Permanent `verify_log` | A `verify_log` row stamped `-200 days` survives a full verification pass, while the pass still writes a new row per startup | PASS |
| **F-04** `founded` provenance | The column keeps its name (`founded_at` absent); `date_source` is recorded for each branch (`llm` / `wayback` / `rdap` / `unknown`); a legacy value is untouched; existing rows default to `unknown` | PASS |
| **F-05** Provenance flags | A fresh seed is `machine_drafted`; a human confirm flips it to `human_confirmed`; a `reuse_profile` refresh never downgrades it; `mark_human_confirmed` refuses a table outside its whitelist; every teardown evidence row is `machine_drafted` | PASS |
| **F-06** Feature extraction | A capture yields 6 features (5–10 bound); `<5` → `[]`, never padded; `>10` capped; one sourced evidence row per feature | PASS |
| **F-07** Pricing ingestion | Plan rows each carry a price + a period; malformed rows dropped; `pricing_captured_at` and `pricing_source_url` stamped; the free tier is its own claim; nothing is stored when the pricing page could not be read | PASS |
| **F-08** Positioning line | A non-empty one-liner, with its own sourced evidence row | PASS |
| **F-09** Negative claims | Every negative traces to an **enumerating** page; a 404 on a guessed `/api` produces nothing; the page plan never fetches a guessed path; a verdict-shaped claim is rephrased; a deterministic probe beats the LLM's duplicate; an unreadable page is `unknown` @0.1 with a source; `validate()` refuses a sourceless / non-enumerating observation | PASS |
| **F-10** Founder URL path | Drafts from the page with `features` left `[]` (never invented), stored in the founder store, not auto-confirmed, readable back by id | PASS |
| **F-11** Founder form path | Drafts a full record; a form without 5–10 features is a clear 400; a link-less submission is accepted as comparison-only | PASS |
| **F-12** Founder agent-JSON path | A valid payload drafts with both store links; malformed JSON → 400; an unknown agent key → 400; an unknown **top-level** key on create → 422 | PASS |
| **F-13** Confirm & publish gate | `assert_comparable` and `POST /api/compare` both refuse an unconfirmed app (`409 {"state": "not_confirmed"}`); nothing is auto-confirmed; consent creates a `pending` submission; a `publish` key on create is refused (422) **and writes no draft** (no partial write a retry could duplicate) | PASS |
| **F-14** Idempotency & dedup | A re-seed keeps the row id, keeps the teardown fields, never downgrades `human_confirmed`; a unique-index collision is still a clear `ValueError` → 400 | PASS |
| **F-15** Comparison | The five bands are correct for the fixture; every non-`unknown` "they" cell carries a source; an unsourced "doesn't do" cell renders `unknown`, never "no"; a negative is only rendered from an enumerating page; dimension 7's two destinations; no verdict line | PASS |
| **F-16** Exports | Markdown carries the four groups incl. the demand group; JSON is re-processable and names only the caller's `you`; CSV has the exact columns and an `asked_for` band value; re-running is **byte-identical**; an unknown format 404s; an export never triggers a capture | PASS |
| **F-17** Stable slug | A known slug resolves; an unknown slug 404s; a duplicate-name group resolves deterministically (verified first, then lowest id) | PASS |
| **F-18** Search with reasons | Exact name first; the ladder is non-decreasing; the reason vocabulary is the frozen eight; dead **and** pivoted sink last; stars are a tie-break only; multi-term AND; the empty-query contract; `%` / `_` literal; and the pure-read posture (no evidence row, no queued capture, armed tripwire) | PASS |
| **F-19** Store-link columns | Both columns are added and writable through the normal writer (`_upsert`); a **store-only** link satisfies the eligibility gate | PASS |
| **F-20** Link eligibility & containment | Link-less → `local_only` with no consent question; `/api/startups`, `/api/stats`, `/api/categories` and `verify.list_suggested` never see the founder store; the two stores are two files with two schemas | PASS |
| **F-21** Trust badges | Both badges are explicit fields (never inferred from a timestamp); a stale `last_checked` reads `machine_verified=false` while `admin_verified` stays true; a fresh check reads true; no badge ever appears in a claim/row cell | PASS |
| **F-22** Just-in-time capture | Two concurrent captures of one competitor → **exactly one** job; in-flight → the explicit retry state; inside 7 days → `cached`; outside → re-queued; an unknown id → `not_found`; no public job endpoint; `/api/compare` wiring returns queued then the table | PASS |
| **F-23** Reviews | One evidence row per review with the permalink as `source_url`; a walled provider (403) is a **skip**, never a failure or a strike; positive and negative both classified; no score/aggregate/NPS of ours stored; every extracted ask links to its review | PASS |
| **F-24** `founder_submissions` lifecycle | `pending` → approve sets `archive_startup_id`; a rejection needs a note; resubmitting is a **new row**; `archive_status` is derived from the newest row; the admin queue unions founder submissions with the archive's rows | PASS |
| **§6** invariants | MUTATION_AUTH 403s every write endpoint (and 404 with the token, so the 403 is auth and not a dead route); the SSRF guard blocks 9 non-public targets; LIKE-escape keeps `%`/`_` literal; the rate limiter 429s past 60/min and evicts expired keys; tri-state liveness (403 skips, 404 strikes); a verified row is never auto-flipped or struck; an automated pass never stamps `verified=1` | PASS |

The remaining §6 guarantees are pinned by `tests/smoke.py` and deliberately **not** copied here, per the phase brief — the six-write-endpoint matrix (it does assert all six), the failed-auth lockout (10/min then 429), the startup refusal when `MUTATION_AUTH` is on with an empty `ADMIN_TOKEN`, the three-strike dead flip and the "verified rows are protected" cases, the queue serialization / restart recovery, the pagination ceilings and the truncation contract, the category whitelist, `_http_url`'s scheme filter, and the numeric-coercion bug. `npm test` runs both suites, so nothing is lost by not duplicating them.

### 3. `npm test` — all five steps green

```
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm test

[PASS] backend smoke (exit 0)                       RESULT: ALL PASS
[PASS] backend functional (Phase 5 gate) (exit 0)   RESULT: ALL PASS
[PASS] frontend sort check (exit 0)                 RESULT: ALL PASS
[PASS] frontend lint + build (exit 0)               ✓ Compiled successfully in 3.5s
[PASS] frontend e2e verification (exit 0)           TEST RESULTS: 35 PASSED, 0 FAILED

RESULT: ALL PASS
```

Zero `[FAIL]` lines; the backend suite's own tail reads `TESTS: 187 run, 187 passed, 0 failed`.

### 4. The real-backend smoke — against the real archive

Checklist §7 item 3. Run deliberately, in the prompt's order. The script is a one-off (not part of `npm test`) and lives outside the repo's tracked tree.

**4.1 Backup first — SQLite's own backup API, never a file copy**

```
backend\.venv\Scripts\python.exe -c "import sqlite3; s=sqlite3.connect('backend/data/ideasexist.db'); d=sqlite3.connect('backend/data/ideasexist.db.bak-phase5'); s.backup(d); d.close(); s.close()"
```

`[1] backup written: ideasexist.db.bak-phase5 (1,650,688 bytes)` — same size as the live file; both are under `backend/data/`, which is git-ignored, so neither is committed.

**4.2 Boot against the real file, and the schema before/after**

`TestClient` with `DB_PATH` left at its default (`backend/data/ideasexist.db`) — the real file, not a copy. This is the **first boot since Phase 1**, so `init_db()` → `migrate()` ran against the real archive for the first time:

```
[2] [BEFORE] startups columns=18 rows=1282 tables=['jobs', 'sqlite_sequence', 'startups', 'verify_log']
[3] DB_PATH in use: E:\New-Personal-Projects\Does this Startup Exist\backend\data\ideasexist.db
[3] FOUNDER_DB_PATH in use: E:\New-Personal-Projects\Does this Startup Exist\backend\data\founder.db
2026-09-16 19:14:05,411 INFO     ideasexist: starting: mutation_auth=True rate_limit=True admin=True
[4] [AFTER BOOT] startups columns=40 rows=1282 tables=['evidence', 'jobs', 'sqlite_sequence', 'startups', 'verify_log']
...
[7] [AFTER] startups columns=40 rows=1282 tables=['evidence', 'jobs', 'sqlite_sequence', 'startups', 'verify_log']
[8] founder store tables: ['founder_apps', 'founder_submissions', 'sqlite_sequence']
```

**18 → 40 columns, the `evidence` table appearing, and the row count unchanged at 1,282** — exactly the migration Phase 1 predicted, now proven on the live file. The founder store (`backend/data/founder.db`) was created at this boot because it did not exist before; that is also a recorded state change.

**Recorded state change:** the live archive is now migrated. `backend/data/ideasexist.db.bak-phase5` is the pre-migration snapshot if that ever needs revisiting.

**4.3 The endpoints, answering with real data**

```
[5] === GET /api/health ===
{ "ok": true, "llm_model": "deepseek-v4-flash", "db": "ideasexist.db" }

[5] === GET /api/stats ===
{ "total": 1282, "verified": 1278, "dead": 0, "last_checked": "2026-09-04 15:04:08" }

[5] === GET /api/categories (top 5) ===
[ { "category": "other", "count": 302 }, { "category": "ai", "count": 222 },
  { "category": "finance", "count": 173 }, { "category": "health", "count": 165 },
  { "category": "devtools", "count": 140 } ]   ... (11 categories)

[5] === GET /api/search?q=obsidian (top 3) ===
[ { "id": 1, "name": "Obsidian", "category": "productivity", "reason": "Exact name match" },
  { "id": 566, "name": "BlueStone.com", "category": "ecommerce", "reason": "Similar to your search" },
  { "id": 503, "name": "BYJU'S", "category": "education", "reason": "Similar to your search" } ]
... (16 hits)

[5] === GET /api/startups/obsidian (badges, trimmed) ===
{ "slug": "obsidian", "resolved_id": 1, "resolved_name": "Obsidian",
  "website_url": "https://obsidian.md", "category": "productivity",
  "verified": 1, "verified_at": "2026-08-10 08:54:46",
  "last_checked": "2026-09-04 14:29:12", "status": "active",
  "admin_verified": true, "admin_verified_at": "2026-08-10 08:54:46",
  "machine_verified": false, "machine_verified_at": "2026-09-04 14:29:12",
  "duplicate_group": [ { "id": 1, "name": "Obsidian", "verified": true } ] }
```

The slug endpoint on the real archive shows F-21 exactly as specified: `admin_verified` is `true` and never decays, while `machine_verified` is `false` because the last check (2026-09-04) is 12 days old — past the 7-day window. `/api/search?q=obsidian` returns the real Obsidian row at #1 with the frozen reason string.

**4.4 The founder app, and the real JIT capture — the decision, and its cost**

**Decision: run the capture for real, on one competitor.** The competitor is **`Obsidian` (archive id 1, `https://obsidian.md`)** — a real row that had never been captured. A real founder app was drafted first (`POST /api/founder-app`, form path, `feature`-id 1, `website_url: https://phase5-smoke.example`), then confirmed, then `POST /api/compare` was called with `{"you": {"id": 1}, "competitors": [{"id": 1}]}`.

```
[6] === POST /api/founder-app (form path, real founder store) ===
{ "founder_app_id": 1, "confirmed": false, "publish_offered": true, "archive_status": "local_only" }
confirm -> True

[6] === POST /api/compare (real competitor — triggers the real JIT capture) ===
{ "state": "queued", "message": "capture queued", "startup_id": 1 }
2026-09-16 19:14:06,114 INFO httpx: HTTP Request: GET https://obsidian.md "HTTP/1.1 200 OK"
2026-09-16 19:14:06,611 INFO httpx: HTTP Request: GET https://obsidian.md/pricing "HTTP/1.1 200 OK"
2026-09-16 19:14:07,249 INFO httpx: HTTP Request: GET https://obsidian.md/docs "HTTP/1.1 404 Not Found"
2026-09-16 19:14:08,203 INFO httpx: HTTP Request: POST https://opencode.ai/zen/go/v1/chat/completions "HTTP/1.1 401 Unauthorized"
2026-09-16 19:14:09,094 INFO httpx: HTTP Request: POST https://opencode.ai/zen/go/v1/chat/completions "HTTP/1.1 401 Unauthorized"
2026-09-16 19:14:09,094 WARNING ideasexist: capture 1: teardown LLM failed (LLM call failed after retries:
    Client error '401 Unauthorized' for url 'https://opencode.ai/zen/go/v1/chat/completions') — fields stay unknown
2026-09-16 19:14:09,411 INFO httpx: HTTP Request: GET https://www.reddit.com/search.json?q=obsidian.md&sort=relevance&limit=25 "HTTP/1.1 403 Blocked"
2026-09-16 19:14:10,469 INFO httpx: HTTP Request: GET https://www.reddit.com/search.rss?q=obsidian.md&sort=relevance&limit=25 "HTTP/1.1 200 OK"

[6] capture job 108d2350fc5b: status=done ok=1 skipped=0 failed=0 errors=[]  (6.0s)
[6] job result:
{ "state": "captured", "features": 0, "plans": 0, "positioning": false, "negatives": 3,
  "evidence_rows": 3, "reviews": 0, "reviews_skipped": 1, "asks": 0,
  "unknown": ["features", "pricing", "positioning"],
  "pages": { "homepage": { "url": "https://obsidian.md", "state": "readable", "reason": "" },
             "pricing":  { "url": "https://obsidian.md/pricing", "state": "readable", "reason": "" },
             "docs":     { "url": "https://obsidian.md/docs", "state": "unreadable", "reason": "HTTP 404" } } }

[6] === POST /api/compare, second call (should now serve the table) ===
{ "you": "Phase 5 Smoke App", "competitors": ["Obsidian"],
  "bands": { "you_have_they_dont": 6, "they_have_you_dont": 0, "both_have": 2, "unknown": 4, "asked_for": 0 } }
    [you_have_they_dont] Features | you='local files' | them='not in their feature list (Obsidian)' | src=https://obsidian.md
    [you_have_they_dont] Features | you='markdown notes' | them='not in their feature list (Obsidian)' | src=https://obsidian.md
    [both_have] What it doesn't do | them='no self-host (Obsidian)' | src=https://obsidian.md/pricing
    [both_have] What it doesn't do | them='no mobile app (Obsidian)' | src=https://obsidian.md
    [unknown] Pricing | you='Pro $8/monthly' | them='unknown' | src=
    [unknown] Free tier | you='Free up to 3 docs' | them='unknown (Obsidian)' | src=
```

**Cost:** one page-plan fetch (3 URLs) plus up to two LLM attempts, **6.0 s** wall clock, the whole capture job. No verify pass was triggered: `VERIFY_AUTO_STALE_DAYS` was pinned to `0` for the smoke, because the archive's last check is 2026-09-04 and the default (7) would have enqueued a **real liveness walk over all 1,282 rows — 1,282 outbound requests**. That walk is not what this gate proves; the choice is recorded here rather than left implicit.

**The teardown written to the real archive for `Obsidian` (id 1):**

```
{ "name": "Obsidian", "features_json": "[]", "pricing_json": null,
  "pricing_captured_at": null, "pricing_source_url": null, "positioning": null,
  "provenance": "machine_drafted", "date_source": "unknown" }

evidence rows: [{"evidence_type": "negative", "c": 3}]
    [negative  ] no self-host                conf=0.8 src=https://obsidian.md/pricing
    [negative  ] API: unknown                conf=0.1 src=https://obsidian.md/docs
    [negative  ] no mobile app               conf=0.8 src=https://obsidian.md
```

**State the archive is left in, stated plainly.** The capture **succeeded as a job and wrote real evidence**, but it is **partial by cause of a credential failure, not a code failure**: the LLM gateway (`opencode.ai/zen/go`) answered **401 Unauthorized** to both attempts, so the model-drafted fields — `features_json`, `pricing_json`, `positioning` — are empty/`[]` and the job reports them as `unknown`. The **deterministic** half ran perfectly against the real pages: three sourced negative observations (the pricing page lists no self-host tier; the home page's own links list no App Store / Google Play link; the docs URL 404s so the API question is `unknown` at confidence 0.1, which is the honest answer rather than "no"). Reddit's `.json` endpoint returned 403 (a skip), the RSS feed returned 200 with no matching items, so no review rows were written. Provenance is `machine_drafted`; `date_source` stays `unknown`.

That is a **coherent, honest** end state, not a corrupt one: the row now renders `unknown` cells rather than inventing anything, and the three negative rows are genuine citations a reader can open. The archive was **not** left half-written in the dangerous sense — there is no partially-populated teardown claiming to be complete. Two consequences worth recording for the owner:

1. **`OPENCODE_GO_API_KEY` in `backend/.env` is rejected by the gateway (401).** Every LLM-drafted path — the teardown capture *and* the seed profiling — is therefore dead until that key is replaced. It does not fail the Phase 5 gate (this gate's evidence is the offline suite plus the endpoints answering), but it must be fixed before Phase 6 can demo a real teardown, and it means a real product capture today yields `unknown` for features/pricing/positioning.
2. Because a capture that wrote evidence counts as a cache entry (F-22), `Obsidian` will read `cached` for 7 days. Re-capturing it with a working key means waiting out the window or re-triggering after the evidence ages — the designed behaviour, recorded here so it is not mistaken for a bug.

**4.5 The markdown export, on the real pair**

```
[6] === GET /api/export/markdown (real pair, head) ===
HTTP 200, 1601 bytes
    # Gap table — Phase 5 Smoke App vs Obsidian

    _You: Phase 5 Smoke App. Competitor(s): Obsidian._

    ## You have — they don't

    | Dimension | You | Competitor | Source |
    |---|---|---|---|
    | Features | local files | not in their feature list (Obsidian) | https://obsidian.md |
    | Features | markdown notes | not in their feature list (Obsidian) | https://obsidian.md |
```

**Final live-archive state (read back afterwards):**

```
cols: 40 rows: 1282
tables: ['evidence', 'jobs', 'sqlite_sequence', 'startups', 'verify_log']
evidence rows total: 3
rows with features_json populated: 1        (Obsidian, "[]")
rows with provenance set: 1                 (Obsidian, machine_drafted)
rows with date_source <> 'unknown': 0
capture jobs: {'id': '108d2350fc5b', 'status': 'done', 'ok': 1, 'failed': 0}
founder_apps: Phase 5 Smoke App (form, human_confirmed, confirmed_at 2026-09-16 09:14:50)
founder_submissions: 0
```

Nothing else in the archive changed: still 1,282 rows, still 1,278 verified, still 0 dead.

### 5. The four per-phase verifiers — still green on this branch

```
backend\.venv\Scripts\python.exe scripts\phase1-verify.py   -> RESULT: ALL PASS   (31 checks)
backend\.venv\Scripts\python.exe scripts\phase2-verify.py   -> RESULT: ALL PASS   (74 checks)
backend\.venv\Scripts\python.exe scripts\phase3-verify.py   -> RESULT: ALL PASS   (47 checks)
backend\.venv\Scripts\python.exe scripts\phase4-verify.py   -> RESULT: ALL PASS   (59 checks)
```

They still need the live archive (and `ideasexist.db.bak-phase1`) to exist — expected, and documented in `scripts/verify.mjs` and in §7 of `docs/codebase-comprehension.md`. They remain the audit evidence for Phases 1–4; the new suite is the continuous gate.

### 6. Findings raised by the gate itself

Two checks went red while this phase was being built. Both were investigated rather than worked around, and neither was made green by weakening a check.

**Finding 1 — my own check was wrong, and was fixed as a check, not as a code change.** The first draft asserted "the migration source contains no DROP and no RENAME" by grepping `db.migrate`'s source text — which trips over the function's own docstring ("Never DROP, never RENAME"). Replaced with a real check: a SQLite trace callback records every statement `migrate()` actually executes against a fresh legacy DB, and the assertion is that all 23 statements are exactly 1 `PRAGMA table_info` + 22 `ALTER TABLE … ADD COLUMN`, with no `DROP` and no `RENAME` anywhere. Strictly stronger than what it replaced.

**Finding 2 — my fixture was wrong, and the app was right.** Two seeded reviews were both classified `negative`, so the F-23 check "positive and negative are both classified" failed. That was the classifier behaving correctly (`reviews.classify` treats an ask as an unmet need, and both fixtures contained "wish"). The fixture gained a third review ("Works well for our team") so the check exercises both labels, as §9 of the teardown spec intends. No product code changed.

### 7. Audit-trail maintenance — `phase4-verify.py` was repaired, not weakened

`phase4-verify.py` asserts a reachable-rung census and, in its original form, that `problem_statement`, `target_users`, `features_json` and `positioning` are **all 0 rows** — an assertion that was true of the archive as it stood in Phase 4, and stopped being true the moment **this phase's own real-instance proof ran a real JIT capture** on the live archive (F-22 legitimately populates `features_json` / `positioning` for a competitor a founder actually requested — `search.py`'s docstring says exactly that).

Rather than let the audit trail rot, the assertion was stated precisely:

* `problem_statement` / `target_users` are written by **no code path at all** — still asserted at 0 rows, unchanged;
* `features_json` / `positioning` are asserted to be populated on **no row that the JIT capture did not actually run on** (no populated row without teardown evidence) — measured on the pristine copy, before the verifier's own fixtures are inserted.

That is a *stronger* statement about the columns that matter and it is again true of the real archive (1 populated row, and it has evidence behind it). Check count went 58 → 59. This is the same posture as Phase 3's union fix: a gate that passes because a check was softened is worse than a red gate.

### 8. Doc corrections made in this branch

* `docs/codebase-comprehension.md` §7 said `npm test` "runs four suites". It now runs **five** — `tests/functional.py` was added to the runner. Corrected inline and marked, with a Phase 5 note at the top of the document.
* `docs/backend-checklist.md` §7 gains the Phase 5 completion marker and the command that produces the evidence.
* No other product doc was falsified by this phase. (`docs/handoff.md` and the planning documents are local-only and untracked by decision.)

### 9. Phase 5 notes

* **What this phase did and did not do.** It added no product feature, no table, no column and no endpoint. It consolidates F-01–F-24 into one suite that runs on every `npm test`, in the same commit that flips the phase row — so from here on, "the backend is done" is re-checked by the runner rather than asserted.
* **Why the suite is self-contained rather than a thin wrapper over the four verifiers.** Those verifiers are the *recorded evidence* for Phases 1–4 and they work on a copy of the live archive plus `ideasexist.db.bak-phase1`. Neither exists on a fresh checkout, so wiring them into `npm test` would make the runner fail for environmental reasons on any other machine. `functional.py` builds its own legacy archive from scratch (so the F-01 migration is exercised against a real 18-column DB without the live file) and stubs the fetcher, both LLM prompts and both date sources.
* **The suite is offline by construction, and that is enforced by stubbing, not by hope.** `netguard.safe_get` is replaced by a lookup table; anything not in the table 404s. `llm.llm_json` is replaced by one stub serving both prompts. Wayback and RDAP return `None`. There is no code path from this suite to the network.
* **Determinism over speed was not traded.** 187 checks in ~2.8 s, and four consecutive runs produced byte-identical summary lines. The only concurrency in the suite is the F-22 "two concurrent captures → one job" check, which uses explicit events rather than sleeps.
* **One caveat recorded for the owner:** the smoke ran with `VERIFY_AUTO_STALE_DAYS=0` (see 4.4). Under the default configuration, a boot of this archive would immediately enqueue a real verification pass over all 1,282 rows. That is the product working as designed — but it means "start the app and curl it" costs 1,282 outbound requests on this archive, which is worth knowing before Phase 6's manual testing.
* **Row status after this phase:** Phases 0–5 `PASS`; Phases 6–8 moved from `blocked` to `pending` **in the same commit as the Phase 5 row**, so the frontend unlock is part of the audited change. Phase 9 stays `pending`.

---

## Post-gate addition — LLM gateways in the admin panel (2026-09-16)

**Not a phase.** This landed after Phase 5 was set to `PASS`, on the owner's explicit request, and the phase rows above are unchanged by it: Phases 0–5 stay `PASS`, Phases 6–8 stay `pending`. It adds no new `F-` item and changes no existing one; `F-01`–`F-24` all still pass.

**Branch:** `feat/llm-gateway-settings`, cut from **`phase/05-backend-functional-gate`** rather than `main` — the same deviation Phase 2 recorded, for the same reason: Phase 5's PR (#11) is still open, so `main` does not yet contain the consolidated suite this change extends (`backend/tests/functional.py`). The PR is stacked on #11 and retargets to `main` once #11 merges.

**Backend only** — no `frontend/` file touched.

### What the owner asked for

The LLM provider was hardcoded: one base URL, one model, one key, read from `backend/.env` at import. The request was to be able to switch between **OpenCode Go, OpenCode Zen, OpenRouter, Google Gemini and Command Code** from the admin panel settings, without editing `.env` and restarting.

### What shipped

| File | Change |
|---|---|
| `backend/app/gateways.py` | **New** (~520 lines). The provider registry (five entries: id, label, base URL, env-var names, default + suggested models, docs link, notes), the admin-managed settings store in its own SQLite file, the runtime resolver, and the connectivity probe. |
| `backend/app/config.py` | `SETTINGS_DB_PATH` (its own file, mirroring `FOUNDER_DB_PATH`); the `LLM_*` comment now says those three values describe the **default** gateway rather than the only one. |
| `backend/app/llm.py` | `llm_json` resolves the active gateway **per call** (`gateways.resolve()`) instead of reading `config.LLM_*` at import, so a switch needs no restart. The key rides in `Authorization` only; the retry policy, prompt handling and error contract are unchanged. |
| `backend/app/main.py` | Six admin routes under `/api/admin/settings`, two request models, and `gateways.init_settings_db()` at boot. |
| `backend/tests/smoke.py`, `backend/tests/functional.py` | Both pin `SETTINGS_DB_PATH` into their throwaway temp dir — the same protection `FOUNDER_DB_PATH` already had, so a test run can never read or write a real settings file (which holds API keys). |
| `backend/tests/functional.py` | A new section covering the surface: **187 → 219 checks**. |
| `backend/.env.example` | Documents `SETTINGS_DB_PATH` and the four optional per-gateway env fallbacks. |
| `docs/llm-gateways.md` | **New.** The operator notes plus the full frontend contract (endpoints, JSON shapes, suggested `lib/api.ts` functions, the panel section's behaviour, and what is deliberately excluded). This is the document the frontend agent works from. |
| `docs/codebase-comprehension.md` | §4.2 gains the six routes, §7 gains the coverage note, §8's LLM row now names `gateways.py` and the five selectable providers; a post-gate note at the top marks all three. |

### The design decisions worth recording

- **Resolution order is settings → environment → registry default, resolved per call.** That is what makes the change additive: with an empty settings store and today's `.env`, the resolved gateway is exactly the one `config.py` has always described, so nothing about the current install changes and no migration is needed. It is also why a switch takes effect immediately — including on the next call inside a seed that is already running.
- **The settings live in their own file (`backend/data/settings.db`).** API keys are secrets, and the archive file is copied around, backed up and shared — the four phase verifiers copy it routinely. Keeping keys out of it is the same reasoning that put the founder's app in its own file, with a stronger motive.
- **A stored key is write-only.** No response ever contains it; the API returns `has_key`, `key_source` and a 4-character `key_hint`. Keys shorter than 12 characters report the literal `set` instead of a hint, because 4 characters of an 8-character key is half the key.
- **No query-parameter auth, ever — including for Gemini.** Gemini's native API takes `?key=…`, which would put the secret in a URL and therefore into logs and exception text. The gateway uses Gemini's OpenAI-compatible surface with a bearer token instead, and the module documents why there is no opt-in.
- **A gateway cannot be made active unless it is `ready`** (has a key and a model). The refusal is a `400` naming the missing piece. A switch that silently breaks every seed and capture is worse than a refusal.
- **The `Test` endpoint is a result, never a 500,** and it never opens a socket when there is nothing to test (a keyless gateway short-circuits). It works on a gateway that is not active, so a key is verifiable before it is switched in.
- **One flag was removed before shipping.** An earlier draft stored an `enabled` per gateway; nothing read it, so it was deleted rather than shipped as a knob that does nothing. The functional suite asserts an unknown body field is refused (`422`), which is now the guard against exactly that kind of drift.

### Verification

```
cd backend
..\backend\.venv\Scripts\python.exe -m tests.functional
=> RESULT: ALL PASS
   TESTS: 219 run, 219 passed, 0 failed        (exit 0; was 187 before this change)

..\backend\.venv\Scripts\python.exe -m tests.smoke
=> RESULT: ALL PASS

npm test   (five steps: smoke · functional · sort check · lint+build · e2e)
=> RESULT: ALL PASS
```

All four `scripts/phaseN-verify.py` re-run unchanged: 31 / 74 / 47 / 59 checks, `RESULT: ALL PASS` for each — this change does not touch the archive schema, the capture path or the search path, and the verifiers confirm it.

**One finding while building this, recorded because it is the kind of thing that hides:** the first draft of the request-shape check asserted `llm_json` posts to the active gateway's URL, but the suite stubs `llm.llm_json` globally for its own offline checks — so the new check was silently exercising the stub and could never have failed. The suite now keeps a handle on the real function before stubbing it, and the check restores it for that one assertion. A check that cannot fail is worse than no check.

**Date and who ran it:** 2026-09-16, the AutoClaw agent for this repo (`does-this-startup-exist`) on `DESKTOP-KV8OEKP`.
