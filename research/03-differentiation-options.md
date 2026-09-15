# 03 — Differentiation Options

**Product:** IdeaExists (working title) — local-first, verification-first startup directory.
**Reframe under test:** "Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build."
**Access date for all external sources: 2026-09-14.**
**Document status:** decision input, not a plan. Every wedge below is either *kept*, *made conditional on a specific test*, or *disqualified*.

---

## Scope

This document proposes the concrete differentiation wedges available to IdeaExists, tests each against external evidence and against the capability list of the codebase as it exists today, and disqualifies the ones that cannot be defended. It does **not** cover pricing, go-to-market sequencing, or the saturation verdict — those live in `04-market-saturation-verdict.md`. Where a claim cannot be verified from a public source it is marked `[ASSUMPTION]`; where the evidence is genuinely two-sided it is marked `[OPEN QUESTION]`.

**Baseline facts treated as given** (from the codebase audit, not re-derived here): 1,282 filings, 1,278 human-verified (99.7%), 0 dead; 1,229 seeded from websites, 53 from GitHub; 57 rows with a GitHub repo; 3 tables (`startups`, `verify_log`, `jobs`); a human "verified" stamp automation may never write; a weekly automated liveness pass in which only a genuine HTTP 404/410 counts as a strike; 3 consecutive strikes → status `dead`, filed and never deleted; a visible per-entry strike counter; a reverse-chronological verify log with 90-day retention; ingestion via bundled famous-startup list (~65), GitHub search API, pasted URL list, a 201-site curated design library, and single-URL add-by-website/GitHub with LLM profile drafting (deepseek-v4-flash); Wayback first-snapshot and RDAP registration dates as founded-date fallbacks; SSRF guard and per-IP rate limits; client-side Fuse.js search with relevance ranking and facets; card grid + "ledger" table; detail dossier modal; "More like this" scored by shared category/language/tagline words; share-link button; admin panel (seed / verification / health-check); keyboard shortcuts; WCAG AA in both themes; full `prefers-reduced-motion` support.
**Known gaps:** comparison flow, stable `/products/<slug>` routes, export (MD/JSON/CSV), duplicate-merge queue, provenance labels on LLM-drafted text, an evidence table, entity typing (product vs company vs repo), pricing/audience fields.

## Method

1. Enumerate the candidate wedges (seven supplied by the brief, one added because the research pointed to a distribution failure mode the others did not address).
2. For each: state the wedge in one sentence; test the *demand* against external evidence with a link and access date; state what the team would have to be world-class at; separate **already supported in code** from **would have to be built**; state the single strongest counter-argument honestly; assign a verdict.
3. Rank the survivors on defensibility, build cost, codebase leverage and best-fit segment.
4. State plainly where the code gives an unfair advantage and where it does not.
5. Conclude with the ordered shortlist.

A note on evidentiary strength: several sources below are marketing pages of competing products (e.g. validator/prior-art tools). Their *existence* is evidence of a crowded layer; their *claims* are not treated as proof of demand. Where a statistic is only available second-hand, that is stated.

---

## The candidate wedges

### Wedge 1 — Human-verified trust as the product

**One sentence.** Sell the guarantee, not the listing: every entry was verified by a person, is re-checked automatically every week, and a dead entry is *filed, never deleted*.

**Why it might matter.** Directories rot and die quietly. Pew Research found that 38% of webpages that existed in 2013 were no longer available a decade later, and even 8% of pages that existed in 2023 had already disappeared (https://www.pewresearch.org/data-labs/2024/05/17/when-online-content-disappears/ — accessed 2026-09-14). The most-discussed weakness of the incumbent funded-company database, Crunchbase, is missing and stale information — users on G2 cite gaps especially for non-US and mid-market companies (https://www.g2.com/products/crunchbase/reviews?qs=pros-and-cons — accessed 2026-09-14). Crowdsourced alternatives have the mirror problem: AlternativeTo's value proposition is community-built, which is exactly why coverage and freshness vary by category (https://alternativeto.net/ — accessed 2026-09-14).

**What we would have to be good at.** Maintaining a verification ritual at a cadence that never falls behind the archive; making "verified" *legible and auditable* rather than a badge; recruiting/rotating verifiers; and defining what "verified" means per field (URL alive ≠ product alive ≠ product comparable).

**Already supported in code.** The human stamp that automation may never write; the weekly liveness pass; 404/410-only strike definition; 3-strike → `dead`, filed not deleted; per-entry strike counter; verify log; admin verification and health-check panels; 1,278/1,282 human-verified.

**Would have to be built.** A *permanent* verification audit trail (the current log is 90-day retention — a public trust claim cannot be backed by a log that expires); who-verified-what-when attribution; a dispute / re-verification path; second-verifier sampling; per-field verification semantics; "verified" surfaced as a dated, clickable claim on every card.

**Strongest counter-argument.** Trust is table stakes, not a product: nobody pays a free directory for a badge, verification is a permanent cost centre, and any competitor can print the word "verified" without the enforcement machinery. On current data the mechanism is also *unproven* — 0 dead entries means the strike system has never actually resolved an entry to `dead` in production.

**Verdict: CONDITIONAL.** Keep the machinery and surface it, but do not make "trust" the headline product; it is the substrate for Wedge 4, not the offer.

---

### Wedge 2 — Local-first / privacy-first research

**One sentence.** Nothing leaves the machine: no accounts, no tracking, no analytics, searches never transmitted, and (once built) everything exportable.

**Why it might matter.** Local-first is an established, actively debated software philosophy with a durable minority following (https://www.inkandswitch.com/essay/local-first/ — accessed 2026-09-14), and its limits are openly discussed by practitioners, which means the audience is educated rather than naive (https://rxdb.info/articles/local-first-future.html and https://www.reddit.com/r/opensource/comments/1tpj4af/is_localfirst_architectural_complexity_killing/ — both accessed 2026-09-14). The founder-specific argument is that a competitor-research query *is* the sensitive artefact: the pattern of what you search, and when, is a roadmap leak that server-side directories log by default. `[ASSUMPTION]` — this motivation is plausible and widely repeated in founder forums, but no study was found quantifying founders' willingness to pay for search privacy.

**What we would have to be good at.** Distribution of a locally-run app (install friction is the killer); keeping a *local* archive fresh without a server; a genuinely one-click setup; a verifiable "no telemetry" proof.

**Already supported in code.** The whole runtime: FastAPI + SQLite (WAL) + Next.js on the owner's machine; no accounts, no tracking, no analytics; searches never leave the machine; SSRF guard; per-IP rate limits.

**Would have to be built.** One-click installer and updater; an archive-update channel for a local-first app (this is the hard, unresolved problem — if the corpus updates centrally, "local-first" is only about the *search* and the position must be stated that precisely); export (currently missing); a published, checkable privacy statement.

**Strongest counter-argument.** The fear that motivates this wedge is the fear the market has repeatedly told founders to ignore ("nobody is going to steal your idea" is a well-worn position — e.g. https://daniellenewnham.medium.com/no-one-is-going-to-steal-your-idea-ee74e2d60dc8 — accessed 2026-09-14), and, far more damaging, a local install destroys the growth engine a directory depends on: indexable pages. A directory with no public URLs cannot be discovered by search or linked to in an answer, which is precisely how this category acquires users.

**Verdict: CONDITIONAL.** Keep as a *posture* (no account, no tracking, exportable, permissionless) and as a differentiator for a privacy-conscious dev segment; **disqualify local-only delivery as the primary channel** until the distribution counter-argument is answered.

---

### Wedge 3 — "What would be different about your version?" decision support

**One sentence.** Turn existence ("this already exists") into a decision ("here is the closest set, here is where they overlap, here is the gap you could occupy").

**Why it might matter.** The job-to-be-done is large and repeated: "no market need" is the most-cited reason startups fail, widely reported at ~42% from CB Insights' analysis of post-mortems (second-hand aggregations: https://revli.com/blog/50-must-know-startup-failure-statistics/ and https://www.makerstations.io/startup-failure-rate-statistics/ — both accessed 2026-09-14; the underlying figure is CB Insights' and should be treated as directional). Competitive positioning as a discipline is standard in founder-facing guidance (e.g. https://review.firstround.com/future-founders-heres-how-to-spot-and-build-in-nonobvious-markets/ — accessed 2026-09-14). The reframed product statement in the brief *is* this wedge.

**What we would have to be good at.** Producing a *decision* from evidence without becoming an opinion generator; structuring comparability (pricing, audience, positioning); refusing to answer when the evidence is thin — the discipline not to bluff.

**Already supported in code.** Full-archive client-side Fuse.js search with relevance ranking (exact name first); facets for category / founded year / status; 5 sort keys; URL-synced shareable query state; detail dossier modal; a "More like this" block scored by shared category/language/tagline words; share-link button.

**Would have to be built.** A comparison flow (side-by-side N entries, which the brief lists as missing); structured comparability fields — pricing and audience are explicitly absent today; entity typing (product vs company vs repo) so a comparison doesn't mix a repo with a company; stable `/products/<slug>` routes so a comparison is linkable; export of a "differentiation brief" (MD/JSON). Critically, the current similarity signal — shared category, language and tagline words — is a **shallow lexical proxy**; a trustworthy "closest alternatives" claim needs better matching than that, and the brief should say so.

**Strongest counter-argument.** This is the wedge most exposed to commoditisation. The market is already full of tools that answer precisely this question with an LLM's opinion (see the validator cluster in `04-market-saturation-verdict.md`), and if IdeaExists answers with generated advice it is a worse-resourced clone of them. The moment the product gives an *opinion* rather than *evidence*, the one defensible asset — provenance — is spent.

**Verdict: KEEP — but only fused with Wedge 4.** Evidence-grounded decision support is the strongest user-value wedge and the weakest defensible one; it must be delivered as a comparison over verified entries with citations, never as free-form advice.

---

### Wedge 4 — Verifiable prior-art evidence with provenance, not AI opinion

**One sentence.** Every claim in the product traces to a source: a URL, a retrieval date, a snapshot, a verification event — and LLM-drafted text is labelled as such.

**Why it might matter.** Distrust of hallucinated research is now an explicit buying criterion: vendors in competitive-intelligence have built their pitch on "reliable intel without the hallucination risk" versus general assistants (https://klue.com/blog/how-to-do-competitive-analysis-with-chatgpt — accessed 2026-09-14), and analysts writing for practitioners document the limits of chat-based market research explicitly (https://www.intotheminds.com/blog/en/conducting-market-research-with-chatgpt/ — accessed 2026-09-14). Adjacent, a whole paid category exists around *evidence-grade* prior-art search in patents — a market where citations and auditability are the product (https://cypris.ai/insights/best-prior-art-search-automation-tools-in-2025 — accessed 2026-09-14; also https://www.questel.com/resourcehub/how-prior-art-search-tools-can-help-you-increase-productivity/ — accessed 2026-09-14). That adjacency is evidence that "prior art with provenance" can be a *paid, professional* job — `[OPEN QUESTION]` whether that transferable willingness-to-pay extends down-market to a founder checking an idea.

**What we would have to be good at.** Evidence capture discipline (source URL + retrieval date + evidence type + snapshot); labelling provenance everywhere; making auditability a first-class UI surface rather than a footnote; and saying "unknown" instead of guessing.

**Already supported in code.** Reverse-chronological verify log; per-entry strike counter; the 404/410-only strike rule (a narrow, defensible definition of "dead"); Wayback first-snapshot date and RDAP registration date as founded-date fallbacks (real evidence anchors); per-entry dossier; the human-verified stamp; admin health-check tooling.

**Would have to be built.** An **evidence table** (claim → source → retrieved date → evidence type) — listed as missing and the single highest-leverage build; **provenance labels** on LLM-drafted text — also missing, and today deepseek-v4-flash drafts profile text with no visible label, which is an active trust liability; a **permanent** verification/status history (90-day log retention cannot back a permanent claim); snapshot/link-rot mitigation beyond a liveness check (link rot is the norm: Pew's 38%/8% figures above); export so evidence travels (MD/JSON/CSV).

**Strongest counter-argument.** Evidence is easy to *imitate* (a competitor can print citations) and hard to *monetise* in a free directory; and the patent analogy may not transfer — patent stakes are legal and large, a founder's 20-minute idea check is neither, so users may not pay for rigour they cannot feel.

**Verdict: KEEP.** This is the most codebase-aligned and most defensible wedge, and it is the only one that *strengthens* as the archive grows. It is the "why trust us" engine that makes Wedge 3 safe to ship.

---

### Wedge 5 — Narrow deep vertical (one category, exhaustively) vs broad shallow

**One sentence.** Pick one category — most plausibly dev tools / design software, where the 201-site curated library already gives a head start — and be exhaustive there rather than thin everywhere.

**Why it might matter.** Depth and curation are recognised sources of defensibility in data businesses, ranked among the real moats once raw data collection is commoditised (https://www.v7labs.com/blog/data-moats-a-guide and https://travismay.medium.com/the-six-moats-of-data-businesses-01a69638c8f8 — both accessed 2026-09-14). The documented gap in the incumbent — missing coverage of smaller, non-US and mid-market companies (G2 pros/cons, above, accessed 2026-09-14) — is a breadth-and-depth gap a vertical player can exploit.

**What we would have to be good at.** Choosing the right vertical; domain fluency in it; sustaining exhaustive ingestion; resisting drift back to breadth.

**Already supported in code.** Category facets; a 201-site curated design library already seeded; GitHub search ingestion by query; pasted-URL-list ingestion; single-URL add with LLM drafting; admin seed panel.

**Would have to be built.** A vertical taxonomy with per-category fields; exhaustive crawl/curation for one category; category-specific comparability (pricing model, licence, platform); category experts or a curator; and a decision about what to do with the famous-startup breadth that currently *is* the archive.

**Strongest counter-argument.** Narrowing caps the addressable audience and trades the archive's one present asset — recognisable breadth — for depth that a competitor can re-crawl. Depth is a treadmill, not a moat, unless it is paired with human verification the competitor will not do.

**Verdict: CONDITIONAL.** Justified only as "start with dev/design tools because the seed already exists", *not* as a full pivot to one vertical; the breadth asset should be retained.

---

### Wedge 6 — Open data / export / API — "no paywall, no account"

**One sentence.** Give the data away: exportable, no login, no paywall, with a public dataset and (eventually) an API.

**Why it might matter.** Demand for free, open company-data alternatives to expensive incumbents is persistent and organised — practitioners openly discuss building open-source Crunchbase/PitchBook alternatives (https://www.reddit.com/r/venturecapital/comments/1ej65z2/building_an_opensource_alternative_to/ — accessed 2026-09-14), and listicles explicitly rank "free VC databases … that don't cost 30k", naming Crunchbase's free tier and free competitors (https://valueaddvc.com/blog/the-best-free-vc-databases-in-2026-crunchbase-alternatives-that-dont-cost-30k — accessed 2026-09-14; treat vendor-comparison listicles as directional). Openness is also a distribution channel: an open dataset gets cited, mirrored and embedded.

**What we would have to be good at.** Monetising without a paywall (the unsolved part); sustaining data operations with no revenue; licensing and scraping-compliance discipline; and accepting that openness is a one-way commitment.

**Already supported in code.** The data is already local and portable (SQLite); the shareable `?q=…` query state is the seed of a public link-able surface. But export itself — MD/JSON/CSV — is explicitly **missing**, and there is no API.

**Would have to be built.** Export (small); a public/static dataset publication (medium, with licensing and attribution questions); an API (large, and it reintroduces the server, the accounts and the tracking the product's identity is built against); a licence and an update cadence.

**Strongest counter-argument.** "Free and open" is a growth strategy, not a business; open data is trivially cloneable, and once a public corpus is ingested by general AI models the asset is regenerated by anyone — the classic failure mode of data moats when the data is public (https://www.v7labs.com/blog/data-moats-a-guide — accessed 2026-09-14). Free + no account also removes the retention loop and the ability to measure use.

**Verdict: CONDITIONAL.** Ship export now (leverage is high, cost is small, it is a trust and portability feature). **Disqualify "free public API as the business"** — it contradicts the privacy identity and hands the corpus away.

---

### Wedge 7 — The archive as a long-lived public record with history

**One sentence.** The product is the *timeline*: dead entries kept, status changes dated, and a record that outlives the products it describes.

**Why it might matter.** The web is disappearing measurably — Pew: 38% of 2013 pages gone by 2023, 8% of 2023 pages gone within a year (https://www.pewresearch.org/data-labs/2024/05/17/when-online-content-disappears/ — accessed 2026-09-14); the Internet Archive itself reports on this decay (https://blog.archive.org/tag/link-rot/ — accessed 2026-09-14). Meanwhile an anecdotal but widely repeated claim is that most launches quietly die — a Reddit analysis of 500 Product Hunt SaaS launches found 487 dead (`[ANECDOTE]`, https://www.reddit.com/r/SaaS/comments/1mnc3nu/ — accessed 2026-09-14). A directory that *records* that attrition is offering something a live-only listing cannot.

**What we would have to be good at.** Temporal discipline: dating everything, never rewriting the past, snapshotting sources, and resisting the pressure to delete.

**Already supported in code.** Never-delete-on-death; strike counter; status field; sort by founded year; weekly liveness pass; verify log; Wayback and RDAP date anchors; admin health-check panel.

**Would have to be built.** Permanent event history (the 90-day log retention is a direct contradiction of a permanent-record claim); a public per-entry changelog/timeline UI; snapshots; and a dating policy for entries whose founding date came from a Wayback or RDAP fallback (currently undated as "approximate", which a permanent record must state).

**Strongest counter-argument.** Nobody pays for a graveyard; the use is occasional; and with **0 dead entries today** the record is empty — the mechanism is real but unpopulated, so the wedge currently promises a capability the data cannot yet demonstrate.

**Verdict: CONDITIONAL.** Keep the never-delete discipline and surface history as a credibility feature; do not lead with it until the archive contains meaningful status history.

---

### Wedge 8 — "Check before you build" as an embedded step, not a destination *(added by this research)*

**One sentence.** Ship the check where the work already happens — a CLI/agent/editor step that answers "has this been built, and what's the gap?" in seconds — rather than trying to win a destination-website habit.

**Why it might matter.** This directly addresses the counter-argument that sinks Wedges 2 and 5: discovery for new products via destinations is widely reported as collapsing (a prominent "Product Hunt is dead" discussion, https://news.ycombinator.com/item?id=45362569 — accessed 2026-09-14; and an analysis of 76,822 launches concluding the launch-traffic model has peaked, https://blog.getdot.ai/dot-digest-has-product-hunt-peaked-ai-data-analysis-of-76-822-launches-fcee6542fd00 — accessed 2026-09-14). In parallel, agent-based tooling is the fastest-growing software surface (agent market projected from USD 7.84bn in 2025 to USD 52.62bn by 2030, https://www.marketsandmarkets.com/Market-Reports/ai-agents-market-15761548.html — accessed 2026-09-14; vendor projection, directional). Embedding turns distribution from "get people to a website" into "be callable from where they already are".

**What we would have to be good at.** A fast, boring, reliable check that returns in seconds; absolute honesty about coverage limits ("this checks a 1,282-entry archive, not the internet"); and integration surface design.

**Already supported in code.** The local FastAPI backend is *already* the right shape for an embedded/agent-callable service; the search index runs client-side over the whole archive, so a check is cheap; the archive ships with the app.

**Would have to be built.** A documented local endpoint or CLI with a stable contract; a structured response (closest matches + evidence links + explicit coverage caveat); integration packaging for at least one agent/editor environment; `/products/<slug>` routes so results can be linked back.

**Strongest counter-argument.** Embedding a 1,282-entry corpus inside a workflow invites unfavourable comparison with a general assistant that can search the entire web; a tool that says "not in my 1,282 rows" too often trains users to ignore it.

**Verdict: KEEP.** It is the only wedge that answers the distribution problem the other wedges create, and it converts an existing architectural choice (local backend) into a channel.

---

## Wedge ranking table

Defensibility 1–5 (5 = hardest to copy), Build cost S/M/L, Codebase leverage = how much of the wedge is already supported.

| Wedge | Defensibility | Build cost | Codebase leverage | Best-fit founder segment | Verdict |
|---|---|---|---|---|---|
| 4. Verifiable prior-art evidence with provenance | 4 | M | High | Founders + analysts/investors who must defend a decision | **KEEP** |
| 3. "What would be different?" decision support | 3 | M–L | Medium | Indie hackers, product strategists | **KEEP (fused with 4)** |
| 8. Embedded "check before you build" | 3 | M | Medium | Dev-tool/agent-using builders | **KEEP** |
| 1. Human-verified trust as the product | 3 | M | High | Risk-averse founders, analysts | CONDITIONAL (substrate, not offer) |
| 7. Long-lived public record with history | 3 | M | High | Researchers, curious investors | CONDITIONAL (empty corpus today) |
| 5. Narrow deep vertical | 3 | L | Medium | Design/dev-tools builders | CONDITIONAL (start narrow, don't pivot) |
| 2. Local-first / privacy-first as headline | 3 | L | Medium | Privacy-conscious developers | CONDITIONAL (posture, not channel) |
| 6. Open data / free API as the business | 2 | S (export) → L (API) | High (export) | Developers, data users | CONDITIONAL (ship export; drop free-API-as-business) |

---

## Where the code genuinely gives an unfair advantage — and where it does not

**Genuine advantage.**
- **A verified corpus with an enforcement mechanism.** 1,278/1,282 human-verified, plus a liveness pass, a narrow 404/410-only strike definition, a 3-strike rule and a never-delete policy. Very few directories bind themselves to an *auditable* commitment like this, and it is the raw material for Wedge 4.
- **Real date anchors.** Wayback first-snapshot plus RDAP registration as founded-date fallbacks is a defensible, source-linked dating method — unusual and directly reusable as evidence.
- **A local backend that is already embeddable.** The FastAPI + client-side index shape makes Wedge 8 cheap and makes the privacy posture (Wedge 6 condition) honest rather than marketing.
- **Shareable query state.** `?q=…` URL sync is the seed of a linkable, indexable surface — the missing growth primitive for a directory, and it already exists.
- **Operational tooling.** Admin seed / verification / health-check panels mean the hard part (the verification loop) has a UI, not just a policy.

**No advantage — be honest about this.**
- **Corpus size.** 1,282 entries is three orders of magnitude below the incumbents; there is effectively **no SEO surface** and no statistical depth. Any "closest alternatives" claim is bounded by this.
- **Similarity is lexical.** "More like this" scores shared category/language/tagline words — a shallow proxy, not semantic comparison. Wedge 3 cannot be sold as "closest alternatives" until this improves.
- **Zero comparable fields.** Pricing and audience are absent; entity typing is absent, so repos, products and companies can be mixed. Comparison (Wedge 3) is unbuildable as promised without these.
- **No provenance on generated text.** LLM-drafted profiles are currently unlabelled — an active liability for a provenance-positioned product.
- **History that expires.** A 90-day verify log cannot support a permanent-record claim (Wedges 1 and 7) without change.
- **LLM quality.** deepseek-v4-flash drafting is adequate for scaffolding but is not the differentiator; treating it as one would recreate exactly the commodity the product must avoid.

---

## Conclusion — the wedges worth running, in order

1. **Evidence-grounded prior-art, fused with decision support (Wedge 4 + Wedge 3).** Ship the evidence table and provenance labels first; then the comparison flow and pricing/audience/entity-typing fields; then `/products/<slug>` so a comparison is linkable. This is the only wedge that both exploits the codebase's one real asset and is not eroded by every LLM getting better.
2. **Embedded "check before you build" (Wedge 8).** Answer the distribution problem the other wedges create. The local API is the channel; the honesty about coverage limits is the product.
3. **Verified-trust and history discipline as the substrate (Wedges 1 + 7).** Make the audit trail permanent, keep the log, surface the strike counter and history. It is what makes #1 credible, and it should never be the pitch line.

**Explicitly not the plan:** local-install-first delivery (Wedge 2 as channel), a free public API (Wedge 6 as business), a full vertical pivot (Wedge 5 as identity), or "trust" as the headline (Wedge 1 as offer).

**Open questions carried forward.** `[OPEN QUESTION]` Will founders pay for rigour they cannot feel? `[ASSUMPTION]` that search privacy motivates this segment is unquantified. `[OPEN QUESTION]` whether the patent prior-art market's willingness to pay transfers down-market — this is the single assumption on which Wedge 4's commercial case rests, and it is testable (see the falsification plan in `04-market-saturation-verdict.md`).
