# Phase 1 Prompt — Schema & Evidence Foundation

Copy everything below the line into a fresh chat that is running **inside this repo** (`E:\New-Personal-Projects\Does this Startup Exist`).

---

You are the implementer for **IdeaExists**, executing **Phase 1** of the backend-first implementation plan. Work only on the backend; do not touch the frontend.

## Standing rule (applies to this and every phase)
Work on a branch off `main` — never commit to `main` directly. At the end, push your branch and open a pull request into `main` with a clear title and description. Use Conventional Commits, and include AI attribution on every commit:

```
Co-Authored-By: <your model name and attribution byline>
```

## Step 0 — orient (do not skip)
Read these files first, in this order:
1. `IMPLEMENTATION-PLAN.md` — the Phase 1 section.
2. `docs/backend-checklist.md` — items F-01 through F-05.
3. `docs/codebase-comprehension.md` — §3 (data model) and §10 (technical debt).
4. `backend/app/db.py` (current schema) and `backend/app/verify.py` (the 90-day retention sweep to remove).

## Git setup
```
git fetch && git checkout main && git pull
git checkout -b phase/01-schema-evidence-foundation
```

## The work (backend only)

Additive migration, no data loss. The current schema is in `backend/app/db.py`; it is `CREATE TABLE IF NOT EXISTS` and additive-only by policy.

### F-01 — Additive migration
Add these columns to `startups` (all nullable; existing rows keep their values):
- `entity_type` (TEXT) — `product | company | project | repository | domain | unknown`
- `canonical_domain` (TEXT)
- `aliases` (TEXT — JSON list)
- `problem_statement` (TEXT)
- `target_users` (TEXT)
- `product_url` (TEXT), `docs_url` (TEXT), `demo_url` (TEXT)
- `pricing_json` (TEXT — JSON plan-by-plan)
- `pricing_captured_at` (TEXT), `pricing_source_url` (TEXT)
- `features_json` (TEXT — JSON flat list)
- `positioning` (TEXT)
- `content_notes` (TEXT)
- `activity_checked_at` (TEXT), `activity_summary` (TEXT)
- `last_human_reviewed_at` (TEXT), `review_notes` (TEXT)
- `provenance` (TEXT) — `machine_drafted | human_confirmed | sourced | unknown`, applied to LLM-drafted text fields

The migration must be **idempotent** (re-running is a no-op) and must **not** use `DROP`, `ALTER ... RENAME`, or rewrite any existing row.

### F-04 — Fix `founded`
Replace the single `founded` field with `founded_at` (TEXT) plus `date_source` (TEXT: `llm | wayback | rdap | human | unknown`). Preserve existing values by copying `founded` → `founded_at` and setting `date_source='unknown'` where it cannot be determined. RDAP/Wayback-derived dates must be marked `approximate`, never presented as a founding year.

### F-02 — `evidence` table
Create exactly:
```
evidence(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  startup_id INTEGER NOT NULL,
  evidence_type TEXT NOT NULL,   -- e.g. feature, pricing, positioning, negative, repo_created, homepage_claim, wayback_first, reachability, curator_confirmation
  source_url TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  claim TEXT,
  value TEXT,
  provenance TEXT,
  confidence REAL,
  reviewed_at TEXT
)
```
`source_url` and `captured_at` are required — an evidence row cannot be written without a source.

### F-03 — Permanent `verify_log`
In `backend/app/verify.py`, remove the 90-day retention sweep so `verify_log` rows are never pruned.

### F-05 — Provenance flags
Add a helper that stamps any LLM-drafted text field (`tagline`, `description`, `category`, `features`, `positioning`, `founded`) as `provenance='machine_drafted'` until a human confirms it. No generated text may be written without a provenance marker.

## Verification you must record (the exit gate)

1. **Back up first:** `copy backend\data\ideasexist.db backend\data\ideasexist.db.bak-phase1`.
2. Run the migration against a **copy** of the live DB and confirm:
   - row count unchanged (expect ~1,282),
   - `PRAGMA table_info(startups)` shows the new columns,
   - the `evidence` table exists,
   - a `verify_log` row older than 90 days survives a pass (F-03).
3. Run the backend test suite: `python backend/tests/smoke.py` (or `npm test`) — it must stay green.
4. Update `docs/phase-ledger.md`: set Phase 1 to `PASS` with the evidence (command + output summary + date).

## Done-when
- Branch `phase/01-schema-evidence-foundation` is pushed and a PR is open into `main` (title `Phase 1: schema & evidence foundation`).
- The migration is verified on a DB copy with no row loss.
- The smoke suite is green.
- `docs/phase-ledger.md` Phase 1 row is `PASS` with evidence.

## Do not
- Touch anything under `frontend/`.
- Commit to `main`.
- Run the migration against the live DB without a backup.
- Drop, rename, or rewrite existing data.
- Start any Phase 2+ work.
