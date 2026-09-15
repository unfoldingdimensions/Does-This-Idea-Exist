# Codebase Comprehension — IdeaExists / "Does this Startup Exist"

**Prepared:** 2026-09-14
**Repo:** `E:\New-Personal-Projects\Does this Startup Exist`
**Method:** full read of every hand-written source file in `backend/`, `frontend/`, `scripts/`, plus the project docs, changelog and prior dogfood reports. No file in those trees was skipped (see §12 for the exact list and for generated/vendored paths that are not hand-written source).

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
  app/            the whole server (10 modules, ~1,600 LOC of hand-written Python)
    config.py     env-driven settings, validated at boot
    db.py         schema v1 + connection + URL identity normalisation
    main.py       FastAPI app, all routes, admin gate, rate limiting, auto-verify
    seeder.py     job queues + workers, batch sources, job persistence/recovery
    verify.py     the liveness pass + the human-approval queue
    enrich.py     seed orchestration, LLM output bounding, upsert
    github.py     GitHub REST client
    website.py    homepage fetch, text extraction, Wayback + RDAP date lookups
    llm.py        OpenAI-compatible chat client for profile drafting
    netguard.py   SSRF guard + size-capped GET
  data/           ideasexist.db (git-ignored) + bundled seed lists + backups
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

## 3. Data model — exactly three tables

`backend/app/db.py:9-57` creates the entire schema. There is no migration framework; `init_db()` runs `executescript(SCHEMA)` with `CREATE TABLE IF NOT EXISTS`, and the file header states the rule: **additive changes only**.

### `startups` (the archive) — 20 columns
`id, name, tagline, description, category, website_url, github_url, founded, stars, language, status, verified, verified_at, last_checked, check_failures, source, created_at, updated_at`
Two unique indexes: `lower(website_url)` and `lower(github_url)`.

### `verify_log` (append-only audit trail)
`id, startup_id, checked_at, website_ok, github_ok, notes`. Written once per entry per verification pass; pruned to a 90-day window by the pass itself (`verify.py`, retention statement at the end of `run_verify_job`).

### `jobs` (job history that survives restarts)
19 columns: identity, `kind`, `source`, `params_json`, counters, `errors_json`, `ok_urls_json`, `skipped_urls_json`, timestamps, `breakdown_json`, `result_json`. The in-memory `JOBS` dict in `seeder.py` is mirrored here on every state change.

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
- `GET /api/startups` — the whole archive as one JSON array. Server accepts `?q=`, `?category=`, `?limit=`, `?offset=` but the frontend uses none of them for filtering; it pulls everything and filters client-side. Default limit **3,000**, max 5,000 (`main.py:LIST_LIMIT_DEFAULT`). Truncation returns HTTP 200 with a short body — the frontend detects it by comparing against `/api/stats`.

**Owner-gated reads (`X-Admin-Token`):**
- `GET /api/admin/check`, `/api/admin/seed/jobs`, `/api/admin/seed/status/{id}`, `/api/admin/verify/suggested`, `/api/admin/verify/status/{id}`, `/api/admin/verify/current`

**Mutations (token required because `MUTATION_AUTH` defaults on):**
- `POST /api/seed/github`, `/api/seed/website`, `/api/verify/run`
- `POST /api/startups/{id}/verify|unverify|dead`
- `POST /api/admin/seed`, `POST /api/admin/verify/approve`

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

### 4.5 Verification — the product's trust engine (`verify.py`)
`check_url_ok` (`verify.py:30`) and `check_github_ok` are both **tri-state** `(ok, note, skipped)`:
- Only a genuine **404/410** is a real strike.
- Bot walls (401/403), rate limits (429), 5xx and network errors are **skips** that reset the streak — the code documents a real incident where Cloudflare 403s dead-filed WHOOP and Capterra.
- Three consecutive strikes flip `status` to `dead`. Nothing is ever deleted.
- A `verified=1` row is **protected from automation**: it never accumulates strikes and never auto-flips; a failed check surfaces in `failed_list` as a re-check item instead.

The human gate is `approve_suggested` (`verify.py:154`) — the **only** bulk writer of `verified=1` — plus the single-row endpoint. `list_suggested` (`verify.py:137`) is the queue: `verified=0 AND status='active' AND check_failures=0`.

`run_verify_job` (`verify.py:205`) walks every row, buckets its *current* state into a verified/unverified/dead breakdown, commits **per row** (so a parallel seed is never blocked by a long write lock), writes a `verify_log` row per entry, prunes the log to 90 days, and persists live progress to `jobs` as it goes.

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

---

## 10. Technical debt and risks (code-verified)

| # | Item | Evidence | Impact on the revamp |
|---|---|---|---|
| 1 | **No evidence/provenance model.** Three tables only. | `db.py:9-57` | Blocks "evidence-backed research result" and the whole Phase 4 of the revamp plan. |
| 2 | **LLM prose is indistinguishable from fact.** `description`/`tagline`/`category`/`founded` come from `llm.py` with no stored provenance flag. | `enrich.py:86-160` | The revamp's "machine-drafted vs human-confirmed" rule has no schema to sit in. |
| 3 | **`founded` is often a domain-registration date, not a founding date.** Live rows: Notion `2000-11-01` (Notion was founded 2013), Zoom `1996-10-18` (Zoom was founded 2011). Source order is LLM → Wayback → RDAP. | `website.py:102-145`, live DB | A "founded" column used for filtering/sorting is misleading — a direct provenance bug. |
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
| "LLM prose is treated as fact." | **Yes.** No provenance column or UI label exists. |
| "Duplicates exist and contradict each other." | **Mostly resolved.** 10 groups merged; 6 same-name/different-company groups remain, correctly flagged, not merged. |
| "Dead entries retained." | **Mechanically yes, empirically empty.** 0 dead rows today. |

---

## 12. Coverage statement — what was read, what was not

**Read in full:** every file under `backend/app/`, `backend/scripts/`, `backend/tests/`, all of `frontend/app/`, `frontend/lib/`, all 34 `frontend/components/` (including `components/ui/`), `scripts/`, and the root docs (`README.md`, `PRODUCT.md`, `PROJECT.md`, `DESIGN.md`, `DEPLOYMENT.md`, `CHANGELOG.md`, `BACKEND-REMEDIATION.md`, `deploy-readiness-report.md`, `ORIGINAL_REQUEST.md`, `IDEA.md`, `revamp-plan.md`, `Revamp-thinking.txt`), plus `docs/research-features-ux.md`, `docs/research-ui-personality.md`, `docs/security-audit-2026-08-10.md` and `dogfood-output/*.md`.

**Read as data, not prose:** `backend/data/ideasexist.db` (queried directly — the numbers in §3), `backend/data/seed_famous.json`, `backend/data/seed_design_library.json`, `backend/data/topstartups_checkpoint.json`.

**Deliberately not read (not hand-written source):** `node_modules/`, `frontend/package-lock.json`, `package-lock.json`, `frontend/tsconfig.tsbuildinfo`, `scripts/lh-*.json` (Lighthouse dumps), `frontend/.mimosa/` hook-state baselines, `.agents/`, `.hermes/`, `.openclaw/`, `.zcode/`, `.impeccable/` tool state, `frontend/public/sky/*.svg`, and `backend/data/ideasexist.db.*` backups (superseded snapshots of the same schema).

No file in the two application trees was skipped.
