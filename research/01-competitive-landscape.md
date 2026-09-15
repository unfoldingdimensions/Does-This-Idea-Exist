# 01 — Competitive Landscape: "Does this exist?" / Prior-art & product-discovery tooling

**Access date for all sources: 2026-09-14.**
**Product under study:** *IdeaExists* (working title) — a local-first, verification-first directory of startups, reframed from a binary "does this startup exist?" badge into: *"Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build."* Primary audience: founders, indie hackers, product strategists, investors researching a real product idea.

---

## Scope & method

This is **public desk research** conducted with a web-search tool. **In-scope:** products and services whose core job is to help a person answer one of three questions — *"Does something like this already exist?"*, *"What are the closest alternatives?"*, or *"Is this idea already validated / already dead?"* — plus the adjacent directories, databases, launch platforms, review sites, AI-tool catalogs, CI/trend platforms and community lists that a founder would realistically land on while doing that job. **Out of scope:** general search engines as a *product* category (covered only as the status-quo substitute), design-inspiration galleries, code hosting, notebook/blog content, and any paid/gated reports I could not read. **Method limits:** everything here is from public web pages and public press releases; **no paid or gated data was purchased, no accounts or signups were created, no paywalls were bypassed.** Prices below are list prices observed on third-party comparison pages or vendor pages and are **not** verified quotes; they move frequently. Anything I could not confirm from a live page is tagged `[ASSUMPTION]` or `[OPEN QUESTION]`. Because I did not log into any product, feature claims describe *published positioning*, not hands-on use.

---

## Headline count

**59 named players, across 8 segments.**

| # | Segment | Named players |
|---|---------|---------------|
| A | Idea-existence / idea-validation checkers | 12 |
| B | Software-alternatives & product directories | 9 |
| C | Startup / company databases | 9 |
| D | Founder launch platforms & directories | 8 |
| E | AI-tool directories | 5 |
| F | Competitive-intelligence / market-research SaaS | 8 |
| G | Open-source / community curation lists | 5 |
| H | Status-quo substitute (Google / ChatGPT / Perplexity) | 3 |
| | **Total** | **59** |

Every player named below is repeated once, with a URL, in **02-competitor-profiles.md** (name, home URL, build, target user, pricing, positioning, evidence) plus a 59-row landscape matrix. The count above equals the number of players named in this file.

---

## Segment map

### Segment A — Idea-existence / idea-validation checkers (12 players)
**What it is:** Tools that take a one-line idea and return a report or score aimed at telling you whether the idea is worth pursuing — increasingly "AI validator" products that scan the web, reviews and complaints for prior art and demand signals. **How crowded:** very — a fast-growing long tail of near-identical AI wrappers, plus a small set of SEO-dominant incumbents. **Maturity:** young (most are 2023–2026), low barriers, high churn.
**Named players:**
- IdeaProof — https://ideaproof.io/
- DimeADozen — https://www.dimeadozen.ai/
- ValidatorAI — https://validatorai.com/
- Preuve AI — https://preuve.ai/
- ScribeAI — https://usescribeai.com/
- StartupConcept.ai — https://startupconcept.ai/
- FounderSpace — https://www.founderspace.work/
- BigIdeasDB — https://bigideasdb.com/
- IdeaBrowser — https://www.ideabrowser.com/
- Startups.RIP — https://startups.rip/
- Loot Drop — https://www.loot-drop.io/
- Failory — https://www.failory.com/

### Segment B — Software-alternatives & product directories (9 players)
**What it is:** Crowd-sourced or editorial directories that map "product X → its alternatives", plus B2B software review/comparison platforms. This is the closest thing to a *functional* competitor for the "what already exists?" job. **How crowded:** very crowded for generic software; consolidating at the enterprise end. **Maturity:** old and mature — AlternativeTo launched **2009**; G2/Capterra now consolidating (see maturity read below).
**Named players:**
- AlternativeTo — https://alternativeto.net/
- OpenSourceAlternative.to — https://www.opensourcealternative.to/
- Alternative.me — https://alternative.me/
- StackShare — https://stackshare.io/
- G2 — https://www.g2.com/
- Capterra — https://www.capterra.com/
- GetApp — https://www.getapp.com/ `[ASSUMPTION: canonical home domain; evidenced indirectly via TrustRadius comparison page and the G2 acquisition release]`
- Software Advice — https://www.softwareadvice.com/
- TrustRadius — https://www.trustradius.com/

### Segment C — Startup / company databases (9 players)
**What it is:** Structured databases of companies, funding, headcount and market maps — the "is anyone already building this, and who funded them?" layer. Almost all are commercial, sales-led, and expensive. **How crowded:** moderately — a handful of incumbents with high data-acquisition costs. **Maturity:** mature, capital-intensive, consolidation-prone; **Dealroom raised $7M in Jan 2026** (Tracxn profile), showing the segment is still actively funded.
**Named players:**
- Crunchbase — https://www.crunchbase.com/
- PitchBook — https://pitchbook.com/
- CB Insights — https://www.cbinsights.com/
- Tracxn — https://tracxn.com/
- Dealroom — https://dealroom.co/ `[ASSUMPTION: canonical home domain; evidenced indirectly via Tracxn company profile]`
- Wellfound — https://wellfound.com/
- F6S — https://www.f6s.com/
- Owler — https://www.owler.com/ `[ASSUMPTION: canonical home domain; evidenced indirectly via third-party comparison pages]`
- ZoomInfo — https://www.zoominfo.com/ `[ASSUMPTION: canonical home domain; evidenced indirectly via third-party comparison pages]`

### Segment D — Founder launch platforms & directories (8 players)
**What it is:** Places founders announce products and browse what others just shipped — the "who launched something like this last week?" layer. Product Hunt is the anchor; a long tail of indie launch clones sits under it. **How crowded:** heavily crowded and highly substitutable. **Maturity:** Product Hunt is mature (founded Nov 2013, acquired by AngelList for a reported ~$20M); the indie clones are young and mostly SEO/backlink plays.
**Named players:**
- Product Hunt — https://www.producthunt.com/
- BetaList — https://betalist.com/ `[ASSUMPTION: canonical home domain; evidenced indirectly via third-party directory roundups]`
- TinyLaunch — https://www.tinylaunch.com/
- MicroLaunch — https://microlaunch.net/
- Peerlist — https://peerlist.io/
- DevHunt — https://devhunt.org
- Hacker News — https://news.ycombinator.com/
- Indie Hackers — https://www.indiehackers.com/

### Segment E — AI-tool directories (5 players)
**What it is:** High-volume catalogs of AI products, monetised by paid listings and backlinks. Functionally the same "browse what exists" job, but scoped to AI and generally *unverified* and *unmaintained*. **How crowded:** extremely — dozens of near-duplicate directories; listing counts run into the tens of thousands, which itself proves how low the curation bar is. **Maturity:** young (2022–present), consolidating; futurepedia claims 4,000+ tools and 500,000+ accounts, Toolify ~22,000 tools.
**Named players:**
- There's An AI For That — https://theresanaiforthat.com/
- Futurepedia — https://www.futurepedia.io/
- Toolify — https://www.toolify.ai/
- FutureTools — https://futuretools.io/
- AI Tools Directory — https://aitoolsdirectory.com/

### Segment F — Competitive-intelligence / market-research SaaS (8 players)
**What it is:** Paid platforms that monitor competitors, markets and trends for teams — same *job to be done* as "understand the closest alternatives", but sold as enterprise software at five-figure annual contracts. **How crowded:** moderately crowded at the top, with clear leaders. **Maturity:** mature; Klue/Crayon price around $15–16k/yr, Semrush/Similarweb/Ahrefs dominate traffic intelligence.
**Named players:**
- Crayon — https://www.crayon.co/
- Klue — https://klue.com/
- Kompyte — https://www.kompyte.com/
- Semrush — https://www.semrush.com/
- Similarweb — https://www.similarweb.com/ `[ASSUMPTION: canonical home domain; evidenced via third-party comparison pages]`
- Ahrefs — https://ahrefs.com/ `[ASSUMPTION: canonical home domain; evidenced via third-party comparison pages]`
- Exploding Topics — https://explodingtopics.com/
- Glimpse — https://meetglimpse.com/

### Segment G — Open-source / community curation lists (5 players)
**What it is:** Free, community-maintained lists and directories (awesome-lists, self-hosted app directories, "made in X" lists). Trusted and link-rich, but manually curated, unevenly updated and not searchable by *idea*. **How crowded:** thousands of lists exist; the *category* is crowded, no single winner. **Maturity:** old and stable — the awesome-list convention dates to ~2014; some repos show "Updated on Mar 21, 2024".
**Named players:**
- awesome-selfhosted — https://github.com/awesome-selfhosted/awesome-selfhosted
- selfh.st (Apps) — https://selfh.st/apps/
- Up For Grabs — https://up-for-grabs.net/
- made-in-iran — https://github.com/mohebifar/made-in-iran
- GitHub "awesome-lists" topic — https://github.com/topics/awesome-lists

### Segment H — The status-quo substitute (3 players)
**What it is:** The free behaviour a founder actually performs today: ask Google, ask an LLM, ask people. It is not a product in this category but it is the **real competitor** for the "does this already exist?" moment, and it is where most of the demand currently leaks. Covered here only as a placeholder; the deep dive sits in a separate file.
**Named players:**
- Google Search / Google Trends — https://trends.google.com/
- ChatGPT — https://chatgpt.com/ `[ASSUMPTION: canonical consumer domain; evidenced indirectly via industry coverage of AI-based idea validation, e.g. Inc. 2026]`
- Perplexity — https://www.perplexity.ai/ `[ASSUMPTION: canonical home domain; included because AI-assisted research is repeatedly named as the substitute behaviour]`

---

## Where our product actually sits

**It truly competes in Segment A (idea-existence / validation checkers) and partially in Segment B (software-alternatives directories).** Those are the only two segments where the *job* — "find what already exists, see the closest alternatives, decide what's different" — is the actual product promise rather than a side feature.

**Segment E (AI-tool directories) is adjacent, not core.** Those catalogs answer "what AI tools exist?" but they are unverified, submission-monetised and structurally unable to answer "is this idea distinct?" Their value to us is as a *source of seed data*, not as a competitor.

**Segments C, D and F are periphery / different buyer.** Crunchbase-class databases answer "who is funded?"; launch platforms answer "who shipped recently?"; Crayon/Klue answer "what are our competitors doing?" — all served by paid tools with different buyers (investors, growth teams, sales teams).

**Segment G is closest in *spirit* (free, curated, community-trusted, "lists of what exists") but weakest in *function*** — no liveness checking, no stable per-product pages, no verification. That gap is the wedge.

---

## Market maturity read

- **The "alternatives" segment is old and consolidating.** AlternativeTo launched in **2009** and is still run by two founders in Sweden (Wikipedia / site "made by Ola and Markus in Sweden"). In the enterprise review corner, **G2 (a $1.1B-valuation unicorn after a $157M Series D) agreed to acquire Capterra, Software Advice and GetApp from Gartner** (PR Newswire / company.g2.com / Wikipedia). That is classic maturity: the review-directory layer is rolling up.
- **The "AI idea validator" segment is young and fragmenting.** Most named players (IdeaProof, DimeADozen, Preuve AI, ScribeAI, StartupConcept.ai, FounderSpace) are 2023–2026 vintage, monetised by one-off credits ($9–$179 per report), and compete largely on SEO. Low barriers ⇒ new entrants keep appearing. DimeADozen's own marketing says it went from launch to a reported ~$58K revenue in 5 months and was listed for sale at a ~$160K asking price (spymetrics) — i.e. these are cash-flow micro-apps, not durable moats.
- **The "startup graveyard / rebuild" niche is emerging fast.** Startups.RIP (1,700+/5,700+ dead YC startups with rebuild plans), Loot Drop (1,749 startups, $535.4B burned) and Failory (+400 failed startups) all appeared/recently surfaced, and one of them explicitly reasons: *"Every failed startup represents a validated market with unfulfilled potential."* This is the closest philosophical neighbour to IdeaExists and it is still thinly populated — the strongest signal in this research.
- **New entrants are still appearing in every segment**, but only Segment A and the graveyard niche are *not* capital-gated; the databases (C) and CI tools (F) are effectively closed to a solo builder.

---

## Conclusion

- **59 named players across 8 segments** — the space is crowded *in aggregate* but the crowd is unevenly distributed.
- **The truly contested ground is Segment A (12 players) and Segment B (9 players).** Everything else is adjacent.
- **Nobody in the list combines all three of IdeaExists' claimed traits:** (1) *liveness verification*, (2) *a human stamp that survives automation*, and (3) *entries that are never deleted*. Validators score ideas but don't maintain a verified corpus; directories maintain a corpus but don't verify liveness; graveyards track death but not liveness-at-scale.
- **The "does it exist / is it dead" angle is genuinely thin.** Startups.RIP and Loot Drop own the *death* story but only for YC/curated cohorts; no free, general, verified liveness index surfaced in this research. `[OPEN QUESTION: could not source any general-purpose, free, LLM-agnostic liveness-verified startup index other than the product under study.]`
- **Money is concentrated at the edges, not the middle.** Free crowd-sourced directories (B, G) and enterprise databases/CI (C, F) both have scale; the *free, verified, founder-facing middle* — where IdeaExists sits — is where incumbents are weakest.
- **The biggest real competitor is Segment H** (Google/ChatGPT/Perplexity), which is free, instant and already in every founder's workflow. Any positioning must beat "just ask ChatGPT."
- **Pricing wedge is visible.** Segment A charges $9–$179 one-off; Segment C charges $49–$199+/mo; Segment F charges ~$15–100k/yr. A free/local, verified alternative has clear daylight.
- **Consolidation risk is real for Segment B** (G2 swallowing Capterra/GetApp/Software Advice) but that consolidation *increases* the opening for an independent, non-pay-to-play index.
- **Data-quality is the unclaimed axis.** Every crowded segment competes on *volume* (22,000 AI tools; 4M+ companies); none competes on *verified liveness*. That is the defensible niche.

*See 02-competitor-profiles.md for the per-player profiles, the 59-row matrix, maturity/traction signals, adjacent-but-not-competitor list, and the sourced pricing detail.*
