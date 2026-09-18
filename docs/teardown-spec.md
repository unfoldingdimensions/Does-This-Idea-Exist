# Teardown Spec — MVP

**Version:** 1.1 (rev. 2026-09-15 — Round 5 trust model applied) · **Date:** 2026-09-15
**Owner-confirmed scope:** a competitor teardown that a founder uses to line up their own app against a competitor and get a concrete gap. This is the MVP shape; anything beyond these six fields is post-MVP.
**Companion docs:** `docs/gap-table-format.md` (the output table) · `reworked-revamp-plan.md` §6, §10, §11 · `docs/codebase-comprehension.md` (what exists today).
**Decisions applied:** `docs/discussion-record.md` §9 Round 5 (2026-09-15) — the trust model (Admin vs Machine Verified), the founder-app link rule and separate store, just-in-time capture, and the reviews-what-they-ask-for design. Where this file and an older plan doc disagree on a **column name**, see §5 — the names in §5 are canonical.

---

## 1. What a teardown is

A teardown is a **structured, sourced snapshot** of one competitor, built from the archive plus the evidence table. It is *not* an essay and *not* an AI opinion. Every field is either sourced or marked **unknown**; nothing is inferred silently.

The product already produces most of the *identity* fields (name, tagline, description, category, founded, URLs, liveness). A teardown **adds** the six fields below. So a teardown = existing dossier + these six.

---

## 2. The six MVP fields

| # | Field | What it captures | Source | Evidence rule | Completeness bar |
|---|---|---|---|---|---|
| 1 | **Pricing** | Full plan-by-plan breakdown: each plan's name, price, billing period, and the free tier (or "no free tier") | pricing page / `/pricing`, docs | one `evidence` row per plan with `captured_at` + source URL; staleness shown to the user | At least the list price and the free-tier flag; full plan rows where reachable |
| 2 | **Features (5–10, flat list)** | A flat list of what the product actually does, in the founder's terms, not marketing terms — one capability per item, no grouping in MVP | homepage, docs, demo | each feature traces to a page or doc section | 5–10; "unknown" if a source can't support even 5 |
| 3 | **Positioning (one line)** | How they describe themselves / who they say it's for | homepage hero / meta description | sourced quote or paraphrase with URL | one line; always available (homepage exists for 100% of rows) |
| 4 | **What they don't do (3–5)** | Observations about a linked page that **enumerates**: e.g. "pricing page lists Free / Pro / Team — no self-host tier" (full rule in §8.2) | a page that enumerates the whole set (pricing page, docs index, footer links) | **the strictest rule in the product**: a negative is only ever an observation about an enumerating page, quoted with its URL and capture date. It is never a verdict about the world, and a 404 on a guessed URL is **not** evidence of absence. If no enumerating page can be found, the cell reads `unknown` | 3–5 observed; if fewer are supportable, show fewer and mark the rest unknown |
| 5 | **Activity** (already exists) | Liveness: last check, dead/alive, repo activity | the weekly verify pass | existing `verify_log` / `last_checked` | always present |
| 6 | **Gap table** (the output) | You vs them, two-sided, sourced | the fields above + the founder's own app | every cell sourced or unknown | see `docs/gap-table-format.md` |

**The three rules that make this defensible rather than another AI validator:**

1. **Every positive claim is sourced** (a URL + a capture date). A competitor's claim is taken at face value *because* the link is right there — the product attributes, it does not adjudicate.
2. **Every negative is an observation about an enumerating page**, or `unknown` — never a verdict. A "doesn't do" that can't be traced to a page that lists the whole set is *not* printed as fact. Negative evidence is the gap report's payload and the easiest thing to fake, so it gets the strictest handling.
3. **Badges attach to the record, never to a claim.** Admin Verified and Machine Verified (§8) describe the *business*, not its marketing. Every claim instead wears its own label: "per their pricing page, captured 2026-09-15". A verified badge rendered next to a competitor's claim reads as an endorsement of that claim, which is the one thing this model cannot survive.

---

## 3. The founder's own app (the "you" side)

Owner-confirmed: the founder describes their app via **three paths**, and the flow is always **ingest → confirm → diff** (never auto-diff).

1. **URL path.** If the founder has a site, run it through the existing `seed_from_website` pipeline (`backend/app/enrich.py`) — the same path that ingests competitors — to draft name, tagline, category, description, and founded. This is a **new mode of an existing primitive**, not new backend code.
2. **Form path.** A short form — *name · one-line description · target user · category (from the existing 12-value whitelist) · **features (required, flat 5–10)** · pricing (free tier + plans) · links: website URL · GitHub · **App Store URL · Play Store URL** (all optional)*. A good feature list is required because the gap table compares feature-by-feature; without it the comparison is hollow.
3. **Agent-prompt path.** The founder can paste a structured payload produced by their own agent (ChatGPT/Claude/etc.) from the copy-paste prompt below — same fields, same JSON shape, zero manual typing.

**Copy-paste AI prompt (give this to your agent):**

```text
Describe my app in a strict JSON object with exactly these keys, no extra prose:

{
  "name": "string — display name",
  "description": "string — 2-3 sentences: what it is, who it's for, what problem it solves",
  "target_user": "string — one sentence naming the primary user",
  "category": "one of: productivity, ai, devtools, desktop, freelance, finance, health, education, ecommerce, social, media, other",
  "features": ["5 to 10 short capability strings, one per item, e.g. 'local files', 'real-time collaboration', 'public API'"],
  "positioning": "string — one line: how you describe yourselves and who it's for",
  "pricing": {
    "free_tier": "string — e.g. 'Free up to 3 docs', or 'No free tier'",
    "plans": [{"name": "string", "price": "string — e.g. '$8/mo' or 'custom'", "period": "monthly|annual|one-time"}]
  },
  "links": {
    "website": "string — or \"\" if none",
    "app_store": "string — or \"\" if none",
    "play_store": "string — or \"\" if none",
    "github": "string — or \"\" if none"
  }
}

Rules: use only facts about my app. Keep features to 5-10 items. Do not invent a feature
or a price I did not state. If a field is unknown, use "" or []. Output JSON only.
Links are optional — but note that an app with no link can be compared and will never
be added to the archive.
```

**Confirm-before-diff (owner-confirmed):** after any of the three paths, the founder **reviews and confirms** the auto-drafted profile before the gap table runs — they can edit fields inline, then confirm. The gap table never renders against an unconfirmed profile.

### 3.1 Two stores: eligibility vs consent (Round 5)

The founder's app lives in **its own database** (`FOUNDER_DB_PATH`, mirroring `DB_PATH`), never in the archive file. It carries the same record shape so the gap table can diff two like-for-like records, but nothing in the founder store is ever listed, counted or searched by the archive endpoints.

Two separate gates, deliberately not merged:

| Gate | Rule |
|---|---|
| **Eligibility — a real link** | A founder app may only enter the archive if it has at least one verifiable link: `website_url` · `github_url` · `app_store_url` · `play_store_url`. **No link → comparison only, never published, and no consent question is asked** (nothing is published, so there is nothing to consent to). |
| **Consent — the checkbox** | The opt-in checkbox is shown **only** when a fetchable link exists. Ticked → the app is submitted to the archive alongside competitors and goes through the same admin approval queue. Unticked → founder store only. |

**The outcome is tracked in `founder_submissions`, and `archive_status` is derived from it — not stored on the founder record.** There are no accounts to notify, so the submission row is what makes a ticked-and-rejected request visible to the founder instead of vanishing.

Both tables live in the **founder store** (`FOUNDER_DB_PATH`):

```
founder_apps            -- the founder's own record; same column shape as `startups` (F-10)
  id, name, ..., features_json, pricing_json, positioning, website_url,
  github_url, app_store_url, play_store_url, ...

founder_submissions
  id                 INTEGER PRIMARY KEY AUTOINCREMENT
  founder_app_id     INTEGER NOT NULL   -- FK → founder_apps.id (same file)
  submitted_at       TEXT NOT NULL
  status             TEXT NOT NULL      -- pending | approved | rejected | withdrawn
  archive_startup_id INTEGER            -- set on approval: the row created in the archive DB
  decided_at         TEXT               -- when the admin gate resolved it
  decided_by         TEXT               -- the admin stamp, same gate as any competitor
  note               TEXT               -- rejection reason / review note, shown to the founder
```

Rules:

1. **`archive_status` is a derived view**, not a column: the `status` of the **newest** submission row for that founder app, or `local_only` when there are none.
2. **Resubmission after a rejection is a new row**, never an edit — so rejected → resubmitted → approved is auditable, which is the same posture as the permanent `verify_log` and the phase ledger.
3. **`archive_startup_id` is the cross-store link.** It closes the gap flagged when the founder store was split off: without it, the founder's app and its archive twin are two unconnected records and the diff can end up comparing the founder with themselves. It is a soft reference across two files, like everything else in the compare path.
4. **The admin queue unions both stores.** "The same queue as competitors" now means the queue endpoint reads pending `founder_submissions` from the founder store and merges them with the archive's suggested rows — a submission row in another file will not appear in `list_suggested()` on its own.

Privacy note: "stays on this machine" is true when the founder store is local. If an instance is hosted, the founder's app sits in that instance's founder DB — so hosting must exclude `FOUNDER_DB_PATH` from backups and the privacy copy must say which of the two is true.

---

## 4. What is deliberately NOT in the MVP

- No generated "you will beat them because…" paragraph (facts only — see §18 of the plan).
- No review **scoring**, no NPS, no sentiment score, no aggregate rating of our own — see §9 for what reviews *are* used for.
- No headcount/funding, no SEO/traffic panel.
- No automatic *web-wide* feature extraction. MVP captures these fields through the existing ingestion (homepage fetch + LLM draft + human confirm), one competitor at a time.
- No "alternatives ranking" or scores. The gap table compares, it does not rank.

---

## 5. Schema mapping (what to build, in order)

### 5.1 Canonical column names (do not re-litigate)

Older plan documents use different spellings for the same fields. These are the canonical ones — the migration, the tests and the exports must all use exactly these:

| Canonical | Older/legacy spelling (superseded) | Notes |
|---|---|---|
| `features_json` | `features` | TEXT, JSON array of 5–10 short strings |
| `pricing_json` | `pricing`, `pricing_model` | TEXT, JSON `{"free_tier": "…", "plans": [{"name", "price", "period"}]}` |
| `pricing_captured_at`, `pricing_source_url` | — | every pricing write stamps both |
| `positioning` | — | one line |
| `founded` | `founded_at` (proposed rename, **rejected**) | the column **keeps its name**; see below |
| `date_source` | — | new: `llm` · `wayback` · `rdap` · `human` · `unknown` |
| `app_store_url`, `play_store_url` | — | new, nullable; the mobile links a founder may submit |
| `evidence_type` | — | `feature` · `pricing` · `positioning` · `negative` · **`review`** · `repo_created` · `homepage_claim` · `wayback_first` · `reachability` · `curator_confirmation` |

`revamp-plan.md` (v1, superseded) and `Revamp-thinking.txt` are the sources of the legacy spellings. `reworked-revamp-plan.md` §10 was updated on 2026-09-15 to match this table.

### 5.2 Where the fields land

- `startups` gains the fields in §5.1 (plus `entity_type`, `canonical_domain`, `aliases`, `problem_statement`, `target_users`, `product_url`, `docs_url`, `demo_url`, `content_notes`, `activity_checked_at`, `activity_summary`, `last_human_reviewed_at`, `review_notes`, `provenance` — full list in `implementation-plan.md` Phase 1).
- `evidence` rows back every feature, pricing plan, positioning line, negative observation and review item with `evidence_type`, `source_url`, `captured_at`, `claim`, `value`, `provenance`, `confidence`.
- **`founded` keeps its name** (owner decision, Round 5). Add `date_source` and copy the existing value across; no rename, because the rename alone becomes a ~20-file change across backend and frontend and does not fix anything the display rule doesn't. RDAP/Wayback-derived dates must still never be *presented* as founding years — that is a display fix (Phase 6, `startup-card.tsx` / `page.tsx`), tracked as the frontend half of F-04.

Build order (matches plan §16): `entity_type` + provenance flag → `evidence` table → the four teardown fields → comparison → gap table → export.

### 5.3 URL column definitions (owner-confirmed, Round 5 follow-up)

The archive grew five URL-shaped fields, and undefined overlap between them is exactly what produced the `pricing_model` drift. These definitions are canonical:

| Column | Definition |
|---|---|
| `website_url` | **The company's / product's primary site.** The front door. One of the two dedup identities (`idx_startups_website`). |
| `github_url` | The repository. The other dedup identity (`idx_startups_github`). |
| `product_url` | The product's own page **when it is separate** from the site above (e.g. a subdomain or a `/product` path). NULL when the site *is* the product page. |
| `app_store_url` | The **iOS** App Store listing. NULL when there is no iOS app. |
| `play_store_url` | The **Google Play** listing. NULL when there is no Android app. |
| `docs_url` | Documentation. |
| `demo_url` | A demo, sandbox or try-before-you-buy page. |

Two consequences worth stating: the two store links are **identity evidence and eligibility inputs**, but **not dedup keys** — dedup stays on `website_url` / `github_url`, so a publisher shipping several apps does not collide. And a mobile-only product with no website is still eligible for the archive (F-20) with a NULL `website_url`.

---

## 6. Worked example (skeleton, not shipped data)

**Competitor:** a fictional dev-tool "Noted".

- **Pricing:** Free (up to 3 docs) · Pro $8/mo annual · Team $12/user/mo · *no self-host tier* — captured 2026-09-15, source `noted.app/pricing`.
- **Features (7):** markdown notes · backlinks · graph view · local files · plugins · sync (paid) · publish.
- **Positioning:** "A private, local-first note app that links your thinking." (homepage hero).
- **Doesn't do (4, all sourced):** no API (docs have no API section) · no mobile app (no mobile page, no store link) · no self-host (pricing page lists no self-host) · no real-time collaboration (homepage does not claim it).
- **Activity:** alive, last checked 2026-09-14.
- **Gap table:** against the founder's app (e.g. an online-first note app with an API) — see `docs/gap-table-format.md` for the rendered form.

---

## 7. Open questions

Resolved in Round 4 (2026-09-15): features are a **flat 5–10 list**; the form fields are fixed with a **required feature list** plus an **agent-prompt path**; the flow is **always confirm-before-diff**.

Resolved in Round 5 (2026-09-15) — all three of the previous round's open items are now decisions:

1. **The `enrich.py` change list** — see Phase 2 of the implementation plan. Answered in full: which functions extend, the silent-drop trap, and the `reuse_profile` carve-out.
2. **Where the founder's app lives** — a **separate database**, with link-eligibility and consent as two different gates (§3.1). Decided, not a flagged row in `startups`.
3. **How negatives are captured** — a **deterministic pass first** (probes against enumerating pages), **LLM fallback second** (over the already-fetched text only), and the negative is stored and printed as an observation about a page, never as a verdict (§8.2).

Resolved in Round 5 follow-up (2026-09-15):

1. **Reviews placement — DECIDED: a seventh gap-table dimension.** "What their users ask for" is dimension 7 of the gap table (`docs/gap-table-format.md` §2 and §1's fourth group).
2. **Just-in-time freshness window — DECIDED: weekly.** A cached teardown risks being re-captured after 7 days, aligned with the existing `VERIFY_AUTO_STALE_DAYS` default. Capture is still JIT (first founder request), never on seed or on approval.
3. **Machine Verified — DECIDED: an explicit API field.** `machine_verified` (+ `machine_verified_at`) is exposed per row rather than left implicit, and the weekly pass re-checks **all** entries including old ones, so the badge refreshes archive-wide instead of only for new rows (§8.1).
4. **The URL columns — DECIDED: defined here, in §5.3.**

Resolved in Round 5 follow-up (2026-09-15), second pass:

5. **`archive_status`'s home — DECIDED: a `founder_submissions` table** in the founder store, with `archive_status` **derived** from its newest row rather than stored on the founder record (§3.1). Chosen over a column so a rejected-then-resubmitted request keeps its history, and so the approval carries the cross-store `archive_startup_id` link.

**No open items remain on this spec.** Everything in §7 above is decided; anything new that comes up should be added here rather than settled in a phase prompt.

---

## 8. The trust model (Round 5)

### 8.1 Admin Verified vs Machine Verified

Two badges, two different claims, and they must never be rendered as one:

| Badge | Backed by (existing data) | What it attests | Decays? |
|---|---|---|---|
| **Admin Verified** | `verified` + `verified_at` — the human stamp; stamped by `verify.approve_suggested()`, the single-row /verify endpoint and the bulk admin route | a human confirmed this is a real business that exists online | no — it is the admission ticket to the archive |
| **Machine Verified** | `status` + `last_checked` + `check_failures` — the weekly pass | automation confirmed the link was reachable at that date | yes — re-earned on every pass |

Human admission is the entry gate for every row a human has looked at; the automated funnel also
admits rows, and those are NOT Admin Verified (see 8.4) — so **Machine Verified is the badge that actually moves**, and it is the one the founder should see varying.

Neither badge says anything about the truth of a claim. We cannot verify what a competitor says; we can only verify **that the business exists online** and **that every fetched item carries the link it came from**. The product's contract is therefore: *every row is a quotation with a citation.*

Implementation note: **`machine_verified` is an explicit API field** (owner decision, Round 5 follow-up), paired with `machine_verified_at` (the `last_checked` value it is derived from) so a client never has to infer the badge from a raw timestamp. No new column is required — but the weekly pass re-checks **every** entry, old ones included (`run_verify_job` already walks the whole table), so the badge refreshes archive-wide rather than only for freshly-seeded rows. `admin_verified` / `admin_verified_at` are exposed the same way from `verified` / `verified_at`.

### 8.2 Negatives — the strict rule

A negative is **an observation about a page that enumerates**, never a verdict about the world:

- Yes: *"Pricing page lists Free / Pro / Team — no self-host tier (captured 2026-09-15, acme.com/pricing)."* — a fact about a page the founder can click.
- No: *"Acme has no self-host tier."* — our assertion, resting on nothing anyone said.
- No: *"No API"* derived from a 404 on a guessed `acme.com/api` URL. **A 404 on a guessed URL is not evidence of absence.**

Only pages that enumerate the whole set count (a pricing page listing every tier, a docs index listing every section, a footer listing every store link). If no enumerating page can be found, the cell is `unknown` — which is itself useful signal ("go check whether they have an API").

A retrieval failure is not a negative either: a page that renders client-side and returns an empty shell is *"we could not read it"*, never *"they don't have it"*. That distinction is what `confidence` on the evidence row is for.

Consequence: no per-negative curator queue is needed. The review burden sits on the **competitor record** (which goes through the existing admin approval gate), not on each claim inside it.

### 8.3 What we never assert

- We never score, rank or grade a competitor.
- We never print a generated "you will beat them because…" line.
- We never present a marketing claim as our own finding — it is always "they say X, per this page, captured on this date".

### 8.4 Admission provenance (Round 6, 2026-09-18 - the funnel decision)

Owner decision: at archive scale a human cannot be the gate for every row. The liveness funnel admits
the clean majority automatically and routes only the walled, repurposed, notorious or unresolved rows
to the admin queue (`docs/scale-to-10000-plan.md` §3).

That splits one question into two - "is this row admitted" and "who admitted it" - and they must not
collapse back into one flag. `verified=1` alone would render Admin Verified on a row no human ever
looked at, which is exactly the badge-lies failure this trust model cannot survive. Admission
provenance is therefore recorded explicitly:

| Column | Values | Meaning |
|---|---|---|
| `approval_source` | `human` · `machine` · NULL | who admitted the row. NULL predates this column and reads as human; no existing row was rewritten to say so |
| `approved_by` | `admin` · `funnel:http` · `funnel:render` | which gate admitted it |
| `approval_note` | text | optional reason / re-check note |

Rules:

1. **`verified` keeps its meaning** - "admitted to the archive". Every existing filter, count and
   listing keeps working unchanged.
2. **Admin Verified requires `approval_source != 'machine'`.** A machine-admitted row renders
   **Machine Approved**, naming the stage that admitted it, and never Admin Verified.
3. **Three writers of `verified=1`, and only these**: `verify.approve_suggested()` (bulk, human), the
   single-row `/api/startups/{id}/verify` route (human), and `verify.approve_machine()` (funnel). The
   first two stamp `approval_source='human'`; only the third stamps `'machine'`, and it rejects any
   `by` value that does not name a funnel stage.
4. **The same base guard on both paths**: `verified = 0 AND status = 'active' AND check_failures = 0`.
   A machine can never re-stamp an admitted row, resurrect a `dead` one, or admit a row sitting on a
   failure strike - the dead-flip outranks the funnel.
5. **Provenance can never be clobbered by enrichment.** These columns are deliberately NOT in
   `enrich.UPDATABLE`, so a re-seed or teardown upsert cannot overwrite them.
6. **Un-verifying clears the provenance**, rather than leaving a stale stamp for the badges to read.

Consequence for the funnel: the admin queue is defined by what is *not* machine-approvable, not by
what is unverified. `list_suggested()` already excludes `verified = 1`, so machine-admitted rows never
appear in it.

---

## 9. Reviews — legitimacy, never a score

Reviews answer the one question the teardown otherwise cannot: *does this thing actually have users, and what do those users ask for?*

**Rules:**

1. **Fetch and report, never score.** No star aggregate of our own, no NPS, no sentiment score. Where a platform shows a rating, it is quoted with its source and capture date — the same attribution rule as every other claim.
2. **Positive and negative are both surfaced**, labelled as the reviewer's view, not ours.
3. **Negative reviews become "what their users ask for"** — the features and fixes reviewers actually requested, each linked to the review it came from. Same evidence rule as the gap table, one level up: the product hands the founder what users asked for and stops there. It does **not** turn that into "you should build X" — that stays the founder's call.
4. **`provenance='machine_drafted'`** on anything a model extracts, with the review link attached, until a human confirms it.

**Providers are config, not code.** A `review_sources` list (Reddit, RSS feeds, ProductHunt, review platforms) so adding a platform is a config edit, not a phase.

**Walled providers are expected.** G2 / Capterra / Trustpilot bot-wall datacenter traffic — the same failure that once dead-filed WHOOP and Capterra, and the reason `verify.py` treats 403/429 as a *skip*. A walled review page is "listed but not fetched": show the link, claim nothing about it, never count it as a strike.

**Confirmed (Round 5 follow-up):** this is gap-table **dimension 7** — "What their users ask for". See `docs/gap-table-format.md` §1 (fourth group) and §2 (dimension 7).
