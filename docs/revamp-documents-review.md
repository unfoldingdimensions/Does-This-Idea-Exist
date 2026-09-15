# Review of the Two Existing Revamp Documents

**Prepared:** 2026-09-14
**Documents reviewed:**
- `revamp-plan.md` — "IdeaExists Revamp Plan" (14,145 bytes, 8 sections + implementation order + stop conditions)
- `Revamp-thinking.txt` — untitled working memo (11,147 bytes, same structure, denser, with file-path citations)

**Method:** both documents were read end to end and then read again against the codebase (`docs/codebase-comprehension.md`). Every claim below is either (a) the document's own stated text, quoted or paraphrased, or (b) marked as an observed difference between the two. Nothing is attributed to a document that is not in it.

---

## 1. What the two documents are

They are **two drafts of the same plan**, not two different plans. `Revamp-thinking.txt` is the earlier, more operational draft: it is written like working notes, cites concrete files and line ranges, and names the code hooks (`backend/app/db.py:81-108`, `frontend/lib/search.ts:62-82`, `frontend/components/startup-detail.tsx`, `dogfood-output/adversarial-ux-report.md:23-28`). `revamp-plan.md` is the polished version of the same content: same recommended direction, same phases, same keep/change/defer lists, same validation plan — reorganised into a cleaner "plan" shape (numbered phases, a deduplicated roadmap, no line-level citations, a "Product truth model" section that the thinking draft does not have).

**Practical consequence:** the user's "I like the approach in the revamp plan" attaches to the *shared* content of both, and the differences between the drafts are stylistic plus three small substantive additions in `revamp-plan.md`. Any rework must preserve the shared spine.

---

## 2. The founder problem the plan claims to solve

Both documents state the same reframe, in near-identical language:

> Reframe the product from **"Does this startup exist?"** to **"Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build."**

And both name the same user and the same moment of pain:

- **User:** founders, indie hackers, product strategists, and investors researching a real product idea (`revamp-plan.md`, "Product direction").
- **Moment:** the founder has an idea and needs to know what already exists **before spending time building it** — the phrasing in `Revamp-thinking.txt` is "settle the question … before spending time on an idea".
- **The job:** not "is it taken?" but "what is already out there, how close is it, and what would make my version different?" The strongest support cited inside the documents is the Hacker News comment they both quote: the value is "to understand existing approaches and see if our insights can lead to a meaningfully different solution."

**The plan's core promise to the founder is therefore:** *the archive should not just tell you that your idea exists; it should help you decide what to do next.* Both documents call the old binary badge the problem and the research result the fix.

Both also explicitly keep the hook: "Keep 'Does this startup exist?' as the memorable entry-point question and brand personality" (`revamp-plan.md`); `Revamp-thinking.txt` says the same — "the hook and brand personality".

---

## 3. The shared approach (identical in both documents)

### 3.1 The killer workflow
A first-time user completes this in **under two minutes** (both documents):
1. Enter a product name, URL, GitHub repo, or a plain-English idea.
2. Get results grouped into **Direct matches / Closest alternatives / Related products**.
3. See **why** each result matched.
4. Open a **product dossier** — what it does, target user and problem, website/demo/docs/GitHub links, activity and freshness signals, human review date, evidence sources, caveats and unknowns.
5. Select **up to three** products to compare.
6. Answer **"What would be different about your version?"**
7. **Share or export** the research.

### 3.2 The success event
Both state it verbatim in substance: the win is *not* "the user clicked a card", it is **"the user found a relevant existing product and understood how it relates to their idea."**

### 3.3 Keep / Change / Defer
Identical in both:

| | Items |
|---|---|
| **Keep** | Local-first architecture · no accounts by default · human review · dead entries retained · conservative link verification · warm archive identity · existing admin tooling and seed data |
| **Change** | The binary "exists" framing → research and alternatives · generic `Verified` meaning → evidence-based signals · stars as a primary ranking signal → secondary metadata · modal-only details → canonical dossiers · LLM prose treated as fact → provenance-aware summaries |
| **Defer** | Broad uncontrolled scraping · accounts · comments and community moderation · votes and leaderboards · funding-heavy metadata · AI-generated verdicts · decorative work that does not improve research completion |

### 3.4 The phased roadmap
Both documents carry the same seven/eight phases and the same implementation order. Phase numbering differs by one (`revamp-plan.md` folds the trust model into its "Product truth model" section and keeps trust copy inside Phase 1/2; `Revamp-thinking.txt` makes "Replace the overloaded trust model" its own Phase 3).

| Phase (shared) | Content |
|---|---|
| 1 | Establish the product contract and baseline — record counts, audit duplicate domains/repos, category distribution, verified/unverified/dead proportions, freshness, which fields are sourced vs LLM-generated; define query types and the entity model |
| 2 | Fix data integrity and search — canonical domain, normalised GitHub owner/repo, redirect tracking, alias URLs, duplicate candidates, admin duplicate-review queue, conservative merges; **classified** search ranking (exact name → exact domain → phrase → tagline → problem → category → fuzzy), explanations per result, regression tests |
| 3 | Build the research-result experience — four result sections (Best matches / Closest alternatives / Related products / No strong match found), the no-match copy, the product dossier, and a stable canonical route (`/products/obsidian`) |
| 4/5 | Add evidence and provenance — new `startups` columns (`entity_type`, `canonical_domain`, `aliases`, `problem_statement`, `target_users`, `product_url`, `docs_url`, `demo_url`, `pricing_model`, `activity_checked_at`, `activity_summary`, `last_human_reviewed_at`, `review_notes`) **and** a separate `evidence` table (`id, startup_id, evidence_type, source_url, captured_at, claim, value, provenance, confidence, reviewed_at`) |
| 5/6 | Comparison and decision support — select up to three, compare nine dimensions, store in localStorage, export Markdown/JSON/CSV, and the "What would be different?" prompt list |
| 6/7 | Enrich data carefully — the seven-step source order (existing archive → GitHub API → site metadata/redirects → Wayback → curated lists → permitted APIs → careful scraping), one adapter at a time, with dedup, rate limits, retry/backoff, resumable jobs, import reports, provenance |
| 7/8 | Discoverability and retention — indexable product pages, category pages, alternatives pages, example searches, "recently added / verified / marked dead", a change feed, "request this product", and only then any measurement |

### 3.5 The first slice and the stop conditions
Both documents end with the same instruction and the same brake:

- **First coding slice:** *not* scraping, *not* semantic AI search. "Audit the current data, remove identity conflicts, improve search explanations, and make the trust model precise."
- **Stop conditions:** users cannot find relevant results · the archive cannot stay fresh · the human-review backlog outgrows the owner · users read the product as a guarantee or a scam detector · no test user returns for a second session · data acquisition costs more maintenance than it delivers value.

### 3.6 Validation plan
Both propose testing with **10–20** founders/indie hackers/product strategists/investors on real ideas, with the same ten measures (did they find a relevant product, was the first result useful, did they understand why it matched, did they open evidence, did they compare, did they export, did they return, did they understand "verified" correctly, would they use it instead of Google, would they contribute a missing product), the same quality targets (exact matches first · no duplicate identity with conflicting status · ≥80% of queries have a relevant result in the top three · every trust claim evidenced or marked unknown · the trust model understood without explanation · search-to-dossier under two minutes), the same funnel events, and the same headline: **"The strongest validation signal is repeated research, not compliments about the interface."**

---

## 4. What `revamp-plan.md` adds over `Revamp-thinking.txt`

Only three substantive additions; everything else is restructuring.

1. **A named "Product truth model" section** (`revamp-plan.md`). It turns the trust problem into seven explicit, separately tracked evidence dimensions — *website reachable · product evidence found · repository active · company identity confirmed · human reviewed · last checked · status history* — and adds an explicit "must not imply" list: legitimacy, quality, funding, safety, customer traction or investment value. The thinking draft has the same idea but compressed into a phase.
2. **A published "How this archive works" copy block** with five plain-language state definitions (`Unverified` / `Reachable` / `Dead` / `Human reviewed` / `Unknown`) and the statement that **"Unknown" must remain a valid answer**. The thinking draft keeps "Unknown should remain a valid answer" but as a bullet, not as copy.
3. **An explicit compatibility constraint**: "Retain the current archive states for compatibility" and "Preserve the current local-first deployment and admin-token model while keeping the data model compatible with a future hosted read-only archive." The thinking draft says "the local-first model can remain the default while offering a hosted read-only archive later" but does not state the data-model compatibility requirement.

Smaller differences: `revamp-plan.md` merges the thinking draft's duplicate phase list into one roadmap; it drops the thinking draft's line-level code citations; it adds "Do not automatically merge ambiguous companies that merely share a name" (the thinking draft has it too, so this is a wash); and it renames "Phase 3: Replace the overloaded trust model" into a "Product truth model" that sits *before* Phase 1 rather than inside the roadmap.

---

## 5. Internal assumptions the documents rest on (stated or implied)

Each of these is load-bearing for the plan. They are listed here because the rework has to either confirm, revise or drop them.

| # | Assumption | Where it lives | Status against the code |
|---|---|---|---|
| A1 | The archive is large and clean enough to be useful as research material. | Whole plan | **Partly.** 1,282 rows, 100% with a URL, but only 4.4% with a GitHub repo and 0 dead rows — no negative examples to research against. |
| A2 | Deterministic local search can carry the "plain-English idea" query type without an LLM. | Phase 3, both docs | **Plausible but unproven.** Today's Fuse config matches phrases well and has no idea-sentence mode; the plan itself says semantic search "only after deterministic search has been measured". |
| A3 | Stars are currently a primary ranking signal that must be demoted. | Change list | **Overstated.** Stars are a tie-breaker and the second key of one of five sorts; 95.6% of rows have no stars at all. |
| A4 | "Verified" currently implies more than it should, and users misread it. | Phase 3 / truth model | **Confirmed by prior evidence.** The adversarial dogfood report found a cold-start user reading the grey majority as "unfinished"; the CHANGELOG records a copy fix where "Every listing checked by a human" contradicted the 317-of-1,292 reality. |
| A5 | Duplicates are a live trust problem. | Phase 2 | **Mostly fixed already.** 10 same-home groups were merged (1,292 → 1,282); 6 same-name/different-company groups remain and are correctly *not* merged. |
| A6 | The owner can absorb a human-review backlog. | Stop conditions | **Held so far**: 1,278 of 1,282 rows are stamped. |
| A7 | The entity model (product / company / project / repo / domain) can be separated without a rewrite. | Phase 1–2 | **Not yet true in schema** — one flat `startups` table, no `entity_type`. |
| A8 | Provenance can be added "incrementally" without migrations breaking existing rows. | Phase 4/5 | **Feasible**: schema is `CREATE TABLE IF NOT EXISTS` + additive-only by policy; a new `evidence` table is the lowest-risk option the plan itself recommends. |
| A9 | A future hosted read-only archive is on the table, but not now. | Product direction | **Constrained by code.** In-process job queue + `--workers 1` + SQLite file means "hosted" is a read-only mirror, not a hosted product. |
| A10 | The plan is about product direction, not branding. | Working title note in `PRODUCT.md` | **Consistent** — the plan keeps "Does this startup exist?" as the hook and treats the public persona question (Curator internal vs public) as open. |

---

## 6. What the two documents do **not** contain

This is the gap list that the research and the reworked plan have to fill. None of these is a criticism of the drafts' intent; they are the things a plan of this shape naturally omits, and each one is now answerable.

1. **No competitor analysis of any kind.** Neither document names a single competing product, estimates a market size, or states whether the space is saturated. (The repo's own `docs/research-features-ux.md` is a *feature* benchmark, not a competitive landscape, and it is dated 2026-08-09, before this reframe.)
2. **No differentiation analysis.** "Research result, not a badge" is a product behaviour, not yet a defensible wedge. No wedge is named, ranked, or tested.
3. **No definition of the target founder beyond a list of personas.** "Founders, indie hackers, product strategists, investors" is a set, not a segment; the plan never cuts it to one beachhead.
4. **No acquisition or distribution thinking.** Discoverability (Phase 7/8) is about SEO and change feeds inside a local-first app that has no host — the plan does not say how the first hundred users arrive.
5. **No business model beyond "no accounts / no paywall".** The docs' own cited evidence (users resenting Crunchbase paywalls) implies a position but not a revenue path.
6. **No effort estimates, no sequencing across the phases beyond the numbered list, and no owner.** The implementation order is a list, not a schedule with dependencies.
7. **No success metric for the product itself.** The validation plan measures a test session; nothing defines what "the archive is good enough" means numerically (e.g. result coverage per query, share of rows with a problem statement, evidence coverage).
8. **No treatment of the two most awkward code facts:** 0 dead entries (so the plan's "dead entries retained" story is untested) and 4.4% GitHub coverage (so "repository active" is an evidence dimension that applies to almost nobody).
9. **No decision on the human gate's future.** If the product becomes research-oriented, does every entry still need an owner stamp, and does the stamp still gate things the way it does today? The docs keep the gate but never test it against the new goal.
10. **No explicit delta discipline.** Neither document says which parts of itself are load-bearing versus provisional, which is exactly why a rework needs a delta document.

---

## 7. Summary — what must survive any rework

The user said they like "the approach" and "how we solve a problem for the founders". Stripped to its load-bearing parts, that is:

1. **The reframe**: existence → alternatives → differentiation. (Hook kept: "Does this startup exist?")
2. **The two-minute killer workflow** with grouped results, per-result reasons, a dossier, a three-way compare, and a "what would be different?" answer.
3. **The success event**: the user found a relevant product *and understood how it relates to their idea*.
4. **Trust as the product**: evidence dimensions instead of one `Verified`, human review as a real gate, dead entries filed and never erased, and a precise "How this archive works" legend.
5. **Honesty about provenance**: machine-drafted text is labelled until a human confirms it.
6. **The brakes**: no uncontrolled scraping, no accounts, no AI verdicts, and the stop conditions.
7. **The first slice**: fix data, dedupe, explain matches, make the trust model precise — *before* building anything clever.

Anything the rework changes has to be argued against this list, and the delta document is where that argument is recorded.
