# Codebase Comprehension — IdeaExists / "Does this Startup Exist"

**Prepared:** 2026-09-14
**Repo:** `E:\New-Personal-Projects\Does this Startup Exist`
**Method:** full read of every hand-written source file in `backend/`, `frontend/`, `scripts/`, plus the project docs, changelog and prior dogfood reports. No file in those trees was skipped (see §12 for the exact list and for generated/vendored paths that are not hand-written source).

> **Phase 1 note (2026-09-15):** this document was prepared on 2026-09-14 and describes the pre-Phase-1 codebase. Phase 1 (F-01–F-05, F-19) added the teardown columns and the `evidence` table, removed the `verify_log` retention sweep, and introduced `provenance` / `date_source`. The affected passages are corrected inline below and marked. Everything else still holds.

> **Phase 2 note (2026-09-15):** Phase 2 (F-06–F-14, F-20, F-22–F-24) added the teardown pipeline — a page plan (`app/pages.py`), a second LLM prompt (`llm_teardown`), `app/teardown.py`, `app/evidence.py`, `app/negatives.py`, `app/reviews.py`, the just-in-time capture (`app/capture.py`) and the founder's own store (`app/founder.py` + `FOUNDER_DB_PATH`). The backend gained seven modules and thirteen endpoints; the archive schema did not change. The affected passages are corrected inline below and marked.

> **Phase 4 note (2026-09-16):** Phase 4 (F-18) added `backend/app/search.py` + `GET /api/search` — classified results with a frozen per-result `reason`, ordered by the plan's ladder. The affected passages (§4.2 read surface, §7 harness, §9 "what is missing") are corrected inline below and marked.

This document exists so a reader who has never opened the repo can describe, accurately, what the product is, how it is built, what it actually does today, and where the founder-facing value sits in the code.

---

## 1. What the product is, in code terms

Two standalone processes that talk over HTTP:

| Process | Stack | Port | Entry point |
|---|---|---|---|
| `backend/` | Python 3.11, FastAPI, stdlib `sqlite3` (WAL), `httpx` | 8020 | `backend/app/main.py` → `app = FastAPI(...)` (`main.py:119`) |
| `frontend/` | Next.js 16 (App Router), React 19, Tailwind v4, shadcn/ui, `motion/react` | 3023 | `frontend/app/page.tsx` (`HomePage`, `page.tsx:114`) |

There is **no hosted multi-tenant version**. The backend is a single-owner service gated by one token; the frontend is a single client-side page that pulls the entire archive into memory and filters it locally. The `README.md`, `PRODUCT.md` and `DEPLOYMENT.md` all describe the same shape: local-first, SQLite file, `--workers 1`, no accounts.

### Working title
`IdeaExists` — and `PRODUCT.md` explicitly says the name is **not final** ("do not over-invest in the wordmark"). The brand string already lives in `frontend/app/layout.tsx` (metadata), the header, and the backend `User-Agent` constants.

---

## 2. Repository map

```
backend/
  app/            the whole server (17 modules, ~3,700 LOC of hand-written Python)
    config.py     env-driven settings, validated at boot
    db.py         schema v1 + connection + URL identity normalisation + table_ddl
    main.py       FastAPI app, all routes, admin gate, rate limiting, auto-verify
    seeder.py     job queues + workers (seed / verify / capture), batch sources, job persistence
    verify.py     the liveness pass + the human-approval queue
    enrich.py     seed orchestration, LLM output bounding, upsert, the website draft primitive
    github.py     GitHub REST client
    website.py    homepage fetch, text extraction, Wayback + RDAP date lookups
    llm.py        OpenAI-compatible chat client: the identity prompt AND the teardown prompt
    netguard.py   SSRF guard + size-capped GET
    pages.py      the page plan: homepage + /pricing + /docs, each with an explicit read state (Phase 2)
    teardown.py   bounds + writes features / pricing / positioning (Phase 2)
    evidence.py   the only evidence writer — no source, no row (Phase 2)
    negatives.py  the strict "doesn't do" rule: deterministic probes first, LLM second (Phase 2)
    reviews.py    what their users ask for — never a score (Phase 2)
    capture.py    just-in-time teardown capture, 7-day window, one job per competitor (Phase 2)
    founder.py    the founder's own store + the two gates + the submission lifecycle (Phase 2)
  data/           ideasexist.db (git-ignored) + founder.db (its own store) + seed lists + backups
  scripts/        merge_duplicates.py, restore_false_dead.py (operator tools)
  tests/smoke.py  in-process test suite (~900 lines, no network)
frontend/
  app/            layout.tsx, page.tsx (the entire app), globals.css, SEO routes
  components/     34 components: cards, dossier modal, admin panel, sky, chrome
    ui/           shadcn primitives + bespoke ones (discovery bar, palette, ticker)
  lib/            api.ts, search.ts, types.ts, format.ts, motion.ts, sound-engine.ts
scripts/          verify.mjs (test runner), sort-check.ts, e2e-verify*, a11y helpers
docs/             prior research, security audit, readiness reports
dogfood-output/   prior adversarial + QA reports and screenshots
```

Everything else at the root is documentation (`PRODUCT.md`, `DESIGN.md`, `README.md`, `DEPLOYMENT.md`, `BACKEND-REMEDIATION.md`, `CHANGELOG.md`, `revamp-plan.md`, `Revamp-thinking.txt`), config (`docker-compose.yml`, `package.json`), or tool state (`.agents/`, `.hermes/`, `.mimosa/`, `.openclaw/`, `.zcode/`, `.impeccable/`).

---

## 3. Data model — four tables in the archive, two more in the founder store *(four from Phase 1)*

`backend/app/db.py` creates the entire schema. **Phase 1 (F-01) added a migration path:** `init_db()` now runs `executescript(SCHEMA)` (the full schema, `CREATE … IF NOT EXISTS`, for a fresh DB) **and** `db.migrate(conn)`, which adds any missing columns from `NEW_STARTUP_COLUMNS` to an existing database. That one tuple feeds both paths, so a fresh DB and an upgraded one cannot drift apart; `migrate()` is idempotent by construction (`PRAGMA table_info` decides what is missing) and the rule still holds: **additive changes only** — no `DROP`, no `RENAME`, no row rewrite.

### `startups` (the archive) — 40 columns
`id, name, tagline, description, category, website_url, github_url, founded, stars, language, status, verified, verified_at, last_checked, check_failures, source, created_at, updated_at` — plus the **22 nullable teardown columns added in Phase 1** (`entity_type`, `canonical_domain`, `aliases`, `problem_statement`, `target_users`, `product_url`, `docs_url`, `demo_url`, `app_store_url`, `play_store_url`, `pricing_json`, `pricing_captured_at`, `pricing_source_url`, `features_json`, `positioning`, `content_notes`, `activity_checked_at`, `activity_summary`, `last_human_reviewed_at`, `review_notes`, `provenance`, `date_source`). Canonical names: `docs/teardown-spec.md` §5.1. (`founded` keeps its name — the `founded_at` rename is rejected.)
Two unique indexes: `lower(website_url)` and `lower(github_url)`.

### `verify_log` (append-only audit trail)
`id, startup_id, checked_at, website_ok, github_ok, notes`. Written once per entry per verification pass. **Phase 1 (F-03): the audit trail is permanent** — the 90-day retention sweep that used to sit at the end of `run_verify_job` is gone, and the pass only ever inserts.

### `evidence` (one row per claim) — added in Phase 1 (F-02)
`id, startup_id, evidence_type, source_url, captured_at, claim, value, provenance, confidence, reviewed_at`. `source_url` and `captured_at` are **NOT NULL** — evidence without a source is not evidence, and the DB is the last line of defence behind the API's checks. `evidence_type` values: `feature` · `pricing` · `positioning` · `negative` · `review` · `repo_created` · `homepage_claim` · `wayback_first` · `reachability` · `curator_confirmation`. Indexed on `startup_id`. **Phase 2 is what writes rows here** — `app/evidence.py` is the only writer, and it refuses a source-less claim by construction. The freshest teardown row is also what the JIT capture's 7-day freshness window is measured against.

### `jobs` (job history that survives restarts)
19 columns: identity, `kind`, `source`, `params_json`, counters, `errors_json`, `ok_urls_json`, `skipped_urls_json`, timestamps, `breakdown_json`, `result_json`. The in-memory `JOBS` dict in `seeder.py` is mirrored here on every state change. **Phase 2 added a third kind, `capture`** (the just-in-time teardown capture), on its own worker.

### The founder store — a second database (Phase 2, F-10 / F-20 / F-24)
`config.FOUNDER_DB_PATH` (default `backend/data/founder.db`) is its own SQLite file with two tables, and **no archive endpoint ever reads it** — that separation is the property the split exists for:
- `founder_apps` — the founder's own record, the **same column shape as `startups`** (both built from `db.table_ddl`), plus three bookkeeping columns (`source_kind`, `input_json`, `confirmed_at`) so the gap table can diff the two records like for like.
- `founder_submissions` — `id, founder_app_id, submitted_at, status (pending|approved|rejected|withdrawn), archive_startup_id, decided_at, decided_by, note`. `archive_status` is **derived** from the newest row (`local_only` when there are none) rather than stored on the founder record, and a resubmission after a rejection is a NEW row, so rejected → resubmitted → approved stays auditable.

### Live data facts (queried from `backend/data/ideasexist.db`, 2026-09-14)

| Metric | Value |
|---|---|
| Filings | **1,282** |
| Status breakdown | `active` 1,282 · `dead` **0** · `pivoted` **0** |
| `verified = 1` (human-stamped) | **1,278 (99.7%)** |
| `verified = 0` | 4 |
| Rows with a `website_url` | 1,282 (100%) |
| Rows with a `github_url` | **57 (4.4%)** |
| Rows with both | 57 |
| Source split | `website` 1,229 · `github` 53 |
| `tagline` populated | 1,256 |
| `description` populated | 1,258 |
| `founded` populated | 1,277 |
| `stars` populated | 57 |
| `last_checked` populated | 1,282 (max 2026-09-04) |
| `verify_log` rows | 5,987 |
| `jobs` rows | 10 |

**Category distribution:** other 302 · ai 222 · finance 173 · health 165 · devtools 140 · productivity 109 · ecommerce 67 · media 49 · education 37 · social 14 · freelance 4.

**Duplicate name groups:** 6 (`Stability AI`, `Motion`, `Fathom`, `Cal.com`, `Bun`, `Bird`). All six are **same name, different company or different home** — they were deliberately *not* auto-merged by `backend/scripts/merge_duplicates.py`, which merged 10 clear-cut same-home groups (1,292 → 1,282 rows) and left these for human review. Zero duplicate domains remain.

### Five things the data model cannot express today
1. **Provenance.** `tagline`/`description`/`category`/`founded` are LLM-drafted (`llm.py`) but there is no column saying so; a reader cannot tell a human-written fact from a machine draft.
2. **Evidence.** No table links a claim to a source URL, capture date or confidence. `verify_log` records *liveness checks*, not *claims*.
3. **Identity typing.** A filing can be a company, a product, an open-source repo or a URL — `entity_type` does not exist, so "Notion" (a company) and "Whisper" (a repo) are the same kind of row.
4. **Alternatives / audience / pricing.** `problem_statement`, `target_users`, `pricing_json`, `product_url`, `docs_url`, `demo_url`, `app_store_url`, `play_store_url` do not exist. (Naming note: older plan drafts call the pricing field `pricing_model` — **`pricing_json` is canonical**, along with `features_json`, per `docs/teardown-spec.md` §5.1. `founded` keeps its name; a `date_source` column does not exist yet and is what F-04 adds.)
5. **Comparison.** There is nowhere to store a user's product selection or a "what would be different" answer; the frontend keeps nothing beyond URL state.

---

## 4. Backend architecture

### 4.1 Boot sequence (`main.py:68-95`, `lifespan`)
1. `_check_auth_config()` — refuses to start if `MUTATION_AUTH=1` and `ADMIN_TOKEN` is empty (fail-closed, no silent-open state).
2. `db.init_db()` — creates the three tables.
3. `seeder.recover_interrupted_jobs()` — any job left `queued`/`running` by a restart becomes `failed (interrupted)`.
4. `_maybe_auto_verify()` — if any row's `last_checked` is older than `VERIFY_AUTO_STALE_DAYS` (default 7), enqueue a pass synchronously, so the first request never sees a stale archive.
5. `_auto_verify_loop()` — repeats that staleness check every 24 h (`main.py:55`).

Importing `seeder` starts two daemon threads (`seeder.py:427-428`): the **seed worker** and the **verify worker**. They are the serialization points: any number of seed jobs queue FIFO on one worker, verify jobs on the other, and the two kinds run **concurrently**. `--workers 1` is a correctness constraint, not a preference — more uvicorn workers means two job queues and two writers on one SQLite file.

### 4.2 HTTP surface
**Public reads (no token):**
- `GET /api/health`, `GET /api/categories`, `GET /api/stats`
- `GET /api/founder-app/{id}` — the founder's own draft plus both gates and the derived `archive_status` (Phase 2; reads the founder store, never the archive).
- `GET /api/startups` — the whole archive as one JSON array. Server accepts `?q=`, `?category=`, `?limit=`, `?offset=` but the frontend uses none of them for filtering; it pulls everything and filters client-side. Default limit **3,000**, max 5,000 (`main.py:LIST_LIMIT_DEFAULT`). Truncation returns HTTP 200 with a short body — the frontend detects it by comparing against `/api/stats`.
- **Phase 4:** `GET /api/search` — classified search with a per-result `reason` (F-18). Ordered by the plan's ladder (exact name → exact domain → phrase/name → tagline → problem-description → category/keyword → fuzzy); dead/pivoted rows last; stars a tie-break only; multi-term queries AND across terms with the worst term scoring. The reason vocabulary is frozen in `app/search.py`. A missing/blank/punctuation-only `q` returns **200 with an empty list** (the documented empty-query contract — never the archive). Unlike `/api/compare` it is a **pure read**: a search never triggers the JIT capture. Optional `?limit=` mirrors the list endpoint's ceiling.
- **Phase 3:** `GET /api/startups/{slug}` — one product by its name slug (the backend for the future `/products/<slug>` route). A same-name collision resolves deterministically (the human-verified row first, then the lowest id) and the payload names the row it got (`resolved_id`, `resolved_name`, `duplicate_group`); the two trust badges ship as explicit fields (`admin_verified`/`admin_verified_at` from `verified`/`verified_at`, `machine_verified`/`machine_verified_at` from `status`/`last_checked`/`check_failures`, F-21). An unknown slug is a clean 404.
- **Phase 3:** `GET /api/export/{markdown|json|csv}` — the gap table in the three formats (`docs/gap-table-format.md` §5). **Stateless**: it takes the same inputs as `POST /api/compare` as query parameters (`?you=<id|slug>&competitors=<id|slug>`, repeatable or comma-separated) and recomputes deterministically, so re-running with the same inputs yields the same bytes. It is a pure read — an export never triggers a capture.

**Owner-gated reads (`X-Admin-Token`):**
- `GET /api/admin/check`, `/api/admin/seed/jobs`, `/api/admin/seed/status/{id}`, `/api/admin/verify/suggested`, `/api/admin/verify/status/{id}`, `/api/admin/verify/current`
- **Phase 2:** `GET /api/admin/founder/submissions` (pending publish requests) and `GET /api/admin/capture/status/{job_id}`. `verify/suggested` now **unions** the archive's suggested rows with the founder store's pending submissions (F-24) — a submission in another file would not appear there otherwise. There is deliberately **no public capture-job endpoint**: a job payload carries error strings and fetched URLs.

**Mutations (token required because `MUTATION_AUTH` defaults on):**
- `POST /api/seed/github`, `/api/seed/website`, `/api/verify/run`
- `POST /api/startups/{id}/verify|unverify|dead`
- `POST /api/admin/seed`, `POST /api/admin/verify/approve`
- **Phase 2, founder app (deliberately NOT admin-gated — the path cannot write the archive):** `POST /api/founder-app` (URL / form / agent-JSON), `POST /api/founder-app/{id}/confirm`, `POST /api/founder-app/{id}/publish`.
- **Phase 2, admin:** `POST /api/admin/founder/submissions/{id}/approve|reject`, `POST /api/admin/capture/{startup_id}`.
- **Phase 3:** `POST /api/compare` — the gap table (F-15). Body `{you: {...}, competitors: [...]}` (≤3); the sides are **named** because the `you` record lives in the founder store and the competitors in the archive, so a bare `id=7` is ambiguous across the two files. It refuses an unconfirmed `you` with an explicit `409 {"state": "not_confirmed"}` (F-13), triggers the just-in-time capture for each competitor (F-22 — queued before it is cached), then diffs the two stores in Python and returns the five bands (`you_have_they_dont`, `they_have_you_dont`, `both_have`, `unknown`, `asked_for`).

### 4.3 Security layer (all in `main.py` + `netguard.py`)
- `require_admin` (`main.py:230`) — HMAC constant-time compare, compared as **bytes** so a non-ASCII header 403s instead of raising.
- Failed-auth counter — 10 failures/min per IP then 429; successful use is never throttled.
- Per-IP sliding-window rate limits on every mutating/admin route; keys are evicted when their window expires.
- `netguard.safe_get` — every outbound fetch validates scheme, hostname and **every redirect hop's resolved IP** (`ipaddress.is_global`), caps bodies at 2 MB, max 5 redirects.
- `_like_escape` — `%` and `_` in `?q=` are escaped so `q=%` cannot dump the table.
- Security headers on every response (nosniff, DENY, no-referrer, Permissions-Policy, HSTS).

### 4.4 The seed pipeline (`enrich.py`)
`seed_from_github` (`enrich.py:86`) and `seed_from_website` — both fetch evidence, ask the LLM for a JSON profile, bound the output, then upsert:
- `_clean_profile` clamps `name` 120 / `tagline` 300 / `description` 4,000 chars and resolves `category` against an 12-value whitelist (else `other`, `enrich.py:22-49`).
- `_http_url` rejects non-http(s) values — this closes a real click-to-execute hole, because GitHub's `homepage` field (owner-controlled) lands in `website_url`, which the UI renders straight into an `href`.
- `reuse_profile=True` (the default for batches) skips the LLM for rows already on file — re-seeding is idempotent and near-free.
- `_upsert` returns `_inserted`, and a unique-index collision becomes a clear `ValueError` (→ HTTP 400) rather than a raw 502.

`github.py` is a thin REST client with explicit 404 (gone) vs 403/429 (rate-limited) semantics. `website.py` extracts homepage text with a stdlib `HTMLParser`, reads `<title>`/meta description with regexes, resolves `<title>`-less names from the URL, and derives `founded` from **LLM → Wayback CDX first-200 snapshot → RDAP domain registration** — in that order. `llm.py` is an OpenAI-compatible chat client tuned for a reasoning model (8,000 max tokens, 180 s timeout, one retry, tolerant JSON parsing).

**Phase 2 — the teardown is not the seed.** Capturing a competitor's teardown is a separate, just-in-time path that never runs on seed or on approval:

- `pages.fetch_pages` fetches the **page plan** — homepage, `/pricing`, `/docs` — each through `netguard.safe_get`, and reports one of three explicit states per page: `readable`, `unreadable` (404/403/429/empty shell) or `not_fetched`. "Unreadable" is never collapsed into "no page": that collapse is the easiest way to fake a negative.
- `llm.llm_teardown` is a **second prompt**, passed explicitly to the same client; `SYSTEM_PROMPT` (the identity profile) is untouched because the GitHub path shares it and has no pricing page to read.
- `teardown.clean_teardown` bounds the reply before it touches SQLite: features 5–10 or `[]` (unknown, never padded), plans `{name, price, period}` with malformed rows **dropped**, positioning one capped line, JSON via `json.dumps`.
- `negatives` runs the **deterministic probes first** (pricing page → free tier / self-host; docs index → API; footer links → mobile) and the **LLM's negatives second, validated against pages we actually read**. A 404 on a guessed URL produces nothing — the guessed capability paths are never fetched at all.
- `reviews` fetches the configured `REVIEW_SOURCES`, stores one `evidence` row per review (`evidence_type='review'`, permalink as the source) and extracts the asks; a walled provider is a skip, and no score is stored anywhere.
- `capture.start_capture` is the JIT entry point: cache inside a 7-day window, otherwise one job per competitor (keyed on the existing `try_enqueue_exclusive` guard), and an explicit "capture in progress — retry" state while one is in flight.

### 4.5 Verification — the product's trust engine (`verify.py`)
`check_url_ok` (`verify.py:30`) and `check_github_ok` are both **tri-state** `(ok, note, skipped)`:
- Only a genuine **404/410** is a real strike.
- Bot walls (401/403), rate limits (429), 5xx and network errors are **skips** that reset the streak — the code documents a real incident where Cloudflare 403s dead-filed WHOOP and Capterra.
- Three consecutive strikes flip `status` to `dead`. Nothing is ever deleted.
- A `verified=1` row is **protected from automation**: it never accumulates strikes and never auto-flips; a failed check surfaces in `failed_list` as a re-check item instead.

The human gate is `approve_suggested` (`verify.py:154`) — the **only** bulk writer of `verified=1` — plus the single-row endpoint. `list_suggested` (`verify.py:137`) is the queue: `verified=0 AND status='active' AND check_failures=0`.

`run_verify_job` (`verify.py:205`) walks every row, buckets its *current* state into a verified/unverified/dead breakdown, commits **per row** (so a parallel seed is never blocked by a long write lock), writes a `verify_log` row per entry (**never pruned** — Phase 1 / F-03 removed the 90-day sweep), and persists live progress to `jobs` as it goes.

---

## 5. Frontend architecture

One page, one file: `frontend/app/page.tsx` (32 KB). Everything is client-side.

- **Data load:** `loadAll()` fires `fetchStartups`, `fetchCategories`, `fetchStats` in parallel (`Promise.allSettled`); a rejection flips the `online` flag and the UI shows a fixed Retry pill instead of a frozen skeleton. Every request has a hard timeout (`api.ts`: 10 s reads, 90 s writes).
- **Search + facets:** `lib/search.ts` — a `Fuse` index built once per data array (cached in a `WeakMap` by identity) with `threshold: 0.3` and weights name 3 / tagline 2 / description 1.5 / category 1. Multi-term queries are **AND across terms**; the combined score is the worst term. When a query is present and sort is default, results stay in Fuse relevance order (exact name first); dead/pivoted sink to the bottom; stars only break ties. Facets are category, founded year and status. Sort keys: `top` (trust-weighted), `newest`, `verified`, `name`, `founded`.
- **URL state:** `readInitialParams()` (`page.tsx:60`) reads `?q= &category= &year= &status= &sort= &page=` **after mount** (to avoid a hydration mismatch), and a `replaceState` effect writes them back — back-button-safe, shareable, never `pushState`.
- **Cards:** `components/startup-card.tsx` — `StartupCard` (gallery, `:289`) and a dense ledger variant, plus `StatusPill` (`:80`). The pill is the human gate in the UI: for an unlocked owner it opens a three-state menu and a themed confirm dialog; for a visitor it is a read-only popover explaining what the stamp means.
- **Dossier:** `components/startup-detail.tsx` (`:24`) — a modal with the metadata table (founded, stars, language, category, source, verified date, last checked, failure counter), website/code links, a share-link button, and a "More like this" block scored by shared category + language + trust state + tagline tokens (`startup-detail.tsx`, `similar` memo). Focus is trapped and restored; Escape peels exactly one layer.
- **Admin:** `components/admin-panel.tsx` — token unlock, then three collapsible sections (`admin-seed-section`, `admin-verify-section`, `admin-health-section`) with a 2 s poll while any job is active, persisted job history, batch approve, and a live health-check progress bar.
- **Chrome:** celestial animated background (`sky-stage.tsx`, `sky-background.tsx`), morphing discovery bar, command palette (⌘K), audio toggle, density toggle, archival ticker, odometer counters, landing strips (`home-sections.tsx`: Just added / Recently verified / Dead recently).
- **Accessibility:** `prefers-reduced-motion` is honoured at both CSS and component level; skip link; focus rings via a hand-written `.search-focus-ring` (framer-motion's layout projection was clobbering Tailwind rings); status is dot **plus** word **plus** tooltip, never colour alone.

---

## 6. The two real user journeys, as they exist in code

### Journey A — the visitor researches an idea
1. `GET /` → `loadAll()` → the archive arrives as one array.
2. Types into the discovery bar → 150 ms debounce → `filterStartups()` → Fuse relevance order.
3. Optionally narrows with category chip / year / status / sort → `?q=…&year=…` written to the URL.
4. Clicks a card (name, Details, or the card body) → `StartupDetail` modal opens with the dossier.
5. Reads the metadata table, clicks Website / Code (external), or "Share Entity" (copies `/?q=name`).
6. Clicks "More like this" → the modal morphs to the next dossier without closing.
7. Closes → focus returns to the triggering card; the archive is where it was.

### Journey B — the owner (the Curator) maintains the archive
1. Footer gear → admin dialog → enters `ADMIN_TOKEN` → `POST /api/admin/check` → token stored in `sessionStorage`.
2. **Seeding** — picks a source (`famous`, `github_search`, `url_list`, `design_library`) and a cap (1–500), or uses the header split-button to add one repo/website. `POST /api/admin/seed` → job queued → the panel polls `/api/admin/seed/jobs` every 2 s.
3. Each candidate runs through `_ingest` → GitHub or website pipeline → LLM profile → upsert. Failures are counted, listed and logged, never swallowed.
4. **Verification** — the suggested queue lists alive-but-unstamped rows grouped by creation day; the owner approves one, a batch, or all (`POST /api/admin/verify/approve`), each behind a confirm dialog.
5. **Health check** — `POST /api/verify/run` starts the automated liveness pass; the panel shows a progress bar and, on completion, three expandable buckets (already verified / suggested / failed) with open-link and mark-verified actions.
6. Any card's status pill flips verified ⇄ unverified ⇄ dead, reversibly.

Both journeys are covered by the in-process smoke suite and previously by two dogfood passes (`dogfood-output/`).

---

## 7. Test and verification harness

- `npm test` (root `package.json`) → `scripts/verify.mjs` runs four suites: the backend smoke suite, the frontend sort regression, the frontend lint + production build, and `scripts/e2e-verify.mjs`.
- `backend/tests/smoke.py` (~900 lines, 80+ assertions) spins up a throwaway SQLite DB with `TestClient` and pins: the API surface, schema bootstrap, admin gate on all six write endpoints, the startup refusal, the job lifecycle with fake sources, queue serialization, dedup upsert, tri-state verify logic, restart recovery, the human-gate invariants, LIKE escaping, the SSRF guard, rate limiting and the category whitelist. **No network, no LLM.**
- `scripts/sort-check.ts` runs the *real* `frontend/lib/search.ts` under Node's native type-stripping to pin the dead-last ordering for all five sort keys.
- **Phase 2:** `scripts/phase2-verify.py` is the exit-gate verifier for the teardown work. It works on a copy of the live archive (SQLite's backup API — the archive is in WAL mode) plus a throwaway founder store, stubs the fetcher and both LLM prompts, and prints `[PASS]`/`[FAIL]` per check plus `RESULT: ALL PASS` or `RESULT: n FAILED`; it exits non-zero on failure. Nothing in it touches the network or the live files.
- **Phase 3:** `scripts/phase3-verify.py` is the exit-gate verifier for comparison, the gap table and the exports. Same discipline as Phase 2 (a copy of the live archive via SQLite's backup API, a throwaway founder store, the fetcher and both LLM prompts stubbed, `[PASS]`/`[FAIL]` + `RESULT:` and a non-zero exit on failure) and it pins: the five bands for a fixture, sourced-or-unknown cells, the enumerating-page negative rule, dimension 7's two destinations, the F-13 compare guard, the F-22 JIT wiring, the three exports (parsing + byte-determinism), the slug collision rule, the two trust badges, and that the founder store never leaks into the archive surface.
- **Phase 4:** `scripts/phase4-verify.py` is the exit-gate verifier for search classification and match reasons. Same discipline as Phases 2/3 (a copy of the live archive via SQLite's backup API, a throwaway founder store, `[PASS]`/`[FAIL]` + `RESULT:` and a non-zero exit on failure) and it needs no fetcher or LLM at all, because search reads stored data only. It pins: the ladder's order and the exact-name-first rule on a real product, every frozen reason string (including the latent "Same audience, different approach"), dead **and** pivoted sinking under an otherwise equal match, stars as a tie-break only, multi-term AND with a worst-term score, the empty-query contract, literal LIKE metacharacters, the pure-read tripwire (a search never calls `capture.start_capture`), the founder-store containment, the data-awareness rule (an empty column never matches everything), and the reachable-rung census on a pristine copy of the real archive.
- Known limitation, documented in `README.md`: the runner is Windows-only (it shells out to `backend/.venv/Scripts/python.exe` and `npm` through a shell) and there is **no CI**.

---

## 8. External integrations (the complete list)

| Integration | Where | Why | Auth |
|---|---|---|---|
| GitHub REST API | `github.py`, `seeder._gh_search` | repo metadata, search | optional `GITHUB_TOKEN` (60 → 5,000 req/h) |
| LLM gateway (OpenAI-compatible) | `llm.py` | draft the profile JSON | `OPENCODE_GO_API_KEY` |
| Target websites | `website.fetch_homepage` via `netguard.safe_get` | homepage text, title, meta | none |
| Wayback CDX API | `website.wayback_first_snapshot` | first archived snapshot → `founded` fallback | none |
| RDAP (`rdap.org`) | `website.rdap_registration_date` | domain registration → `founded` fallback | none |
| Reddit (public `.json` + RSS) | `reviews.fetch_source` via `netguard.safe_get` | what a competitor's users ask for (F-23) | none — public endpoints |

Nothing else leaves the machine. There is no analytics, no CDN font fetch at runtime, no favicon fetching (a deliberate privacy rule stated in `PRODUCT.md` and `README.md`), and no third-party script in the frontend.

---

## 9. Where the founder-facing value actually lives in the code

If the thesis is "help a founder understand what already exists and decide what would be different", then the value is concentrated in five places — and only two of them are currently productised:

1. **The archive itself** — 1,282 researched, human-reviewed filings with a live URL, category, founded date and a one-shot description (`backend/data/ideasexist.db`, `startups`). This is the only asset that cannot be rebuilt in a weekend.
2. **The trust layer** — tri-state liveness (`verify.py:30-77`), the 3-strike-never-delete rule, and the human-only `verified` stamp (`verify.py:154`). This is the differentiator the code takes most seriously; `PRODUCT.md` calls it "the product".
3. **Search relevance** — `lib/search.ts`, after the dogfood cycle, is the piece that makes "does THIS exist?" answerable at all (exact match first, dead last, stars only as tie-break).
4. **The dossier** — `startup-detail.tsx` is the closest thing to "research output": metadata, evidence links, freshness, and a "More like this" block. It is a modal, not a deliverable, so nothing survives the session.
5. **The freshness surfaces** — `last_checked` on every card, the "Recently verified / Dead recently" strips, and the `/api/stats` counters. Honesty about staleness is the trust product's raw material.

**What is missing where the value would actually be captured:** there is no "these are the closest alternatives to *your* idea", no "here is why each one matched", no side-by-side comparison, no export, and no stable URL for a single product (`/products/<slug>` does not exist — the app is one route). The archive is strong; the *decision support* layer the revamp plan describes has almost no code behind it yet.

**Phase 3 correction (2026-09-15):** the *backend* half of that gap is now closed — `POST /api/compare` produces the side-by-side gap table, `GET /api/export/{markdown|json|csv}` exports it, and `GET /api/startups/{slug}` is the stable per-product endpoint the frontend's `/products/<slug>` route will read. What is still missing is the **frontend** on top of it: there is no gap-table view, no export buttons and no `/products/<slug>` route in the app yet, and search-with-reasons is Phase 4. Those are Phases 4–6 and stay blocked until the Phase 5 backend gate is PASS.

**Phase 4 correction (2026-09-16):** the *backend* half of point 3 — "the piece that makes 'does THIS exist?' answerable at all (exact match first, dead last, stars only as tie-break)" — is now server-side too: `GET /api/search` (F-18) returns the same ordering contract **plus a per-result `reason`**, which is what the §11 premise "Search relevance needs classification, not just ranking" asked for and what `lib/search.ts` still cannot produce. `lib/search.ts` is deliberately untouched and stays the client path for a small archive (the plan keeps it); the two share the same invariants (exact name first, dead/pivoted last, stars as a tie-break only, AND-across-terms with a worst-term score) and the intentional differences are named in `app/search.py`. What is still missing is the **frontend** that renders the reasons — Phase 6, still blocked until Phase 5 is PASS.

---

## 10. Technical debt and risks (code-verified)

| # | Item | Evidence | Impact on the revamp |
|---|---|---|---|
| 1 | ~~**No evidence/provenance model.** Three tables only.~~ **Resolved in Phase 1 (F-02/F-05):** four tables; `evidence` added; `provenance` and `date_source` columns added. | `db.py` | Unblocks the evidence-backed research result — Phase 2 writes the rows. |
| 2 | ~~**LLM prose is indistinguishable from fact.**~~ **Resolved in Phase 1 (F-05):** `enrich.stamp_provenance()` marks every payload carrying LLM-drafted text `machine_drafted`, applied inside `_upsert` as a safety net; `mark_human_confirmed()` is the human half (Phase 2 wires it to the founder confirm path). The UI label is Phase 6. | `enrich.py` | The "machine-drafted vs human-confirmed" rule now has a schema to sit in. |
| 3 | **`founded` is often a domain-registration date, not a founding date.** Live rows: Notion `2000-11-01` (founded 2013), Zoom `1996-10-18` (founded 2011). Source order is LLM → Wayback → RDAP. **Phase 1 (F-04) now records WHICH branch produced the date, in `date_source`; the live rows are still unmigrated and the UI still presents the date as a founding year — that half is Phase 6.** | `website.py`, live DB | Half-fixed: the data can express the distinction; the display is Phase 6. |
| 4 | **99.7% verified, 0 dead.** The trust model is proven mechanically but never actually exercised at scale against real deaths; the "dead" surfaces are untested with data. | live DB | The revamp's dead-vs-live story is currently theoretical. |
| 5 | **Client-side search ceiling ~3,000 rows.** Measured 22 ms/term at 1,292, 70 ms at 5,000. Beyond that, `LIST_LIMIT_DEFAULT` truncates and the UI banners it. | `main.py:129-146`, `page.tsx` truncation banner | Any "add evidence + more sources" plan must decide FTS5 vs staying capped. |
| 6 | **Single-page = no canonical product URL.** Everything is `?q=` state on `/`. | `frontend/app/` (one page + SEO routes) | Blocks `/products/<slug>`, sharing, SEO, and the hosted-archive option. |
| 7 | **Duplicates are detected but not resolvable in-app.** A CLI script exists; there is no admin merge queue. 6 same-name groups remain by design. | `backend/scripts/merge_duplicates.py`, live DB | The revamp's "identity cleanup" phase needs a UI, not just a script. |
| 8 | **`jobs` queue is in-process.** Restart = interrupted jobs marked failed; a job cannot be resumed. | `seeder.py` `recover_interrupted_jobs` | Fine locally, a hard constraint the moment anything is hosted. |
| 9 | **No CI; Windows-only test runner.** | `README.md`, `scripts/verify.mjs` | Verification of any new work is manual. |
| 10 | **Batch sources are thin.** 1,229 of 1,282 rows came from website seeding; only 57 rows have a GitHub repo, so "stars" — one of the five sort keys — is meaningful for 4.4% of the archive. | live DB, `lib/search.ts` | The revamp's "stars are metadata, not a ranking signal" instinct is already justified by the data. |
| 11 | **Topstartups scrape exists but is not in `SOURCES`.** The `jobs` table shows a `topstartups` seed run (35 ok / 38 skipped / 6 failed) but `seeder.SOURCES` only exposes four sources. | `seeder.py:418-423`, live `jobs` rows | Dead/legacy path; the UI cannot re-run it. |

---

## 11. Consistency check against the revamp plan's premises

| Revamp premise | Verified in code? |
|---|---|
| "The current `Verified` state carries multiple meanings." | **Yes.** One `verified` integer + one `verified_at`; no separate reachable/evidence-found/repo-active/identity-confirmed dimensions. |
| "Search relevance needs classification, not just ranking." | **Yes.** `lib/search.ts` ranks well (exact first, dead last) but produces no *reason* per result — no "exact name match" label anywhere in the frontend. |
| "Stars are used as a primary ranking signal." | **Partly.** Stars are the tie-breaker and the `top` sort's second key, and only 4.4% of rows have them. The plan's own framing slightly overstates the current weight. |
| "Details are modal-only; no canonical dossier route." | **Yes.** One route; detail is a modal; "Share Entity" copies `/?q=<name>`. |
| "LLM prose is treated as fact." | **Fixed in the backend by Phase 1 (F-05)** — `provenance` is stamped `machine_drafted`; the UI label is Phase 6. |
| "Duplicates exist and contradict each other." | **Mostly resolved.** 10 groups merged; 6 same-name/different-company groups remain, correctly flagged, not merged. |
| "Dead entries retained." | **Mechanically yes, empirically empty.** 0 dead rows today. |

---

## 12. Coverage statement — what was read, what was not

**Read in full:** every file under `backend/app/`, `backend/scripts/`, `backend/tests/`, all of `frontend/app/`, `frontend/lib/`, all 34 `frontend/components/` (including `components/ui/`), `scripts/`, and the root docs (`README.md`, `PRODUCT.md`, `PROJECT.md`, `DESIGN.md`, `DEPLOYMENT.md`, `CHANGELOG.md`, `BACKEND-REMEDIATION.md`, `deploy-readiness-report.md`, `ORIGINAL_REQUEST.md`, `IDEA.md`, `revamp-plan.md`, `Revamp-thinking.txt`), plus `docs/research-features-ux.md`, `docs/research-ui-personality.md`, `docs/security-audit-2026-08-10.md` and `dogfood-output/*.md`.

**Read as data, not prose:** `backend/data/ideasexist.db` (queried directly — the numbers in §3), `backend/data/seed_famous.json`, `backend/data/seed_design_library.json`, `backend/data/topstartups_checkpoint.json`.

**Deliberately not read (not hand-written source):** `node_modules/`, `frontend/package-lock.json`, `package-lock.json`, `frontend/tsconfig.tsbuildinfo`, `scripts/lh-*.json` (Lighthouse dumps), `frontend/.mimosa/` hook-state baselines, `.agents/`, `.hermes/`, `.openclaw/`, `.zcode/`, `.impeccable/` tool state, `frontend/public/sky/*.svg`, and `backend/data/ideasexist.db.*` backups (superseded snapshots of the same schema).

No file in the two application trees was skipped.
