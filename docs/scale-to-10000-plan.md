# Scale to 10,000 — Plan

**Status:** draft for owner decisions · **Date:** 2026-09-18
**Depends on:** `docs/teardown-spec.md` (field contract + trust model) · `docs/gap-table-format.md` (output shape) · `docs/phase-ledger.md` (how work is verified here)
**Evidence base:** measured DB baseline (below) + read-only code recon at `.openclaw/tmp/scale/recon.md`
**Funnel engine:** `scripts/site_liveness_audit.py` (built 2026-09-18; commits `b9fba6b`, `2ee968b`, `f4d70ab`)

### Status

| Phase | State | Evidence |
|---|---|---|
| **A** approval model | **done** 2026-09-18 | `approval_source` / `approved_by` / `approval_note` added as a separate non-enrichment column list; `verify.approve_machine()` is the funnel's admission path; `compare.badges()` withholds Admin Verified from a machine row; frontend reads "Machine Approved"; decision recorded in `teardown-spec.md` §8.4. Live archive migrated additively 40 -> 43 columns, 1,258 rows unchanged. Commit `805a7da`; gate `npm test` ALL PASS (backend 243/243, e2e 239/239) |
| **B** funnel dry-run | **done** 2026-09-18, re-run 09-19 after D2 | 1,258 rows: **admit 1251 · reject 0 · admin 7**. Zero rows a human admitted that the funnel would reject. 7 rows were recovered by the renderer; the 7 admin rows are 4 walled + 2 unreadable + 1 moved-owner (Hysolate -> Fortinet). Archive admission fingerprint unchanged before/after, both runs. D2 refined 2026-09-19 per §3.3/§3.4 (7 triggers -> 5, banned category moved to auto-reject, seizure added, disagreement removed). `.openclaw/tmp/scale/phaseB/liveness-2026-09-19-0013/phaseB-report.md` |
| **C** sourcing + staging | next | needs D1/D2 confirmed in the form implemented, then 3,000 candidates with no publishes |
| **C0** company gate | **done** 2026-09-19 | built and measured on real candidates before being trusted, per §3.5: on the pilot's 50, 10 non-companies rejected (all hand-verified), 0 inflated queue. Wired into both `audit` and `verify` and into the report. `selftest` 47/47 |
| **D** enrichment pilot | blocked on C | 200 rows, measures $/row - the number D3 needs |
| **P** platform unblock | not started | §7.1 paging, §7.2 FTS5, §7.7 sitemap |

**D1/D2 as implemented in Phase A** (override any of this and A is re-done): approval provenance is an explicit column rather than automation writing `verified` silently; the admin queue is the 7 triggers in §3.3.

---

## 0. What "scaling" actually means here

Three different problems hide behind "10,000 websites". They have different costs and must be phased
separately: the cheap one (liveness) is already solved, the existing-but-unscalable one (enrichment)
is a plumbing problem, and the expensive one (volume) is a budget problem.

| # | Problem | Today | At 10k | Real cost driver |
|---|---|---|---|---|
| **A** | Acquire candidates | 1,258 rows | ~13,000 candidates to net 10,000 live | sourcing breadth + dedupe |
| **B** | Prove they are alive and real | 1,254 admin-verified by hand | ~10,000 auto-approved, hundreds to admin | HTTP + render throughput |
| **C** | Enrich them | machinery exists, coverage ~0% | 10,000 × six sourced fields | **fetches + LLM tokens, unmetered today** |
| **D** | Serve them | one sitemap URL, 3,000-row read ceiling | 10k pages, searchable, indexable | API paging, FTS, sitemap, build |

**Measured baseline (2026-09-18, read-only).** 1,258 startups · 1,254 `verified=1` · 4 unverified ·
all `status='active'` · 11 distinct categories · 9,430 `verify_log` rows spanning 2026-08-08 → 09-17.

| Layer | Coverage today |
|---|---|
| Identity | `name` 100% · `category` 100% · `website_url` 100% · `founded` 99.6% · `description` 98.6% · `tagline` 98.4% · `github_url` 4.5% |
| Rich (the product's actual value) | `features_json` 0.3% · `pricing_json` 0.2% · `positioning` 0.2% · `target_users` 0.1% · `problem_statement` **0%** · `activity_summary` **0%** · `canonical_domain` **0%** · `entity_type` **0%** · `aliases` **0%** |
| Evidence | **27 rows total** (11 negative, 10 feature, 5 pricing, 1 positioning) |
| Reviews / competitors / use cases | no reviews rows, no competitor table, no use-case field |

So the directory is at 1,258 rows and the *content* is near zero beyond a description. A plan that
only grows the row count multiplies the weakest part of the product.

**Throughput ceiling today.** The app's verify pass is one serial worker: `1,283 rows in 1,220s`
(1.05/s) best case; a bad run took 3,336s (0.21/s). A 10k pass at that rate is **2.6–4.5 hours**, and
so is every weekly re-verify. The new auditor did 1,266 rows in **92s (13.7/s)**. Porting the funnel
onto it is the single biggest throughput win available, and it is already built and tested.

### 0.1 Hard blockers found by recon (all pre-existing, none caused by volume planning)

These bite before 10k, and several bite at 2–3k. Fixes are in §7.

| # | Blocker | Where |
|---|---|---|
| 1 | `/api/startups` **truncates at 3,000 rows (max 5,000) and still returns HTTP 200** — at 10k the directory silently serves ~30% of the archive | `main.py:640, 653-686` |
| 2 | Frontend fetches the **entire archive per page load** and filters client-side with Fuse; ~950 KiB raw / 225 KiB gzip at 1.3k → **~7 MB at 10k**, re-introducing documented 120–180 ms/keypress jank | `api.ts:52-55`, `page.tsx:214-233`, `search.ts:20-27` |
| 3 | Search is a **Python linear scan** over `SELECT *`; FTS5+bm25 is named as the next step but not built | `main.py:735-739`, `search.py:118-125` |
| 4 | Seed jobs are **serial, single-threaded, capped at 500 candidates/job**, one **synchronous LLM call per candidate** → 10k needs ≥20 jobs and days of wall-clock, with no checkpoint/resume | `seeder.py:38, 288-296, 301-337, 449-451` |
| 5 | **No LLM cost control at all** — no token accounting, no $ cap, no concurrency limit; up to 2×8,000-token attempts per call | `llm.py:150-180`, `docs/llm-gateways.md` §6 |
| 6 | SQLite contention: three writer threads, connection re-opened and committed **per candidate/row**, only `busy_timeout=5000` | `db.py:152-165`, `seeder.py:301-337` |
| 7 | Dedupe is **URL-only**, with an **O(n) full-table scan** fallback; no name/alias/domain merge, no merge tool | `db.py:98-99, 236-262` |
| 8 | Teardown capture is **JIT and serialized across all competitors** — by design. 10k teardowns through it is infeasible | `capture.py:1-8`, `seeder.py:92-130` |
| 9 | Sitemap emits **exactly one URL**; every `/products/<slug>` page is client-rendered and unindexed | `sitemap.ts:6-15` |
| 10 | Approval does not batch: `ApproveIn.ids` capped at 1,000, the suggestion list returns unnarrowed (10k rows at scale), and the verify pass walks every row serially | `main.py:420-423, 427-479`, `verify.py:208-331` |

Two more worth naming: evidence rows **never expire or dedupe** (`reviewed_at` is declared but never
written, `evidence.py:67`), and the rate limiter/lockout is **process-local in-memory**
(`main.py:198-261`) — fine now, wrong for any multi-worker deployment.

---

## 1. Decisions this plan needs from you

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **D1** | **Approval model.** `teardown-spec.md` §8.1 currently makes admin approval the *admission ticket* and states automation never stamps `verified=1` — the codebase enforces that (`verify.py:157-206`), and `enrich.mark_human_confirmed` is deliberately **not** wired to the liveness gate (`enrich.py:96-99`). You are asking automation to admit the clean majority. | (a) let automation write `verified=1`; (b) add explicit `approval_source` / `approved_at` / `approved_by` and make machine approval its own distinguishable stamp | **(b).** The trust model only survives if "a robot let this in" is visible on the record. Also record the decision in `teardown-spec.md` §8.1 — that spec explicitly says new items go there, not into a phase prompt |
| **D2** | **"Genuinely notorious" — the admin-queue trigger list** | §3.3 | adopt the 7 listed triggers; everything else auto-approves |
| **D3** | **Enrichment budget.** There is no metering today (blocker 5), so the number is currently unknowable | measure first, then choose: full depth on all 10k · full depth on top N + lighter depth elsewhere · on-demand only | Phase D measures $/row before any volume commitment (§5.5) |
| **D4** | **Publish timing** | publish as soon as liveness passes (content lands later) · hold until enriched | publish-on-liveness, with a visible `enrichment_state` so "no teardown yet" is a state, not a broken page |
| **D5** | **Storage** | SQLite (WAL) · Postgres for the archive | SQLite survives read-heavy 10k; revisit only if writer concurrency grows (§7.5) |

---

## 2. The funnel you described, mapped to the code

*Only walled and genuinely notorious websites go to the admin; the rest are approved by an HTTP pass;
the ones that fail go to the renderer; then the ones left go to the admin.*

```
        ┌──────────────┐
   →    │ 0. INGEST    │  candidate → staging table (never straight into `startups`)
        │  + DEDUPE    │  dedupe: canonical_domain → website_url → github_url → alias/name
        └──────┬───────┘
               ▼
        ┌──────────────┐   clean LIVE            ┌────────────────────────────┐
        │ 1. HTTP PASS │ ──────────────────────▶ │ AUTO-APPROVE               │
        │ (auditor)    │                         │ approval_source='machine'  │
        └──────┬───────┘                         │ published                  │
               │ not clean LIVE                  └────────────────────────────┘
               ▼
        ┌──────────────┐   resolves to LIVE      ┌────────────────────────────┐
        │ 2. RENDER    │ ──────────────────────▶ │ AUTO-APPROVE (same stamp,  │
        │ (Chrome)     │                         │ render evidence recorded)  │
        └──────┬───────┘                         └────────────────────────────┘
               │ walled / notorious / unresolved
               ▼
        ┌──────────────┐                         ┌────────────────────────────┐
        │ 3. ADMIN     │ ──────────────────────▶ │ human approve / reject /   │
        │ QUEUE        │                         │ re-queue, with a note      │
        └──────────────┘                         └────────────────────────────┘

   machine-rejected (404 / parked / repurposed) → status='dead', kept forever as a negative
   record, never deleted (existing repo rule), excluded from listings.
```

Both passes write the same receipt: a render-approved row records its rendered capture (final URL,
title, text sample) into `verify_log.notes` and evidence rows, so any machine approval can be
re-examined later — the same discipline as the drop manifest of 2026-09-18.

### 2.1 Stage 1 — HTTP pass (auto-approver)
`scripts/site_liveness_audit.py audit`: multi-UA, SSRF-guarded, cache-backed, resumable, 13.7/s
measured. Rules already in production: 200-is-not-life · 403-is-not-death · parked/for-sale/lander/
server-default/soft-404 · repurposing classes A/B/C · brand-aware challenge guard. Auto-approve on
`state == LIVE`.

### 2.2 Stage 2 — renderer pass (resolver)
Only non-LIVE rows go here — **~10–30% of a fresh candidate list**. Reuses the committed pattern
(`puppeteer-core` + installed Chrome, rendered DOM + visible text), judged by the **same** rules. In
its last run it settled 16 of 18 rows HTTP could not, and exposed three rule gaps now fixtured.

### 2.3 Stage 3 — admin queue
Only the exception path (§3.3). Everything else is machine-approved.

### 2.4 What already exists, and what is actually missing

The recon's most useful correction to the obvious plan: **the enrichment machinery is largely
built**. The work is not "write an enrichment pipeline" — it is "make the existing one batch-capable,
metered, and complete".

| Need | Already exists (cited) | What is actually missing |
|---|---|---|
| Liveness classification | auditor (rules + fixtures, now a shared module: `backend/app/liveness_rules.py` — canonical copy in the app package, loaded by the CLI too) | ~~emit machine-approval output~~ **done 2026-09-19** — `POST /api/admin/funnel/import` admits a run's clean majority via `verify.approve_machine` and queues the exceptions; the verify pass also runs the same content rules on 2xx bodies (`VERIFY_CONTENT_CHECK`) |
| App-side tri-state check | `verify.check_url_ok` (404=strike, wall/429/5xx=skip) | run it on the parallel engine, not one serial worker |
| SSRF guard | `netguard.safe_get` (2 MB cap, 5 redirects), auditor `guard_url` | — |
| Page plan for a teardown | `pages.fetch_pages` (homepage → /pricing → /docs), `readable/enumerating` | — |
| Teardown extraction | `teardown.write_teardown` + confidence constants (features 5–10, positioning, pricing plan-by-plan) | nothing structural |
| Negative claims | `negatives.probe_absence` — deterministic first, LLM second, enumerating-page rule | — |
| Reviews | `reviews.capture` (Reddit JSON+RSS, fetch-and-report, never score, walls = skip, one evidence row per review) | more sources; batch path |
| Evidence writer | `evidence.write_evidence` (mandatory `source_url`, closed 10-type vocab) | only 5 of 10 types are ever written; `reviewed_at` never set |
| LLM client + prompts | `llm.llm_json`, `llm.teardown_brief`, `SYSTEM_PROMPT`, `TEARDOWN_SYSTEM_PROMPT` | **no token accounting, no budget, no concurrency cap** |
| Jobs / progress / recovery | `seeder` kind-scoped queues, `jobs` table, `recover_interrupted_jobs` | batch kinds; parallel workers; checkpoint/resume |
| Dedupe identity | `db.normalize_url`, unique indexes on `lower(website_url)`/`lower(github_url)` | `canonical_domain` (0% populated), aliases, name-level resolve, a merge tool |
| Approval gate | `verify.list_suggested` / `approve_suggested` | machine-approval stamp (D1); batch-friendly queue |
| Teardown driver | `capture.capture_teardown` — **JIT only**, triggered by `/api/compare` | a batch/pre-warm capture path (blocker 8) |

---

## 3. Stage rules

### 3.1 Auto-approve (machine)
All of: reachable (HTTP 2xx/3xx, or a successful render); not parked/for-sale/lander/server-default/
soft-404/seized; not repurposed (A/B/C); not a banned category; no brand-vs-content mismatch;
identity unambiguous (one row per domain, no alias collision).

### 3.2 Machine-reject (no human involved)
Hard 404/410 · parked / for-sale / registrar lander · repurposed or monetised redirect ·
server-default page · **legal seizure / takedown notice** · **banned category**. Action: the row is
not listed (`status='dead'` for the dead cases; a `BANNED` verdict for the policy cases, because the
site is alive and calling it dead would be a lie), row and evidence kept.

**Banned category is enforced two ways, and the content rule is only a backstop.** The primary
enforcement is an **intake filter** on the candidate's own metadata (source list and declared
category) during ingest. The content rule exists for what intake cannot see, and it is deliberately
narrow: markers are commercial-OFFER phrasing (`casino bonus`, `free spins`, `poker room`, `sports
betting`, `escort service`, `torrent download`, `payday loans`), never topic vocabulary, and a marker
counts only in the **title** or as **two distinct** hits. See §3.4 for why that caution is not
hypothetical.

### 3.3 "Genuinely notorious" → admin queue (D2 - owner-confirmed 2026-09-19)
1. **WALLED after render** - every client refused, the renderer included.
2. **Moved to a different owner** - the stored domain now serves a live site with no token of the
   company anywhere on it. An acquisition that keeps the brand (guildeducation.com -> guild.com) is
   an ordinary redirect and stays LIVE; one that loses it is a policy call, so a human decides.
3. **Identity conflict at domain level** - two rows claim one domain, or an exact name+domain
   collision. Deliberately NOT a fuzzy name match: two unrelated companies may share a name, and the
   app already renders that as a duplicate group. *(Specified here; implemented with the
dedupe/staging work in Phase C, since `canonical_domain` is still 0% populated.)*
4. **Unresolved after render** - `UNKNOWN` (blank page, firewall 502 on a foreign domain, JS redirect
   shell whose target will not resolve).
5. **Sampled-QA hit** - anything the random audit flags (§6.2).

**Removed: "automation disagreement".** The admin reviews a row only when the render pass ALSO
cannot resolve it. A disagreement between the passes is resolved by the render - that is the render's
whole job - and the provenance column already records that the row was admitted by `funnel:render`
(`approved_by`), so those rows stay auditable without a human gate.

### 3.4 The banned-category rule, and the seven companies it nearly deleted

Worth recording, because it is the cheapest lesson this plan has produced. The first draft of the
banned-category rule scanned topic vocabulary and produced **7 machine-rejects on this very archive,
every one of them a real company**:

| Rejected | Actually is | Matched on |
|---|---|---|
| Cockroach Labs | a database | `gambling` + `streaming` (customer verticals) |
| Conduktor | a Kafka tool | `adult` + `streaming` |
| PharmEasy, Pelago | health / pharmacy | `pharmacy` + `adult` |
| Aura | digital security | `adult` + `loan` |
| Gametime | event tickets | `casino` + `torrent` |
| Brightside | a fintech that exists to **replace** payday loans | one mention of `payday loans` |

A company's site is allowed to name the industries it serves. Word-level scanning cannot tell "we are
a casino" from "we serve casinos", and no amount of two-tier tuning fixes that - the distinction is
about **offer vs topic**, not frequency. Hence: offer phrasing only, title-or-two-hits, intake filter
first. All seven cases are now `selftest` fixtures, so the rule cannot regress into rejecting them
again (`selftest` is 50/50 — the 47 parity fixtures plus the company-gate cases).

### 3.5 The company gate - "is this a company, or a project page?"

**Why it exists.** The liveness funnel answers "is this link alive, and whose is it". It cannot
answer "is this a company" - and the pilot-50 run put a price on that. A GitHub-`homepage` channel
yielded reactnative.dev, d3js.org, pptr.dev, ohmyz.sh, caddyserver.com, an awesome-list and a
Telegram channel: every one correctly LIVE, not one of them a startup. The gate runs on the same
captures, before admission and before enrichment, so a docs page never costs three more fetches and
two LLM calls.

| Verdict | Meaning | Funnel action |
|---|---|---|
| `COMPANY` | commercial intent present (pricing, demo request, careers, buy now, trusted by, case studies) | admit-eligible |
| `UNVERIFIED` | no project markers found, but no commercial evidence either | admit-eligible - **not** a queue |
| `NOT_COMPANY` | a project-hosting host, or three or more distinct project/docs markers with no commercial signal | rejected at intake |
| `REVIEW` | free hosting (netlify.app, vercel.app, ...): a company may use it, or a side project may | human |

The order is deliberate and counter-intuitive: project-host check first, then free-host, then
**commercial intent wins** (so a real company with a docs section stays a company), then the marker
cluster, then unverified.

**UNVERIFIED is deliberately not a queue.** The first draft sent every row without commercial
vocabulary to REVIEW, which on these 50 candidates produced 23 review items - more than the 17 the
liveness funnel was already escalating. "We could not read the page" and "we read a personal
project" are different things, and only the second is this gate's business. The gate *removes obvious
non-companies*; the admin path still decides everything else. A channel is judged by what share of
its rows come back `COMPANY`.

**Measured on the pilot's 50 real candidates** (offline, from the same captures):
17 `COMPANY` - 23 `UNVERIFIED` - 10 `NOT_COMPANY` - 0 `REVIEW`. All ten rejections hand-checked as
genuinely not companies: syncthing, iptv-org.github.io, reactnative.dev, ohmyz.sh, pptr.dev,
hellogithub.com, t.me/g4f_channel, awesome-cpp, github.github.com/spec-kit, caddyserver.com.

Two known imprecisions, recorded rather than hidden: **d3js.org came back `COMPANY`** (it matched
"pricing" somewhere on the page but is a library), and **java.doocs.org / cyc2018.xyz /
learn.shareai.run passed as `UNVERIFIED`** because the marker vocabulary is English-centric and those
are docs/notes sites. The consequence is the important part: **the content gate cannot be the only
control on a noisy channel - channel selection is the primary control, and the gate is the backstop.**

---

## 4. Stage A — acquiring ~13,000 candidates

Target **10,000 accepted**. Raw lists are dirtier than the current archive: assume **70–85% live yield**
on crawled lists, ~95% on curated lists → **13,000–15,000 candidates**.

| # | Channel | Mechanism | Candidates | Quality | Notes |
|---|---|---|---|---|---|
| 1 | GitHub | existing `github_search` + topics/trending + npm/PyPI `homepage` | 2,500–4,000 | high | **token required** (unauth search = 10/min, repo API 60/hr); `THROTTLE_S=1.0` is per-URL and hardcoded |
| 2 | Curated lists | `awesome-*`, "alternatives to X" indexes | 1,500–3,000 | high | cheapest per accepted row |
| 3 | Launch feeds | Product Hunt, BetaList, HN "Show HN" (Algolia) | 2,000–3,500 | med-high | store the launch permalink as evidence |
| 4 | Accelerator batches | public YC + similar directories | 1,000–2,000 | high | one-off import then steady state |
| 5 | App stores | mobile-only products (F-20 allows NULL `website_url`) | 1,500–2,500 | medium | needs the store-listing identity rule |
| 6 | Competitor graph | follow accepted rows' "alternatives/compare" pages | 2,000–4,000 | high, focused | bounded depth 1 |
| 7 | Existing bundles | `seed_famous.json`, `seed_design_library.json` | ~300 | high | already wired |
| 8 | Long-tail crawls | directory/registry pages, wiki lists | 1,000–2,000 | low | most render/admin traffic |

**Rules for every channel:** candidates land in a **staging table**, never directly in `startups`;
dedupe on `canonical_domain` → `website_url` → `github_url` → alias/name (today only the middle two
exist, and `canonical_domain` is 0% populated); record `source` + `source_url` + `captured_at`;
respect `robots.txt` and provider ToS; per-host politeness. Deliverable: staging table + `SOURCES`
entries + a per-channel yield report so channels can be ranked by cost per accepted row.

---

## 5. Stage C — enrichment (existing machinery, made scalable)

### 5.1 The fields

| Field | Status | Contract |
|---|---|---|
| `description`, `tagline` | 98.6% / 98.4% today | backfill the tail |
| `category` | 100% | 12-slug whitelist (`enrich.CATEGORIES`); archive shows 11 |
| `positioning` (1 line) | 0.2% | `teardown.write_teardown`, sourced |
| `features_json` (5–10 flat) | 0.3% | one evidence row per feature |
| `pricing_json` (plan-by-plan + free tier) | 0.2% | one evidence row per plan; `pricing_captured_at` + `pricing_source_url` stamped |
| negatives (3–5) | 27 evidence rows total | `negatives.probe_absence`: enumerating-page rule, observation never verdict |
| reviews ("what users ask for") | none | `reviews.capture` → one evidence row per review, `classification` + `asks[]`, **never scored** |
| `problem_statement`, `target_users` | 0% | **written by no phase today** — new fill |
| `use_cases` | no field | new: `use_cases_json` + `evidence_type='use_case'`, mirroring features |
| `activity_summary` | 0% | derive from `verify_log` |
| `entity_type`, `canonical_domain`, `aliases` | 0% | **written by no phase today** — needed for dedupe/identity |
| competitors | — | archive-to-archive: the gap table diffs the founder's app against archive rows. Decision (D3-adjacent): curated `competitor_links`, or leave the founder to name rivals as today |

### 5.2 Pipeline (already implemented — this is the order to preserve)
`pages.fetch_pages` (homepage → /pricing → /docs, 3 fetches, tri-state read) → deterministic
extraction (`readable` / `enumerating`, JSON-LD, footer inventory) → `negatives.probe_absence`
(deterministic first, LLM fallback over *already-fetched text only*) → `llm.teardown_brief` →
`teardown.write_teardown` → `reviews.capture` → evidence rows via `evidence.write_many`.

### 5.3 What must be added
1. **A batch driver.** `capture.capture_teardown` is JIT-only and serialized across competitors
   (blocker 8). Teardown must become a pre-warm batch job with checkpoint/resume, not a
   first-visitor-triggered side effect.
2. **Metering.** Per-run token accounting and a $/row report, a concurrency cap, and a per-batch
   budget that hard-stops (blocker 5). `docs/llm-gateways.md` §6 already names usage/cost accounting
   as the missing piece.
3. **The empty columns.** `entity_type`, `canonical_domain`, `aliases`, `problem_statement`,
   `target_users`, `activity_summary`, `use_cases_json` — several are *already declared in the
   schema* and written by nothing.
4. **Evidence hygiene.** Dedupe on re-capture (today a 7-day re-capture just appends), a retention
   rule, `reviewed_at` actually set on human confirmation, and use the 5 declared-but-unused
   evidence types (`reachability`, `repo_created`, `homepage_claim`, `wayback_first`,
   `curator_confirmation`) — `reachability` in particular would make the funnel's own decisions
   first-class evidence instead of only a `verify_log` note.

### 5.4 Quality gates (non-negotiable)
Every claim sourced (`evidence.source_url`/`captured_at` are NOT NULL; `SourceRequiredError` enforces
it) · a negative is an observation about an **enumerating page** or `unknown` — a 404 on a guessed URL
is not evidence of absence · an empty shell is "we could not read it", never "they don't have it" ·
reviews quoted, never scored · badges attach to the record, never to a claim · `confidence`
distinguishes retrieval from assertion (existing constants: features 0.6, pricing 0.7, positioning
0.6, deterministic negatives 0.8, LLM negatives 0.5, unreadable 0.1).

### 5.5 Cost and time (measure, do not guess)
Phase D runs 200 rows end-to-end and reports seconds/row, tokens/row, $/row, and per-field accuracy
against human labels. Only then does 10k get a budget number. The current estimate to validate is
**3 page fetches + ~1 teardown call + review fetches per row, at up to 8,000 tokens/output-call**. If
the total does not fit, the fallback is **tiered depth** (full teardown on the highest-value N, the
lighter identity fields elsewhere) — never cutting the evidence rules.

---

## 6. Quality control at scale

1. **Liveness regression net.** The auditor's `selftest` (50 fixtures, every one a real regression)
   must stay 50/50. Every new real-world false positive becomes a fixture — that is how the four rule
   gaps of 2026-09-18 were closed, and the three the renderer found.
2. **Auto-approval error budget.** Proposed **<0.5%** false-approval rate, measured by sending a
   random sample of auto-approved rows to human QA every batch. A breach **stops the batch and
   tightens the rules** — it does not proceed with a known-bad rate.
3. **Enrichment sampling.** Per-field human review on a random sample per batch; per-field accuracy
   published. A field below its bar ships as `machine_drafted` with its confidence, not as verified.
4. **Stop-the-line.** Any batch breaching either budget halts the pipeline; the finding is recorded
   (phase-ledger style) and the rule is fixed before resuming.
5. **Reversibility.** Fresh evidence, backup, manifest, verified backup, every batch — the
   2026-09-18 drop is the template.

---

## 7. Fixes the platform needs (from §0.1)

| # | Fix | Why it is required before volume |
|---|---|---|
| 7.1 | **Replace the 3,000-row read ceiling with pagination** (`main.py:640, 653-686`) — or raise it and page properly; never truncate behind an HTTP 200 | At 10k the directory silently serves a third of the archive |
| 7.2 | **Server-side search + FTS5** (`main.py:735-739`, `search.py:118-125`), and stop shipping the whole archive to the browser (`api.ts:52-55`) | ~7 MB payload and client Fuse jank at 10k |
| 7.3 | **Batch/parallel orchestration** — parallel workers with checkpoint/resume, replacing serial 500-capped jobs (`seeder.py:38, 449-451`) | Days of wall-clock per pass otherwise |
| 7.4 | **LLM metering**: token accounting, $/row, concurrency cap, per-batch hard budget (`llm.py:150-180`) | Unbounded, unmetered spend today |
| 7.5 | **Write path**: chunked writes, keep per-row commits, raise/queue past `busy_timeout` (`db.py:152-165`); move to Postgres only if concurrent writers grow (D5) | "database is locked" backoff under batch load |
| 7.6 | **Identity/dedupe**: populate `canonical_domain`, add aliases, replace the O(n) `normalize_url` scan (`db.py:236-262`), add a merge tool | Duplicates at 10k are unrecoverable by hand |
| 7.7 | **Sitemap + indexable product pages** (`sitemap.ts:6-15`): emit all `/products/<slug>`, split the sitemap, make the pages crawlable | 10k pages that search engines cannot see is the point of the directory, lost |
| 7.8 | **Batch approval endpoint** for the admin path (`main.py:420-479`) and a narrowed queue payload | The admin queue must stay reviewable, not become a 10k-row wall |
| 7.9 | **Evidence hygiene**: de-dupe on re-capture, retention rule, set `reviewed_at`, use the unused evidence types (`evidence.py:20-31, 67`) | The evidence table is the product's asset; unbounded duplicates erode it |
| 7.10 | **Process-local rate limiting** (`main.py:198-261`) → shared store, if/when multiple workers exist | Silent under-enforcement after any horizontal scale |

---

## 8. Phases, each independently verifiable

| Phase | Scope | Acceptance criteria | Rollback |
|---|---|---|---|
| **A** | Approval model: `approval_source`/`approved_at`/`approved_by` + machine-approval path + badge exposure | additive migration idempotent; machine vs human approvals distinguishable in API and UI; the existing 1,254 rows unchanged; `teardown-spec.md` §8.1 updated as a recorded decision; smoke + functional pass | drop the new columns (additive only) |
| **B** | Funnel v2 dry-run over the **existing** 1,258 rows, publishing nothing | reproduces the 2026-09-18 outcome (the 8 dead/repurposed + Magdrive walled); auto-approval changes nothing about the current verified set; auditor `selftest` 50/50 | nothing published, nothing deleted |
| **C** | Sourcing harness + `candidates` staging; pull 3,000 candidates, **no publishes** | per-channel yield report; zero duplicates by `canonical_domain`; >95% of staged rows carry `source_url`+`captured_at` | truncate staging table |
| **D** | Enrichment pilot, 200 rows, six fields, end-to-end | measured s/row, tokens/row, $/row; per-field accuracy vs human labels; 100% of claims have evidence rows; **reports the real 10k budget (D3)** | delete pilot enrichment, keep rows |
| **P** | Platform unblock: §7.1 paging, §7.2 FTS5 search, §7.7 sitemap+indexable pages | 10k-row synthetic fixture served correctly by paged read; search p95 sane; sitemap lists every product page | revert frontend/API |
| **E** | Enrichment v2 + batch driver: use cases, negatives, competitors, reviews, metering, evidence hygiene | batch teardown with checkpoint/resume; budget hard-stop works; negatives all trace to enumerating pages; reviews quoted not scored; walls "listed but not fetched" | per-field revert |
| **F** | Scale to 10k in batches of 500–1,000 | every batch inside both error budgets; stop-the-line honoured; verified backup per batch; §7.3/7.4/7.5 proven under load | restore batch backup |
| **G** | Product surface at 10k: search UX, pagination, badges, performance budget | 10k pages build inside budget; badges render per §8.1 rules | revert frontend |

**Sequencing:** **A → B** first (they define who is allowed in, before any volume arrives). **D**
before **F** (F's budget depends on D's measurement). **P** must land before or with **F** — at 10k it
is not a polish item, it is the difference between a 10k archive and a 3k one with a broken banner.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Automation admits junk at 10k | notorious rules (§3.3) + QA sampling + error budget + stop-the-line |
| LLM spend blowout (currently unmetered) | Phase D measures $/row first; per-batch hard budget; concurrency cap; tiered-depth fallback |
| Silent quality decay as volume rises | per-batch published per-field accuracy; fixtures grow with every new false positive |
| ToS / legal exposure (review platforms, scraping) | fetch-and-report, never score, respect walls and robots, store links rather than copied bodies where required |
| Duplicate/alias explosion | `canonical_domain` + alias resolution before any write; staging table is the only door in; merge tool |
| Reaching 10k rows before the platform can serve them | **P** is a hard prerequisite for F, not a follow-up |
| Spec drift (the exact failure the specs exist to prevent) | any rule change recorded in `teardown-spec.md` / `gap-table-format.md`, never only in a phase prompt |
| Irreversible mistakes | additive migrations, never delete (dead rows kept), fresh evidence + backup + manifest before any removal |

---

## 10. Next steps

1. **Decide D1–D5** (§1). D1 and D2 gate everything else.
2. **Phase A + B**: approval model, then the funnel dry-run over the existing 1,258 rows.
3. **Phase C**: staging + 3,000 candidates, publishing nothing, reporting yield per channel.
4. **Phase D**: the 200-row pilot that turns "10k enrichment" from a guess into a number.
5. Then **P** (platform) → **E** → **F** (batches to 10k) → **G**.

Nothing here requires deleting data or weakening the evidence rules. The one thing it changes is
*who admits a row* — and that is recorded on the row, not lost.
