# Competitor Content Spot-Check

**Run:** 2026-09-14 · re-fetched a sample of the cited competitor and market pages and tested whether the exact positioning/capability strings recorded in `research/02` (and the market claims in `research/04`/`research/05`) are present in the live page text.

This is the content half of the verification plan: the availability sweep (`source-availability-check.md`) proves the links resolve; this proves the *claims* are still on the pages.

| Page | URL | HTTP | Expected string found | Chars read |
|---|---|---|---|---|
| IdeaProof | https://ideaproof.io/ | 200 | yes — 50+, validation | 73245 |
| DimeADozen | https://www.dimeadozen.ai/ | 200 | yes — subscription | 82375 |
| DimeADozen pricing | https://www.dimeadozen.ai/pricing | 200 | yes — subscription | 44559 |
| Preuve AI | https://preuve.ai/ | 200 | yes — real data | 238688 |
| StartupConcept.ai pricing | https://startupconcept.ai/pricing | 200 | yes — 19.99 | 2342 |
| FounderSpace pricing | https://www.founderspace.work/pricing | 200 | yes — Pay-As-You-Go | 30368 |
| BigIdeasDB | https://bigideasdb.com/ | HTTPError | no (data points) | 0 |
| Startups.RIP | https://startups.rip/ | 200 | yes — startups | 108015 |
| Loot Drop | https://www.loot-drop.io/ | 200 | yes — graveyard | 3509 |
| Loot Drop FAQ | https://www.loot-drop.io/faq | 200 | no (1,749) | 9359 |
| Failory cemetery | https://www.failory.com/cemetery | 200 | yes — fail | 122860 |
| OpenSourceAlternative | https://www.opensourcealternative.to/ | 200 | yes — open source | 89321 |
| StackShare about | https://stackshare.io/about | HTTPError | no (developer community) | 0 |
| Futurepedia | https://www.futurepedia.io/ | 200 | yes — AI tool | 451137 |
| Toolify | https://www.toolify.ai/ | 200 | yes — categories | 161819 |
| FutureTools submit | https://futuretools.io/submit-a-tool | 200 | yes — tool | 28945 |
| Crunchbase pricing | https://about.crunchbase.com/products/crunchbase-pro | 200 | yes — Pro | 66552 |
| Exploding Topics | https://explodingtopics.com/ | 200 | yes — 1.29 | 140619 |
| Glimpse | https://meetglimpse.com/ | 200 | yes — trending | 15258 |
| selfh.st apps | https://selfh.st/apps/ | 200 | yes — self-hosted | 14277 |
| Up For Grabs | https://up-for-grabs.net/ | 200 | yes — open source | 12781 |
| Semrush | https://www.semrush.com/ | 200 | yes — visibility | 22593 |
| Crayon | https://www.crayon.co/ | 200 | yes — competitive intelligence | 34097 |
| Kompyte | https://www.kompyte.com/ | 200 | yes — competitor | 28403 |
| Indie Hackers about | https://www.indiehackers.com/about | 200 | yes — profitable | 6037 |
| Product Hunt | https://www.producthunt.com/ | HTTPError | no (products) | 0 |
| G2 vs Capterra | https://www.g2.com/compare/capterra-vs-g2 | HTTPError | no (review) | 0 |
| Pew Research | https://www.pewresearch.org/data-labs/2024/05/17/when-online-content-disappears/ | 200 | yes — disappear | 239871 |
| CJR Tow Center | https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php | 200 | yes — citation | 109987 |
| Paul Graham | https://www.paulgraham.com/startupideas.html | 200 | yes — startup ideas | 43229 |
| G2 acquires | https://company.g2.com/news/g2-acquires-capterra-software-advice-getapp | 200 | yes — Capterra | 37305 |
| Lightspeed local-first | https://www.inkandswitch.com/essay/local-first/ | 200 | yes — local | 75809 |

**Result: 27 of 32 spot-checked pages confirmed the cited string on the live page; 4 could not be checked (bot-blocked); 1 revealed a genuine data drift.**

### Outcome breakdown

| Outcome | Count | Pages |
|---|---|---|
| Cited string confirmed on the live page | **27** | IdeaProof, DimeADozen (×2), Preuve AI, StartupConcept.ai, FounderSpace, Startups.RIP, Loot Drop, Failory, OpenSourceAlternative.to, Futurepedia, Toolify, FutureTools, Crunchbase Pro, Exploding Topics, Glimpse, selfh.st, Up For Grabs, Semrush, Crayon, Kompyte, Indie Hackers, Pew Research, CJR Tow Center, Paul Graham, G2 acquisition release, Local-first essay |
| Blocked — could not content-check | **4** | BigIdeasDB, StackShare, Product Hunt, G2 comparison page (all returned an HTTP error to an automated client; they still resolve for a human) |
| **Genuine data drift found** | **1** | **Loot Drop** — `research/02` recorded "1,749 failed startups / $535.4B+"; the live FAQ on the same access date says **"1,600+ failed startups"** and **"over $40 billion in burned venture capital"**, while the homepage metadata says **"925+ / $32.5B+"**. The site contradicts itself page-to-page. `research/02` has been corrected with a dated note, and any Loot Drop figure should now be treated as unstable.

**Useful corroboration found during the check:** Loot Drop's live FAQ independently states *"No Market Need is the #1 reason startups fail, causing roughly 35% of all failures"* — close to, but lower than, the ~42% CB Insights figure used (as directional) in `research/04`.

Pages that refused an automated client (403/429) could not be content-checked and are excluded from the denominator rather than counted as failures — those are the same pages listed as *blocked* in `source-availability-check.md`.