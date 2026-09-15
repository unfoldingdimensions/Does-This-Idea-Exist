# Backend Feature & Verification Checklist

**Purpose:** the single source of truth for *"is the backend fully working?"* The Phase 5 gate is PASS only when every item here has a test that passes and recorded evidence.
**Read with:** `IMPLEMENTATION-PLAN.md` (phases) · `reworked-revamp-plan.md` §10–§12 · `docs/teardown-spec.md`.

Each feature is itemized as: **behaviour → inputs → outputs → acceptance check → test id**. Test ids `F-xx` map to the functional suite in Phase 5.

---

## 1. Schema & evidence foundation (Phase 1)

### F-01 Additive migration
- **Behaviour:** apply new columns + `evidence` table without dropping or rewriting existing rows.
- **Inputs:** a copy of the live `ideasexist.db`.
- **Outputs:** migrated DB; `PRAGMA table_info(startups)` shows the new columns; `evidence` table exists.
- **Acceptance:** row count unchanged after migration (1,282 expected baseline); no `DROP`/`ALTER ... RENAME` in the migration; re-running is a no-op (idempotent).

### F-02 Evidence table
- **Behaviour:** `evidence(id, startup_id, evidence_type, source_url, captured_at, claim, value, provenance, confidence, reviewed_at)`.
- **Outputs:** rows written with `source_url` + `captured_at` for every claim.
- **Acceptance:** an evidence row cannot be written without `source_url` (rejected or flagged); `captured_at` auto-filled.

### F-03 Permanent verify_log
- **Behaviour:** the 90-day retention sweep in `verify.py` is removed.
- **Acceptance:** a `verify_log` row older than 90 days survives a verification pass.

### F-04 `founded` fix
- **Behaviour:** `founded_at` + `date_source` replace the single `founded`; RDAP/Wayback-derived dates are marked `approximate`, never presented as a founding year.
- **Acceptance:** a seeded row whose date came from RDAP has `date_source='rdap'` (or equivalent) and the API no longer claims it as the founding year.

### F-05 Provenance flags
- **Behaviour:** every LLM-drafted field (`tagline`, `description`, `category`, `features`, `positioning`, `founded`) is marked `machine_drafted` until a human confirms.
- **Acceptance:** a fresh seed has `provenance='machine_drafted'` on generated text; a human confirm flips it.

---

## 2. Enrichment & teardown fields (Phase 2)

### F-06 Feature extraction
- **Behaviour:** `seed_from_website`/`seed_from_github` populate `features_json` (flat 5–10 items).
- **Inputs:** a homepage/repo URL.
- **Outputs:** `features_json` list; one `evidence` row per feature.
- **Acceptance:** 5–10 features; each feature has a source; an empty source list → `unknown`, not a guessed list.

### F-07 Pricing ingestion (plan-by-plan)
- **Behaviour:** `pricing_json` holds plan rows `{name, price, period, free_tier}` with `pricing_captured_at` + `pricing_source_url`.
- **Inputs:** a pricing page URL.
- **Outputs:** plan-by-plan rows; capture date.
- **Acceptance:** the free-tier flag is correct; every plan row has a price/period; capture date is present and surfaced by the API.

### F-08 Positioning line
- **Behaviour:** `positioning` holds a one-line sourced description.
- **Acceptance:** non-empty after seed; carries a source.

### F-09 Negative-claim capture (the strict one)
- **Behaviour:** record sourced "does not do X" claims (evidence_type `negative`).
- **Acceptance:** a negative claim **without** a source is refused (or stored as `unknown`) and never printed as fact; a sourced negative claim ("pricing page lists no free tier") is stored with `source_url`.

### F-10 Founder-app capture — URL path
- **Behaviour:** `POST /api/founder-app {url}` reuses the website seed path to draft the founder's own app.
- **Outputs:** a draft profile (same `startups` shape, flagged as the founder's app).
- **Acceptance:** returns drafted fields; does not auto-confirm.

### F-11 Founder-app capture — form path
- **Behaviour:** `POST /api/founder-app {form fields}` with a required flat feature list.
- **Inputs:** name, description, target_user, category, features (5–10), pricing.
- **Acceptance:** rejected with a clear 400 if `features` is missing or <5; accepted otherwise.

### F-12 Founder-app capture — agent-JSON path
- **Behaviour:** `POST /api/founder-app {json}` accepts the exact agent-prompt shape from `docs/teardown-spec.md` §3.
- **Acceptance:** valid JSON → draft; malformed/unknown keys → 400; invented fields are not silently accepted.

### F-13 Founder-app confirm
- **Behaviour:** `POST /api/founder-app/{id}/confirm` flips the draft to confirmed.
- **Acceptance:** compare/gap-table refuses an unconfirmed founder app (returns an explicit "not confirmed" state).

### F-14 Idempotency & dedup preserved
- **Behaviour:** `reuse_profile` still skips the LLM for known URLs; unique-index collisions still 400.
- **Acceptance:** re-seeding the same URL does not duplicate; the existing dedup tests stay green.

---

## 3. Comparison, gap table & export (Phase 3)

### F-15 Comparison endpoint
- **Behaviour:** `POST /api/compare {founder_app_id, competitor_ids[]}` (≤3) returns the three-band gap table.
- **Outputs:** `you_have_they_dont`, `they_have_you_dont`, `both_have`, `unknown`, each row `{dimension, you, them, source, captured_at}`.
- **Acceptance:** bands are correct for fixtures; an unsourced "doesn't do" cell renders `unknown`, not "no".

### F-16 Export — Markdown / JSON / CSV
- **Behaviour:** `GET /api/export/{format}` returns the comparison in the shapes in `docs/gap-table-format.md` §5.
- **Acceptance:** each format parses; Markdown has the three bands; CSV has the right columns; JSON is re-processable.

### F-17 Stable slug endpoint
- **Behaviour:** `GET /api/startups/{slug}` returns one product by slug.
- **Acceptance:** `/api/startups/obsidian` returns the Obsidian record; unknown slug → 404.

---

## 4. Search classification & match reasons (Phase 4)

### F-18 Search with reasons
- **Behaviour:** `GET /api/search?q=…` returns classified matches in order (exact name → domain → phrase → tagline → problem → category → fuzzy), each with a `reason`.
- **Acceptance:** exact name first; reasons are correct strings; stars are tie-break only; dead/pivoted sink last; empty query returns the contract (no crash).

---

## 5. Unchanged invariants that must keep passing

These are the existing human-gate/verification guarantees — the functional suite must assert them **still** hold after the new work:

- Human `verified` stamp is the only bulk writer of `verified=1`; automation never stamps.
- Tri-state liveness: only 404/410 counts; 403/429/5xx are skips; 3 strikes → `dead`; never deleted.
- Verified rows are protected from automation.
- `MUTATION_AUTH` gating, rate limits, SSRF guard, LIKE-escape — unchanged and tested.

---

## 6. Phase 5 gate — what must be recorded before frontend starts

The orchestrator records in `docs/phase-ledger.md`:

1. `F-01`–`F-18` + the invariants above: **all tests pass, failed = 0**.
2. The command run and its actual output (e.g. `python -m tests.functional` with the pass/fail summary).
3. A **real-backend smoke**: the dev backend is started against the real DB and the new endpoints return real responses (pasted sample output, not an assertion).
4. Date + who ran it.

Only after those four are in the ledger does Phase 6 (frontend) move from `blocked` to `running`.
