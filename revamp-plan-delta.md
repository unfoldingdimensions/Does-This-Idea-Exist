# Delta — `reworked-revamp-plan.md` vs the original `revamp-plan.md`

**Date:** 2026-09-14
**Baseline:** `revamp-plan.md` (v1) — with `Revamp-thinking.txt` treated as its earlier draft of the same plan (`docs/revamp-documents-review.md` §1).
**Comparison:** `reworked-revamp-plan.md` (v2).
**How to read this:** four tables — **KEPT**, **CHANGED**, **ADDED**, **DROPPED**. No v1 element is silently missing: anything not in KEPT appears in one of the other three tables with a reason. Each reason carries an evidence tag: `[CODE]` = `docs/codebase-comprehension.md`, `[R01]`–`[R05]` = `research/01`–`research/05`, `[REV]` = `docs/revamp-documents-review.md`, `[DISC]` = `docs/discussion-record.md`.

---

## 0. Phase-by-phase map (v1 heading → v2 section)

Every heading in `revamp-plan.md` is accounted for here, so the two plans can be diffed conceptually without reading both end to end.

| v1 heading | v2 location | Status |
|---|---|---|
| Product direction | §1 Product direction | **kept verbatim** |
| The killer workflow | §1 (referenced), §9 | **kept verbatim** |
| Product truth model | §5 Product truth model | **kept + extended** (permanent audit trail, coverage caveat, enforcement named as the claim) |
| Phase 1 — establish the product contract and baseline | §7 | **kept**, baseline numbers now measured; `founded` semantics added |
| Keep / Change / Defer | §14 | **kept**, two corrections + two additions |
| Phase 2 — fix data integrity and search | §8 | **kept**, duplicate scope reduced (job already done), match explanations split out |
| Duplicate and identity cleanup | §8 | **kept + scoped down** |
| Search quality | §8 | **kept + corrected** (stars framing) + per-result explanations |
| Phase 3 — build the research-result experience | §9 | **kept verbatim** |
| Query types | §9 | **kept verbatim** |
| Result sections | §9 | **kept verbatim** + coverage caveat |
| Product dossier | §9 | **kept verbatim** |
| Phase 4 — add evidence and provenance | §10 | **kept**, internally reordered (`entity_type` + provenance first) |
| Phase 5 — build comparison and decision support | §11 | **kept + upgraded** (ends in a two-sided you-vs-them gap table; teardown dimensions added) |
| Phase 6 — enrich data carefully | §12 | **kept verbatim** + dead `topstartups` path flagged |
| Phase 7 — discoverability and retention | §13 | **kept verbatim** + published-dataset and embedded-check hedge |
| Validation plan | §15 | **kept verbatim** |
| Initial quality targets | §15 | **kept verbatim** |
| Core funnel events | §15 (folded into the validation layer) and §13 (export/change feed) | **kept**, absorbed rather than restated — the events survive as the measurement list behind tests 3 and 6 |
| Implementation order | §16 | **reworked** (Phase 0 prepended; two items moved up) |
| Stop conditions | §17 | **kept** + three additions |
| — | §2 The founder problem | sharpened (one added sentence) |
| — | §3 Who we serve | beachhead added |
| — | §4 Why us / §4.1 counter-argument | **new** |
| — | §6 Phase 0 — concierge proof | **new** (now 25 competitor teardowns) |
| — | §18 What we are not doing | **new** |
| — | §19 Open questions | **new** |
| — | §20 Traceability | **new** |

**Coverage result:** 23 v1 headings, 23 accounted for above; 0 dropped without a reason. The only v1 element *absorbed* rather than restated is the list of 9 core funnel events, which survives as the measurement layer behind falsification tests 3 and 6.

---

## 1. KEPT — unchanged in v2

| # | v1 element | Evidence that it stays |
|---|---|---|
| K-1 | The reframe: existence → alternatives → differentiation; keep "Does this startup exist?" as the hook | `[REV]` §2; the user's stated preference; nothing in `[R01]`–`[R04]` contradicts it |
| K-2 | The killer workflow: 7 steps, under two minutes | `[REV]` §3.1; no research contradicts it |
| K-3 | The success event ("found a relevant product and understood how it relates to their idea") | `[REV]` §3.2 |
| K-4 | Result sections: Best matches / Closest alternatives / Related products / No strong match found, with v1's no-match copy | `[R04]` — the four-section shape is exactly what the "validate the alternatives, not the idea" job needs |
| K-5 | The product dossier contents (summary, problem/target user, why this matched, evidence links, activity, review date, similar products, history, unknowns, caveat) | `[R03]` Wedge 4 — the dossier is the surface where provenance becomes visible |
| K-6 | The seven evidence dimensions + the "must not imply" list | `[REV]` §4; `[CODE]` §11 confirms the current single `verified` integer cannot express them |
| K-7 | The five public state definitions (Unverified / Reachable / Dead / Human reviewed / Unknown), with "Unknown is a valid answer" | `[R01]` — no competing directory publishes a comparable legend |
| K-8 | Classified search ranking order (exact name → domain → phrase → tagline → problem → category → fuzzy), stars only as a tie-breaker | `[R03]` — relevance is the mechanism that makes "this specific idea" answerable |
| K-9 | Regression test list for search (names, domains, multi-word ideas, synonyms, unrelated fuzzy matches, empty results, duplicates) | `[CODE]` §7 — the harness already exists (`smoke.py`, `sort-check.ts`) |
| K-10 | Move search server-side (FTS5) when the archive passes the client-side ceiling | `[CODE]` §10.5 — measured knee ~3,000 rows, documented in `main.py` |
| K-11 | Deterministic search first for plain-English ideas; semantic/LLM search only after measurement | `[R04]` — an LLM-per-search is the path into the saturated validator layer |
| K-12 | The `evidence` table schema and all the proposed `startups` columns | `[R03]` Wedge 4 calls the evidence table "the single highest-leverage build"; `[CODE]` §3 shows none of it exists |
| K-13 | "LLM output is machine-drafted until a human confirms it"; generated prose is never ground truth | `[CODE]` §3, §10.2 — this is an active liability today |
| K-14 | Comparison across v1's nine dimensions, stored in `localStorage`, exported as Markdown/JSON/CSV | `[R03]` Wedge 3 — the decision-support job; `[CODE]` §9 shows nothing exists |
| K-15 | The "What would be different about your version?" prompt list (9 prompts) | `[R03]` — this is the wedge v1 named and the user liked |
| K-16 | The seven-step enrichment source order (archive → GitHub → site metadata → Wayback → curated lists → permitted APIs → careful scraping) | `[R01]` — the crowded segments compete on volume; careful breadth is the anti-volume position |
| K-17 | "One adapter at a time" with dedup, rate limits, retry/backoff, resumable jobs, import reports, provenance | `[CODE]` §4.4 — the existing job/queue machinery already supports this shape |
| K-18 | Per-import recording: source URL, capture date, import method, human-reviewed, fact/inference/generated | `[R03]` Wedge 4 |
| K-19 | "Do not build a giant scraper before the workflow has proven demand" | `[R04]` — the thesis is falsifiable for the cost of 20 interviews and 25 briefs |
| K-20 | Discoverability items: product/category/alternatives pages, example searches, recently-added/verified/dead, change feed, "request this product" | `[R03]`/`[R04]` — discovery still matters, it just gets a hedge (see A-9) |
| K-21 | Defer list: scraping, accounts, comments, votes, leaderboards, funding metadata, AI verdicts, decorative work | `[R04]` "what we deliberately do NOT do" endorses every one of these |
| K-22 | Validation targets (≥80% relevant in top three, no conflicting duplicate status, trust model understood unaided, search-to-dossier < 2 min, repeated research) | `[REV]` §3.6 — kept verbatim, then extended (A-10) |
| K-23 | The stop conditions from v1 | `[REV]` §3.5 — kept, then extended (A-11) |
| K-24 | The first coding slice: audit data, remove identity conflicts, improve search explanations, make the trust model precise | `[REV]` §3.5 — kept verbatim, with one addition (A-2) |
| K-25 | The six "keep" items (local-first, no accounts, human review, dead retained, conservative verification, warm identity, existing tooling and seed data) | `[REV]` §3.3 — no research argues against any of them |
| K-26 | Retain archive states for compatibility; keep the admin-token model; stay compatible with a future read-only hosted archive | `[CODE]` §4.1 — schema is additive-only by policy |

---

## 2. CHANGED — same intent, different content or position

| # | v1 said | v2 says | Why (one line) | Evidence |
|---|---|---|---|---|
| C-1 | "Generic `Verified` meaning → evidence-based signals" (implies replacing it) | Keep the human stamp **and** add the evidence dimensions beside it; the 1,278 existing stamps are not re-opened | The stamp is the product's one genuinely hard-to-copy asset and it already works — replacing it would destroy 99.7% of the trust layer to fix a labelling problem | `[CODE]` §3 (1,278/1,282 verified); `[R03]` Wedge 1 verdict "substrate, not offer"; `[DISC]` D-4 |
| C-2 | "Stars as a primary ranking signal → secondary metadata" | Re-worded: "keep stars as metadata; never let them outrank a text match" — and note the code already does this | Stars exist on only 57 of 1,282 rows (4.4%), so v1's framing overstates the current risk | `[CODE]` §3, §10.10; `[DISC]` D-7 |
| C-3 | Duplicates presented as a live trust problem requiring audit + cleanup | Re-scoped: the merge is **done** (1,292 → 1,282); the 6 remaining name groups are different companies and must stay unmerged; add only a guard queue for new duplicates | Redoing a completed job wastes the first slice; the remaining groups are a disambiguation feature, not a bug | `[CODE]` §3 (0 duplicate domains, 6 name groups); `CHANGELOG.md` "Data — duplicate merge"; `[DISC]` D-8 |
| C-4 | Trust-model work spread across Phase 1–3 | A dedicated **Phase 0 gate** on the trust mechanics: make `verify_log` permanent before any public history claim | The 90-day log sweep directly contradicts a permanent-record claim | `[CODE]` §10.6, §4.5; `[R03]` Wedge 7 gap; `[DISC]` D-6 |
| C-5 | Phase 1 baseline to be *measured* | Baseline is *already measured*; Phase 1 becomes "write it down and stop debating" | All nine baseline questions now have real numbers | `[CODE]` §3 |
| C-6 | Product dossier / stable routes late in the roadmap | `/products/<slug>` promoted earlier | A page-less product has no funnel, and destination discovery is reported to be declining — pages are a prerequisite for the discovery hedge | `[R03]` Wedges 2/8; `[R04]` (76,822-launch analysis); `[DISC]` D-11 |
| C-7 | Evidence/provenance phase lists schema additions and the evidence table together | `entity_type` + a provenance flag are pulled to **first** inside that phase | Both are prerequisites: `entity_type` for honest "closest alternatives", provenance because unlabelled LLM text is a live liability for a traceability product | `[CODE]` §3, §10.2; `[R03]` "would have to be built" list |
| C-8 | "Search" as one workstream | Split: relevance/ranking (largely done) vs **per-result match explanations** (not started) | "See why each result matched" is a v1 promise with zero code behind it; merging the two made it look done | `[CODE]` §5, §11 |
| C-9 | v1's "Change" bullet for LLM prose | Moved to first within its phase and framed as a liability, not a hygiene item | Same intent, higher urgency | `[CODE]` §10.2 |
| C-10 | Validation plan measured the tool | v1's targets kept verbatim **plus** the research's six falsification tests and kill rule layered on top | v1 measures whether the tool works; the research measures whether the thesis is true — both are needed | `[R04]` §Falsification plan |
| C-11 | Implementation order: baseline first | Phase 0 (concierge) first; then baseline; then the two promoted items | The concierge test needs no code and is the cheapest way to falsify the core claim | `[R04]` "First proof" + kill rule |
| C-12 | Stop conditions reactive (pause when things go wrong) | Added a **false-`dead`** condition and a **first-real-death** condition | The strike rule exists because of a real incident, and 0 dead entries means the mechanism is unproven in production | `[CODE]` §4.5, §10.4; `CHANGELOG.md` (WHOOP/Capterra false dead-flips) |
| C-13 | Four personas treated as one audience | Same four as the long-term market, **plus** one named 90-day beachhead | A set is not a segment; the archive's dev/design seed gives a warm start | `[R04]` underserved segment; `[DISC]` D-3 |
| C-14 | `founded` used as a filter facet without comment | Phase 1 must fix its semantics (rename / split with `date_source` / drop from facets) | Live rows prove domain-registration dates are being shown as founding dates | `[CODE]` §3 (Notion `2000-11-01`, Zoom `1996-10-18`), §10.3 |
| C-15 | Comparison ends in a side-by-side list across nine dimensions | Comparison ends in a **two-sided gap table** ("what you have that they don't / what they have that you don't"), with every cell sourced, joined by the teardown dimensions (pricing, content, features, does/doesn't) | Owner direction 2026-09-15; the founder walks away with a gap report, not a list | `[DISC]` §9 |
| C-16 | The founder's own product is captured via a short structured form | **A form OR a URL** — if the founder has a site, the existing `seed_from_website` path ingests it (same pipeline as competitors, new mode) | Owner answer 2026-09-15; no new backend primitive required | `[DISC]` §9; `[CODE]` §4.4 (`enrich.py`) |
| C-17 | Pricing captured as list price + tier count + free-tier flag | **Full plan-by-plan breakdown**, with a `captured_at` + source URL per pricing row and staleness surfaced to the user | Owner answer 2026-09-15; pricing decays fast, so it must be dated, never undated | `[DISC]` §9 |
| C-18 | Founder's own app entered via a form or URL | **Three paths (URL / form / agent prompt)** with a required flat 5–10 feature list, and the flow is **always confirm-before-diff** | Owner answer 2026-09-15 (Round 4); the gap table must never run against an unconfirmed profile | `[DISC]` §9; `docs/teardown-spec.md` §3 |

---

## 3. ADDED — not in v1 at all

| # | Added element | Why (one line) | Evidence |
|---|---|---|---|
| A-1 | **§4 "Why us — and not another directory or an assistant"** with the 59-competitor landscape, the three "we are not" statements and the honest one-liner | v1 had no competitive section at all, so its positioning was unfalsifiable | `[R01]` (59 players, 8 segments), `[R02]` (matrix), `[R04]` verdict |
| A-2 | **Per-result match explanations as an explicit first-slice item** | It is the cheapest change that turns v1's promise into a feature | `[CODE]` §11 |
| A-3 | **A coverage caveat everywhere** ("this checks a 1,282-entry archive, not the internet") and the ability to say "not covered" | The honest-answer discipline is what separates the product from a validator | `[R03]` Wedge 8 counter-argument; `[R04]` "no AI verdict without sources" |
| A-4 | **The enforcement mechanism named as the public claim** (404/410-only strike, 3 strikes → dead, never deleted, verified rows protected from automation) | v1 kept the mechanism but never stated it; it is the hardest thing for a competitor to copy | `[CODE]` §4.5; `[R03]` Wedge 4 "genuine advantage" |
| A-5 | **Phase 0: 25 hand-made evidenced briefs** as a gate before any build | Cheapest possible test of the core claim; no code required | `[R04]` "First proof" |
| A-6 | **Six falsification tests with pass/fail thresholds and a kill rule** | Converts the strategy from assertion to something that can be killed for the cost of 20 interviews | `[R04]` §Falsification plan |
| A-7 | **A named beachhead segment** | Gives the first slice a target and the recruitment a place to start | `[R04]` underserved segment; `[R03]` Wedge 5 |
| A-8 | **Beachhead recruitment from existing assets** (the 57 GitHub-linked rows, the 201-site curated design library) | Turns existing seed data into a distribution start rather than more corpus | `[CODE]` §3 (57 repos; design library); `[R04]` "First user" |
| A-9 | **Discovery hedge: published static read-only dataset + an embedded check**, alongside v1's SEO pages | v1 bet the growth path on a discovery channel the research says has peaked | `[R03]` Wedge 8; `[R04]` peak-of-discovery evidence |
| A-10 | **`entity_type` moved ahead of the pricing/audience fields** | Comparison is dishonest while a repo, a company and a product are the same kind of row | `[CODE]` §3 (no `entity_type`); `[R03]` gap list |
| A-11 | **Fix or remove the dead `topstartups` seed path** | The `jobs` table shows a completed run the admin panel can no longer trigger | `[CODE]` §10.11 |
| A-12 | **The similarity upgrade named explicitly** (structured field overlap before embeddings) | "More like this" is currently shared category + language + tagline words — a lexical proxy that cannot carry a "closest alternatives" promise | `[CODE]` §5 (`startup-detail.tsx` `similar` memo); `[R03]` "no advantage" list |
| A-13 | **§18 "What we are explicitly not doing"**, including "no free public API as the business" and "no trust as the headline" | Two of the eight researched wedges were disqualified for cause; recording the disqualifications prevents drift back into them | `[R03]` Wedge 1 and Wedge 6 verdicts, Wedge 5 |
| A-14 | **§19 Open questions** with owner decisions recorded | v1 had no open-questions section, so unresolved forks looked settled | `[DISC]` §5–§7 |
| A-15 | **§20 Traceability + a delta document + a source ledger** | Makes every change auditable against a codebase or research finding | this file; `[R05]`; `docs/codebase-comprehension.md` |
| A-16 | **Baseline numbers written into the product surface** ("1,282 filings, 1,278 human-checked, last checked …") | v1 asked for measurement; the measurement should be visible, not just recorded | `[CODE]` §3 |
| A-17 | **The teardown as the core output** (competitor teardown — pricing, content, features, does/doesn't — plus a you-vs-them gap table), with "does this startup exist?" kept as the entry point | Owner direction 2026-09-15; it is Wedge 3 + Wedge 4 with the output upgraded from a list to a teardown | `[DISC]` §9; `[R03]` Wedges 3 & 4 |
| A-18 | **Negative-claim fields** ("no API", "no free tier", "no mobile") each backed by an evidence row, so the gap report's "what they don't do" is sourced, not invented | The gap report's payload is negative evidence, which is the easiest part to fake | `[DISC]` §9; `[R03]` Wedge 4 |
| A-19 | **The MVP teardown spec and the gap-table format as concrete artifacts** (`docs/teardown-spec.md`, `docs/gap-table-format.md`) — six capped teardown fields + evidence rules + the two-sided table shape | Owner confirmed the MVP teardown fields (pricing + 5–10 features + positioning + 3–5 "doesn't do" + gap table); writing them down makes Phase 0/4/5 buildable | `[DISC]` §9 |

---

## 4. DROPPED — removed or absorbed

| # | v1 element | Disposition | Why |
|---|---|---|---|
| X-1 | The duplicated phase list (v1 restates the roadmap twice: once as "Implementation order", once inline) | **Absorbed** into one ordered table (§16) | `[REV]` §4 — the duplication is presentational, not substantive |
| X-2 | Line-level code citations in `Revamp-thinking.txt` (e.g. `db.py:81-108`, `search.ts:62-82`) | **Replaced** by file-level citations in `docs/codebase-comprehension.md` | The line numbers drift as the code changes; the comprehension doc is re-verifiable and already corrected one of them (`normalize_url` is at `db.py:81`, matching) |
| X-3 | "Retain the current archive states for compatibility" as a *phase* item | **Promoted** to a standing constraint (§14, K-26) | It is a rule, not a task |
| X-4 | v1's framing of duplicates as an open audit | **Scoped down and partially dropped** | The audit is complete: 0 duplicate domains remain | `[CODE]` §3 |
| X-5 | "Stars as a primary ranking signal" as a current-state description | **Dropped as a description**, kept as a rule | It is no longer an accurate description of the code | `[CODE]` §10.10 |
| X-6 | Nothing else | — | Every remaining v1 element is in KEPT, CHANGED or the four tables above; no element was removed without a reason recorded here |

---

## 5. One-line conceptual diff

> **v1 said: stop shipping a badge, start shipping research.**
> **v2 says the same thing, and adds why anyone would believe it: 59 competitors already sell opinions, none of them sells a traceable, private, human-checked answer — so the product keeps v1's workflow exactly, fixes the three things the code audit found (unlabelled machine text, misleading founded dates, no per-result reasons) before it adds anything clever, and gates the build on 25 hand-made briefs.**
> **v2.1 (2026-09-15) upgrades the destination: the research result is a *competitor teardown + you-vs-them gap report* — pricing, content, features, what each does and doesn't — every cell sourced, with "does this startup exist?" kept as the front door.**

---

## 6. Verification of this delta

- Every row in KEPT/CHANGED/ADDED/DROPPED carries an evidence tag; no row is unexplained.
- The v1 elements named here were checked against `docs/revamp-documents-review.md`, which was itself written line-by-line against `revamp-plan.md` and `Revamp-thinking.txt`.
- The codebase claims tagged `[CODE]` are re-checkable against `docs/codebase-comprehension.md` §12, which lists what was read.
- The research claims tagged `[R01]`–`[R05]` are re-checkable against `research/00-method-and-sources.md`, which lists every URL and its access date.
