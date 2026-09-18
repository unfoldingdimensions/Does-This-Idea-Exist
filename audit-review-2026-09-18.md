# Review of the 2026-09-18 liveness audit + drop

**Reviewer:** second agent, 2026-09-18 20:40-21:00 (Australia/Sydney)
**Subject:** the liveness audit of the IdeaExists archive and the follow-up drop of
dead/repurposed rows, as done by the previous agent at 20:10-20:28.
**Method:** I did not read the earlier results and nod along. I re-ran everything with my own
scripts, my own HTTP client and my own user agent, and separately re-fetched the URLs the
previous agent deleted. Nothing I ran wrote to the archive.

Artefacts I produced:

- `.openclaw/tmp/check-verify/db_state.py` - post-drop DB state, manifest/backup reconciliation
- `.openclaw/tmp/check-verify/indep_live.py` - full independent pass over all 1,270 rows
- `.openclaw/tmp/check-verify/control_check.py` - 3 user agents on the 13 dropped + 5 promoted rows
- `.openclaw/tmp/check-verify/focused.py` / `focused2.py` - close reads of the suspicious rows
- `.openclaw/tmp/check-verify/gh_recheck.py` - GitHub homepage claim, from scratch

## Verdict

**The audit's numbers hold up. The drop is clean and fully reversible. But the audit missed at
least four domains that are now somebody else's spam, and those are still in the archive marked
"active / verified".**

| Check | Result |
|---|---|
| 1,283 rows checked, one by one | confirmed |
| Header counts (LIVE 1267 / DEAD 9 / REPURPOSED 3 / WALLED 4) | confirmed, adds to 1,283 |
| 9 DEAD + 3 REPURPOSED rows deleted | confirmed - all 12 were genuinely dead or repurposed |
| Weaveworks (13th drop) | confirmed - `weave.works` and the stored URL both land on ambking1234.dev (gambling signup) |
| Post-drop DB: 1,270 rows, `integrity_check` ok | confirmed |
| Backups + JSON manifests match the deleted rows | confirmed (1,283 -> 1,271 -> 1,270 across the two backups) |
| 57 github_url / 45 declared homepages / all 45 alive | confirmed, all 45 return HTTP 200 |
| 14 GitHub-only rows | confirmed |
| ~~Repurposed detection complete~~ | **FAILED - see below** |

## Confirmed correct (with the evidence I regenerated)

**The dropped 13 were the right 13.** Re-fetched with Chrome, Firefox and Googlebot UAs:

- Datree 404, IronNet 404 (hard deaths)
- Credy `Welcome to nginx!`, Lula `lula.is`, Pavilion Data `Paviliondata.com for sale`,
  Soylent `soylent.me`, Vidcode `vidcode.io`, Wicked Ride `HugeDomains ... is for sale`
  (parked / for-sale, all served with HTTP 200)
- Rapid Robotics - the stored URL is an `atom.com/name/...` for-sale listing
- Catalia Health -> cakhiazac.tv, Skydrop -> xoilaczbi.tv (Vietnamese football streams),
  Station -> dinosaurcoffee.com (Thai gambling)
- Weaveworks -> ambking1234.dev (gambling signup)

**The 4 remaining WALLED rows are real walls, not deaths.** Magic Eden, SSENSE and UNIQLO returned
403 to both of the auditor's UAs and to mine; nothing else was mislabelled as dead.

**The 5 rows the auditor promoted back to LIVE are correctly promoted.** I reproduced each:
Cloudflare 200/200/200, LeafLink 200/200/200, Product Hunt 403-Chrome but 200-Firefox and
200-Googlebot, NYT 200-Chrome but 403 to the other two, Squire same pattern as Product Hunt.
A 403 is a wall, not a death - that call was right, and I found no row where it was applied
inconsistently.

**The drop itself is textbook.** `PRAGMA integrity_check` = ok, 1,270 rows, all 13 ids gone from
`startups` *and* `verify_log`, backups and per-row JSON manifests present for both passes, and the
manifest rows byte-match what was in the pre-drop backup. The 43 orphan `verify_log` rows
(10 ids) are pre-existing August dedupe cruft, exactly as the previous agent said - not caused by
this work. Only one defect in the archive predates and survives the drop: nothing.

## What the audit missed

The parking scan catches "domain for sale" and "welcome to nginx". It has no check for
*"this page is no longer about the company"*. It found its 3 repurposed rows by hand, and
hand-inspection does not scale - so four more slipped through, and they are still in the DB:

| # | Name | Stored URL | Now serves | Class |
|---|---|---|---|---|
| 1006 | Helium Health | heliumhealthcare.com | `KPKTOTO - Penyeragaman Agen Togel Toto Macau` (Indonesian togel gambling) | REPURPOSED |
| 1260 | Creator | ttoto99.com | `TOTO99: Bandar ... Toto Slot ... Mix Parlay` (Indonesian toto/casino) | REPURPOSED |
| 922 | Oribi | oribi.io | `Best Online Casinos in Canada: Top Sites Compared 2026` (Oribi nav still on the page) | REPURPOSED |
| 1033 | Raise (formerly HelloOffice) | hellooffice.com | Indonesian general-content SEO blog, dated 2026-09-18 | REPURPOSED |

All four answered 200 to all three user agents, and all four are `verified = 1` in the archive
because the app's own verifier only records the HTTP status (`website: HTTP 200`).

Five more are not obviously junk but are no longer the company's own site. These need a human,
not an automatic delete:

| # | Name | Stored URL | What it is now |
|---|---|---|---|
| 726 | Queenly | gritbrokerage.com/inquiry | a domain-broker inquiry page, "Price upon request" |
| 998 | ADVANO | advanotech.com | `Error. Page cannot be displayed. Please contact your service provider` |
| 630 | MyGlamm | myglamm.com | a CIRP insolvency notice for Sanghvi Beauty and Technologies |
| 1157 | SmileDirectClub | smiledirectclub.com | redirects to smileset.com "What Happened to SmileDirectClub?" |
| 1188 | Zenaton | gillesbarbier.dev | the founder's personal consulting site |

Three more are JS "Redirecting..." shells whose destination cannot be confirmed without a browser:
Behalf (923), Hysolate (1043), GirnarSoft (1233).

## Smaller findings

1. **The report is patched, not reproducible.** `audit_report.py` hard-codes the corrections in two
   id-keyed dicts (`PROMOTE_LIVE`, `REPURPOSED`). Re-running the pipeline without those edits
   reproduces WALLED: 8, UNKNOWN: 1 - not the published table. Nothing here is wrong, but the
   report is not a pure function of the data, and the next operator will not know that.
2. **The bot-challenge regex still contains `cloudflare`.** `CHALLENGE_RE` matches "cloudflare"
   anywhere in a title, which is why Cloudflare's own homepage read as a challenge. It was fixed by
   an override entry, not by changing the pattern - so the trap is still loaded for the next run.
   The same regex produced "bot-challenge" on ~250 rows, harmless only because the summariser
   ignores the park field for state.
3. **The 20:10 report is stale against the 20:28 drop.** It still lists Weaveworks as WALLED, and
   its WALLED definition line says "403 to both user agents" for a table that includes a row now
   deleted. Regenerate the MD after the drop, or stamp the drop into it.
4. **Redirect count is hostname-based.** "9 stored URLs redirect to a different domain" counts
   benign moves such as `carrd.co -> carrd.com` and `docs.x -> x`; at registered-domain level
   there are 5. Fine as a table, misleading as a headline number.
5. **Cosmetic:** the earlier 19:25 report is non-ASCII and renders as mojibake in PowerShell
   (`A�`, `�?"`). The 20:10 pass fixed this by forcing ASCII. Keep that rule.

## Bottom line

Method, numbers and cleanup: solid, and the drop is safe. Detection: incomplete. The archive
still advertises four live, "verified" domains that are now gambling or casino spam, plus five
rows that are dead-ish in ways the parking regex cannot see. Recommended: (a) drop the four clear
repurposed rows through the same scripted, backed-up path, (b) queue the five borderline rows for a
human call, (c) add a content check - title vs company name, plus gambling/streaming keyword
detection - to the audit so the next pass finds these on its own.

(a) and (c) were carried out at 21:00-21:10. See Round 2.

---

# Round 2 - the drop and the audit fix (21:00-21:10)

## 1. The four repurposed rows are gone

`.openclaw/tmp/check-verify/drop_repurposed.py` - same shape as the earlier passes: capture fresh
live evidence first, back the DB up, write a per-row manifest, delete from `startups`, `evidence`
and `verify_log`, vacuum, verify. It refuses to delete anything whose evidence does not classify.

| # | Name | Now serves | Class |
|---|---|---|---|
| 922 | Oribi | `Best Online Casinos in Canada: Top Sites Compared 2026` | A:spam-keyword |
| 1006 | Helium Health | `KPKTOTO - Penyeragaman Agen Togel Toto Macau` | A:spam-keyword |
| 1033 | Raise (formerly HelloOffice) | stock WordPress shell, no brand token anywhere | B:content-shell |
| 1260 | Creator | `TOTO99: Bandar ... Toto Slot ... Mix Parlay` | A:spam-keyword |

All four answered 200 to Chrome and Firefox before deletion. Result: 1,270 -> **1,266 rows**,
`integrity_check` ok, all four ids gone from `startups` *and* `verify_log`, backup
`backend/data/ideasexist.db.bak-drop-20260918-205926`, manifest
`dropped-dead-repurposed-20260918-205926.json` (4 startups, 21 verify_log rows, evidence classes
recorded). The 43 orphan `verify_log` rows are the same pre-existing August cruft as before.

## 2. The audit now catches repurposing on its own

Three scripts in `.openclaw/tmp/`:

- **`audit_fresh.py`** captures the signals: `page_spam` (word-bounded keywords, scanned over
  rendered visible text and the title - not raw HTML, so script noise cannot trip it),
  `page_markers` (WordPress / `Sample Page` / skip-to-content), `title_has_brand`,
  `text_has_brand`. New CSV columns. `IDEAEXIST_DB` / `AUDIT_OUT` overrides added.
- **`audit_summarise.py`** decides a new **REPURPOSED** state from two evidence classes:
  - **A** - the page trades in gambling/SEO spam;
  - **B** - a stock WordPress shell still carrying its `Sample Page` artefact, with no token of
    the company name in the title or the page text.

  It also gains a brand-aware challenge guard: a bot-challenge keyword that is the company's own
  name no longer files the row as WALLED. That is finding 2 from the first pass (the Cloudflare
  trap) now fixed at the rule instead of by an id override.
- **`audit_report.py`** drops the hard-coded `REPURPOSED` dict - repurposed rows now come from the
  rules, so the report is a function of the run again. `PROMOTE_LIVE` stays (UA-dependent walls
  are a genuinely different case). `AUDIT_REPORT_DIR` / `AUDIT_STAMP` overrides added so a re-run
  cannot clobber a published report.

Precision matters more than recall when a row can be deleted, so class A is two-tier and
word-bounded. Tier 1 (one hit settles it): `agen togel`, `bandar togel`, `toto slot`, `slot gacor`,
`rtp slot`, `daftar situs`, `link alternatif`, `online casino`, `casino online`,
`best online casinos`, `maxwin`, `sbobet`, `xoilac`, `cakhia`, `bong da`, `truc tiep`, `togel`.
Tier 2 (needs two distinct): `judi`, `bandar`, `situs`, `prediksi`, `bocoran`, `parlay`,
`taruhan`, `kasino`.

That split is not decoration. My first draft used unbounded substrings and flagged Color,
Snap Inc., Bolt, Amino (judi.health), Collective Health and Shipper as gambling sites - `judi`
sits inside "judicial"/"judiciario", and `situs` is Indonesian for "site" (Shipper's page says
"formulir kontak di situs kami"). Word boundaries plus the two-tier test removed every one of
those false positives without losing a single true one.

## 3. Regression proof

The updated pipeline was run end-to-end against the **pre-drop backup** (1,283 rows), i.e. it
scored the exact state the original audit scored:

| Result | Original 20:10 | Regression |
|---|---|---|
| LIVE | 1267 | 1256 |
| DEAD | 9 | 9 |
| REPURPOSED | 3 | 8 |
| WALLED | 4 | 8 |
| UNKNOWN | 0 | 2 |

- The 9 DEAD are the same 9 rows for the same reasons - the parked/404 path is unchanged.
- Three of the 8 REPURPOSED are the earlier agent's hand-found rows (735 Station, 979 Skydrop,
  1262 Catalia Health). The rule rediscovers them unaided - the ad-hoc manual step is now
  automated.
- The other five are the four this pass dropped (922, 1006, 1033, 1260) plus one more below.
- WALLED 8 / UNKNOWN 2 are the usual UA and network variance (403/429 walls, one timeout, one TLS
  reset). `PROMOTE_LIVE` plus the recheck pass handle those, unchanged.
- **No false positives**: all 8 flagged rows were read by hand; every one is genuinely repurposed.

Artifacts: `.openclaw/tmp/check-verify/regression2/` (fresh + states + `liveness-audit-2026-09-18-regression2.md`/`.csv`).

## 4. The new rule immediately found a fifth repurposed row

| # | Name | Stored URL | Now serves |
|---|---|---|---|
| 1014 | Narrator | narratordata.com | a poetry/essay blog carrying posts on Singapore and Danish online casinos |

Title: `Narrator Data - Poetry and Reflections on Modern Life`; the page reads "this breakdown of
each Singapore online casino covers banking, licensing and support" and "Et casino uden licens".
`status=active`, `verified=1`, `last_checked 2026-09-17`. **Not dropped** - it sits outside the
four that were named, so it is yours to call.

## 5. Still open

- **1014 Narrator** - new, unambiguous, awaiting a decision.
- The five borderline rows from the first pass (726 Queenly, 998 ADVANO, 630 MyGlamm,
  1157 SmileDirectClub, 1188 Zenaton) and the three JS redirect shells (923 Behalf, 1043 Hysolate,
  1233 GirnarSoft) remain a human call. Class B will not catch them - they are not stock WordPress
  shells - so they stay on the manual list.
- `backend/data/topstartups_checkpoint.json` still lists the dropped domains. It is a raw
  crawl-URL list (1,258 entries) read by no code - only `docs/codebase-comprehension.md` mentions
  it - so it is provenance, not live data. Left alone deliberately.

---

# Round 3 - one durable script for the whole process (22:40-23:00)

## Why

The pipeline that produced Rounds 1 and 2 lived as three files in `.openclaw/tmp/` plus a one-off
`drop_repurposed.py`. It worked, but the process existed in four places, it was wired to one SQLite
file and one table, `audit_report.py` carried a hand-maintained id dict for the repurposed rows, and
the reasoning behind each rule lived in the head of whoever wrote it. It has been consolidated into
`scripts/site_liveness_audit.py` - one file, 1,927 lines, pure ASCII, stdlib plus httpx (with a
stdlib fallback so it runs anywhere).

It is generic on purpose: this corpus is one source among several we fetch. Sources can be a SQLite
table (any table, any column names), a CSV/TSV, JSON/JSONL, a plain list of URLs, or inline
arguments. The vocabulary is data, so another corpus (piracy-heavy, cyrillic-spam-heavy) is handled
with `--config kw.json` instead of a code edit.

```
python scripts/site_liveness_audit.py selftest
python scripts/site_liveness_audit.py audit --db backend/data/ideasexist.db --out ./audit-out
python scripts/site_liveness_audit.py audit --file other_sites.csv --name-col company --url-col homepage
python scripts/site_liveness_audit.py verify --run ./audit-out/liveness-2026-09-18-2252   # offline
python scripts/site_liveness_audit.py drop   --run ... --db backend/data/ideasexist.db    # dry-run
```

Subcommands: `audit` (capture, classify, recheck, report), `verify` (re-classify a saved run with
zero network), `report`, `drop` (dry-run unless `--confirm`), `print-config`, `selftest`.

## What the script carries that the old pipeline did not

- **The doctrine, in the file.** Each rule has its reason next to it: a 200 is not proof of life, a
  403 is not proof of death, one HTTP client is not evidence, "is it still this company?" is the
  real question, short foreign words are never bare substrings, a company may be named after a CDN,
  scan visible text rather than raw HTML, never delete without a receipt.
- **A self-test that fails when a rule drifts.** 26 fixtures, every one a real case that caused a
  false positive or a false negative. `selftest` exits 4 if any of them stops behaving.
- **An SSRF guard.** URLs come from datasets, so private / loopback / link-local / reserved targets
  are refused before any request (`--allow-private` to override).
- **A capture cache, keyed by URL + user agent.** Re-runs resume; `verify` re-classifies with no
  network at all; a rule fix can be re-applied to an existing run in seconds.
- **Brakes on the delete.** Fresh evidence re-captured at drop time, sqlite backup API (not a file
  copy), manifest written BEFORE the delete, child-table history captured, and a refusal if more
  than `--max-drop-fraction` (25%) of the corpus would go, or if any row no longer demonstrates the
  evidence on re-fetch.
- **Atomic, ASCII reports.** Written temp-then-rename; markdown transliterated to ASCII (the first
  report was UTF-8 and came out mojibake in a PowerShell console); CSV as utf-8-sig for Excel.

## Validation

- `selftest`: 26/26.
- Full live run over the current 1,266-row archive (worker pool 16, ~92s capture + ~128s recheck):
  **LIVE 1242, DEAD 1, REPURPOSED 1, WALLED 4, UNKNOWN 18**.
- `verify` on that run reproduced the classification from the cache with no network.
- Every flag hand-checked with two independent user agents, separately from the classifier:
  - 998 ADVANO (advanotech.com) - HTTP 200, empty title, body "page cannot be displayed / please
    contact your service provider". A bare placeholder. DEAD confirmed.
  - 1014 Narrator (narratordata.com) - HTTP 200, title "Narrator Data - Poetry and Reflections on
    Modern Life", strong hit `online casino`. REPURPOSED confirmed. This is the same row flagged in
    Round 2, now found by rule instead of by hand.
  - The 4 WALLED (Magic Eden, SSENSE, NYT, UNIQLO) are 403 to all three user agents.

## Four precision regressions found while building it (and fixed)

The generic rules reproduced, on 1,266 real pages, every false-positive class the earlier rounds hit
by hand. Each is now a fixture.

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | Deel filed UNKNOWN | "stay tuned" is ordinary marketing copy | placeholder wording counts only as the title, or on a short brandless page |
| 2 | 8 acquisitions filed REPURPOSED | `skip to content` is an accessibility link, not a CMS corpse | class B needs the literal WordPress `Sample Page` artefact, a generic title, and zero brand tokens |
| 3 | Naked Labs filed DEAD | "no longer available" about a discontinued product, on a page whose title is the brand | body-level soft-404 needs a short/titleless page and no brand in the title |
| 4 | Astro, CodeCrafters, Castle, Clerk filed WALLED | bare `cloudflare` / `bot detection` are mentions, not walls | CDN and product names dropped from the vocabulary; a wall phrase must be in the title or on a short page |

Regression 2 is the instructive one: biomodal.com, redhat.com, rewardgateway.com, processunity.com,
dovahealth.ca, cb4.com, aspiretech.us and igniteaccess.com all serve a real company site on the
acquirer's domain. Those are redirects to a new owner, not hijacks - a different category, already
reported by the "redirected off the stored domain" column.

## Still open

- 1014 Narrator: still in the DB, `status=active, verified=1`. Awaiting a decision.
- The five borderline rows from Round 1 (726 Queenly, 998 ADVANO, 630 MyGlamm, 1157 SmileDirectClub,
  1188 Zenaton) - ADVANO is now caught by rule; the other four remain a human call.
- The 18 UNKNOWN are dominated by client-rendered SPAs (empty body, no title) and JS redirect
  shells. An HTTP auditor cannot settle those; they need a browser pass. The tool reports them as
  UNKNOWN rather than guessing, which is the intended behaviour.

---

# Round 4 - the browser pass on the 18 UNKNOWN (23:02-23:15)

## How

Playwright is not installed, so this used the `puppeteer-core` already vendored in
`.openclaw/tmp/browser/` plus the Chrome that is on the machine - no downloads, no project
changes. Each URL was rendered (`networkidle` with a bounded wait, then read), capturing final URL,
title, h1, visible text and the rendered DOM. The rendered captures were then judged by the same
rules as the HTTP pass, so both passes have one source of truth.

## Result

| Result | HTTP pass | After the browser pass |
|---|---|---|
| LIVE | 1242 | 1251 |
| DEAD | 1 | 6 |
| REPURPOSED | 1 | 2 |
| WALLED | 4 | 5 |
| UNKNOWN | 18 | 2 |
| **Total** | **1266** | **1266** |

Nine of the eighteen are simply alive - client-rendered sites the HTTP client saw as an empty body
(Chaldal, Ninjacart, Rupeek, Standard AI, Summersalt, Vivace Therapeutics) plus two acquisitions
forwarding to the acquirer (Hysolate -> Fortinet, Guild Education -> guild.com) and Airbnb's geo
redirect to its own `airbnb.co.in`.

Newly confirmed dead or repurposed, all previously UNKNOWN:

| # | Name | Stored URL | Rendered result |
|---|---|---|---|
| 1009 | goDutch | godutchpay.in | GoDaddy lander at `/lander`: "Related Searches ... Copyright (c) 1999-2026 GoDaddy, LLC" |
| 1274 | Luminostics | cliphealth.com | `cgi-sys/defaultwebpage.cgi` - "Default Web Site Page" |
| 1074 | Run The World | runtheworld.today | `/lander`: "runtheworld.today is parked free, courtesy of GoDaddy.com" |
| 1139 | Tara Intelligence | tara.ai | `/lander`: "tara.ai is parked free, courtesy of GoDaddy.com" |
| 1195 | Templarbit | templarbit.com | `/lander`: "templarbit.com is parked free, courtesy of GoDaddy.com" |
| 923 | Behalf | behalf.com | forwards to headlinelogic.com `?d=behalf.com&pcid=56` - a parked-domain news portal |
| 1038 | Magdrive | magdrive.space | 202 + "Robot Challenge Screen" at `/.well-known/sgcaptcha/` - a wall, not a corpse |

Still UNKNOWN, honestly: **1233 GirnarSoft** (girnarsez.com is behind a Sucuri firewall returning
502 - and that is not even the company's own domain) and **932 Zilingo** (renders `about:blank`).

## Three rule gaps this pass exposed - now fixed and fixtured

1. **Registrar landers that never say "parked".** godutchpay.in/lander carries no forbidden phrase
   at all, only a GoDaddy copyright line. Added lander boilerplate (`courtesy of godaddy`,
   `godaddy, llc`, `get this domain`) and the parking-only URL shapes (`/lander`,
   `cgi-sys/defaultwebpage.cgi`).
2. **SiteGround captcha.** magdrive.space answers 202 with an empty HTTP body, so the HTTP pass saw
   a mysterious LIVE. The rendered page says "Robot Challenge Screen"; that phrase is now a wall
   marker.
3. **Parked-domain monetisation redirects.** behalf.com forwards to a portal with the requested
   domain echoed in the query string. New evidence class **C: monetised-redirect** - parking-network
   parameters (`pcid=`, `d=<domain>`, `brand=<domain>`) plus no token of the company anywhere.

`selftest` is now **30/30**. The three new fixtures are `godaddy-lander`, `siteground-captcha`,
`monetised-redirect`, plus `acquirer-domain-is-not-spam` to keep the acquisition case from being
swept up with them.

## Where the archive now stands (1,266 rows)

LIVE 1251 | DEAD 6 | REPURPOSED 2 | WALLED 5 | UNKNOWN 2.

Reported, not yet actioned: the six DEAD and two REPURPOSED rows above are still in the DB. They are
now all rule-derived, so `drop` can take them with fresh evidence, a backup and a manifest whenever
that decision is made.
