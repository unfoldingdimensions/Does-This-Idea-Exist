# Backend Feature & Verification Checklist

**Purpose:** the single source of truth for *"is the backend fully working?"* The Phase 5 gate is PASS only when every item here has a test that passes and recorded evidence.
**Read with:** `implementation-plan.md` (phases) · `reworked-revamp-plan.md` §10–§12 · `docs/teardown-spec.md` (canonical column names in §5.1, trust model in §8, reviews in §9 — the names there win over any older doc).
**Round 5 (2026-09-15):** the trust model, the founder-app link rule and its separate store, just-in-time capture and reviews are decided. F-04 changed (no rename), and F-19–F-23 are new.

Each feature is itemized as: **behaviour → inputs → outputs → acceptance check → test id**. Test ids `F-xx` map to the functional suite in Phase 5.

---

## 1. Schema & evidence foundation (Phase 1)

### F-01 Additive migration
- **Behaviour:** apply new columns + `evidence` table without dropping or rewriting existing rows.
- **Inputs:** a copy of the live `ideasexist.db`.
- **Outputs:** migrated DB; `PRAGMA table_info(startups)` shows the new columns; `evidence` table exists.
- **Acceptance:** row count unchanged after migration (1,282 expected baseline); no `DROP`/`ALTER ... RENAME` in the migration; re-running is a no-op (idempotent); the two new store-link columns (`app_store_url`, `play_store_url`) are present and every new column is also added to `enrich.UPDATABLE` — a column missing there is **silently dropped** by `_upsert`.

### F-02 Evidence table
- **Behaviour:** `evidence(id, startup_id, evidence_type, source_url, captured_at, claim, value, provenance, confidence, reviewed_at)`.
- `evidence_type` values: `feature` · `pricing` · `positioning` · `negative` · **`review`** · `repo_created` · `homepage_claim` · `wayback_first` · `reachability` · `curator_confirmation`.
- **Outputs:** rows written with `source_url` + `captured_at` for every claim.
- **Acceptance:** an evidence row cannot be written without `source_url` (rejected or flagged); `captured_at` auto-filled; `confidence` carries the retrieval-vs-assertion distinction for negatives (a page we could not read is never a negative).

### F-03 Permanent verify_log
- **Behaviour:** the 90-day retention sweep in `verify.py` is removed.
- **Acceptance:** a `verify_log` row older than 90 days survives a verification pass.

### F-04 `founded` date provenance
- **Behaviour:** the column **keeps the name `founded`** (owner decision, Round 5 — the `founded_at` rename is rejected). Add `date_source` (`llm` · `wayback` · `rdap` · `human` · `unknown`) and record which of the three existing branches produced the date. RDAP/Wayback-derived dates are never *presented* as founding years.
- **Acceptance:** a seeded row whose date came from RDAP has `date_source='rdap'`; the column list is unchanged; no file outside the backend is touched in Phase 1. The display half (the UI must stop saying "founded 1997" for a domain-registration date) is a **Phase 6 follow-up** — `startup-card.tsx` and `page.tsx`, which also carries a hardcoded `"2021"` fallback that fabricates a vintage when the date is null. F-04 is backend-half-complete until then.

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
- **Outputs:** a draft profile in the **founder store** (`FOUNDER_DB_PATH`), carrying the same record shape as `startups` so the gap table can diff like for like.
- **Acceptance:** returns drafted fields; does not auto-confirm; **nothing is written to the archive DB**; the row is never returned by `/api/startups`, `/api/stats` or `/api/categories`.

### F-11 Founder-app capture — form path
- **Behaviour:** `POST /api/founder-app {form fields}` with a required flat feature list.
- **Inputs:** name, description, target_user, category, features (5–10), pricing, links (website_url / github_url / app_store_url / play_store_url — all optional).
- **Acceptance:** rejected with a clear 400 if `features` is missing or <5; accepted otherwise; a **link-less submission is accepted and stored as comparison-only** (`archive_status='local_only'`) and is never offered the publish checkbox.

### F-12 Founder-app capture — agent-JSON path
- **Behaviour:** `POST /api/founder-app {json}` accepts the exact agent-prompt shape from `docs/teardown-spec.md` §3 (extended with the two store links).
- **Acceptance:** valid JSON → draft; malformed/unknown keys → 400; invented fields are not silently accepted.

### F-13 Founder-app confirm and publish gate
- **Behaviour:** `POST /api/founder-app/{id}/confirm` flips the draft to confirmed. Publishing is a **separate** gate: link present **and** the opt-in checkbox ticked → the app is submitted to the archive and enters the **same admin approval queue as competitors**.
- **Acceptance:** compare/gap-table refuses an unconfirmed founder app (explicit "not confirmed" state); the checkbox is only offered when a fetchable link exists; `archive_status` moves `local_only` → `pending` → `approved`/`rejected` and is readable by the founder locally (there are no accounts to notify).

### F-14 Idempotency & dedup preserved
- **Behaviour:** `reuse_profile` still skips the LLM for known URLs; unique-index collisions still 400.
- **Acceptance:** re-seeding the same URL does not duplicate; the existing dedup tests stay green.

---

## 3. Comparison, gap table & export (Phase 3)

### F-15 Comparison endpoint
- **Behaviour:** `POST /api/compare {you: {...}, competitors: [...]}` (≤3) returns the three-band gap table. The sides are **named** rather than passed as one flat id list because the two records live in different databases — `id=7` is ambiguous across files.
- **Outputs:** `you_have_they_dont`, `they_have_you_dont`, `both_have`, `unknown`, each row `{dimension, you, them, source, captured_at}`.
- **Acceptance:** bands are correct for fixtures; an unsourced "doesn't do" cell renders `unknown`, not "no"; a negative is only rendered when it traces to an enumerating page.

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

## 5. Teardown capture, trust badges & reviews (added Round 5, 2026-09-15)

### F-19 Store-link columns
- **Behaviour:** `app_store_url` and `play_store_url` (both nullable TEXT) exist on `startups` and are writable.
- **Acceptance:** the migration adds both; both are in `enrich.UPDATABLE`; a founder app carrying only a store link is eligible for the archive (F-20); the store links are also the deterministic "is there a mobile app" probe (F-23's source).

### F-20 Link-eligibility gate
- **Behaviour:** a founder app may only enter the archive with at least one verifiable link — `website_url` | `github_url` | `app_store_url` | `play_store_url`. No link → comparison only.
- **Acceptance:** a link-less submission returns a working comparison and `archive_status='local_only'`; the opt-in checkbox is offered only when a fetchable link exists; archive endpoints (`/api/startups`, `/api/stats`, `/api/categories`) and the verify walk never see founder-store rows.

### F-21 Trust badges
- **Behaviour:** expose `admin_verified` (from `verified`/`verified_at`) and `machine_verified` (from `status`/`last_checked`/`check_failures`) as distinct signals — a read-layer change, not new columns.
- **Acceptance:** an approved row reads `admin_verified=true` regardless of check age; a row whose last check is stale reads `machine_verified=false` while staying admin-verified; **no badge is ever rendered against a claim cell** (`docs/teardown-spec.md` §8.1).

### F-22 Just-in-time teardown capture
- **Behaviour:** teardown capture runs on the **first founder request** for a competitor, then caches; serialized on the existing exclusive-job guard (`seeder.try_enqueue_exclusive`) keyed per competitor; a freshness window prevents re-capture on every request.
- **Acceptance:** two concurrent requests for the same never-captured competitor produce exactly **one** capture job; a request inside the freshness window is served from cache; a request outside it returns an explicit "capture in progress — retry" state rather than a partial teardown; no public job-detail endpoint is exposed (job payloads carry errors and URLs, which is why they are admin-gated).

### F-23 Reviews & "what their users ask for"
- **Behaviour:** fetch reviews from the configured `review_sources` (config, not code), store each as an `evidence` row (`evidence_type='review'`, `source_url`, `captured_at`, `provenance='machine_drafted'`), classify positive/negative, and extract the features/fixes reviewers asked for.
- **Acceptance:** no score, aggregate or NPS of our own is ever stored or rendered; a 403/429 from a walled provider is a **skip, never a failure or a strike**; every extracted request links to the review it came from; the output is a list of what users asked for, never a recommendation (`docs/teardown-spec.md` §9).

---

## 6. Unchanged invariants that must keep passing

These are the existing human-gate/verification guarantees — the functional suite must assert them **still** hold after the new work:

- Human `verified` stamp is the only bulk writer of `verified=1`; automation never stamps.
- Tri-state liveness: only 404/410 counts; 403/429/5xx are skips; 3 strikes → `dead`; never deleted.
- Verified rows are protected from automation.
- `MUTATION_AUTH` gating, rate limits, SSRF guard, LIKE-escape — unchanged and tested.
- **Badges attach to records, never to claims** — Admin/Machine Verified describe the business, not its marketing.
- **Nothing enters the archive without a real link and admin approval** — competitor and founder submissions use the same gate.
- **The founder store is never listed, counted or searched** by the archive endpoints.
- **A negative is never printed without an enumerating source**; a page we could not read is `unknown`, not "no".

---

## 7. Phase 5 gate — what must be recorded before frontend starts

The orchestrator records in `docs/phase-ledger.md`:

1. `F-01`–`F-23` + the invariants above: **all tests pass, failed = 0**.
2. The command run and its actual output (e.g. `python -m tests.functional` with the pass/fail summary).
3. A **real-backend smoke**: the dev backend is started against the real DB and the new endpoints return real responses (pasted sample output, not an assertion).
4. Date + who ran it.

Only after those four are in the ledger does Phase 6 (frontend) move from `blocked` to `running`.
