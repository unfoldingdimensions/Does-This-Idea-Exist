# 05 — Substitutes and the Status Quo
### What founders actually do instead of "does this startup exist?"

**Product under study:** IdeaExists (working title) — a local-first, verification-first startup directory.
**Reframe in progress:** *"Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build."*
**Audience:** founders, indie hackers, product strategists, investors researching a real idea.

---

## Scope

This document maps the **substitutes** for the job "does this idea already exist?" — the tools, habits and people founders reach for *today*, before any dedicated product exists in their workflow. It is not a feature comparison of competitor directories. It is a study of the **status quo**: what is already free, already open in another tab, and already trusted.

Coverage is limited to the ten substitutes named in the brief: (1) Google search, (2) ChatGPT / Claude / chat LLMs, (3) Perplexity / AI answer engines, (4) Product Hunt, (5) Crunchbase and similar databases, (6) AlternativeTo-style software directories, (7) GitHub search, (8) Hacker News / Reddit / indie communities, (9) asking a person / accelerator / mentor, (10) building a quick scraper or spreadsheet.

Out of scope: pricing strategy for IdeaExists, technical architecture, and investor/market-sizing for the category itself.

## Method

- Desk research using the `web_search` tool, plus direct retrieval of **primary sources** where they were technically reachable: the Hacker News Items API (`hn.algolia.com`), `indiehackers.com` post pages, `paulgraham.com`, `support.crunchbase.com`, `github.com` community discussions, and `arstechnica.com`.
- **Reddit limitation (disclosed):** on the access date, Reddit's JSON and HTML endpoints refused programmatic retrieval (HTTP 302 → 404 / "Welcome to Reddit" interstitial). Reddit evidence below is therefore quoted from **search-surfaced thread excerpts** and is explicitly labelled as such. Quotes are reproduced exactly as retrieved and never extended.
- Every external claim and every quotation carries a URL and the access date **2026-09-14**. Nothing is invented; where a number is reported by a secondary source it is labelled as such.
- Items that are inference rather than evidence are tagged `[ASSUMPTION]` or `[OPEN QUESTION]`.

---

## Executive summary

- **The real competitor is not another directory — it is a ten-minute Google search, a ChatGPT prompt, and a shrug.** The dominant, authoritative advice to founders is that checking whether an idea exists is a *quick, low-stakes* step. Paul Graham's canonical essay says: *"Ten minutes of searching the web will usually settle the question… It's exceptionally rare for startups to be killed by competitors — so rare that you can almost discount the possibility."* ([paulgraham.com/startupideas.html](https://www.paulgraham.com/startupideas.html), accessed 2026-09-14). Any new entrant is fighting a norm, not a product.
- **The job is real and recurring, but it is fragmented across 5+ free surfaces.** A founder asking the question in public describes the current workflow exactly: *"Normally, I have to use ChatGPT, Google, Product Hunt, Crunchbase, etc."* ([r/startups](https://www.reddit.com/r/startups/comments/1ohx9g1/where_do_you_reliably_check_if_your_idea_is/), accessed 2026-09-14 — search-surfaced excerpt).
- **AI answer engines are now the default first stop, and they are measurably unreliable for this exact job.** The Tow Center (Columbia Journalism Review) tested eight AI search engines over 1,600 queries and found they failed to retrieve correct information **more than 60% of the time**, with Perplexity wrong in **37%** of tested queries ([cjr.org](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php), accessed 2026-09-14).
- **The strongest substitute is free and already installed; the weakest is paid and stale.** The strongest is the **chat LLM / Google combination** (zero friction, "good enough", already habitual). The weakest for this job is **Crunchbase and funding databases** — free tier is a lookup tool, not a research tool, and paid tiers start around $49–$99/month ([support.crunchbase.com](https://support.crunchbase.com/hc/en-us/articles/360062989313-What-is-the-Difference-between-a-Free-Crunchbase-Account-and-Crunchbase-Paid-Subscriptions), accessed 2026-09-14).
- **No substitute answers "is it alive?" well.** Product Hunt buries launches within hours, Crunchbase skews to funded companies, AlternativeTo lists abandoned apps, and GitHub caps results at 100. **Liveness — the thing IdeaExists claims as its wedge — is the single most under-served sub-job.**
- **The killer counter-argument is economic, not technical:** if building is now an afternoon, research is no longer cheap insurance. An Indie Hackers post from **11 September 2026** makes it directly: *"Validation made sense when building was the expensive part… That ratio has flipped and I don't think our advice has caught up."* ([indiehackers.com](https://www.indiehackers.com/post/we-sell-validate-before-you-build-the-only-thing-i-ve-opened-every-day-this-week-is-the-thing-i-never-validated-a244c2b092), accessed 2026-09-14).
- **The strongest pro-entrant evidence is emotional, and it is repeatable.** Founders consistently describe the moment of discovery as demoralising and identity-threatening — *"my inspiration evaporated"*, *"I just felt invisible"* — which suggests the job is felt strongly, even if it is not yet *paid* for.
- **Net read:** the status quo is beatable on **trust, liveness and verification** (things no free substitute guarantees), but it is only *durably* beatable if the product attaches to a moment a founder already treats as important. Selling "research" against free, good-enough substitutes is uphill; selling "don't waste three weeks building a duplicate" or "don't ship into a dead category" is a sharper wedge. `[ASSUMPTION]`

---

## The jobs-to-be-done

"What a founder is actually trying to learn" decomposes into six distinct jobs. They are often conflated, but a substitute can be good at one and useless at another — which is why the market feels simultaneously served and unserved.

### Job 1 — Name collision check ("is this name already taken?")
- **The job:** Avoid launching under a name someone else owns, or that collides with an existing brand/domain.
- **What a good answer looks like:** A fast, exact/near-match search across product names, domains and existing companies, with a confidence signal (does a live thing own this name?).
- **What today's tools deliver:** Google, domain registrars and app stores do this decently. This is the one sub-job the status quo handles well, which reduces the value of a directory doing it too. `[ASSUMPTION]`

### Job 2 — "Is anyone already building this?" (duplicate check)
- **The job:** Find out whether a direct equivalent to *my specific product* exists, so I don't rebuild it.
- **What a good answer looks like:** A ranked list of near-identical products, distinguishing "same idea" from "same words".
- **What today's tools deliver:** Poorly and inconsistently. Google depends on my keyword guesses; ChatGPT invents or omits; Product Hunt only shows what was launched *here*. The classic failure mode is described by a founder who assumed a pre-existing implementation did what he wanted, then found it didn't — *"my experience has been that things that look the same are off."* ([HN 19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14).

### Job 3 — "Who would I be competing with?" (landscape)
- **The job:** Understand the set of players, their positioning, pricing, and where the gaps are.
- **What a good answer looks like:** A comparison view — features, pricing, target segment — not just a list of links.
- **What today's tools deliver:** Partial. Crunchbase and funding DBs cover *funded* companies; AlternativeTo covers *software* alternatives; nobody covers indie/unfunded products coherently. Comparison is almost always assembled by hand in a spreadsheet.

### Job 4 — "Is the space alive or dead?" (momentum)
- **The job:** Know whether competitors are shipping, growing, or abandoned — i.e. is this category rising or a graveyard.
- **What a good answer looks like:** A liveness signal per product (last activity, dead/404, archived repo, discontinued) and a sense of category trajectory.
- **What today's tools deliver:** Badly, and this is the biggest gap. Product Hunt gives a launch-day snapshot and no liveness; AlternativeTo lists dead apps; GitHub shows archived repos only if you filter manually; Crunchbase tracks funding, not liveness. **No free substitute answers "is it alive?" reliably.**

### Job 5 — "What would I do differently?" (differentiation)
- **The job:** Turn competitor knowledge into a defensible angle.
- **What a good answer looks like:** Explicit contrasts — feature/price/segment gaps, and honest "you'd be a knockoff unless you…" feedback.
- **What today's tools deliver:** Almost nothing structural. It is *advice*, so it comes from people (mentors, communities), not from search. As one HN commenter put it, the value of a "does it exist" tool is precisely *"a way to understand existing approaches and see if our insights can lead to a meaningfully different solution"* ([HN 44898394](https://news.ycombinator.com/item?id=44898394), accessed 2026-09-14).

### Job 6 — "Is this worth my time?" (go / no-go)
- **The job:** Decide whether to start, pivot, or drop the idea.
- **What a good answer looks like:** A judgement, with the reasoning exposed, not just data.
- **What today's tools deliver:** Nothing, by design. And the authoritative advice actively *discourages* over-indexing on it: *"Even if you find someone else working on the same thing, you're probably not too late."* This is the job where a tool most risks being blamed for a bad decision — and the job where founders most want a human. `[ASSUMPTION]`

**Synthesis:** Jobs 1 and 6 are already well-served or deliberately unserved. Jobs 3 and 4 are poorly served by free tools. Jobs 2 and 5 are the emotional core. A dedicated product that wins on **Job 4 (liveness)** and **Job 2 (trusted duplicate detection)** is attacking the parts of the job the status quo genuinely fails.

---

## Substitute-by-substitute analysis

### 1. Google search

- **Good at:** Zero friction, universal habit, unbeatable coverage of anything with a marketing site. It is the default first move — a widely-upvoted Reddit answer literally starts *"First search google with product/idea related keywords. A tip is to include start-up."* ([r/startups 3ubimv](https://www.reddit.com/r/startups/comments/3ubimv/how_do_you_know_if_your_startup_idea_already/), accessed 2026-09-14 — search-surfaced excerpt).
- **Fails for this job:** It is a *keyword* tool, not a *concept* tool. If you don't already guess the right words, you find nothing — and "finding nothing" is read as "no competitor", the most dangerous possible false negative. Results are increasingly AI-summarised and SEO-contested, so the ranking reflects marketing spend and content volume, not existence.
- **Cost & friction:** Free. One keystroke. That is precisely why it is hard to displace.
- **Source:** Paul Graham, *How to Get Startup Ideas* — *"Ten minutes of searching the web will usually settle the question."* ([paulgraham.com/startupideas.html](https://www.paulgraham.com/startupideas.html), accessed 2026-09-14).

### 2. ChatGPT / Claude / other chat LLMs

- **Good at:** Explaining a space, generating a list of "typical competitors", drafting a positioning statement. Extremely low friction; already part of many founders' daily loop.
- **Fails for this job:** Hallucination and staleness. A practitioner write-up on using ChatGPT to validate business ideas lists the failure plainly: *"Hallucinations: Sometimes it invents fake competitors or data."* ([ai.plainenglish.io](https://ai.plainenglish.io/the-30-minute-startup-test-how-i-use-chatgpt-to-validate-or-kill-any-business-idea-2cfa2b744ceb), accessed 2026-09-14). The tool that is most convenient is the tool least verifiable — it will confidently name a competitor that does not exist, or miss one that does.
- **Cost & friction:** Free tier; ~$20/month tiers for heavier models. Near-zero friction.
- **Source:** Same article, plus the general hallucination literature (e.g. *AI Search Has a Citation Problem*, [cjr.org](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php), accessed 2026-09-14).

### 3. Perplexity / AI answer engines

- **Good at:** Web-grounded answers with citations — closer to "search + synthesis" than a raw chat model. Feels like research.
- **Fails for this job:** The citations do not guarantee correctness. The Tow Center's study of eight AI search engines found they **failed to retrieve correct information in more than 60% of 1,600 test queries**, with Perplexity wrong in **37%** of tested queries ([cjr.org](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php), accessed 2026-09-14). For a question whose whole point is *"does this thing exist?"*, a 1-in-3 error rate on the answer engine is a structural problem. It also inherits Google's keyword dependence and has no liveness data at all.
- **Cost & friction:** Free tier; Pro around ~$20/month. Low friction.
- **Source:** [cjr.org — AI Search Has a Citation Problem](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php) and [niemanlab.org](https://www.niemanlab.org/2025/03/ai-search-engines-fail-to-produce-accurate-citations-in-over-60-of-tests-according-to-new-tow-center-study/), accessed 2026-09-14.

### 4. Product Hunt

- **Good at:** A dated archive of "new products launched" with an audience that self-selects for early adopters. It is *the* place founders look to see what shipped recently.
- **Fails for this job:** It is a launch-marketing channel, not a research index. Coverage is uneven (only products that chose to launch), it is heavily gamed, and it is a snapshot with no liveness. The community's own verdict is brutal: *"In theory it's a place for you to do a quick check of 'is this a good idea or thing to work on'. In practice it's a bunch of serial founders upvoting each others ideas."* ([HN 45362569](https://news.ycombinator.com/item?id=45362569), accessed 2026-09-14).
- **Cost & friction:** Free to browse; paid "launch" spend is common (one founder reports ~$15K for ~100 users — [LinkedIn post](https://www.linkedin.com/posts/thomas-mazimann_is-product-hunt-dead-we-just-launched-our-activity-7424214398602498048-IWK3), accessed 2026-09-14, vendor-reported).
- **Source:** HN 45362569 and HN 42712666, both accessed 2026-09-14.

### 5. Crunchbase and similar databases

- **Good at:** Funded-company intelligence — funding rounds, investors, headcount, firmographics. Excellent if your target is "who is funded in this space".
- **Fails for this job:** Wrong denominator. It skews to companies that raised money and reported it; indie/bootstrapped products (exactly the ones a solo founder is most likely to duplicate) are largely absent. The **free tier is a lookup tool, not a research tool** — Crunchbase's own documentation describes Free as for individuals who *"want to quickly learn about a company"*, with Pro/Business for research "at scale" ([support.crunchbase.com](https://support.crunchbase.com/hc/en-us/articles/360062989313-What-is-the-Difference-between-a-Free-Crunchbase-Account-and-Crunchbase-Paid-Subscriptions), accessed 2026-09-14). Secondary reporting puts the free account at roughly ~11 profile views/month with no export, and notes the free API tier was removed in 2026 ([pipeline.zoominfo.com](https://pipeline.zoominfo.com/sales/crunchbase-pricing), [dataforb2b.ai](https://dataforb2b.ai/blog/crunchbase-api-review), accessed 2026-09-14 — secondary sources, verify before citing as fact).
- **Cost & friction:** Free tier (lookup-only); Pro commonly quoted at ~$49–$99/month, Business higher; API access paid. High friction for a pre-idea founder.
- **Source:** [support.crunchbase.com](https://support.crunchbase.com/hc/en-us/articles/360062989313-What-is-the-Difference-between-a-Free-Crunchbase-Account-and-Crunchbase-Paid-Subscriptions), accessed 2026-09-14.

### 6. AlternativeTo-style software directories

- **Good at:** Crowdsourced "alternatives to X" lists; useful for finding *software* neighbours and free/open-source substitutes.
- **Fails for this job:** It is oriented around *replacing an existing tool*, not *checking whether an idea exists*. Entries go stale, dead products persist, and there is no notion of "alive". Quality is community-dependent, and user reviews are mixed to hostile — a Trustpilot reviewer writes: *"SCAM DIRECTORY - careful - many of these 'apps' listed on this website steal your credit card."* ([trustpilot.com/review/www.alternativeto.net](https://www.trustpilot.com/review/www.alternativeto.net), accessed 2026-09-14 — review text surfaced in search; Trustpilot blocked direct retrieval).
- **Cost & friction:** Free; crowdsourced edits.
- **Source:** [alternativeto.net](https://alternativeto.net/) and Trustpilot, accessed 2026-09-14.

### 7. GitHub search

- **Good at:** Finding *code* — if the competitor is open source, GitHub is the most honest signal there is (stars, commits, archived flags, last push).
- **Fails for this job:** It finds repositories, not products. Most commercial competitors are closed-source and invisible here. Repository search is capped and awkward: a top-voted community complaint is that *"The 5 page limit with no indication of total counts makes it extremely difficult to use Code Search in its current form."* ([github.com/orgs/community/discussions/9868](https://github.com/orgs/community/discussions/9868), accessed 2026-09-14). It is also a proxy for "developer built it", which excludes most no-code/indie products.
- **Cost & friction:** Free.
- **Source:** GitHub community discussion #9868, accessed 2026-09-14.

### 8. Hacker News / Reddit / indie communities

- **Good at:** Genuine human signal — people describe *their own* competitor discoveries in the threads, and posts surface products that never appear in databases ("Show HN", "I built X"). It is where liveness is felt rather than measured.
- **Fails for this job:** No index, no structure, no liveness. Search is weak; recency dominates; a thread from 2019 and a thread from today look identical. It answers the question only if you already know what to search for, and only qualitatively.
- **Cost & friction:** Free; requires an account to post, not to read.
- **Source:** HN 19774997, HN 42712666, HN 44898394, accessed 2026-09-14.

### 9. Asking a person / accelerator / mentor

- **Good at:** Context, judgement and pattern-matching — the only substitute that can answer Job 5 (differentiation) and Job 6 (go/no-go). Mentor networks explicitly market "validate your idea before you build" conversations ([growthmentor.com](https://www.growthmentor.com/mentors-for/idea-validation), accessed 2026-09-14).
- **Fails for this job:** Not searchable, not scalable, biased toward the mentor's own experience, and unavailable to most first-time founders. It also doesn't *verify existence* — it gives opinions about it.
- **Cost & friction:** Highly variable. Free (informal), paid 1:1 mentoring, or equity/fee through accelerators. High friction; scarce.
- **Source:** [growthmentor.com — Idea Validation Mentors](https://www.growthmentor.com/mentors-for/idea-validation), accessed 2026-09-14; the broader point that the authoritative advice is *"ask users"* rather than *"search databases"* comes from Paul Graham ([paulgraham.com/startupideas.html](https://www.paulgraham.com/startupideas.html), accessed 2026-09-14).

### 10. Building a quick scraper or spreadsheet yourself

- **Good at:** Tailored to the exact question, re-runnable, ownable. The "competitor matrix in Google Sheets" is a standard, taught artefact — see, e.g., Antler's guidance to *"draw up a competitor matrix… a simple Excel or Google Sheets table"* ([antler.co](https://www.antler.co/blog/startup-competitor-analysis), accessed 2026-09-14).
- **Fails for this job:** Time-expensive, quickly stale, and biased by whatever sources the founder already knew. It also produces *data* without *liveness* or *verification* — the same spreadsheet problem every other substitute has, just self-inflicted. Practitioners report "hours doing this manually" before automating it ([LinkedIn post](https://www.linkedin.com/posts/connorgillivan_7-claude-prompts-that-replaced-my-competitor-activity-7469704135869681664-cw7O), accessed 2026-09-14).
- **Cost & friction:** Free in money; high in time. Only worth it for high-conviction founders.
- **Source:** [antler.co/blog/startup-competitor-analysis](https://www.antler.co/blog/startup-competitor-analysis), accessed 2026-09-14.

---

## Why the status quo is beatable — and why it is not

### The case *for* a new entrant

1. **Fragmentation is real and admitted.** The job is stitched together from five free tools, and founders say so out loud. Nobody defends the current workflow; they merely tolerate it.
2. **No substitute verifies and no substitute tracks liveness.** IdeaExists' claimed differentiators — a human "verified" stamp that automation can never write, a weekly liveness check, 3× 404/410 → "dead but never deleted" — map onto the *two weakest* sub-jobs (Jobs 2 and 4). This is the cleanest white space in the analysis.
3. **AI answer engines are not trustworthy enough to close the gap.** With a >60% failure rate on a study of 1,600 queries ([cjr.org](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php), accessed 2026-09-14), "just ask Perplexity" is a real but fragile substitute — and fragility is opportunity.
4. **The local-first, no-account, nothing-leaves-the-machine posture is a genuine differentiator.** It answers a growing distrust of tracking-heavy SaaS and does not exist among the free substitutes. `[ASSUMPTION: that this audience values it enough to switch]`
5. **The emotional payload is high.** Founders describe duplicate discovery in visceral terms (see below). High emotion is a wedge for adoption *if* the product can be present at the moment of discovery.

### The strongest case *against* a new entrant

1. **Authoritative advice says the job is trivial.** Paul Graham's essay — *"Ten minutes of searching the web will usually settle the question"* — is the founding text of the audience. A product that implies the job needs a dedicated tool is arguing with the scripture ([paulgraham.com/startupideas.html](https://www.paulgraham.com/startupideas.html), accessed 2026-09-14).
2. **The economics flipped.** Cheap builds destroy the rationale for expensive research. The Indie Hackers post of 11 Sept 2026 is the cleanest articulation: *"If the build is an afternoon, then the research costs more than the thing it's protecting."* ([indiehackers.com](https://www.indiehackers.com/post/we-sell-validate-before-you-build-the-only-thing-i-ve-opened-every-day-this-week-is-the-thing-i-never-validated-a244c2b092), accessed 2026-09-14). If this is true, willingness to pay is structurally low.
3. **Free + "good enough" is a formidable bundle.** Google + ChatGPT covers 80% of the felt need at zero cost and zero onboarding. Competing on accuracy alone loses to competing on habit.
4. **`Substitute incumbent network effects`** — Product Hunt, Google and Crunchbase all benefit from scale and inertia. Replacing behaviour is harder than replacing features.
5. **The job is infrequent.** A founder asks this question a handful of times, maybe once a quarter. Infrequent jobs produce poor retention and thin willingness to pay. `[ASSUMPTION]`
6. **The advice that actually helps is "ask users", not "search databases".** A tool that answers "does it exist" may be answering a question the ecosystem deliberately tells founders *not* to over-weight.

**Verdict:** The status quo is beatable *on accuracy, liveness and trust* — but not *on convenience*. The product must win where the substitute is provably wrong (hallucinated competitors, false negatives, dead listings) and attach to a moment of consequence, not to idle curiosity.

---

## Behavioural evidence

Real user quotes describing this job or complaining about the substitutes. **Every quote carries a URL and access date 2026-09-14.** Reddit quotes are marked as search-surfaced excerpts because Reddit blocked direct programmatic access on that date.

**1. The founder who found out too late (building a tool for exactly this job):**
> *"not knowing if my 'brilliant' idea already existed… until it was too late."*
— HN user `e33or-assasin`, Show HN: *Prexist – Find if your startup idea already exists out there!*, [news.ycombinator.com/item?id=44898394](https://news.ycombinator.com/item?id=44898394), accessed 2026-09-14.

**2. The precise reframe (this quote is the case for the product's new positioning):**
> *"Most initial ideas are going to exist somewhere around the world but they may not focus on the angle that we are interested in. So, I think this is more useful as a way to understand existing approaches and see if our insights can lead to a meaningfully different solution."*
— HN user `anyg`, same thread, [news.ycombinator.com/item?id=44898394](https://news.ycombinator.com/item?id=44898394), accessed 2026-09-14.

**3. Inspiring at the idea, dead on discovery:**
> *"Big market, check. Validated demand, check. Product or service exists, uh-oh. … Turns out someone beat me to it and my inspiration evaporated."*
— HN user `strip099`, Ask HN: *Are you put off building something because it already exists?*, [news.ycombinator.com/item?id=19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14.

**4. The emotional cost, and the abandonment it causes:**
> *"there's already another website that does exactly the same thing. I feel like people will just think I copied there idea… It's always been an issue for me, and because of it, I've never been able to finish anything."*
— HN user `woutr_be`, same thread, [news.ycombinator.com/item?id=19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14.

**5. The counter-frame the incumbent advice rests on:**
> *"Just because something exists, doesn't mean it can't be done better, faster, smarter, cheaper. In fact it's usually a good sign that someone else built it first because it may indicate a valid market."*
— HN user `manav`, same thread, [news.ycombinator.com/item?id=19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14.

**6. The "same words ≠ same product" trap — the core false-positive risk:**
> *"How sure are you that the thing that you think is a preexisting implementation actually does what you want your thing to do? … my experience has been that things that look the same are off."*
— HN user `_Nat_`, same thread, [news.ycombinator.com/item?id=19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14.

**7. The bar a duplicate must clear to be worth attention:**
> *"If it's 'exactly the same thing', I personally wouldn't do it. It doesn't have to be something so significantly different, but it has to be a solution to some real pain points that persist on the existing solution."*
— HN user `blacksoil`, same thread, [news.ycombinator.com/item?id=19774997](https://news.ycombinator.com/item?id=19774997), accessed 2026-09-14.

**8. Product Hunt as a research surface, in the community's own words:**
> *"In theory it's a place for you to do a quick check of 'is this a good idea or thing to work on'. In practice it's a bunch of serial founders upvoting each others ideas."*
— HN user `maccard`, *Product Hunt is dead*, [news.ycombinator.com/item?id=45362569](https://news.ycombinator.com/item?id=45362569), accessed 2026-09-14.

**9. "No one even saw it" — the discoverability failure of the substitute founders use as a directory:**
> *"It got buried under dozens of other launches within hours. All that work, all that excitement is gone in the blink of an eye. No one even saw it. … mostly, I just felt invisible."*
— HN user `lakshikag`, Show HN: *I built a fair alternative to Product Hunt for indie makers*, [news.ycombinator.com/item?id=42712666](https://news.ycombinator.com/item?id=42712666), accessed 2026-09-14.

**10. Attention ≠ adoption (why "I found it" is not the same as "it works"):**
> *"My app Payload got featured in fastcompany, and I thought that was amazing. It drove traffic to the website and I was just waiting for the users… that didn't come."*
— HN user `klabb3`, same thread, [news.ycombinator.com/item?id=42712666](https://news.ycombinator.com/item?id=42712666), accessed 2026-09-14.

**11. Network effects as the moat against new directories (directly relevant to IdeaExists' "why it is not beatable" section):**
> *"I see a new product-hunt alternative launched every couple months here. Maybe I'm cynical, but I don't think we're going to displace product hunt with things like new voting dynamics. They already have the network effects…"*
— HN user `pinkmuffinere`, same thread, [news.ycombinator.com/item?id=42712666](https://news.ycombinator.com/item?id=42712666), accessed 2026-09-14.

**12. The authority the status quo leans on:**
> *"Ten minutes of searching the web will usually settle the question. Even if you find someone else working on the same thing, you're probably not too late. It's exceptionally rare for startups to be killed by competitors — so rare that you can almost discount the possibility."*
— Paul Graham, *How to Get Startup Ideas* (2012), [paulgraham.com/startupideas.html](https://www.paulgraham.com/startupideas.html), accessed 2026-09-14.

**13. The economic counter-argument (2026):**
> *"Validation made sense when building was the expensive part. You spent two weeks researching because you were about to spend three months building. The research was cheap insurance on an expensive bet. That ratio has flipped and I don't think our advice has caught up."*
— Lily, Indie Hackers post dated 11 September 2026, [indiehackers.com](https://www.indiehackers.com/post/we-sell-validate-before-you-build-the-only-thing-i-ve-opened-every-day-this-week-is-the-thing-i-never-validated-a244c2b092), accessed 2026-09-14.

**14. The AI-tool failure mode, from someone using it for this job:**
> *"Hallucinations: Sometimes it invents fake competitors or data."*
— *How I Use ChatGPT to Validate (or Kill) Any Business Idea*, [ai.plainenglish.io](https://ai.plainenglish.io/the-30-minute-startup-test-how-i-use-chatgpt-to-validate-or-kill-any-business-idea-2cfa2b744ceb), accessed 2026-09-14.

**15. Tool-search is capped and awkward (GitHub):**
> *"The 5 page limit with no indication of total counts makes it extremely difficult to use Code Search in its current form."*
— GitHub community discussion #9868, [github.com/orgs/community/discussions/9868](https://github.com/orgs/community/discussions/9868), accessed 2026-09-14.

**16. The current workflow, named by a founder asking exactly this question:**
> *"Hi everyone, what's your go-to way to de-duplicate an app idea? Normally, I have to use ChatGPT, Google, Product Hunt, Crunchbase, etc., but I still …"*
— r/startups, *Where do you reliably check if your idea is already [exists]*, [reddit.com/r/startups/comments/1ohx9g1](https://www.reddit.com/r/startups/comments/1ohx9g1/where_do_you_reliably_check_if_your_idea_is/), accessed 2026-09-14. **[Search-surfaced excerpt — Reddit blocked direct retrieval; quote reproduced as retrieved and not extended.]**

**17. The duplicate-discovery gut-punch, in a founder's own words:**
> *"But today, I stumbled upon something very similar that already exists, and now I feel completely drained. It's like all my excitement just …"*
— r/SaaS, *Just Found Out Someone Built Something Similar to My [Idea]*, [reddit.com/r/SaaS/comments/1jakbte](https://www.reddit.com/r/SaaS/comments/1jakbte/just_found_out_someone_built_something_similar_to/), accessed 2026-09-14. **[Search-surfaced excerpt.]**

**18. "Research didn't find the real competitors" — evidence the substitute under-delivers:**
> *"I'm building a vertical SaaS product and I'm getting close to launch. When I first started, I did some research and honestly felt like the space …"*
— r/SaaS, *I found my real competitors after building most of the [product]*, [reddit.com/r/SaaS/comments/1svi6yf](https://www.reddit.com/r/SaaS/comments/1svi6yf/i_found_my_real_competitors_after_building_most/), accessed 2026-09-14. **[Search-surfaced excerpt.]**

**19. The manual workflow, taught as folklore (Google → Betalist → Product Hunt):**
> *"First search google with product/idea related keywords. A tip is to include start-up. Then I would search on Betalist.com, product hunt and …"*
— r/startups, *How do you know if your startup idea already exists?*, [reddit.com/r/startups/comments/3ubimv](https://www.reddit.com/r/startups/comments/3ubimv/how_do_you_know_if_your_startup_idea_already/), accessed 2026-09-14. **[Search-surfaced excerpt.]**

**20. The measured unreliability of the default first stop:**
> *"The generative search tools we tested had a common tendency to cite the wrong article… Across 1,600 test queries, the search engines failed to retrieve the correct information more than 60% of the time."*
— Tow Center for Digital Journalism / Columbia Journalism Review, *AI Search Has a Citation Problem*, [cjr.org](https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php), accessed 2026-09-14.

---

## What a substitute user would have to give up to switch

Switching costs are low in money and high in *habit*. A founder currently on the status quo would have to surrender:

1. **The comfort of Google.** Instant, universal, unlimited, and free — no tab to learn.
2. **The conversational flexibility of a chat LLM.** No more "what if I narrowed it to X?" follow-ups in the same breath.
3. **The archive effect of Product Hunt / HN.** Launch-day colour, comments, and "what shipped this week" that a verified directory may not replicate.
4. **Zero-effort privacy of "I didn't tell anyone".** Notably, local-first is *aligned* with this, not against it — but only if the founder trusts the local-first claim. `[ASSUMPTION]`
5. **The ability to hand-assemble a bespoke view.** Today a founder can build a bespoke spreadsheet exactly matching their question; a structured directory imposes *its* schema. The absence of **export** and a **comparison flow** in the current product makes this trade-off sharper — a Crunchbase export and an AlternativeTo comparison list are things the status quo does provide.
6. **The illusion of an answer.** Chat LLMs and AI engines always respond. A verification-first directory may legitimately say "we don't know yet" — honest, but less satisfying than a confident (if wrong) answer.

Net: the switch is not blocked by price; it is blocked by **habit, coverage gaps, and missing export/comparison affordances**. Those are addressable, which is why the product is not obviously doomed.

---

## Conclusion

The status quo is a **stitched-together, mostly-free, mostly-good-enough workflow**: Google for naming, ChatGPT for a quick take, Perplexity for "grounded" answers, Product Hunt for what launched, Crunchbase if you're serious about funded competitors, GitHub if it's open source, HN/Reddit for vibes, a mentor for judgement — and for the truly committed, a homemade spreadsheet.

That workflow is beatable, but only on three narrow fronts where the substitutes are **demonstrably wrong rather than merely inconvenient**:

1. **False negatives** — Google and chat LLMs miss products you didn't know to search for, and the resulting silence reads as "no competitor". This is the highest-consequence failure, and it is exactly the failure IdeaExists' verification philosophy targets.
2. **Liveness** — no free substitute answers "is it alive or dead?" Product Hunt is a snapshot, AlternativeTo lists corpses, Crunchbase tracks funding not survival. A weekly liveness check with a "dead but never deleted" record is a genuinely new primitive.
3. **Verification** — a human stamp automation can never write is, in a post-hallucination market, a legible trust signal that AI answer engines cannot fake. The measured 60%+ failure rate of AI search on citation turns this from a nice-to-have into the core value proposition.

The status quo is *not* beatable on convenience, price, or breadth. And there is one serious, evidence-backed threat to the whole premise: **if building is now an afternoon, the research the product sells may cost more than the thing it protects** ([indiehackers.com, 11 Sept 2026](https://www.indiehackers.com/post/we-sell-validate-before-you-build-the-only-thing-i-ve-opened-every-day-this-week-is-the-thing-i-never-validated-a244c2b092), accessed 2026-09-14).

**Strategic read:** sell the *outcome*, not the research. The product should attach to the moments where the substitute's error is expensive — "you're about to spend three weeks on something that shipped last year", "this category is a graveyard", "your closest competitor was verified three weeks ago" — rather than to the abstract virtue of research. The reframe in progress ("understand the closest alternatives, and decide what would be meaningfully different before you build") is directionally right because it targets Jobs 3 and 5, which the substitutes serve worst and which carry the most consequence. `[ASSUMPTION]`

---

## Assumptions and open questions

- `[ASSUMPTION]` Output comes from web search + primary-source fetch; Reddit's own endpoints refused programmatic access on 2026-09-14, so Reddit quotes are search-surfaced excerpts (labelled). Some Reddit threads could not be verified beyond the excerpt.
- `[ASSUMPTION]` Crunchbase free-tier limits (~11 profile views/month, no export, free API removed) come from **secondary** sources (ZoomInfo, dataforb2b) and should be re-verified against Crunchbase's own pages before being used externally.
- `[ASSUMPTION]` The claim that this audience values "local-first / nothing leaves the machine" enough to switch is unproven; no behavioural evidence for it was found in this pass.
- `[OPEN QUESTION]` Willingness to pay, and whether this is a *subscription* job or a *one-off-per-idea* job. If the latter, pricing and retention need a different model. No price-sensitivity evidence was collected here.
- `[OPEN QUESTION]` Whether the "dead but never deleted" rule is a feature users want or a data-quality liability; no substitute does this, so there is no precedent to borrow from.
- `[OPEN QUESTION]` The count "1,282 filings / 1,278 human-verified / 0 dead" is taken as given from the brief and was not independently verified in this document.
- `[OPEN QUESTION]` Whether AI answer engines (Perplexity, ChatGPT Search, Google AI Overviews) become *good enough* within 12–24 months to close the accuracy gap, which would collapse the verification wedge.

*Document version: 1.0 — compiled 2026-09-14. All external URLs accessed 2026-09-14.*
