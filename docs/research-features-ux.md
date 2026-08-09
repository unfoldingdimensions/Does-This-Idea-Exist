# Feature & UX Research — IdeaExists

*Research date: 2026-08-09. Method: direct inspection of the analogue products themselves (their own pages/features) plus user-generated demand/pain evidence from Hacker News (via the official Algolia API) and Reddit (via the PullPush archive — reddit.com itself blocks automated fetch; thread URLs given are the canonical reddit.com permalinks). Every claim below carries its source.*

## 1. Executive summary

- **Search + faceted filters are table stakes for every directory that works.** Y Combinator's directory filters by batch, industry, HQ region, company size, hiring status and more [2]; topstartups.io filters by HQ, industry, employee size, founded year, funding stage and investor, and sorts by "Recent Funding" / "Highest Valuation" [5]. TAAFT's whole model is "find exactly the AI you need" [4].
- **Freshness/status signals are the #1 trust feature.** TAAFT's stated curation promise includes "We routinely re-test links, refresh descriptions, and retire defunct entries" and it keeps an "Inactive AIs" section instead of deleting [4]. The made-in-nigeria list flags dead projects with "🏁 Inactive" [9]; its web version shows "Active" status per project [10]. This directly validates IdeaExists' 3-failed-checks → 'dead' (never deleted) model.
- **"Alternatives" / same-category peers are a core navigation pattern**, not a nice-to-have: StartupStash has an Alternatives section and "23 Zoom Alternatives" pages [6]; a Prexist user said the value is "to understand existing approaches and see if our insights can lead to a meaningfully different solution" [11]; HN advice threads tell founders to "find out the current alternatives" [12].
- **Verification is a selling point.** StartupStash marks listings "Verified" [6]; TAAFT's About page stresses "manual vetting, clear labeling, and relentless pruning" and explicitly checks "duplicates" [4]; YC's batch badge is an implicit verification mark [2]. IdeaExists' human 'mark verified' gate + auto link-checking is exactly this pattern.
- **Paywalls and data-gating are the most hated thing in this space** — and "no paywall, no tracking" is itself a marketing hook ("I built a Crunchbase for web3 startups… (No ads, no paywall, no tracking.)") [22]. Crunchbase's paywall draws complaint threads [19][21] and people actively hunt free alternatives [20][16]. IdeaExists' local-first, no-accounts positioning is a genuine differentiator.
- **Bookmarks/saves and collections are standard** (TAAFT: "Saved tools", "My saved AIs", "Sign in to save", 13,000+ user Collections [3][4]; StartupStash "Top Lists" [6]; Product Hunt launch archive [7]) — implementable without accounts via localStorage.
- **Newsletters/digests are the dominant retention mechanism** (TAAFT: 2.5M newsletter subscribers, "world's largest AI newsletter" [4]; Product Hunt: daily newsletter [7]; topstartups.io: "Subscribe" [5]) — for a local-first app, an exportable "what changed" feed (RSS/JSON) is the account-free analogue.
- **Users want the directory to answer "is it alive and real?"** — GitHub activity, founded date, and status on the card/detail, not just a name and a link (YC detail pages: Founded, Batch, Team Size, Status, Location, website, founders [2]; topstartups "Quick facts" + "Take action" [5]; madeinnigeria.dev shows language, stars, Active status per project [10]).

## 2. Evidence table

| # | Finding | Where it comes from (product/source) | Source URL | Relevance to IdeaExists |
|---|---------|-------------------------------------|-----------|-------------------------|
| 1 | YC directory ships search + faceted filters: Top Companies, Is Hiring, Nonprofit, Batch, Industry, HQ Region, Company Size (slider), video/application-answer checkboxes; sort by Launch Date | Y Combinator Startup Directory (live page) | https://www.ycombinator.com/companies | IdeaExists already has fuzzy search + category chips; adding founded-year/status filters and a sort control matches the expected baseline |
| 2 | topstartups.io filters by HQ, Industry (20+), employee Size, Founded year, funding Stage, Investor; sorts by Recent Funding / Highest Valuation; "Updates daily"; "1,259 startups" count | topstartups.io homepage (fetched live) | https://www.topstartups.io/ | Filters + sort + a result count ("N startups") are cheap, high-signal additions |
| 3 | topstartups cards show "Quick facts" (HQ, employees, founded, funding) and "Take action" (company site, jobs) | topstartups.io homepage (fetched live) | https://www.topstartups.io/ | Card density pattern: factual row + action links (website/GitHub) — matches IdeaExists fields |
| 4 | YC detail pages: tagline, batch badge, status (PUBLIC), category tags, location, tabs (Company / Jobs / News), description, founder bios, Founded/Batch/Team Size/Status/Location, external links (website, LinkedIn, X, Crunchbase) | YC company detail page (Airbnb, fetched live) | https://www.ycombinator.com/companies/airbnb | Blueprint for IdeaExists detail page: put founded date, status, tags, website + GitHub links, description in a consistent layout; "founded" is a headline field |
| 5 | TAAFT nav: Search, Deals, Leaderboard, Tasks, Mini tools, Characters, Saved tools, Just launched, Featured, Trending, Popular, Agents, Lists, Requests, Most saved, Timeline, Find a Job, Map, Prompts | theresanaiforthat.com homepage (fetched live) | https://theresanaiforthat.com/ | Discovery-oriented sections (Just launched / Featured / Most saved) give new/old entries fair exposure; Requests = demand capture |
| 6 | TAAFT curation promise: "manual vetting, clear labeling, and relentless pruning to keep results useful"; reviewers check "functionality, accuracy of claims, pricing clarity, safety, and duplicates"; "We routinely re-test links, refresh descriptions, and retire defunct entries"; keeps "Inactive AIs" | TAAFT About page (fetched live) | https://theresanaiforthat.com/about/ | Direct validation of IdeaExists' verify-first, re-check links weekly, mark-dead-never-delete model; adds duplicate-checking as an explicit promise |
| 7 | TAAFT scale/retention: 5M+ MAU, 2.5M newsletter subscribers, 140k+ entities indexed, 50k+ tools, 11k+ tasks; "hit 100k visits in week one" after Dec 2022 launch; "143,912 searches today" counter | TAAFT About page (fetched live) | https://theresanaiforthat.com/about/ | Newsletter + activity counters are their growth/retention engine; for local-first, an exportable changelog/RSS substitutes for newsletters |
| 8 | TAAFT per-tool data: pricing model labels ("Freemium", "$20/mo", "Free trial"), feature tags ("Agents, API, MCP"), comments, "Most saved", empty states ("No AI tools match these filters", "Clear filters") | TAAFT homepage list markup (fetched live) | https://theresanaiforthat.com/ | Feature tags and "free/paid" clarity are valued metadata; empty-state with a clear-filters action is a UX detail IdeaExists should copy |
| 9 | TAAFT saves: "Saved tools", "My saved AIs", "Sign in to save" — bookmarking exists but is gated behind accounts | TAAFT homepage (fetched live) | https://theresanaiforthat.com/ | Saves are expected; IdeaExists can offer them without accounts via localStorage (a UX win over the analogues) |
| 10 | Product Hunt: upvotes, category tags on every card, "Yesterday's/Last Week's/Last Month's Top Products", "Top Product Categories" taxonomy, Launch Guide, Launch archive, Forums, Kitty Points + Streaks leaderboards, newsletter; upvotes hidden for first 4 hours so new products get a chance | Product Hunt homepage (fetched live) | https://www.producthunt.com/ | Time-windowed top lists and "new gets a chance" fairness idea apply to a directory where default sort would otherwise bury new entries |
| 11 | Crunchbase: "Advanced Search", pricing/Start Free Trial/Talk With Sales (paywall-first), example searches ("Build a list of AI startups founded in last 6 months"), "This month on Crunchbase" activity stats, trending predictions/insights/fundraises feed | Crunchbase homepage (fetched live) | https://www.crunchbase.com/ | Confirms demand for "list of startups founded in last N months" queries (founded-date filtering); paywall is what users resent — IdeaExists' open data is the contrast |
| 12 | StartupStash: "Verified" badges, "Free Tool" badges, Categories, "Alternatives" nav + "23 Zoom Alternatives" pages, "Top Lists", "List A Product" | StartupStash homepage (fetched live) | https://www.startupstash.com/ | Verification badges = trust; Alternatives pages = comparison navigation; "List a product" = inbound submission channel |
| 13 | made-in-nigeria GitHub list: alphabetical curation, GitHub links, author credits, "🏁 Inactive" flags on dead projects; web version (madeinnigeria.dev): Featured Projects, View Project detail, View Contributor Profile, Make a Submission, per-project language + stars + "Active" status | GitHub repo README + website (fetched via GitHub API / live) | https://github.com/acekyd/made-in-nigeria and https://madeinnigeria.dev/ | The exact "made in X / does it exist" genre: status flags + stars + contributor attribution are the core metadata; IdeaExists' GitHub-centric fields mirror this |
| 14 | HN user: Prexist founder built it because of "not knowing if my 'brilliant' idea already existed… until it was too late"; features: search 8+ platforms, similar products, keywords + relevance scores; commenter: "recent searches would be very very interesting, I assume many people would be put off by that" (privacy) | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=44898394 | Direct evidence for the core use case; shows privacy-sensitivity about saved searches and demand for "similar products" comparison |
| 15 | HN user on idea-exists tools: "This is useful but not to decide whether to work on an idea or not… more useful as a way to understand existing approaches and see if our insights can lead to a meaningfully different solution" | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=44898394 | Users want to *compare against what exists*, not just get a yes/no — supports an "alternatives/similar in category" view |
| 16 | HN Ask: when your idea already exists — top advice "find out the current alternatives. If the existing one is doing a good job, let it go"; another: "They have validated the idea for you" | HN Ask HN threads (via Algolia API) | https://news.ycombinator.com/item?id=2894632 and https://news.ycombinator.com/item?id=29334744 | The mental model of the target user is alternatives-comparison, not binary existence — surface similar entries prominently |
| 17 | HN Ask "best source for discovery of new startups": complaint "KillerStartups is really lacking… it's very spammy… hard to not click on an ad"; "I wish there was a better way" | HN Ask HN thread (via Algolia API) | https://news.ycombinator.com/item?id=1375898 | Users punish ad-spammy directories; a clean, ad-free local app is a feature in itself |
| 18 | HN user on StartupList EU (a startup directory): "no option to skip the funding and valuation info… you can only exist in this world if you are burning someone else's money" (bootstrapped founders excluded); "you're getting buried in lists-of-lists" (fragmentation) | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=44564849 | IdeaExists' GitHub-centric, funding-free entries serve bootstrapped/indie projects the VC directories ignore; don't add required funding fields |
| 19 | HN "A Free Crunchbase Alternative" thread: users demand an API, "price for the api was $100 or less per month (not $450+ like crunchbase)", suggest USPTO patent data and SEC filings as public data sources | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=48572472 | Export/API access is a real request; a JSON/CSV export or static-data dump fits IdeaExists' local-first model perfectly |
| 20 | HN "Tell HN: Crunchbase Is Now Paywalled" (title alone, 0 comments) and "Ask HN: Alternatives to Crunchbase?" — paywall-driven demand for alternatives | HN threads (via Algolia API) | https://news.ycombinator.com/item?id=33151590 and https://news.ycombinator.com/item?id=33729052 | Open/free access is the differentiation users actively seek |
| 21 | Reddit r/assholedesign: "Crunchbase uses an Evercookie to do the paywall" (score 23, 9 comments — users resort to incognito/paywall-bypass) | Reddit via PullPush archive | https://www.reddit.com/r/assholedesign/comments/12nn87n/ | Users go to lengths to dodge paywalls; never build one into IdeaExists |
| 22 | Reddit r/CryptoCurrency: "I built a Crunchbase for web3 startups as a side project. (No ads, no paywall, no tracking.)" — privacy/no-ads/no-paywall used as the headline pitch | Reddit via PullPush archive | https://www.reddit.com/r/CryptoCurrency/comments/x7espi/ | "No tracking, no paywall" is a proven pitch; matches IdeaExists' local-first identity |
| 23 | Reddit r/AI_Agents and r/Entrepreneur: "Is theresanaiforthat.com worth it?" — users publicly asking whether the directory is worth using/paying for | Reddit via PullPush archive | https://www.reddit.com/r/AI_Agents/comments/1kc5ctw/ and https://www.reddit.com/r/Entrepreneur/comments/1jwcmpd/ | Even the biggest directory generates "is it worth it" skepticism — trust and free value are the answer |
| 24 | Reddit r/BuyFromEU: "AlternativeTo now shows country of origin" and "Alternativeto.net cares about Europe" — transparency metadata (origin country) shipped as a feature | Reddit via PullPush archive | https://www.reddit.com/r/BuyFromEU/comments/1k9xwr4/ | Origin/geography metadata is a valued transparency feature, even on review sites (note: alternativeto.net itself blocked automated fetch — Cloudflare) |
| 25 | TAAFT HN launch feedback: users loved discovery ("Found quite a few I had no clue it existed") but flagged slow search, broken back-button (search terms pushed to history), and broken mobile search | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=34069825 | Search performance, history hygiene and mobile are make-or-break UX details for a search-first directory |
| 26 | HN Startuplister thread: users asked for directory importance ranking (Alexa/PageRank-style) and an API listing submitted sites | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=8175019 | Users want signal on *which* listings matter and machine access to them — relevance/ranking and export again |
| 27 | HN: "How do you research if a startup idea already exists?" (Ask HN) — recurring question with zero answers, i.e., unmet need | HN Ask HN (via Algolia API) | https://news.ycombinator.com/item?id=32191850 | Confirms the gap IdeaExists fills; nobody has a good default answer to point to |

## 3. Recommended features

Grounded in the table above; constrained by IdeaExists' identity: local-first, no accounts, verification-first, GitHub-centric, single admin.

### P0 — quick wins, high value

1. **Status badge + "last verified" timestamp on every card and detail page** — *Why:* freshness/status is the #1 trust signal in this genre; TAAFT "re-test links… retire defunct" and its Inactive AIs [6], made-in-nigeria's "🏁 Inactive"/"Active" flags [13]. IdeaExists already computes dead/verified; just surface it visually (e.g., green "verified", red "dead", grey "unverified" + "checked <date>"). *Effort: S.*
2. **Sort control (newest added / founded date / stars / name) + result count** — *Why:* every major directory sorts (YC: Launch Date [1]; topstartups: Recent Funding [2]) and shows counts ("1,259 startups" [2]); without a default, new entries get buried (Product Hunt's fairness fix [10]). *Effort: S.*
3. **Founded-year + status filters alongside category chips** — *Why:* Crunchbase's own example query is "list of AI startups founded in last 6 months" [11]; YC filters by batch/industry/region/size [1]; topstartups filters by founded year [2]. *Effort: S.*
4. **Empty state with "clear filters" + a suggestion to seed** — *Why:* TAAFT ships "No AI tools match these filters" + "Clear filters" [8]; a dead-end search is the fastest way to lose a user. *Effort: S.*
5. **"Similar / alternatives in this category" block on the detail page** — *Why:* the core mental model of users is alternatives-comparison ("find out the current alternatives" [16]; Prexist "similar products" [14][15]; StartupStash Alternatives pages [12]). Cheap with existing category field. *Effort: S–M.*
6. **Home sections: "Just added", "Recently verified", "Dead recently"** — *Why:* TAAFT's Just launched/Featured/Most saved [5], PH's time-windowed top lists [10], madeinnigeria.dev's Featured Projects [13]. Gives both freshness and honesty visibility. *Effort: S–M.*
7. **Search via URL param (`?q=` / `?category=`) so results are shareable/linkable** — *Why:* TAAFT supports `?search=` [25]; shareable queries are the account-free way to "save" a search (privacy-respecting, per [14]). *Effort: S.*

### P1 — next tier

8. **localStorage bookmarks ("Saved startups")** — *Why:* saves are standard (TAAFT "Saved tools"/"My saved AIs" [9], but gated behind accounts); IdeaExists can beat the analogues by doing it without any signup, fully local. *Effort: M.*
9. **GitHub liveness signals on cards: last commit date / recent release / open issues count** — *Why:* answers "is it alive?" directly; stars alone already exist; "Active" flags [13] and freshness promises [6] show demand. *Effort: M.*
10. **JSON/CSV export (and a static dump) of the whole directory** — *Why:* repeated API/export demand [19][26]; fits local-first perfectly (data belongs to the owner; export = account-free "RSS" for power users). *Effort: M.*
11. **Duplicate detection during admin seeding (normalize by domain/GitHub repo)** — *Why:* TAAFT explicitly checks duplicates [6]; duplicates were called out as a directory failure mode by users. *Effort: M.*
12. **Keyboard shortcut (⌘/Ctrl+K) for search + "recently viewed" list (localStorage)** — *Why:* TAAFT ships ⌘+K [4/About nav]; "Recently viewed" is a TAAFT nav item [5]; cheap delight. *Effort: S.*
13. **"Request to add" note on the 404/no-results state** ("Not found? Ask the curator to add it — submit the GitHub repo/URL") — *Why:* TAAFT's "Requests" are open demand signals [5]; gives the single admin a lightweight inbound channel without building accounts. *Effort: S.*
14. **Share/copy-link and keyboard-navigable results** — *Why:* PH/others all make list URLs stable; accessibility and shareability are baseline in the analogues. *Effort: S.*

### P2 — later / deliberately deferred

15. **Community reviews/comments** — *Why:* TAAFT comments and PH "Top reviewed" [8][10] exist, but moderation is heavy for a single admin and conflicts with no-accounts; defer. *Effort: L.*
16. **Upvotes/leaderboards** — *Why:* PH upvotes/Kitty Points/Streaks [10], TAAFT Leaderboard [5]; needs accounts or trust to avoid gaming; localStorage-only votes are weak. *Effort: L.*
17. **Jobs section** — *Why:* YC "Work at a Startup" [1][4-tabs], TAAFT Jobs [5], topstartups "View Jobs" [3]; out of scope for a "does it exist" tool and needs fresh data. *Effort: L.*
18. **Side-by-side comparison view (2–3 entries)** — *Why:* Prexist "similar products with AI powered analysis" [14] and AlternativeTo-style comparison [12]; valuable but a real UX build. *Effort: L.*
19. **Change-feed RSS/atom ("recently verified / newly added / marked dead")** — *Why:* newsletters are the retention engine of every analogue [7][10][5]; RSS is the no-accounts, no-tracking, local-first equivalent. *Effort: M.*
20. **Geography/origin metadata (country flag)** — *Why:* AlternativeTo's "country of origin" feature was positively received [24]; could conflict with IdeaExists' minimal-field ethos — decide consciously. *Effort: S.*

## 4. UX improvements

Patterns observed in the analogues that apply directly:

- **Search UX is make-or-break.** TAAFT's launch thread complaints were search slowness, back-button breakage (search terms pushed onto history), and broken mobile search [25]. Rules: debounce input, keep history clean (replaceState, not pushState), and make search work on mobile.
- **Shareable, param-driven state.** TAAFT supports `?search=` URLs [25]. All filters/sorts/queries should be reflected in the URL so results are linkable, refresh-safe and back-button-safe.
- **Filters with counts and a clear path out.** Show result counts per filter and a prominent "Clear filters" action with a friendly empty state ("No startups match these filters") [8].
- **Freshness must be visible, not implicit.** "Verified on <date>", "last checked", status badges (Active/Dead/Unverified) on cards and detail — the pattern is TAAFT's Inactive AIs [6] and made-in-nigeria's Active/🏁 Inactive flags [13].
- **Card design.** One-line tagline, category chips, stars, status dot, GitHub link — as in YC cards [2], topstartups "Quick facts"/"Take action" [3], PH category tags [10], madeinnigeria.dev's language+stars+Active row [13]. Avoid ad-like clutter: users explicitly punish spammy, ad-heavy directories [17].
- **Detail page layout.** Headline tagline + status + founded date + batch/verified source; description; a consistent "links" block (website, GitHub, and any social); related/alternatives block. YC's Airbnb page is the reference [4].
- **Onboarding/first-run.** Crunchbase surfaces example queries ("Build a list of AI startups founded in last 6 months") [11]; a Prexist reviewer asked for an "explore" option [14]. IdeaExists should offer example searches and an "explore everything" entry point on first load.
- **Fairness in default ordering.** Product Hunt hides upvotes for the first 4 hours so new products get a chance [10]; TAAFT keeps "Just launched" separate from "Popular" [5]. Don't let a stars-based default permanently bury new entries.
- **No-accounts is a feature.** TAAFT gates saves behind sign-in [9]; Crunchbase gates everything behind a paywall [11][21]. localStorage-based bookmarks, recently-viewed and shareable URLs give the analogues' features without the accounts — and "no tracking" is a pitch users respond to [22].
- **Honesty as UX.** Users *assume* directories are stale or spammy [17][23]. An explicit "how we verify" blurb (mirroring TAAFT's curation promise [6]) turns the verification-first model into a trust asset.

## 5. Sources

1. Y Combinator Startup Directory (live page, fetched 2026-08-09): https://www.ycombinator.com/companies
2. Y Combinator directory filters/sort (same page): https://www.ycombinator.com/companies
3. YC company detail page (Airbnb): https://www.ycombinator.com/companies/airbnb
4. There's An AI For That — About (curation model, numbers, origin): https://theresanaiforthat.com/about/
5. There's An AI For That — homepage (nav, filters, saves): https://theresanaiforthat.com/
6. topstartups.io — homepage (filters, sort, quick facts, subscribe): https://www.topstartups.io/
7. StartupStash — homepage (Verified/Free badges, Alternatives, Top Lists): https://www.startupstash.com/
8. Product Hunt — homepage (upvotes, categories, top lists, forums, newsletter): https://www.producthunt.com/
9. Crunchbase — homepage (advanced search, pricing, activity stats, trending feed): https://www.crunchbase.com/
10. made-in-nigeria GitHub repo (README, 🏁 Inactive flags): https://github.com/acekyd/made-in-nigeria
11. madeinnigeria.dev (web directory: Featured, View Project, status, stars): https://madeinnigeria.dev/
12. HN "Show HN: Prexist – Find if your startup idea already exists out there!": https://news.ycombinator.com/item?id=44898394
13. HN "Ask HN: When your startup IDEA has already been built by someone else?": https://news.ycombinator.com/item?id=2894632
14. HN "Ask HN: What do you do if it turns out that your product idea already exists?": https://news.ycombinator.com/item?id=29334744
15. HN "Ask HN: Best source for discovery of new startups?": https://news.ycombinator.com/item?id=1375898
16. HN "Show HN: StartupList EU – A public directory of European startups": https://news.ycombinator.com/item?id=44564849
17. HN "Show HN: A Free Crunchbase Alternative": https://news.ycombinator.com/item?id=48572472
18. HN "Tell HN: Crunchbase Is Now Paywalled": https://news.ycombinator.com/item?id=33151590
19. HN "Ask HN: Alternatives to Crunchbase?": https://news.ycombinator.com/item?id=33729052
20. HN "Show HN: There's an AI for That": https://news.ycombinator.com/item?id=34069825
21. HN "Show HN: Startuplister – A startup directory listing service": https://news.ycombinator.com/item?id=8175019
22. HN "Ask HN: How do you research if a startup idea already exists?": https://news.ycombinator.com/item?id=32191850
23. Reddit r/assholedesign — "Crunchbase uses an Evercookie to do the paywall" (via PullPush archive; reddit.com blocked automated fetch): https://www.reddit.com/r/assholedesign/comments/12nn87n/
24. Reddit r/CryptoCurrency — "I built a Crunchbase for web3 startups… (No ads, no paywall, no tracking.)" (via PullPush): https://www.reddit.com/r/CryptoCurrency/comments/x7espi/
25. Reddit r/AI_Agents — "Is theresanaiforthat.com worth it?" (via PullPush): https://www.reddit.com/r/AI_Agents/comments/1kc5ctw/
26. Reddit r/Entrepreneur — "Is TAAFT (theresaiforthat) woth it?" (via PullPush): https://www.reddit.com/r/Entrepreneur/comments/1jwcmpd/
27. Reddit r/BuyFromEU — "AlternativeTo now shows country of origin" (via PullPush): https://www.reddit.com/r/BuyFromEU/comments/1k9xwr4/

**Sources that blocked automated access (used alternatives or omitted):**
- alternativeto.net — Cloudflare "Just a moment…" challenge on both live site and Wayback Machine snapshots; its features are therefore only cited indirectly via the Reddit threads above (rows 24). Primary inspection was not possible; this is a known gap.
- reddit.com (www and old) — bot gate ("Prove your humanity"); the PullPush archive (api.pullpush.io) of Reddit data was used instead; canonical thread URLs cited.
- ycombinator.com/companies.json — returns `{"message":"Not found"}`; no public data API; used the rendered page instead.

## 6. Open questions (for the product owner)

1. **Dead entries by default?** TAAFT keeps "Inactive AIs" browsable [4]; should IdeaExists show dead startups in default results (with a red badge) or hide them behind a filter? This changes what "does this startup exist?" answers.
2. **localStorage-only bookmarks** — acceptable for a local-first app, but should there be a "portable" form (export saved list as JSON/markdown) so users aren't locked to one browser?
3. **"Request to add" channel** — given single-admin and no accounts, do you want an inbound request flow (e.g., a URL-submission form that drops into a pending-import queue), or is GitHub-issue-style manual collection fine?
4. **Category taxonomy depth** — flat chips today; analogues use 2-level taxonomies (PH "Top Product Categories" [10], TAAFT Tasks [7]). At what entry count does a hierarchy pay off?
5. **Default sort** — newest-added (fairness, discovery) vs stars (signal quality)? Relatedly: is "most stars" the metric you want to be known for, given users dislike hype-driven ranking [17]?
