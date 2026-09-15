# Discussion Record — Reworked Revamp Plan

**Started:** 2026-09-14 (round 1)
**Topic:** the IdeaExists revamp — codebase read, the two existing revamp documents, deep research into the competitive landscape, and what the rework should change.
**Status:** Round 1 complete on the agent side. Owner answers to the questions in §5 are **still open**; nothing in §6 has been confirmed by the owner yet.

---

## 1. What this record is

The user asked for a discussion alongside the research ("lets discuss… I like the approach we have in the revamp plan and how we solve a problem for the founders"). This file is the written half of that discussion, so the outcome does not live only in a chat scrollback. It records:

- what was actually read and found (§2–§3),
- what the research says and where it contradicts the plan (§4),
- the questions put to the owner, each with a recommended default (§5),
- the decisions taken by default so the work could continue without blocking (§6),
- what stays unresolved (§7).

When the owner replies, this file is updated with their answers and the affected decisions move from §6 to a "confirmed by owner" note.

---

## 2. Inputs reviewed

| Input | What it is | Verdict |
|---|---|---|
| `backend/`, `frontend/`, `scripts/`, `docs/`, `dogfood-output/` | The whole codebase (every hand-written source file) | Read; findings in `docs/codebase-comprehension.md` |
| `revamp-plan.md` | The polished revamp plan | Read; two drafts of one plan — see `docs/revamp-documents-review.md` |
| `Revamp-thinking.txt` | The earlier working memo of the same plan | Read; same spine, with line-level code citations |
| `research/01-competitive-landscape.md` | 59 named players, 8 segments | 59 players; crowded at the listing layer |
| `research/03-differentiation-options.md` | 8 wedges, each tested and ranked | 3 KEEP, 5 CONDITIONAL, 0 pure DISQUALIFY |
| `research/04-market-saturation-verdict.md` | Saturation verdict + falsification plan | Saturated at "output", open at "accountability" |
| `research/02-competitor-profiles.md` | 59 player profiles + the sourced landscape matrix | Landed; 59 profiles = 59 matrix rows = the stated total |
| `research/05-substitutes-and-status-quo.md` | What founders do today instead (10 substitutes, 20 sourced quotes) | Landed; contains the single strongest argument against the plan |

---

## 3. What the codebase actually says (the part that matters to the plan)

Presented as the "here is what we really have" section, because the plan's premises need checking against the machine.

1. **The archive is real and current, but narrow.** 1,282 filings, all with a live URL, checked as recently as 2026-09-04 — but only **57 rows (4.4%)** have a GitHub repo and **1,229 came from website seeding**. The plan's "stars as a ranking signal" change is aimed at a field that is empty for 95.6% of the archive.
2. **The trust model is proven mechanically and unexercised empirically.** 1,278 of 1,282 rows are human-stamped (99.7%) and **zero entries are `dead`**. "Dead is a status, not an erasure" is true in code and invisible in the data.
3. **There is no evidence layer at all.** Three tables — `startups`, `verify_log`, `jobs`. No `evidence`, no `entity_type`, no provenance flag on the LLM-drafted `tagline`/`description`/`category`.
4. **`founded` is often not a founding date.** Live example: Notion is filed as founded `2000-11-01` (the company was founded in 2013); Zoom is filed as `1996-10-18` (founded 2011). The seeding order is LLM → Wayback first snapshot → **RDAP domain registration**, so a domain-registration date lands in a field the UI presents as "Founded" and the filter bar uses as a facet. This is a concrete, citable provenance bug.
5. **Search is good and silent.** After the dogfood cycle, `frontend/lib/search.ts` ranks the exact match first and sinks dead entries — but it never says *why* a row matched. The plan's "see why each result matched" has zero code behind it.
6. **The product is one route.** Detail is a modal; "Share Entity" copies `/?q=<name>`. There is no `/products/<slug>`, no comparison, no export.

**Discussion point raised:** the plan treats "stars drove the ranking" and "duplicates are a live trust problem" as current problems. In the code, stars are a tie-breaker on a field that is 95.6% empty, and the duplicate merge was **already applied** (1,292 → 1,282; 10 same-home groups merged; the 6 remaining same-name groups are different companies and were deliberately left). Both plan items should be re-pitched as *"keep it that way / finish the job"* rather than *"fix this"*.

---

## 4. What the research says that the plan does not

| Research finding | Source | Why it changes the plan |
|---|---|---|
| **59 named players across 8 segments**; the contested ground is idea-validation checkers (12) and alternatives directories (9) | `research/01-competitive-landscape.md` | The plan has no competitive section at all. The reworked plan needs a "who we are not" section naming the crowded layers. |
| **The saturated layers sell *output* — a score, a listing, an opinion**; the open layer sells *accountability* — a traceable claim, an undying record, a private check | `research/04`, verdict | This is the sharpest sentence available for positioning. The plan's current pitch ("research result, not a badge") says the *shape* of the change but not the *reason to believe*. |
| **DimeADozen already markets "receipts / 600+ citations" as its differentiator** | `research/04` | "We cite sources" is **not** novel on its own. The evidence wedge must be paired with the corpus + liveness + privacy, not sold as citations-vs-no-citations. |
| **AlternativeTo already occupies "free, no-account, no-tracking"** | `research/04` | The plan's implicit "privacy is our differentiator" is only half-true; privacy is a *posture* everyone in the free tier claims. It is the *local* + *verified* combination that is unoccupied. |
| **Peak-of-discovery evidence:** a 76,822-launch analysis concludes the launch-traffic model has peaked; practitioners openly discuss "Product Hunt is dead" | `research/03`, `research/04` | The plan's Phase 7/8 (indexable pages, category pages, change feed) assumes destination-discovery works. That assumption needs a hedge — a published static dataset and an embedded check — or the growth path is a bet on a declining channel. |
| **Only a genuine 404/410 counts as a strike, 3 strikes → dead, never deleted, verified rows protected** | codebase (`verify.py`) | This is the most unusual, hardest-to-copy thing in the product and **none of the two revamp documents names it as the moat**. The rework should promote it from "keep" to "the claim". |
| **The 90-day `verify_log` retention directly contradicts a permanent-record claim** | codebase (`verify.py`) | Any "long-lived public record" or "audit trail" language requires making the log permanent first. Cheap, concrete, and currently missing from the plan. |
| **Nothing in the plan defines a beachhead segment** | `revamp-plan.md`, `Revamp-thinking.txt` | Research proposes one: technical solo founders with a scoped idea in dev tools / design-adjacent software. The plan's "founders, indie hackers, product strategists, investors" is a set, not a segment. |
| **The strongest argument against the plan is economic, and the plan does not contain it**: "Validation made sense when building was the expensive part… That ratio has flipped" (Indie Hackers, 11 Sep 2026) | `research/05` | If a build is an afternoon, research may cost more than the thing it protects. The rework answers "sell the outcome, not the research" and makes test 2 the proof — but this is the one claim that could invalidate the whole project. |
| **The authoritative norm says the job is trivial**: Paul Graham — "Ten minutes of searching the web will usually settle the question" | `research/05` | Any positioning implies arguing with the founding text of the audience. The product must attach to a moment of consequence, not to idle curiosity. |
| **The default substitute is measurably unreliable for this exact job**: AI search engines failed to retrieve correct information in >60% of 1,600 queries (Perplexity wrong in 37%) | `research/05`, Tow Center / CJR | This is the opportunity: the product can win where the substitute is *provably wrong*, not where it is merely inconvenient. |
| **The most under-served sub-job is liveness** ("is it alive?") — no free substitute answers it | `research/05` (jobs 2 and 4; Product Hunt is a snapshot, AlternativeTo lists corpses, Crunchbase tracks funding) | Directly validates the codebase's weekly liveness pass + never-delete rule as the product's best white space. |

---

## 5. Questions put to the owner (with a recommended default)

Each question is answerable with a sentence; each has a default I applied so the work could continue. **None of these has been confirmed yet.**

**Q1 — Is the founder problem the plan solves the right one, or should it be sharpened?**
The plan says: *help the founder decide what would be different before they build.* The research's answer to "why would they come to us instead of ChatGPT" is: *because we hand back evidence you can click, from a corpus that is verified and never deleted, and the check never leaves your machine.*
*Recommended default: keep the founder problem exactly as the plan states it, and add the evidence/accountability line as the "why us".* → applied in `reworked-revamp-plan.md` §2.

**Q2 — Should the target user be cut to one beachhead, or stay the four-persona list?**
*Recommended default: keep all four audiences as the long-term picture, but name one beachhead for the first 90 days — technical solo founders with a scoped idea in dev tools / design-adjacent software.* → applied, §3.

**Q3 — Does the plan keep "verified" as the owner's manual stamp, or move to a per-field evidence model?**
The code has one `verified` integer. The plan wants seven evidence dimensions plus an evidence table.
*Recommended default: keep the human stamp as-is (it is the trust asset and it works: 99.7%), and add the evidence dimension *alongside* it rather than replacing it. Do not re-open the 1,278 stamps.* → applied, §6.

**Q4 — Do we accept the plan's "change stars from a primary ranking signal" framing, given stars only exist on 4.4% of rows?**
*Recommended default: reword it to "keep stars as metadata and never let them outrank a text match", and note that the current code already does this after the dogfood fixes.* → applied, delta item D-7.

**Q5 — Do we finish the duplicate work with an in-app merge queue, or leave the 6 same-name groups flagged?**
*Recommended default: leave the 6 groups as permanent, visible "×N filings" disambiguation (they are different companies), and add the admin merge queue only if a new duplicate appears from seeding.* → applied, §6.

**Q6 — Is the product allowed to become a hosted public archive, or does it stay local-only?**
The code constrains this: in-process job queue, `--workers 1`, SQLite file. Hosting means a read-only mirror, not a hosted product. Research flags that a local-only, page-less product has **no organic funnel**.
*Recommended default: stay local-first as the product; publish a **static, read-only dataset + per-product pages** as the discovery surface; keep the live app local. Do not build accounts.* → applied, §7.
*This is the question with the largest commercial consequence — worth an explicit owner call.*

**Q7 — Does the archive need to grow before the product work, or can both proceed together?**
Research's proposed first proof is 25 hand-made, fully evidenced prior-art briefs, which needs no new code at all.
*Recommended default: prove the brief by hand first (concierge), then build the evidence table and the comparison flow to mechanise it.* → applied, §8.

**Q8 — Which of the research's falsification tests do we commit to running before building?**
*Recommended default: run tests 1 and 2 (20 interviews; 25 concierge briefs) before any build beyond the evidence table; treat tests 3–6 as post-build.* → applied, §9.

**Q9 — Do we accept “sell the outcome, not the research”?**
`research/05` surfaces the one argument that could sink the product: if building is now an afternoon, research costs more than the thing it protects (Indie Hackers, 11 Sep 2026), and the canonical advice tells founders the job takes ten minutes.
*Recommended default: yes — position on the expensive-mistake moments (“you're about to spend three weeks on something that shipped last year”, “this category is a graveyard”) rather than on the virtue of research, and let the Phase 0 concierge briefs be the proof.* → applied, `reworked-revamp-plan.md` §4.1 and §19.

---

## 6. Decisions taken by default this round (unconfirmed by owner)

These are the defaults from §5, applied so the reworked plan and the delta could be written. Each one is reversible and each is marked in the reworked plan where it bites.

| # | Decision | Basis |
|---|---|---|
| D-1 | Keep the founder-problem framing ("decide what would be different before you build") unchanged. | The user said they like it; the research supports it. |
| D-2 | Add an explicit "why us, not ChatGPT" line built on traceable evidence + a maintained verified corpus + a private check. | `research/04`, verdict. |
| D-3 | Name one beachhead segment for the first 90 days; keep the other three personas as the later market. | `research/04`, underserved segment. |
| D-4 | The human `verified` stamp stays and is not rewritten; the evidence model is added beside it. | Codebase (`verify.py`), 99.7% stamped. |
| D-5 | Promote the 404/410-only strike rule + 3-strike-never-delete + verified-rows-protected from "keep" to "the moat, stated publicly". | `research/03` wedge 4; `research/04`. |
| D-6 | Make the `verify_log` permanent (drop the 90-day retention) before making any audit-trail claim. | Codebase contradiction. |
| D-7 | Reword the stars item from "stars are a primary ranking signal" to "keep stars as metadata; text matches always outrank them". | Live data: 57/1,282 rows have stars. |
| D-8 | Leave the 6 same-name filings visible as disambiguation rather than forcing a merge. | CHANGELOG: merge applied; groups are different companies. |
| D-9 | Add `entity_type` and a provenance flag for LLM-drafted fields as the first schema change — before pricing/audience fields. | `research/03` gap list; active trust liability. |
| D-10 | Ship export (Markdown / JSON / CSV) early; do not ship a hosted API. | `research/03` wedge 6 verdict. |
| D-11 | Hedge the discovery plan with a public static dataset + `/products/<slug>` pages, because destination discovery is reported to be declining. | `research/03`/`04` peak-of-discovery evidence. |
| D-12 | Concierge-proof (25 briefs) precedes mechanisation. | `research/04`, first proof + kill rule. |

---

## 7. Open items that are genuinely unresolved

1. **Willingness to pay for provenance.** Unproven. Nothing in the research shows founders will pay for rigour they cannot feel when a free, confident, instant answer is one keystroke away. Tests 1, 2 and 4 in `research/04` exist to settle this and are the reason not to build far ahead of them.
2. **Hosting vs local-only (Q6).** The largest commercial fork; the code constrains it and the research says a page-less product has no funnel. Owner decision required.
3. **Vertical choice (dev tools vs design vs something else).** Research suggests starting where the 201-site curated library and the 57 GitHub rows already give leverage; not yet confirmed.
4. **How many verifiers.** The trust claim rests on a very small number of humans. The plan's stop condition ("review backlog grows faster than it can be resolved") is untested at any scale.
5. **The first real dead entry.** Zero today. Until the mechanism resolves one in production and the product shows it well, the never-delete claim is a policy, not a demonstrated behaviour.
6. **`founded` semantics.** Should the field be renamed, split into `founded_at` + `date_source`, or dropped from the filter bar? The bug is confirmed; the fix is a product decision.
7. **Distribution beyond a declining launch channel.** The embedded-check hedge (research wedge 8) is the proposal; unvalidated.
8. **Is research still worth funding at all?** `research/05`: "if the build is an afternoon, the research costs more than the thing it's protecting." No price-sensitivity evidence exists either way. This is the highest-consequence unknown in the whole engagement.
9. **Does the “dead but never deleted” rule read as a feature or as clutter?** `research/05` notes no substitute does this, so there is no precedent to borrow — and the archive currently has zero dead entries to show.

---

## 8. How this record gets updated

On the owner's reply, this file is revised: each answered question gets a "**Owner:** …" line, the corresponding §6 row moves to a confirmed section, and any decision that changes is reflected in `reworked-revamp-plan.md` and re-stated in `revamp-plan-delta.md` with the reason.

---

## 9. Round 2 — owner's answers (2026-09-15)

### Answers received

**Q1 · Q2 · Q3 — "all defaults".** The three defaults are now confirmed owner decisions, not just applied-by-default:

- **Q1 (hosting):** stay local-first as the product; publish a static read-only dataset + `/products/<slug>` pages as the discovery surface; no accounts, no hosted live product.
- **Q2 (beachhead):** technical solo founders with an already-scoped idea in dev tools / design-adjacent software, for the first 90 days; the other three personas stay the later market.
- **Q3 (framing):** sell the outcome, not the research.

**Q4–Q9** remain as applied-by-default (see §6) until the owner objects.

### New direction stated by the owner

> "My vision is more inclined towards it becoming a tool that founders can use to analyse their competitors — like pricing, content, what they do, what they don't, compare their app with that app and give a concrete comparison on what they have against the competitor and what they lack. We can certainly discuss more on this idea."

**What this changes.** It moves the product's centre of gravity from *existence/alternatives research* to **competitive teardown + gap analysis**. The core output is no longer "here are the closest products and how they relate to your idea" — it is **"here is competitor X, torn down (pricing, content, features, what they do and don't), and here is a concrete you-vs-them gap table: what you have that they don't, what they have that you lack."**

**This is consistent with, and sharpens, everything already in the plan:** it is Wedge 3 ("what would be different?") fused with Wedge 4 (evidence/provenance) from `research/03`, with the output upgraded from a comparison list to a *teardown*. It keeps the liked founder-problem framing — it makes it more literal: the founder walks away with a gap report, not a yes/no.

### What it implies (the honest parts)

1. **The archive must hold per-product *features*, *pricing*, and *content/positioning* — not just name/tagline/description.** Today it has none of those fields. This makes the Phase 4 schema work (which the plan already listed) *required for the product to work at all*, not optional.
2. **"What they don't do" is the hard, valuable, and easy-to-fake part.** Negative evidence ("competitor has no API", "no mobile app", "no free tier") is the gap-report payload, and it is exactly the kind of claim that must be sourced ("their pricing page lists no free tier", "their docs have no API reference") or the gap report is opinion.
3. **It moves the product closer to a crowded-but-enterprise corner.** `research/02` already profiles Crayon/Klue/Kompyte (competitive intel, ~$15k/yr, sold to sales teams), StackShare (dev-tool comparison), and validators like Preuve AI / ScribeAI ("competitor discovery + comparison"). The wedge that keeps us out of that crowd is unchanged: *verified, sourced, founder-priced, local-first, gap-oriented* — a founder's teardown, not a sales battlecard.
4. **The Phase 0 concierge proof becomes teardowns, not just briefs.** 25 hand-made "competitor teardown + you-vs-them gap" documents test whether the vision is real before any code.

### Round 3 — owner's answers on the teardown specifics (2026-09-15)

| # | Question | Owner's answer |
|---|---|---|
| 1 | Minimal teardown (MVP) | **Yes** — pricing (list + free tier), 5–10 features, one-line positioning, 3–5 sourced "doesn't do" claims, gap table |
| 2 | How the founder describes their own app | **A form, or a URL** — if they have a website we ingest it and extract the info (same pipeline as seeding, applied to the founder's own product) |
| 3 | Where "what you lack" comes from | **A gap table (facts)** — no generated verdict |
| 4 | Pricing depth | **Full plan-by-plan breakdown** (not just list + tier count) |
| 5 | Scope | **Teardown sits on top of** the existence/alternatives entry point (kept) |

**What each answer concretely implies:**

1. **MVP teardown = six fields, capped.** Pricing (list + free tier) · 5–10 features · one-line positioning · 3–5 sourced "doesn't do" claims · the gap table. Anything beyond that is post-MVP.
2. **Founder-app capture = form OR URL.** The existing `seed_from_website` pipeline (`enrich.py`) already fetches a homepage and drafts a profile; the same path can ingest the founder's own site to seed the "your app" side of the comparison. No new backend primitive required — a new *mode* of an existing one.
3. **Gap table is facts.** Confirms the guardrail already in §18 ("No AI gap verdict"): every cell sourced or marked unknown.
4. **Full plan-by-plan pricing is the expensive choice, accepted knowingly.** This drives ingestion cost and staleness (pricing changes fast) — so pricing rows must carry a `captured_at` + source URL, and staleness of pricing is a first-class, visible thing, not a hidden one.
5. **Teardown sits on top of existence/alternatives.** "Does this startup exist?" stays the front door and acquisition surface; the teardown is the destination. Confirms the plan's structure.

### Round 4 — owner's answers (2026-09-15)

| # | Question | Owner's answer |
|---|---|---|
| 1 | What counts as a "feature" | **Flat 5–10 list** (no capability groups in MVP) |
| 2 | Founder-app form fields + feature list | **Exactly as recommended**, plus a required good feature list — and add a **small AI prompt** the founder can hand their own agent so it returns their app's data in the structured format |
| 3 | Confirm-before-diff | **Always confirm** — the founder reviews the auto-drafted profile before the gap table runs |

**Implications:** (1) features are a flat list of 5–10, compared at the capability level not the wording level (as already in `docs/gap-table-format.md`); (2) the founder-app capture now has three entry paths — URL (ingest), form (with a required feature list), or **paste a structured payload produced by their own agent** via the copy-paste prompt in `docs/teardown-spec.md` §3; (3) the flow is **ingest → confirm → diff**, never ingest → auto-diff.

### Status

Round 4 recorded. `docs/teardown-spec.md` carries the flat-feature rule, the three-path founder-app input (including the AI prompt), and confirm-before-diff; `reworked-revamp-plan.md` §11 and the delta (C-18) reflect it. The teardown input/output are now fully specified for MVP; the next thing to make concrete when the owner wants is the actual seed/extract pipeline change list (which existing `enrich.py` functions move to the teardown fields).
