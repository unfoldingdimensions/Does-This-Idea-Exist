# IdeaExists — Implementation Plan (Backend-First)

**Version:** 1.0 · **Date:** 2026-09-15
**Author role:** this file is written so a **new orchestrator chat** can pick it up cold and drive delivery phase by phase, with no memory of this conversation.
**Stack (already fixed by the repo, not a placeholder):** backend = Python 3.11 + FastAPI + stdlib SQLite (WAL); frontend = Next.js 16 (App Router) + React 19 + Tailwind v4 + shadcn/ui; tests = `backend/tests/smoke.py` (in-process, no network) + `scripts/sort-check.ts` + `scripts/e2e-verify.mjs`, run via `npm test`.

---

## 0. How to use this plan (read first)

- **Read these before starting:** `docs/codebase-comprehension.md` (what exists), `reworked-revamp-plan.md` (what to build and why), `docs/teardown-spec.md` + `docs/gap-table-format.md` (the exact teardown input/output), `docs/backend-checklist.md` (the itemized backend feature + test spec).
- **The non-negotiable rule:** the phases run in this exact order — **backend build → backend functional tests → frontend build → frontend tests → full end-to-end test.** No frontend code is written, and no frontend task is scheduled, until the **Phase 5 gate** is marked PASS.
- **The ledger:** every phase writes its result to `docs/phase-ledger.md` (created in Phase 0) with `status | evidence | date`. Gating decisions are made *only* from that ledger, never from memory.
- **Git & delivery (standing rule):** every phase is implemented on a branch off `main` (`phase/<NN>-<slug>`) and delivered as its own pull request into `main` — never a direct commit to `main`. Conventional Commits + AI attribution (`Co-Authored-By`). Phase prompts live in `docs/prompts/` and embed this rule.
- **Done-when:** the ledger shows PASS on Phases 1–8, with evidence, and the end-to-end test (Phase 8) records a green run.

---

## 1. Phase list at a glance (strict order)

| # | Phase | Blocked until | Exit gate (what makes it PASS) |
|---|---|---|---|
| 0 | Orchestrator onboarding & baseline | — | docs read; ledger created; baseline recorded |
| 1 | Backend: schema & evidence foundation | Phase 0 | migration applies cleanly to a copy of the real DB; schema matches spec; smoke tests green |
| 2 | Backend: enrichment & teardown fields | Phase 1 | a seeded site yields sourced features/pricing/positioning/negative claims + evidence rows |
| 3 | Backend: comparison, gap table & export | Phase 2 | compare two fixtures → correct three-band gap table + MD/JSON/CSV exports |
| 4 | Backend: search classification & match reasons | Phase 1 | search endpoint returns classified matches with per-result reasons |
| 5 | **Backend functional test gate** | Phases 1–4 | full functional suite green; evidence captured in ledger; **frontend unblocked** |
| 6 | Frontend implementation | **Phase 5 PASS** | teardown UI, founder-app input, gap table, export, stable routes — all wired to the verified backend |
| 7 | Frontend tests | Phase 6 | user flows + visual + a11y + integration tests green |
| 8 | Full end-to-end test | Phase 7 | complete seed→verify→teardown→gap→export loop green, results recorded |
| 9 | Handoff & close-out | Phase 8 | ledger complete; release notes written |

**Frontend phases (6, 7, 8) are explicitly blocked until Phase 5 is PASS.** If Phase 5 fails, work stays in Phases 1–4 until it passes.

---

## 2. Phase details

### Phase 0 — Orchestrator onboarding & baseline
**Goal:** a fresh orchestrator can prove it understands the code and set up the audit trail.
**Tasks:**
1. Read `docs/codebase-comprehension.md`, `reworked-revamp-plan.md`, `docs/teardown-spec.md`, `docs/gap-table-format.md`, `docs/backend-checklist.md`.
2. Run `python backend/tests/smoke.py` (or `npm test`) and record the current pass/fail as the baseline.
3. Query the live DB and record baseline counts (expect ~1,282 filings / 1,278 verified / 0 dead / 57 repos).
4. Create `docs/phase-ledger.md` with the table in §1 and all rows set to `pending`.
**Exit gate:** the ledger exists with baseline rows filled; the current smoke result is recorded.

### Phase 1 — Backend: schema & evidence foundation
**Goal:** make the data model able to hold the teardown. **No feature UI yet.**
**Tasks (all in `backend/app/db.py` + a migration helper):**
1. Additive migration adding the columns from `reworked-revamp-plan.md` §10: `entity_type`, `canonical_domain`, `aliases`, `problem_statement`, `target_users`, `product_url`, `docs_url`, `demo_url`, `pricing_json`, `pricing_captured_at`, `pricing_source_url`, `features_json`, `positioning`, `content_notes`, `activity_checked_at`, `activity_summary`, `last_human_reviewed_at`, `review_notes`, and a `provenance` flag for the LLM-drafted text fields.
2. Split `founded` into `founded_at` + `date_source` (or, minimally, add `date_source` and stop presenting RDAP dates as founding years) per `reworked-revamp-plan.md` §7.
3. Create the `evidence` table exactly as specified: `id, startup_id, evidence_type, source_url, captured_at, claim, value, provenance, confidence, reviewed_at`.
4. Make `verify_log` permanent — remove the 90-day retention sweep in `verify.py`.
**Exit gate (evidence required):** run the migration against a **copy** of `backend/data/ideasexist.db`; confirm zero rows lost and new columns/table present via a `PRAGMA table_info` dump; `python -m tests.smoke` stays green. Record the dump + test output in the ledger.

### Phase 2 — Backend: enrichment & teardown fields
**Goal:** the backend can produce a sourced teardown for a competitor, and accept the founder's own app three ways.
**Tasks (in `backend/app/enrich.py`, `llm.py`, `website.py`, `main.py`):**
1. Extend `_clean_profile`/`seed_from_website`/`seed_from_github` to populate `features_json`, `positioning`, `content_notes`, `pricing_json` (plan-by-plan with `pricing_captured_at` + `pricing_source_url`) and write an `evidence` row per feature, per pricing plan, and per positioning line — each with `source_url` + `captured_at`.
2. **Negative-claim capture:** add a mechanism to record sourced "does not do X" claims into `evidence` (evidence_type `negative`). A negative claim is **only** written when it traces to a source (e.g. "pricing page lists no free tier"); otherwise it is marked unknown and not printed as fact.
3. **Provenance labels:** mark every LLM-drafted `tagline`/`description`/`category`/`founded`/`features`/`positioning` as `machine_drafted` until a human confirms.
4. **Founder-app capture:** add `POST /api/founder-app` accepting three input shapes — a URL (reuses the website seed path), a form (name/description/target_user/category/features/pricing), or a structured JSON (the agent-prompt shape in `docs/teardown-spec.md` §3) — and `POST /api/founder-app/{id}/confirm` to mark the drafted profile confirmed.
5. Keep `reuse_profile` idempotency and the unique-index dedup behaviour intact.
**Exit gate:** seed a real site through the API; assert (in a test) that `features_json` has 5–10 items, `pricing_json` has plan rows with a capture date, `positioning` is non-empty, provenance flags are set, and every negative claim has an evidence row with a source. Record a sample row dump.

### Phase 3 — Backend: comparison, gap table & export
**Goal:** the backend produces the gap table and exports.
**Tasks (in `main.py` + a new `compare.py`):**
1. `POST /api/compare` — takes `{founder_app_id, competitor_ids[]}` (up to 3), loads both sides' teardown fields, and returns the three-band structure from `docs/gap-table-format.md`: `you_have_they_dont`, `they_have_you_dont`, `both_have`, `unknown`, each row = `{dimension, you, them, source, captured_at}`. Every "they" cell carries a source; unsourced cells are `unknown`.
2. `GET /api/export/{markdown|json|csv}` for a comparison — the exact shapes in `docs/gap-table-format.md` §5.
3. `GET /api/startups/{slug}` — a stable per-product endpoint (slug from name) that the frontend's `/products/<slug>` route will call.
**Exit gate:** fixture test comparing two known products returns a correct gap table (assert the three bands and that an unsourced "doesn't do" cell renders as `unknown`); all three export formats parse. Record the fixture input + output.

### Phase 4 — Backend: search classification & match reasons
**Goal:** search returns *why* a result matched.
**Tasks (in `main.py`, optionally `search.py`):**
1. Add `GET /api/search?q=…` that classifies results into the v1 order — exact name → exact domain → phrase/name → tagline → problem-description → category/keyword → fuzzy — and returns a `reason` per result ("Exact name match", "Similar problem description", "Same audience, different approach").
2. Keep stars as a tie-breaker only; dead/pivoted entries sink to the bottom.
3. Keep the existing client-side Fuse path working for <3,000 rows; this endpoint is the server-side contract the frontend will use later.
**Exit gate:** a search test asserts exact-name first, correct reason strings, dead-last ordering, and an empty-result contract. Record test output.

### Phase 5 — Backend functional test gate (the frontend unlock)
**Goal:** prove the backend is fully working **before any frontend is built.**
**Tasks:**
1. Extend `backend/tests/smoke.py` (or add `backend/tests/functional.py`) to cover **every** Phase 1–4 feature: migration idempotency, evidence rows, provenance flags, negative-claim sourcing, founder-app capture (all three paths + confirm), compare/gap-table correctness, all three exports, search classification, slug endpoint, and the unchanged human-gate/verification invariants.
2. Run the full suite against a seeded throwaway DB (no live network; LLM/GitHub mocked).
3. Also run the **real** backend against the real DB and smoke the new endpoints manually (curl/httpx), recording actual responses.
**Exit gate — this is the hard gate:** every test passes; the ledger records the full test output, the counts (tests run / passed / failed = 0), and the date. **Frontend Phases 6–8 remain `blocked` until this row is PASS.**
**If it fails:** fix in Phases 1–4, re-run, update the ledger. Do not touch frontend.

### Phase 6 — Frontend implementation (blocked until Phase 5 PASS)
**Goal:** turn the verified backend into the founder-facing teardown UI, reusing the existing component system.
**Tasks (in `frontend/`, reusing `page.tsx`, `startup-card.tsx`, `startup-detail.tsx`, `lib/api.ts`, `lib/search.ts`):**
1. Upgrade the dossier into a teardown view (pricing plan-by-plan with capture date, features, positioning, sourced "doesn't do" list) rendered from the new endpoints.
2. Build the founder-app input with the three paths (URL / form / paste-agent-JSON) and **always confirm-before-diff**.
3. Build the gap-table view (three bands, sourced cells, `unknown` shown not scored) and wire it to `/api/compare`.
4. Add export buttons (Markdown/JSON/CSV).
5. Add stable `/products/<slug>` routes and the search-with-reasons UI.
6. Keep: WCAG AA both themes, `prefers-reduced-motion`, keyboard/focus, the local-first "no accounts, no tracking" posture.
**Exit gate:** every task above is visibly wired to the *verified* backend and works in a running dev instance; no task is started out of order.

### Phase 7 — Frontend tests (blocked until Phase 6 done)
**Goal:** verify UI behaviour against the verified backend.
**Tasks:**
1. Component/flow tests for: search-with-reasons, dossier→teardown, founder-app (all three paths + confirm), gap-table rendering, export buttons, `/products/<slug>`.
2. Visual/behaviour checks: light+dark themes, reduced-motion, mobile viewport, focus/aria, empty/loading/error states, and the confirm-before-diff path (gap table must not render on an unconfirmed profile).
3. Integration tests asserting the frontend consumes the real backend responses correctly.
**Exit gate:** frontend test run green, with the run output recorded in the ledger.

### Phase 8 — Full end-to-end test (the final gate)
**Goal:** validate the complete loop in sequence, once, with recorded results.
**Tasks:** drive the full journey against the running stack and record each step's actual output:
1. Seed a competitor → verify liveness → open teardown.
2. Enter the founder's app (form or URL or agent JSON) → confirm.
3. Run comparison → check the gap table's three bands and sourced cells.
4. Export all three formats and verify each parses.
5. Confirm search-with-reasons and `/products/<slug>` work end to end.
**Exit gate:** the loop completes with correct results at every step; results are recorded in the ledger as the final PASS. This is the release checkpoint.

### Phase 9 — Handoff & close-out
**Goal:** leave the next person a complete record.
**Tasks:** finalise `docs/phase-ledger.md`; write release notes (what shipped, what's known-broken); update `docs/handoff.md` if anything deviated.
**Exit gate:** the ledger is complete and every phase row has a status + evidence + date.

---

## 3. The result ledger (the audit trail)

`docs/phase-ledger.md` is a table the orchestrator updates after every phase:

| Phase | Status | Evidence (path/command + output summary) | Date |
|---|---|---|---|

Rules:
- A phase is `PASS` only when its exit-gate evidence is recorded in the ledger.
- Phases 6–8 may not be marked `running` while Phase 5 is not `PASS`.
- `FAIL` on any phase means work stops in that phase (or earlier) until the gate passes — no phase-skipping, no "mostly done".

---

## 4. What is out of scope for this plan

- Actual source code changes in this pass (this document is the plan; the build happens in a later orchestrator run).
- Deploying to production or provisioning infrastructure.
- Changing the human-gate/verification semantics, the local-first posture, or the pricing model — those are product decisions already made and recorded in `reworked-revamp-plan.md` and `docs/discussion-record.md`.
- Stack choice — the stack is fixed by the repo.
