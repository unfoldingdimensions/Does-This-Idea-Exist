# IdeaExists — Reworked Revamp Plan

**Version:** 2.0 (reworked)
**Date:** 2026-09-14
**Supersedes:** `revamp-plan.md` (v1) and `Revamp-thinking.txt`
**What this is:** the v1 plan, unchanged in its approach and its founder-problem framing, with the deep research and the codebase audit folded back into it. Every change from v1 is listed, with its reason and its evidence, in `revamp-plan-delta.md`.
**Evidence base:** `docs/codebase-comprehension.md` (what the product is), `docs/revamp-documents-review.md` (what v1 said), `research/00`–`research/05` (the outside world), `docs/discussion-record.md` (the open decisions).

---

## 1. Product direction — kept

Reframe IdeaExists from a binary startup directory into:

> **Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build.**

Keep **"Does this startup exist?"** as the memorable entry point and the brand personality. Make the core output a **research result**, not a yes/no badge. The Curator stays an internal/operator role, not the public persona.

**Unchanged from v1, deliberately.** The user said they like this approach and how it solves a founder's problem. Nothing in the research contradicts it; the research only says *why* it is defensible and *where* it must land. So the reframe, the killer workflow, the two-minute target, the grouped results, the dossier, the comparison and the "what would be different?" answer all survive intact.

### 1.1 The owner's refined vision — the teardown as the core output (2026-09-15)

The owner has sharpened what the research result *is*. The product's centre of gravity moves from **existence/alternatives research** to **competitive teardown + gap analysis**:

> **A founder picks a competitor, sees it torn down — pricing, content/positioning, features, what it does and what it doesn't — then compares their own app against it and gets a concrete gap report: what they have that the competitor lacks, and what the competitor has that they lack.**

"Does this startup exist?" **stays as the entry point and the acquisition surface** (it is the memorable hook), and the killer workflow's first four steps stay (find direct matches, closest alternatives, related products, open a dossier). What changes is the *destination*: the dossier's comparison deepens into a **teardown**, and the "what would be different?" step becomes a **two-sided you-vs-them gap table**. This is Wedge 3 fused with Wedge 4 from `research/03`, with the output upgraded from a list to a teardown.

It is *more* literal about solving the founder's problem, not less: the founder walks away with a gap report, not a yes/no and not a shrug.

---

## 2. The founder problem we solve — kept, then sharpened

**Kept exactly as v1 states it.** A founder with a real product idea needs to know what already exists *before* spending a weekend, a month or a quarter building it — and needs to come away with a view of what would make their version different, not a verdict that kills the idea.

**Sharpened with one sentence (new, §4).** v1 said *what shape* the output takes ("research result, not a badge"). It did not say *why a founder would come here instead of typing the question into ChatGPT*. The research is unambiguous that this is the question the product must answer:

> The crowded layers all sell **output** — a score, a listing, an opinion. Output is exactly what a general-purpose model now produces for free. The open layer sells **accountability** — a claim you can trace, a record that does not rot, and a check that never leaves your machine.
> — `research/04-market-saturation-verdict.md`, verdict

So the founder problem stays the same; the **promise attached to it becomes provable rather than assertive**.

---

## 3. Who we serve — kept, with a beachhead added

**Kept (v1):** founders, indie hackers, product strategists, investors researching a real product idea.

**Added — the beachhead for the first 90 days (new):**

> **A solo or two-person technical founder with an already-scoped idea, typically in software / dev tools / design-adjacent SaaS, who is deciding whether to spend real time on it.**

Not the browsing-for-inspiration user; not a funded company running competitive analysis at scale; not an investor sourcing deals. Rationale and the falsifiable test are in `research/04` ("The underserved segment"). The other three audiences remain the long-term market — this is the *first* segment, not the only one.

**Why a beachhead at all:** v1's four-persona list is a set, not a segment, and it gives the first slice nothing to aim at. The archive already contains 57 GitHub-linked rows and a 201-site curated design library — dev/design is where the warm start is.

---

## 4. Why us — and not another directory or an assistant (new section)

This section did not exist in v1. It is required, because the research found **59 named competitors across 8 segments** (`research/01`, `research/02`) plus a free status-quo substitute. Three sentences do the work:

1. **We are not a validator.** Twelve idea-validation tools already sell a score in 120 seconds, from $9 one-off to $59 a report — output, generated per query (`research/01` Segment A; matrix rows 1–12). We publish no score and no verdict.
2. **We are not a directory.** Nine alternatives directories and review platforms already own "product X → its alternatives" — AlternativeTo since 2009, and G2 is absorbing Capterra, Software Advice and GetApp (`research/02` Segment B + maturity signals). We do not compete on volume; 1,282 verified entries loses to 22,000 unverified ones on volume and we should never pretend otherwise.
3. **We are the layer nobody occupies.** No player found in this research combines **(a)** a maintained corpus, **(b)** liveness verification, and **(c)** human-stamped entries that are never deleted (`research/02`, conclusion). That combination is what makes the answer *checkable* rather than *confident*.

**The honest one-liner** (for pitch, README and the landing header):

> **The check you run privately before you build, backed by evidence you can click — from a corpus that is verified by a person and never deletes anything.**

And the companion anti-claim, which the product must be able to say out loud:

> **If the archive does not cover your idea, we say so.** "Not covered" is an answer; a confident invention is not.

**The teardown one-liner** (the pitch for the refined vision):

> **See a competitor the way a careful founder would — pricing, content, features, and the gaps — sourced and dated, then line it up against your own app. No sales battlecard, no AI opinion.**

### 4.1 The strongest counter-argument against this whole plan (must be answered, not hidden)

`research/05` found the one argument that could sink the product, and it is economic, not technical:

> *"Validation made sense when building was the expensive part… That ratio has flipped and I don't think our advice has caught up."* — Indie Hackers, 11 September 2026

If building is now an afternoon, the research this product sells may cost more than the thing it protects. Two further sources sharpen it: Paul Graham's canonical essay tells founders the job takes *"ten minutes of searching the web"* (the norm we are arguing with), and the Tow Center found AI answer engines fail to retrieve correct information in **more than 60% of 1,600 queries** — which is both the opportunity and the warning that the substitute is free and improving.

**The plan's answer, and the reason it is defensible:** sell the **outcome**, not the research. Attach to the moments where the substitute's error is expensive — *"you're about to spend three weeks on something that shipped last year"*, *"this category is a graveyard"*, *"your closest competitor was verified three weeks ago"* — rather than to the abstract virtue of doing research. That is Jobs 3 and 5 in `research/05`, which the free substitutes serve worst. Test 2 (the concierge briefs) exists to prove the outcome is worth more than the alternative, and if it fails, this plan should be re-read before anything is built.

---

## 5. Product truth model — kept, with three fixes

v1's seven evidence dimensions stand: *website reachable · product evidence found · repository active · company identity confirmed · human reviewed · last checked · status history* — plus the explicit "must not imply" list (legitimacy, quality, funding, safety, customer traction, investment value).

Three code-verified fixes folded in:

1. **The human stamp is kept, not replaced.** 1,278 of 1,282 rows (99.7%) carry a human `verified` stamp and the machinery behind it is the strongest thing in the product. The evidence model is **added alongside** the stamp. The 1,278 stamps are not re-opened (`discussion-record.md` decision D-4).
2. **"Human reviewed" gains a permanent audit trail.** Today `verify_log` is pruned to 90 days — a trust claim cannot rest on a log that expires. Making it permanent is a prerequisite for any public wording about history (D-6).
3. **A new public caveat: coverage.** "This checks a 1,282-entry archive, not the internet." Every result screen carries it.

The five public state definitions from v1 are kept verbatim: **Unverified** / **Reachable** / **Dead** / **Human reviewed** / **Unknown**, with *Unknown must remain a valid answer*.

**Added distinction the plan did not make:** the archive's most defensible rule is not the word "verified" — it is the *enforcement*: only a genuine HTTP 404/410 earns a strike, three consecutive strikes file an entry as dead, dead entries are never deleted, and a human-stamped row is protected from automation entirely (`backend/app/verify.py`). That mechanism is expensive to copy and cheap to state. It becomes the public claim under the "trust" umbrella (D-5).

---

## 6. Phase 0 — prove the brief by hand (new phase, runs first)

**What:** produce **25 hand-made, fully evidenced competitor teardowns** for 25 real, scoped ideas — each with a torn-down competitor (pricing, content/positioning, features, what it does and doesn't) plus a **you-vs-them gap table** (what the founder has that the competitor lacks, and vice versa), every claim sourced — and give them away in dev-tool founder communities.

**Why first:** it is the cheapest possible test of the core claim, it needs **no new code at all**, and it produces the worked examples the product will later be judged against. If 25 concierge teardowns cannot be produced at a quality nobody else offers, no amount of engineering will produce one. This comes from `research/04` ("First proof") and its kill rule, re-scoped to the teardown output.

**Outputs:** 25 briefs (Markdown), a tally of what was hard to answer manually, and the first version of the brief template that Phase 5 will mechanise.

**Gate:** if fewer than 20% of recipients ask for a second brief, or fewer than 4 of 25 report it changed what they planned to build, **stop and re-read `research/04` §Falsification plan before building anything.**

**MVP teardown fields (owner-confirmed 2026-09-15):** each concierge teardown is capped to *pricing (list + free tier) · 5–10 features · one-line positioning · 3–5 sourced "doesn't do" claims · the you-vs-them gap table*. The full field-by-field spec and evidence rules live in `docs/teardown-spec.md`; the gap-table format in `docs/gap-table-format.md`.

---

## 7. Phase 1 — establish the product contract and baseline — kept, numbers now filled in

v1 asked for a baseline before new features. The baseline is now measured (`docs/codebase-comprehension.md` §3) — this phase becomes **write it down and stop debating it**:

| v1 asked for | Measured value (2026-09-14) |
|---|---|
| Current archive counts | 1,282 filings; 1,278 verified (99.7%); 0 dead; 0 pivoted |
| Duplicate domains / repositories | 0 duplicate domains; 6 same-name groups (different companies), deliberately unmerged |
| Category distribution | other 302 · ai 222 · finance 173 · health 165 · devtools 140 · productivity 109 · ecommerce 67 · media 49 · education 37 · social 14 · freelance 4 |
| Verified / unverified / dead proportions | 99.7% / 0.3% / 0% |
| Data freshness | `last_checked` populated on 100% of rows; most recent pass 2026-09-04 |
| Which fields are sourced vs LLM-generated | **Not tracked in the schema today** — this is the Phase 4 fix |
| Website / GitHub coverage | 1,282 websites (100%); 57 GitHub repos (4.4%); sources: website 1,229 · github 53 |

**Phase 1 deliverables (kept from v1):** the supported query types (product name · website URL · GitHub URL · plain-English idea); the entity definitions (product, company, project, repository, domain); the statement that the first audience is founders doing competitive research; and preservation of the local-first deployment and admin-token model.

**Two additions to Phase 1:**
- **Fix the `founded` semantics** before the field is used as a filter. Live rows prove the bug: Notion is filed as founded `2000-11-01` (founded 2013); Zoom as `1996-10-18` (founded 2011), because the fallback chain ends at the RDAP **domain registration** date. Decision required: rename, split into `founded_at` + `date_source`, or drop from the facet bar (`discussion-record.md` §7.6).
- **Write the numbers into the product**, not just the plan: the UI should be able to say "1,282 filings, 1,278 human-checked, last checked 4 Sep 2026" from real data.

---

## 8. Phase 2 — fix data integrity and search — kept, re-pitched for reality

**Duplicates.** v1 treats duplicates as a live problem. The audit says: 10 same-home groups were **already merged** (1,292 → 1,282 rows) by `backend/scripts/merge_duplicates.py`, and the 6 remaining name groups (Stability AI, Motion, Fathom, Cal.com, Bun, Bird) are **different companies sharing a name** and were correctly not merged. So this phase becomes:
- Keep the 6 groups visible as disambiguation — the "×N filings" chip already does this; do not force a merge (D-8).
- Add the **admin duplicate-review queue** only as a guard for *new* duplicates arriving from seeding, plus the existing conservative merge rules (strongest verification state, historical records, alternate URLs, provenance preserved).
- Extend identity handling as v1 asks: canonical domain, normalised GitHub owner/repo, redirect destination tracking, alias URLs.

**Search.** v1's classified ranking order is kept exactly: exact product name → exact domain → phrase/name → tagline → problem-description → category/keyword → fuzzy, with stars only as a tie-breaker. Two adjustments:
- **Note what already exists.** After the dogfood cycle the search already ranks the exact name first and sinks dead entries; the plan's "stars are a primary ranking signal" line should be re-worded to "keep stars as metadata and never let them outrank a text match" (D-7) — only 57 rows have stars at all, so the risk v1 describes is narrower than stated.
- **Add the missing half of v1's own requirement:** per-result match explanations ("Exact name match", "Similar problem description", "Same audience, different approach"). This is the change that makes "see why each result matched" real; it has no code today.

**Regression tests** (kept): exact names, domains, multi-word ideas, synonyms, unrelated fuzzy matches, empty results, duplicate records — added to the existing `backend/tests/smoke.py` + `scripts/sort-check.ts` harness.

**Server-side search trigger** (kept): when the archive passes ~3,000 rows, move search to SQLite FTS5. The measured knee is documented in `main.py`; today's client-side search is 22 ms/term at 1,282 rows.

---

## 9. Phase 3 — build the research-result experience — kept almost verbatim

**Query types (kept):** Name · URL · GitHub repository · plain-English idea. Free-text ideas use deterministic local search first (extract terms, search names/taglines/descriptions/categories/aliases, rank exact and phrase matches strongly, use category/keyword overlap, no LLM per search). Semantic/LLM search only after deterministic search has been measured against real queries — **kept, and reinforced**: `research/04` names "another AI validator" as the trap.

**Result sections (kept):** Best matches · Closest alternatives · Related products · No strong match found — with v1's no-match copy kept as written, plus the coverage caveat from §5.

**Product dossier (kept):** summary, problem and target user, "why this matched", evidence and source links, website/demo/docs/GitHub actions, activity signals, human review date, similar products and alternatives, historical status, explicit limitations and unknowns, and the visible caveat "This is research evidence, not an endorsement."

**Stable canonical route (kept, promoted):** `/products/<slug>`, needed for sharing, bookmarking, SEO and any future hosted archive. **Promoted in priority** because the research flags that destination discovery is declining and a page-less product has no funnel (D-11).

---

## 10. Phase 4 — evidence and provenance — kept, reordered to fix the worst problem first

v1's schema additions and its `evidence` table both stand, unchanged in substance:

```
startups: entity_type, canonical_domain, aliases, problem_statement, target_users,
          product_url, docs_url, demo_url, pricing_model, activity_checked_at,
          activity_summary, last_human_reviewed_at, review_notes

evidence: id, startup_id, evidence_type, source_url, captured_at, claim, value,
          provenance, confidence, reviewed_at
```

**Reordering (the one substantive change in this phase):** v1 lists the field additions and the evidence table together. The rework puts **`entity_type` and a provenance flag on generated fields first**, because:

- `entity_type` is required before any "closest alternatives" claim is honest — today a filing can be a company, a product or a repository with nothing distinguishing them (e.g. `Notion` the company next to `Whisper` the repo).
- provenance is an **active liability**, not a nice-to-have: `tagline`, `description`, `category` and `founded` are LLM-drafted by `llm.py` and are indistinguishable from human-entered facts in both the database and the UI. For a product whose whole claim is traceability, this is the first thing to fix.

Kept from v1: LLM-generated descriptions are labelled machine-drafted until a human confirms them; generated prose is never ground truth without supporting evidence; the evidence examples (repo creation date, latest commit/release, archived state, homepage claims, Wayback first snapshot, automated reachability result, curator confirmation).

**Added for the teardown output (new):** the schema must also carry the fields a gap report needs — **`features` (or a `capabilities` set)**, **`pricing`**, **`content_notes`/`positioning`**, and a way to record **negative claims** ("no API", "no free tier", "no mobile app") each backed by an evidence row. Negative evidence is the payload of the gap report and it is the easiest part to fake, so every "does not do X" must trace to a source or be marked unknown.

**Pricing depth (owner-confirmed 2026-09-15): full plan-by-plan breakdown**, not just a list price. This is the expensive, fast-decaying field: pricing changes constantly, so every pricing row carries a `captured_at` and a source URL, and pricing staleness is surfaced as a first-class signal — the founder sees *"pricing captured 2026-09-14"*, never an undated price presented as current.

**Added:** the `founded` date needs a `date_source` so a Wayback or RDAP-derived date is presented as approximate, not as a founding date (§7).

**Added:** make `verify_log` permanent (drop the 90-day sweep) before any public audit-trail claim (D-6).

---

## 11. Phase 5 — comparison and decision support — kept verbatim

Local-only comparison of up to three products across the nine dimensions v1 lists (problem, audience, product type, category, core workflow, availability, activity, review freshness, evidence quality), stored in `localStorage`, exported to **Markdown, JSON and CSV**.

And the section v1 correctly calls the most important one — the prompts around **"What would be different about your version?"**: target customer · distribution · workflow · business model · technical approach · geography · privacy · integrations · narrower use case.

**Added, and this is load-bearing:** the current "More like this" similarity is a **lexical proxy** (shared category, shared language, shared tagline words). v1's promise of "closest alternatives" cannot be sold on that. This phase must name the matching upgrade explicitly (structured field overlap — problem statement, audience, product type — before any embedding work), and Phase 5 is where the Phase 0 concierge briefs become the quality benchmark.

**Added for the teardown output (new):** the comparison flow ends in a **two-sided gap table**, not just a side-by-side list — *"what you have that they don't / what they have that you don't"* — with every cell sourced. The nine comparison dimensions v1 lists (problem, audience, type, category, workflow, availability, activity, review freshness, evidence quality) are joined by the teardown dimensions the owner named: **pricing, content/positioning, features, and what each does and does not do**.

**Founder-app capture (owner-confirmed 2026-09-15): form, URL, or an agent prompt — always confirm-before-diff.** Three entry paths: (1) a **URL**, ingested through the existing `seed_from_website` path (same pipeline as competitors, new mode); (2) a **short form** with a required flat 5–10 feature list; (3) a **copy-paste AI prompt** the founder hands their own agent to return their app's data in the same JSON shape. Whichever path, the founder **reviews and confirms** the drafted profile before the gap table renders — the gap table never runs against an unconfirmed profile. The gap table is **facts only** — no generated verdict (see §18). Spec + prompt: `docs/teardown-spec.md`.

---

## 12. Phase 6 — enrich data carefully — kept, source order unchanged

v1's source order stands and is now backed by evidence rather than caution:

1. Existing archive → 2. GitHub API and repository activity → 3. existing website metadata and redirect checks → 4. Wayback metadata → 5. curated URL lists → 6. permitted public APIs/datasets → 7. carefully selected scraping, only where permitted and justified.

Kept in full: every imported fact records source URL, capture date, import method, whether it was human-reviewed, and whether it is a fact, inference or generated summary; one adapter at a time; each adapter supports deduplication, rate limits, retry/backoff, resumable jobs, import reports and provenance preservation; **do not build a giant scraper before the workflow has proven demand.**

**Added:** remove the dead `topstartups` path or bring it back into `seeder.SOURCES` — the `jobs` table shows a completed `topstartups` run (35 ok / 38 skipped / 6 failed) that the admin panel can no longer re-run.

---

## 13. Phase 7 — discoverability and retention — kept, with one hedge

Kept from v1: indexable product pages; category pages; alternatives pages for high-quality records; example searches on the landing page; "recently added" / "recently verified" / "recently marked dead"; a change feed or RSS/JSON export; "request this product" in no-result states; privacy-preserving measurement only if validation requires it; keep local-first as the default with a hosted read-only archive possible later.

**The hedge (new), because v1 bets the growth path on a channel the research says is declining:** an analysis of 76,822 launches concludes the launch-traffic model has peaked, and practitioners openly debate "Product Hunt is dead" (`research/03`, `research/04`). So discovery gets **three** legs, not one:
1. `/products/<slug>` pages (v1's plan).
2. **A published static read-only dataset** (the archive as a citable, mirrorable artifact) — export exists in Phase 5; publishing it costs little and is the account-free, page-free distribution route.
3. **An embedded check** — a documented local endpoint/CLI returning closest matches + evidence links + an explicit coverage caveat, so the check can happen where the founder already works instead of requiring a destination visit (`research/03`, Wedge 8 — the only wedge that answers the distribution problem the others create).

**Still deferred, unchanged:** accounts, comments, votes, leaderboards, community moderation — until the core research workflow demonstrates repeat usage.

---

## 14. Keep / Change / Defer — kept, with two corrections and one addition

**Keep (unchanged):** local-first architecture · no accounts by default · human review · dead entries retained · conservative link verification · warm archive identity · existing cards and admin tooling · current seed data where accurate.

**Change (corrected and extended):**
- Binary "exists" framing → research and alternatives. *(unchanged)*
- Generic `Verified` meaning → evidence-based signals, **added alongside the existing human stamp rather than replacing it** *(corrected — v1 implied replacement)*.
- Stars as a primary ranking signal → secondary metadata, **re-worded**: keep stars as metadata and never let them outrank a text match *(corrected — measured: 3 stars-bearing rows in 4.4% of the archive)*.
- Modal-only details → canonical product dossiers, **promoted earlier** *(extended)*.
- LLM-generated prose treated as fact → provenance-aware summaries, **moved first within its phase** *(corrected)*.
- **NEW:** make the verification audit trail permanent (the 90-day `verify_log` sweep contradicts any history claim).
- **NEW:** one named beachhead segment instead of four personas for the first 90 days.

**Defer (unchanged):** broad uncontrolled scraping · accounts · comments and community moderation · votes and leaderboards · funding-heavy metadata · AI-generated verdicts · decorative work that does not improve research completion.

---

## 15. Validation plan — kept, with the research's falsification tests layered on top

**Kept verbatim from v1:** test with 10–20 founders, indie hackers, product strategists or investors on real ideas; measure whether they find a relevant product, whether the first result is useful, whether they understand why it matched, whether they open evidence links, whether they compare, whether they export or share, whether they return for another idea, whether they understand "verified" correctly, whether they would use it instead of Google, whether they would contribute a missing product.

**Kept verbatim — the quality targets:** exact product matches appear first · no duplicate identity has conflicting public statuses · ≥80% of test queries have a relevant result in the top three · every trust claim has visible evidence or says "unknown" · new users understand the trust model without explanation · search-to-dossier under two minutes · users research multiple ideas in one session.

**Kept verbatim — the headline:** *"The strongest validation signal is repeated research, not compliments about the interface."*

**Layered on top (new): the falsification plan from `research/04`**, because v1's targets measure *whether the tool works* and these measure *whether the thesis is true*:

| # | Test | Pass | Fail |
|---|---|---|---|
| 1 | 20 interviews with technical founders who shipped in the last 12 months; reconstruct their last pre-build check | ≥10 used 3+ tools; ≥8 could not tell if results were alive; ≥8 distrust uncited AI; ≥5 would have changed or accelerated a decision | <8 multi-tool, or <5 distrust, or median answer is "asked ChatGPT and moved on" |
| 2 | 25 concierge briefs (Phase 0) | ≥40% ask for a second; ≥8 of 25 changed a plan; ≥5 volunteer to pay | <20% ask again, or <4 report a changed decision |
| 3 | Landing page against "get a verified prior-art brief for your idea" | ≥8% of unique visitors submit an idea; ≥30% of submitters return within 14 days | <3% submit, or <15% return |
| 4 | A/B: LLM-only brief vs evidence-linked brief | ≥60% rate the evidence version more useful; ≥50% trust it more | Evidence version rated equal or worse by ≥50% |
| 5 | Hand-audit 100 archive URLs against the automated liveness result | ≥95% liveness accuracy; ≥90% of entries checked within 30 days; zero false `dead` | <90% accuracy, or any false `dead`, or >20% stale past 30 days |
| 6 | One embedded CLI/agent integration, opt-in local instrumentation for 30 days | ≥10 genuine invocations by ≥3 distinct users | <5 invocations, or zero repeat users |

**Kill rule (from the research, adopted):** if tests 1 and 2 fail, the thesis is dead regardless of 3–6. If 1 and 2 pass but 4 fails, the product can still be a directory but must stop calling itself evidence infrastructure.

---

## 16. Implementation order — reworked

v1's order is kept, with Phase 0 prepended and two items moved earlier for stated reasons:

| # | Step | Change vs v1 |
|---|---|---|
| 0 | **Concierge proof — 25 evidenced briefs** | **NEW** |
| 1 | Baseline data and product-contract document | kept (numbers now measured) |
| 2 | **`entity_type` + provenance flag on generated fields; permanent `verify_log`** | **moved up** — an active trust liability and a prerequisite for any history claim |
| 3 | Duplicate and identity audit (finish, don't redo) | kept, scoped down |
| 4 | Search relevance regression suite | kept |
| 5 | **Per-result match explanations** | **split out** from v1's "search" step — it is the piece that makes "why this matched" real |
| 6 | Trust copy and "How this archive works" legend | kept |
| 7 | Research result sections | kept |
| 8 | Evidence and provenance schema (rest of the fields + `evidence` table) | kept |
| 9 | Product dossier and stable `/products/<slug>` URLs | kept, **promoted** |
| 10 | Comparison, export, and the "what would be different?" flow | kept |
| 11 | GitHub and Wayback activity enrichment | kept |
| 12 | One permitted external source adapter | kept |
| 13 | Founder usability testing (v1's plan + the falsification tests) | kept, extended |
| 14 | Embedded check + published static dataset | **NEW** (discovery hedge) |
| 15 | Iterate on failed searches and observed behaviour | kept |

**The first coding slice is unchanged from v1 and it still is not scraping and not semantic AI search:**

> **Audit the data, remove identity conflicts, explain the matches, and make the trust model precise.**

— with one addition, because the audit found something v1 could not have known: **label the machine-drafted text first.**

---

## 17. Stop conditions — kept, with three additions

**Kept verbatim from v1:** pause and reassess if users cannot find relevant results for real ideas · the archive cannot maintain evidence freshness · the human review backlog grows faster than it can be resolved · users interpret the product as a guarantee or a scam detector · no test users return for a second research session · data acquisition creates more maintenance cost than user value.

**Added:**
- **A false `dead` occurs in production.** The 404/410-only rule exists because a Cloudflare 403 once dead-filed healthy companies; one real false death means either the rule or the corpus is wrong. (Test 5 turns this into a monitored threshold.)
- **The first real `dead` entry cannot be shown honestly.** With 0 dead entries today, the never-delete claim is a policy, not a demonstrated behaviour. If the mechanism resolves its first death and the product cannot present it well, fix that before adding anything else.
- **The concierge brief cannot be produced at a quality nobody else offers.** That is the Phase 0 gate, and it is the cheapest kill available.

---

## 18. What we are explicitly not doing (new)

Drawn from `research/04` ("What we deliberately do NOT do") and `research/03`'s disqualifications:

- No general idea generator or inspiration feed.
- No AI verdict without sources; the product must be able to say "the archive does not cover this".
- No paywalled company database competing with Crunchbase / PitchBook on breadth; no funding data as the spine.
- No accounts, no server-side query logging, no tracking — this is the position, not a limitation.
- No full vertical pivot away from the existing breadth.
- No deletion. Dead entries are filed and kept.
- **No free public API as the business** — it contradicts the privacy identity and gives the corpus away (`research/03`, Wedge 6 verdict).
- **No "trust" as the headline** — trust is the substrate that makes the evidence claim credible, not the offer (`research/03`, Wedge 1 verdict).
- **No AI gap verdict.** The teardown's gap table is derived from sourced fields and shown with evidence; the product must not emit a generated "you will beat them because…" paragraph. A gap table of facts, not an opinion (`discussion-record.md` §9).

---

## 19. Open questions this plan does not resolve

1. **Willingness to pay for provenance.** Unproven; tests 1, 2 and 4 exist precisely because of it.
2. **Hosting vs local-only.** The code constrains it (in-process job queue, `--workers 1`, SQLite file): hosting means a read-only mirror. Discovery argues for published pages; privacy argues for local. Owner decision.
3. **The vertical.** Dev tools vs design vs a third option — dev/design is the recommended start because the seed asset already exists.
4. **Verifier capacity.** The trust claim currently rests on a very small number of humans.
5. **The `founded` field's future** — rename, split, or drop from facets.
6. **Distribution beyond a declining launch channel.**

7. **Whether research is still worth funding at all.** `research/05`'s strongest counter-argument: if a build is an afternoon, the research costs more than the thing it protects. The plan's answer (sell the outcome, not the research) is asserted; test 2 is what proves it.

All seven are recorded with recommendations in `docs/discussion-record.md`.

---

## 20. Traceability

Every change in this document is listed against its reason and its evidence in **`revamp-plan-delta.md`**. Every external claim traces to a URL and an access date in **`research/00-method-and-sources.md`**. Every codebase claim traces to a named file in **`docs/codebase-comprehension.md`**.

**What did not change, and why:** the reframe, the killer workflow, the two-minute target, the success event, the grouped result sections, the dossier, the comparison and "what would be different?", the evidence/provenance schema, the careful-enrichment source order, the deferral list, the validation targets, the stop conditions, and the first coding slice. The user said they like the approach and how it solves a problem for the founders; the research found nothing that argues against any of it, so none of it was rewritten.
