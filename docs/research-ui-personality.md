# UI Personality Research — IdeaExists

*Research date: 2026-08-09. Method: primary-source inspection of live directory/indie sites via a browser (13 sites; several bot-block curl, which is why a browser was used), plus user-voice evidence from Hacker News via the official Algolia API and the sites' own pages. Reddit via PullPush (api.pullpush.io) was attempted but the archive returned HTTP 429 for the whole session — where Reddit sentiment is needed, prior-memo findings are cross-referenced instead of re-cited. Every claim below carries its source; sources that blocked automated access are marked in the Sources section.*

*Companion doc: `research-features-ux.md` (features/UX evidence, same citation scheme). This memo is about personality only — what makes a directory feel human, and how to get there with the current stack (Next.js + shadcn/ui + motion, Plus Jakarta Sans, zinc oklch palette, blue primary, 0.625rem radius).*

## 1. Executive summary — the 8 highest-leverage personality moves

1. **Give the status layer a voice.** The verified/dead/unverified system is the product's soul, and personality-rich directories make their status treatment *the* signature detail: TAAFT ships "This tool has been claimed by its owner." + "Verified author" on every card [1]; killedbygoogle turns death into a theme with tombstones, a guillotine for fresh kills, and "Filter Graveyard List" counts [12]; madeinnigeria stamps projects "ACTIVE" [6]. Move: status pill = dot + label + tooltip microcopy ("A human checked this link on <date> — it's alive"), dead entries styled as an archive, never deleted. *Effort: S. The single highest-ROI move.*
2. **Deterministic-hue initial avatars (and, later, real avatars/favicons).** GitHub's Identicons — "simple 5×5 'pixel' sprites that are generated" deterministically from a user id — exist precisely so faceless entries still get color [21]. Made-in-nigeria uses GitHub avatars on its cards [6]; TAAFT and topstartups use real tool logos [1][5]. IdeaExists already renders initials but in flat `bg-muted` gray [current code: `startup-card.tsx` avatar]. Hashing the name to a hue gives every card a color identity for zero assets, with repo-owner avatars as the M-effort upgrade (GitHub-centric product — the data is right there). *Effort: S.*
3. **Live "curator's desk" counters + freshness stamps.** TAAFT's "196,824 searches today" counter and "Live updating" tab make a directory feel inhabited [1]. IdeaExists already has stats; stamping the grid with "N startups · last checked <date>" and a per-card "Verified <date>" tooltip (already computed: `verified_at`) turns existing data into personality. *Effort: S.*
4. **One signature line + a signed footer.** TAAFT: "The front page of AI." hero, "Used by 90M+ humans." footer, and a founder-signed "PS: We still ship and prune like it's day one. So you get signal, not noise. — Andrei" [1][2]. YC's footer mantra "Make something people want." [4]. The product's core question is "Does this startup exist?" — the signature line writes itself ("A human-kept archive of what exists." / "Checked by a human. Never erased."). *Effort: S (copy only).*
5. **Emoji as a restrained accent system.** TAAFT category tags are emoji-led (🎲 3D objects, 🏠 Floor plans, 🚀 Productivity, 🎨 Graphic design, 🤖 Task automation, 🌐 Websites) [1]; topstartups action links are emoji-led ("See who works here 🤝", "Check company site 📌", "Add Startup or Job 👋") [5]; indiehackers sections ("The Build Board 🪧") [7]; even YC's filter is "💎 Top Companies" [4]. Rule from the evidence: one emoji per concept, in *chips/actions/sections* — never in status pills, where trust semantics live. *Effort: S.*
6. **Editorial typography contrast.** The personality-rich sites pair a workhorse sans with something characterful: YC pairs Outfit with Source Serif 4 on warm off-white [4]; svgl runs Geist + GeistMono on oklch dark [9]. IdeaExists already defines `--font-heading` in tokens but maps it to the body sans [current code: `globals.css`]. Pointing it at a display face (a grotesque like Space Grotesk/Archivo, or a serif) + using `--font-mono` (already wired to Geist Mono) for "evidence" data (stars, dates, check counts) is the cheapest way to stop looking like a default shadcn page. *Effort: S.*
7. **Background texture instead of flat zinc.** madeinnigeria's hero has a low-opacity dot/dash globe pattern [6]; lowtechmagazine's dithered images and "Page Size: 483.60 KiB" footer [15]; 1mb.club's retro badges [13]. A CSS-only dot-grid/paper-grain on the page background (or hero only) removes the "empty template" feel without any asset pipeline. *Effort: S (CSS `radial-gradient` / SVG noise).*
8. **Motion with restraint: stagger-in, hover lift, and one marquee.** TAAFT's feed is "Live updating" [1]; terminal.shop highlights the active line in orange [10]; svgl cards reveal action icons on hover [9]. For IdeaExists: entrance stagger for the card grid (motion), a subtle hover lift, and one signature motion — e.g. the "Just added" strip as a gentle marquee — is enough. Everything else is noise. *Effort: S–M.*

**What to avoid (evidence-backed):** ad-like clutter — users explicitly punish spammy directories [prior memo 17]; "quirky at the expense of trust" — the personality must never joke *about the entries* (killedbygoogle jokes about Google's graveyard, not about the dead products' users [12]); and unpolished search/mobile UX reads as broken, not charming — TAAFT's own launch thread flagged back-button breakage and slow search [3].

## 2. Evidence table

| # | Finding | Where it comes from (product/source) | Source URL | Relevance to IdeaExists |
|---|---------|-------------------------------------|-----------|-------------------------|
| 1 | TAAFT hero + footer: "The front page of AI." / "Used by 90M+ humans."; live counter "196,824 searches today"; "Live updating Today 11" tab; search placeholder "Search..." + Ctrl+K | TAAFT homepage (live fetch) | https://theresanaiforthat.com/ | A one-line claim + a live number + a freshness tab = "inhabited" feel. IdeaExists already has stats; stamp them. |
| 2 | TAAFT card trust layer: "This tool has been claimed by its owner."; "Verified author" + country flag + @handle; emoji category tags (🎲 🏠 🚀 🎨 🤖 🌐); pricing "$15.92 /mo" | TAAFT homepage (live fetch) | https://theresanaiforthat.com/ | Card-level human voice: claim badge, verified-author line, emoji tags. Maps to IdeaExists' status pill + category chips. |
| 3 | TAAFT curation copy: "No hype, no vaporware."; "Our promise: practical discovery, transparent curation."; "We routinely re-test links, refresh descriptions, and retire defunct entries."; founder-signed "PS: We still ship and prune like it's day one. So you get signal, not noise. — Andrei"; "Last updated: July 2026" | TAAFT About page (live fetch) | https://theresanaiforthat.com/about/ | Blueprint for IdeaExists' "how we verify" blurb: promise + process + signed note + last-updated stamp. Founder sign-off is a personality move, not a formality. |
| 4 | TAAFT founder's voice on HN launch: "There is no AI for porn (for now)" (reply to a commenter); launch feedback: "Awesome collection. Found quite a few I had no clue it existed" but also back-button breakage, slow search, broken mobile search | HN Show HN thread (via Algolia API) | https://news.ycombinator.com/item?id=34069825 | Witty founder voice is welcomed in this genre; but search/mobile bugs are judged harshly — personality must sit on a solid base. |
| 5 | YC directory: "💎 Top Companies" emoji filter; editorial typography (Outfit + Source Serif 4) on warm off-white rgb(245,245,238); footer mantra "Make something people want."; numbers-led intro ("5,000 companies… over $1T") | YC Startup Directory (live fetch) | https://www.ycombinator.com/companies | Even the archetypal VC directory uses an emoji and a mantra. Serif+grotesque pairing = the "editorial" personality shortcut. |
| 6 | madeinnigeria.dev: hero "A curation of awesome tools and projects built by Nigerian developers."; teal hero with low-opacity dot/dash globe pattern; cards with GitHub avatar, stars, language, "ACTIVE" status; "Built by Nigerians, for the Rest of the World." section; community interviews ("Creators") | madeinnigeria.dev (live fetch) | https://madeinnigeria.dev/ | Closest genre cousin (made-in-X directory). Avatar + stars + status row is the exact card anatomy IdeaExists has; the hero pattern + community-as-content are the personality layer. |
| 7 | topstartups.io: emoji action links on every card ("See who works here 🤝", "Check company site 📌", "Read reviews ⭐"); "📍HQ: Brooklyn, New York, USA" facts; newsletter CTA "Get newly funded startups delivered to you weekly" + button "Try it"; "Add Startup or Job 👋" in footer | topstartups.io (live fetch) | https://www.topstartups.io/ | Emoji as action-link affordance; friendly newsletter CTA; "Add … 👋" framing for the admin inbound channel. |
| 8 | indiehackers.com: "The Build Board 🪧" + "A daily leaderboard of build-in-public posts."; "Jobs for industrious indie hackers."; "In Case You Missed It"; raw human post titles ("Co-founders suck…", "I tracked my time for 14 days. The result was embarrassing.") | indiehackers.com (live fetch) | https://www.indiehackers.com/ | Section naming with emoji + wit; the community's own voice (raw titles) carries the personality — the curator just frames it. |
| 9 | finddev.tools: "Where developers go for tools" headline; intentionally neutral layout so the *listed tools' own brand colors* carry the page | finddev.tools (live fetch) | https://finddev.tools/ | Counter-pattern: neutrality is a choice. If IdeaExists wants the *entries* to be the color, keep the shell calm (favicon/logo cards later). |
| 10 | svgl.app: dark oklch canvas as a stage for colorful logos; category counts in nav ("AI 67", "Software 283"); "Sponsor me on GitHub" + "View on GitHub (5,000 stars)" inline in header; hover reveals per-card actions (copy/download/favorite) | svgl.app (live fetch) | https://svgl.app/ | Logo-as-card-header pattern (favicon grids); indie personalization ("Sponsor me"); counts as scannable personality. |
| 11 | terminal.shop: entire page styled as a terminal — line numbers, "# use the command below to order your delicious whole bean coffee", "ssh terminal.shop", email input placeholder "# sign up for updates, enter your email address below...", orange active-line highlight, nav as tabs (cron/api/readme/faq) | terminal.shop (live fetch) | https://terminal.shop/ | Full-commitment theme: even the nav and the email form speak the theme. The "detective/terminal" direction in miniature. |
| 12 | HN reaction to terminal.shop: "I don't drink coffee, but what an interface!"; "They know how to appeal to their target market!" | HN thread (via Algolia API) | https://news.ycombinator.com/item?id=40208417 | Proof that interface personality is *the* talking point — people share a UI for its vibe, not its features. |
| 13 | killedbygoogle.com: "Google Graveyard"; tombstone icons per entry; guillotine icon for recently killed; "Filter Graveyard List" with counts ("All (307)", "Apps (68)", "Services (215)", "Hardware (24)"); category label + name + date per row | killedbygoogle.com (live fetch) | https://killedbygoogle.com/ | The canonical "dead entries are first-class citizens" directory. Death as a *theme* (iconography + filter language), which is exactly IdeaExists' dead-never-deleted stance made visual. |
| 14 | 1mb.club: "1MB Club is a growing collection of performance-focused web pages weighing less than 1 megabyte."; "Help keep the lights on! Contribute directly to hosting and domain renewal costs!"; "Supporters of a leaner web!"; retro clickable HTTP badges; table of URL + size | 1mb.club (live fetch) | https://1mb.club/ | Honesty-as-personality: the ethos (small pages) is the brand; funding asks are candid ("keep the lights on"); community identity ("Supporters of a leaner web!"). |
| 15 | 512kb.club: "The 512KB Club is an exclusive list of web pages weighing less than 512 kilobytes."; blunt tagline "The internet has become a bloated mess." | 512kb.club (fetched raw HTML) | https://512kb.club/ | Blunt, opinionated one-liners give a directory a point of view. "The internet has become a bloated mess." is a brand stance in five words. |
| 16 | lowtechmagazine.com: header badge "This is a solar-powered website, which means it sometimes goes offline" + live "Battery used 56%"; footer "Page Size: 483.60 KiB", "Server Stats", "Forecast" | solar.lowtechmagazine.com (live fetch) | https://solar.lowtechmagazine.com/ | The strongest honesty-as-design example: the site's constraints (solar power, small pages) are displayed as live status. A local-first directory can do the same ("runs 100% in your browser — nothing leaves it"). |
| 17 | usesthis.com: "Uses This is a collection of nerdy interviews asking people from all walks of life what they use to get the job done."; "buying me a coffee!" link; hand-made dark purple-gray + purple links, system-ui | usesthis.com (live fetch) | https://usesthis.com/ | One honest adjective ("nerdy") + a self-deprecating support link = personality without any design system investment. |
| 18 | Product Hunt (Wayback): "Top Products Launching Today" ranked list; "Promoted" label on ads; playful taglines ("Wild Pokémon appear while you wait for Claude Code"); emoji-heavy first-person launch posts; "Get the best of Product Hunt, directly in your inbox." | Product Hunt via Wayback snapshot 2026-08-03 (live blocked by Cloudflare) | https://www.producthunt.com/ | Launch-post voice is first-person + emoji + story; "Promoted" labeling keeps ads honest (IdeaExists: none, but the labeling *pattern* shows how to handle any sponsored slots later). |
| 19 | HN: "The modern web is the most efficient version of itself that has ever existed… By every measurable metric, the web in 2023 is the best the web has ever been. And most of it is unbearable." — the demand-side case for personality; commenter: "Funny how the article was published on one of the most esthetically neutral website I have ever seen."; other commenters point to Mmm/Kinopio as personality antidotes | Tim Kicker essay + HN thread (article fetch + Algolia API) | https://tim.kicker.dev/2023/07/25/beautiful-internet/ and https://news.ycombinator.com/item?id=36873312 | Direct user-voice: efficiency without personality reads as "soulless"; the ironic comment about the neutral site design is a warning for clean-but-cold implementations. |
| 20 | HN 404-page appreciation: "Mint.com turns 404 ad page into date ad for developer" (672 pts), "The Financial Times' 404 page" (609 pts), "Bernie Sanders' 404 page" (434 pts) | HN stories (via Algolia API) | https://news.ycombinator.com/item?id=3322561, https://news.ycombinator.com/item?id=28980927, https://news.ycombinator.com/item?id=10122656 | Playful empty/error states are among the most-liked personality artifacts in the genre's history — the "no results" state is a free personality slot. |
| 21 | GitHub Identicons: "GitHub is about to get a lot more colorful. Starting today, we are generating Identicons for anyone without a Gravatar: Our Identicons are simple 5×5 'pixel' sprites that are generated…" (deterministic per user); endpoint verified live (200, image/png) | GitHub Blog post (fetched) + endpoint check | https://github.blog/2013-08-14-identicons/ | The original deterministic avatar pattern; grounds the "hash name → hue" initials upgrade and the later repo-avatar/favicon path. |
| 22 | Brutalism exists as a recognized aesthetic with a reference gallery; HN users ask for "inspired web designs that aren't overdone, but also not overly-brutalist" — i.e., a middle path between generic and shouty | brutalistwebsites.com (fetched) + HN Ask (via Algolia) | https://brutalistwebsites.com/ and https://news.ycombinator.com/item?id=26093217 | Calibrates how far to push: personality stops where legibility/trust start. The sweet spot is "characterful but composed". |
| 23 | YC + madeinnigeria + topstartups all use real logos/avatars as the card identity; svgl builds the whole page on logos; only IdeaExists-class minimal cards use initials | Synthesis of rows 1, 5, 6, 7, 10 (all live) | see rows above | For a GitHub-centric directory, repo-owner avatars (madeinnigeria pattern) are the credible upgrade; deterministic-hue initials are the zero-asset interim. |
| 24 | TAAFT's "This tool has been claimed by its owner." shows claim/verification as *visible card copy*, not hidden metadata | TAAFT homepage (live fetch) | https://theresanaiforthat.com/ | IdeaExists' "Verified <date>" tooltip is currently invisible on the card; promoting it to a visible, worded signal ("A human checked this on <date>") is a trust + personality double win. |

## 3. Voice & microcopy — what personality-in-copy looks like in this genre

### 3.1 Quotable examples (all captured from the live sources above)

Hero / identity lines:
- "The front page of AI." / "Used by 90M+ humans." — TAAFT hero + footer echo [1]
- "A curation of awesome tools and projects built by Nigerian developers." — madeinnigeria [6]
- "Where developers go for tools" — finddev.tools [8]
- "Uses This is a collection of nerdy interviews asking people from all walks of life what they use to get the job done." — usesthis [16]
- "1MB Club is a growing collection of performance-focused web pages weighing less than 1 megabyte." — 1mb.club [13]

Stance / opinion lines:
- "The internet has become a bloated mess." — 512kb.club [14]
- "No hype, no vaporware." — TAAFT curation promise [2]
- "Make something people want." — YC footer mantra [4]
- "Supporters of a leaner web!" — 1mb.club community identity [13]

Honesty / constraint lines:
- "This is a solar-powered website, which means it sometimes goes offline" + "Battery used 56%" — lowtechmagazine [15]
- "Help keep the lights on! Contribute directly to hosting and domain renewal costs!" — 1mb.club [13]
- "PS: We still ship and prune like it's day one. So you get signal, not noise. — Andrei" — TAAFT founder sign-off [2]
- "Last updated: July 2026" — TAAFT About [2]

Card / status microcopy:
- "This tool has been claimed by its owner." — TAAFT [1]
- "Verified author · Country: United States · @crisp3d" — TAAFT [1]
- "See who works here 🤝" / "Check company site 📌" / "Read reviews ⭐" — topstartups [5]
- "📍HQ: Brooklyn, New York, USA" — topstartups [5]

Section / button microcopy:
- "The Build Board 🪧 — A daily leaderboard of build-in-public posts." — indiehackers [7]
- "Jobs for industrious indie hackers." — indiehackers [7]
- "Get newly funded startups delivered to you weekly" + button "Try it" — topstartups [5]
- "Get the best of Product Hunt, directly in your inbox." — Product Hunt [17]
- "Filter Graveyard List" + "All (307)" — killedbygoogle [12]
- "# use the command below to order your delicious whole bean coffee" / "# sign up for updates, enter your email address below..." — terminal.shop [10]

Founder voice (user-visible):
- "There is no AI for porn (for now)" — TAAFT founder on HN [3]
- "Wild Pokémon appear while you wait for Claude Code" — PH launch tagline [17]

### 3.2 A consistent voice around "Does this startup exist?"

The product's question maps naturally onto a **curator/archivist** persona (the app is the archive; the single admin is "the curator"). Draft voice system, built only from the patterns above:

- **Search placeholder:** "Search the archive…" or "Type a name — we'll check our files" (mirrors TAAFT's "Search..." + Ctrl+K affordance [1], with a detective twist).
- **Hero line:** "A human-kept archive of what exists." (echo of TAAFT's one-line claim [1] + madeinnigeria's "curation of awesome tools" [6]).
- **Footer mantra + sign-off:** "Dead is a status, not an erasure." + "Kept by a human. Checked weekly. — The Curator" (mirrors YC mantra [4] + TAAFT signed PS [2]).
- **Verified tooltip:** "A human checked this link on <date>. It's alive." (worded version of TAAFT's claim badge [1]; `verified_at` already exists in the data model).
- **Dead pill tooltip:** "Checked 3 times, link dead each time. Filed, never deleted." (3-strikes rule as copy — killedbygoogle's whole premise [12]).
- **Empty state:** "Nothing in the archive matches. Want it added? Ask the curator." (TAAFT's "No AI tools match these filters" + "Clear filters" [prior memo 8] with voice; 404-personality precedent [20]).
- **"How we verify" blurb:** mirror TAAFT's promise structure — "No hype, no vaporware. Manual vetting, clear labeling, relentless pruning." → "Human review, weekly link checks, 3 strikes to Dead, nothing ever deleted." [2].

### 3.3 How far is too far? (evidence)

- **Personality is wanted:** the "soulless internet" essay + thread is the demand-side proof; "most of it is unbearable" despite perfect efficiency [18][19]. Playful 404s are some of the highest-voted HN personality artifacts ever [20].
- **Personality sells the interface itself:** terminal.shop's only memorable feature is its UI ("what an interface!") [11].
- **But the trust layer is sacred.** The genre's users are skeptical of directories (prior memo rows 23: "is it worth it?" threads). The safe boundary, visible across all sources: **joke about the curator's process, never about the entries.** killedbygoogle mocks Google, not the products' users [12]; TAAFT's "no AI for porn (for now)" is self-deprecating, not about any listed tool [3]. For IdeaExists: witty about the archiving ritual, deadpan-serious about verification facts. A "funny" Dead pill at the expense of a founder whose startup died would read as cruelty in a community that mourns its graveyard (killedbygoogle's tone is solemn-with-wry-icons, not mockery [12]).
- **Unpolished basics read as broken, not quirky:** TAAFT's launch thread punished back-button and mobile search bugs even while loving the product [3]. Personality is the last coat of paint, not the foundation.

## 4. Signature moves for directory cards & lists

**Status as dot + label (recommended over pill-only):** madeinnigeria prints "ACTIVE" [6]; killedbygoogle's whole card is a category + name + date with theme icons [12]. IdeaExists' `StatusPill` already exists — adding a 6px dot (emerald / red / gray) and moving the "Verified <date>" into a worded tooltip matches the genre's best examples without losing scannability [1].

**Initials avatar with deterministic hue (S) → repo-owner avatar (M) → favicon/logo (L):**
- All logo-rich directories (TAAFT [1], topstartups [5], svgl [9]) use real logos; GitHub-centric madeinnigeria uses GitHub avatars [6]; GitHub's Identicons are the canonical deterministic-color answer for faceless entries [21]. IdeaExists' flat-gray initials are the one place it looks more "template" than any of its analogues.
- Implementable: hash name → hue (e.g. `hsl(hash % 360 60% 45%)`), white initials, keep `rounded-md`; next step, use the GitHub repo owner's avatar URL when present (data already GitHub-centric); final step, Google favicon service / `https://www.google.com/s2/favicons?domain=...` for the website field (svgl-style logo card [9]). All three are drop-in `AvatarFallback` → `AvatarImage` swaps.
- Founder-photo vs monogram debate: in this genre, *logos/avatars win* because cards are scanned, not read — svgl builds its entire grid on logos [9] and madeinnigeria's cards are avatar-led [6]; monograms only read as intentional when they carry color (the hue fix) or when they're the brand (usesthis's lowercase wordmark [16]).

**Favicon/logo-driven card headers:** svgl builds its entire grid on logos against a dark canvas [9]; TAAFT and topstartups put the logo top-left of every card [1][5]. This is the "browserless/raycast-style bookmark grid" pattern; svgl is the verified live instance. For IdeaExists: treat the avatar slot as the future logo slot, size it ~h-8/h-10, and don't let any other card element out-shout it (finddev.tools shows what happens when the shell is neutral — the logos become the color [8]).

**What feels cloying/overdone (from the evidence):** emoji in *status* contexts (would blur trust semantics — every personality-rich source keeps statuses word-only or icon-only: ShieldCheck/Archive in IdeaExists today; "ACTIVE" plain in madeinnigeria [6]; tombstones in killedbygoogle are the *theme*, not per-card emoji [12]); more than one emoji per chip/action (topstartups and TAAFT consistently use exactly one [1][5]); and anywhere a personality flourish slows scanning — the genre's users punish clutter explicitly [prior memo 17].

## 5. Local-first / honesty as personality

The product's differentiators (no accounts, no tracking, human verification, dead entries kept visible) are personality assets — the strongest sources in this genre are honest about *their own constraints*:

- **Constraint as live status:** lowtechmagazine shows "This is a solar-powered website, which means it sometimes goes offline" + battery % in the header and "Page Size: 483.60 KiB" + "Server Stats" in the footer [15]. The local-first analogue: a persistent line like "Runs in your browser. No accounts. No tracking. Your searches never leave this tab." — the honest-UI equivalent of TAAFT's "Free mode" toggle [1].
- **Ethos as brand:** 1mb.club/512kb.club turned "small pages" into a club with an "exclusive list" and a blunt stance ("The internet has become a bloated mess.") [13][14]. IdeaExists' stance is equally punchable: "Every listing is checked by a human, not a crawler." / "3 strikes and it's Dead — but it's never deleted."
- **Graveyard as a feature:** killedbygoogle made death the product [12]; TAAFT's curation promise is explicit about retiring defunct entries [2]. IdeaExists' "Dead recently" strip is already this pattern; giving it theme (archive styling, "kept for the record" microcopy, the 3-strikes explainer in the detail modal) turns honesty into identity.
- **Verification as a design element:** TAAFT's "claimed by its owner" and "Verified author" are visible card copy, not metadata [1]; madeinnigeria stamps ACTIVE [6]. Surface `verified_at`, the check-count, and the dead-reason on the card/detail — the previous memo's P0 items, restated here as *personality* because they are also the brand.
- **Candid funding/asks:** "Help keep the lights on!" [13] and "Sponsor me on GitHub" [9] show the genre's acceptable way to ask — direct, personal, and tied to a human behind the site. If IdeaExists ever adds a "buy the curator a coffee" link, that's the register.
- **No-tracking as a *stated* pitch, done tastefully:** the prior memo documented "No ads, no paywall, no tracking." as a proven Reddit pitch [prior memo 22]; the tasteful UI version is one calm line in the footer/hero (lowtechmagazine's register [15]), not a popup.

## 6. Component-level implementation map (stack: shadcn/ui + motion, Next.js)

| Move | Component(s) | Implementation | Effort |
|------|-------------|----------------|--------|
| Display font for headings | `globals.css` tokens + `layout.tsx` | Point `--font-heading` (already defined, currently = sans) at a display face (Space Grotesk/Archivo grotesque, or a serif for "archive" feel); apply `font-heading` to hero + card titles | S |
| Mono for "evidence" data | `startup-card.tsx`, `startup-detail.tsx` | `--font-mono` (Geist Mono already wired) for stars, dates, "checked <date>", GitHub links | S |
| Deterministic-hue initials | `Avatar`/`AvatarFallback` in `startup-card.tsx` | `lib/utils.ts` helper: hash(name) → HSL; `bg-[hsl(...)]` + white text; keep `rounded-md` | S |
| Status dot + worded tooltip | `StatusPill` (`startup-card.tsx`), `Tooltip` (already in ui/) | 6px dot (emerald/red/gray) + `Tooltip` with "A human checked this link on <date>" / "Checked 3 times, link dead each time. Filed, never deleted." | S |
| Hero one-liner + sub-line | `app/page.tsx` hero block | Copy swap + maybe a `motion` fade-up; add live "N startups · last checked <date>" from existing `stats` | S |
| Footer mantra + signed note | footer in `app/page.tsx` | "Dead is a status, not an erasure." + "Kept by a human. Checked weekly. — The Curator" | S |
| Emoji accent system | `Badge` chips, `Button` links, strip headers (`home-sections.tsx`) | One emoji per category chip/action, e.g. strip headers "🆕 Just added", "✅ Recently verified", "⚰️ Dead recently" (or keep chips clean, emoji only in strips/actions) | S |
| Background texture | `app/globals.css` body/hero | CSS dot-grid (`radial-gradient` dots) or SVG noise at ~2–3% opacity on the page background or hero only; dark mode variant | S |
| Hover lift + entrance stagger | Card grid (`app/page.tsx` + `startup-card.tsx`) | `motion.div` per card: `initial={{opacity:0, y:8}} animate` with stagger; `whileHover={{y:-2}}` | S–M |
| Marquee strip | `home-sections.tsx` "Just added" | CSS keyframes marquee (pause on hover) — one signature motion only | S–M |
| Graveyard treatment for dead cards | `startup-card.tsx` (currently `opacity-60`), `home-sections.tsx` | Sepia/desaturate + "filed" styling instead of plain fade; "Dead recently" strip gets archive iconography (killedbygoogle register [12]) | S |
| Empty state with voice | no-results branch in `app/page.tsx` | "Nothing in the archive matches. Want it added? Ask the curator." + "Clear filters" (404-personality precedent [20]) | S |
| Verification history in detail modal | `startup-detail.tsx` | Timeline of checks ("2026-07-14 ✓ alive · 2026-07-21 ✓ alive · 2026-07-28 ✗ → strike 1…") using existing check data; TAAFT's "re-test links, refresh descriptions, and retire defunct entries" is the canonical promise to echo [2] | M |
| Repo-owner avatar / favicon logos | `AvatarImage` in `startup-card.tsx` | GitHub owner avatar when repo present; fallback to hue-initials; later Google favicon service for website field (svgl pattern [9]) | M |
| Live "curator's desk" counters | `home-sections.tsx` / hero | "N startups · X verified · Y dead" from `stats`; "searches today" needs a tiny local counter (optional, local-only per privacy stance) | S–M |
| Custom cursor / mascot / full terminal theme | global | **Flag as heavy:** none of the cited products need one; terminal.shop is a *whole-site* theme, not a component [10]. Defer unless a signature direction demands it | L |

**Cheap vs heavy:** everything above except mascots/illustrations, a full theme, and real logo fetching is CSS/typography/copy/motion — S-effort. The one M-effort item that compounds everything is the avatar→logo path, because it's the difference between "initials grid" and "directory of *things*" (svgl [9], finddev's neutrality note [8]).

## 7. Signature directions — three coherent options

**A. "The Warm Archivist"** (best fit for the honesty core; recommended)
- *Concept:* the product is a hand-kept card catalog; the admin is "the Curator".
- *Type:* body sans stays (Plus Jakarta Sans); headings → an editorial serif (Source Serif 4 is the genre-proven pairing [4]); evidence data (stars, dates, checks) in mono.
- *Color:* warm paper background (zinc → warm off-white like YC's rgb(245,245,238) [4]); blue primary kept for actions; statuses get stamp colors — verified = stamp green, dead = sepia, unverified = gray.
- *Texture:* dot-grid paper background (madeinnigeria pattern [6]), slight noise; cards as index cards with a hairline border.
- *Motion:* entrance stagger like cards being filed; hover lift; "recently verified" strip as a gentle ticker.
- *Copy:* all of section 3.2 verbatim; footer "Kept by a human. Checked weekly."; dead tooltip "Filed, never deleted."
- *Micro-interactions:* status pill tooltips ("A human checked this on <date>"); the detail modal opens like a dossier (staggered sections); a small "stamp" animation (scale+brief rotate) when you mark verified in admin.

**B. "Terminal Detective"** (for a hacker/indie audience)
- *Concept:* the archive is a case file; "does this startup exist?" is an investigation.
- *Type:* mono-forward (Geist Mono for almost everything), headings in mono with `#` comment styling (terminal.shop's exact move [10]).
- *Color:* near-black canvas, one accent (orange active-line [10] or amber — TAAFT's yellow-on-navy accent [1]); statuses as glyphs: `● alive`, `▲ at-risk`, `✕ dead`.
- *Texture:* subtle scanline/noise; terminal header strip with fake file path (`~/archive/startups/`).
- *Motion:* cursor blink on the search field; "checking…" typewriter states during verification; dead entries dimmed like closed cases.
- *Copy:* "Running checks…", "3 failed checks → filed as DEAD", "Search the archive:"; empty state "No records match. Open a new case?"
- *Micro-interactions:* search placeholder reads like a prompt; admin "mark verified" echoes a terminal confirm (`[y/n]`).
- *Risk:* full commitment is L-effort; the safe version is *accent-only* (mono labels + status glyphs) on the current layout — S.

**C. "Indie Zine"** (most playful; highest personality ceiling, highest over-do risk)
- *Concept:* a one-human postcard/zine; stickers, stamps, marquees.
- *Type:* big display grotesque headings; body stays readable sans.
- *Color:* keep zinc but add one loud accent pair (e.g. TAAFT yellow [1] + ink); statuses as sticker-style badges with a 1–2° rotation.
- *Texture:* paper grain; hand-drawn borders (SVG or `border-image`) sparingly — section dividers, not cards.
- *Motion:* marquee strips (Just added), sticker "pop" on verified, hover wiggle on the logo.
- *Copy:* "The Build Board 🪧" register [7]; "Hot off the press: 3 new startups"; footer "Made by one human, for humans."
- *Micro-interactions:* 🎉 toast on admin verification; confetti-free (cheap restraint); emoji in strip headers only.
- *Risk:* the evidence's overdone-list (row 22) sits closest to this direction — apply to strips/hero only, keep cards scannable.

**Recommendation:** A (Warm Archivist) as the base — it makes the trust story literal and needs almost no visual risk — with B's status glyphs and C's marquee strip as the two borrowed accents. All three share the same S-effort foundation (typography, hue avatars, status voice, copy), so the choice is mostly about how loud to go afterwards.

## 8. Sources

1. There's An AI For That — homepage (hero, counters, emoji tags, claim badge; live fetch 2026-08-09): https://theresanaiforthat.com/
2. There's An AI For That — About (curation promise, founder sign-off, "Last updated"; live fetch): https://theresanaiforthat.com/about/
3. HN "Show HN: There's an AI for That" (founder replies incl. "no AI for porn (for now)", launch UX complaints; via Algolia API): https://news.ycombinator.com/item?id=34069825
4. Y Combinator Startup Directory (💎 filter, serif+sans pairing, footer mantra; live fetch): https://www.ycombinator.com/companies
5. topstartups.io (emoji action links, 📍HQ facts, newsletter CTA; live fetch): https://www.topstartups.io/
6. madeinnigeria.dev (hero copy, dot pattern, ACTIVE stamps, GitHub avatars; live fetch): https://madeinnigeria.dev/
7. Indie Hackers (Build Board 🪧, "industrious indie hackers", "In Case You Missed It"; live fetch): https://www.indiehackers.com/
8. finddev.tools ("Where developers go for tools", neutral-canvas pattern; live fetch): https://finddev.tools/
9. svgl.app (logo-grid, category counts, "Sponsor me on GitHub", GitHub stars inline; live fetch): https://svgl.app/
10. terminal.shop (full terminal theme, comment-style microcopy; live fetch): https://terminal.shop/
11. HN "ssh terminal.shop" (interface-love comments; via Algolia API): https://news.ycombinator.com/item?id=40208417
12. Killed by Google (graveyard theme, guillotine icon, filter counts; live fetch): https://killedbygoogle.com/
13. 1MB Club (honesty copy, "keep the lights on", HTTP badges; live fetch): https://1mb.club/
14. 512KB Club ("The internet has become a bloated mess."; fetched raw HTML): https://512kb.club/
15. LOW←TECH MAGAZINE (solar-powered badge, battery %, page-size footer; live fetch): https://solar.lowtechmagazine.com/
16. Uses This ("nerdy interviews", "buying me a coffee!"; live fetch): https://usesthis.com/
17. Product Hunt — homepage via Wayback snapshot 2026-08-03 (ranked list, "Promoted", launch-post voice; live site blocked by Cloudflare): https://www.producthunt.com/ (snapshot: https://web.archive.org/web/20260803145507/https://www.producthunt.com/)
18. Tim Kicker, "The internet has become soulless and i hate it" (article fetch): https://tim.kicker.dev/2023/07/25/beautiful-internet/
19. HN "The internet has become soulless and I hate it" (thread comments; via Algolia API): https://news.ycombinator.com/item?id=36873312
20. HN 404-page personality threads (via Algolia API): https://news.ycombinator.com/item?id=3322561 (Mint.com date-ad 404), https://news.ycombinator.com/item?id=28980927 (FT 404), https://news.ycombinator.com/item?id=10122656 (Bernie Sanders 404)
21. GitHub Blog, "Identicons!" (deterministic 5×5 sprites; fetched): https://github.blog/2013-08-14-identicons/ — endpoint verified live: https://avatars.githubusercontent.com/u/1?size=1 returns 200 image/png
22. Brutalist Websites (reference gallery; fetched): https://brutalistwebsites.com/
23. HN "Ask HN: Inspired web designs that aren't overdone, but also not overly-brutalist" (via Algolia API): https://news.ycombinator.com/item?id=26093217

**Sources that blocked automated access (used alternatives or omitted):**
- producthunt.com (live) — Cloudflare "Just a moment…" challenge; a Wayback Machine snapshot (2026-08-03) was fetched instead [17].
- theresanaiforthat.com/inactive-ais/ — Cloudflare challenge on that specific path (homepage and /about/ fetched fine); the "retire defunct entries / Inactive" curation stance is therefore cited from the About page [2] instead of the dedicated section.
- reddit.com — bot gate (known from the prior memo); PullPush (api.pullpush.io) was attempted for fresh Reddit sentiment (r/webdev, r/Design, r/InternetIsBeautiful) but returned HTTP 429 for the entire session — Reddit-derived claims in this memo are limited to cross-references of the prior memo's verified rows rather than new ones.
- raindrop.io and raycast.com/store — client-rendered; the favicon-grid pattern could not be verified in raw HTML, so the logo-grid claim rests on svgl/TAAFT/topstartups, which were verified live [9][1][5].

## 9. Open questions (for the product owner)

1. **How loud?** The three directions (archivist / terminal detective / zine) are all S-effort to start but diverge fast. Which audience does IdeaExists court — HN/indie hackers (B register) or general founders (A register)? The copy in section 3.2 is written for A; B would rewrite placeholders as prompts.
2. **Dead entries: honor or spectacle?** killedbygoogle [12] shows death can be a *theme*; but IdeaExists' dead entries are real people's projects. Should "Dead recently" get graveyard iconography (C register) or quiet archival styling (A register)? Recommendation: A — file, don't mock.
3. **Avatar upgrade path:** deterministic-hue initials (S) → GitHub owner avatars (M) → favicon/logo cards (L, svgl-style [9]). Is the logo path worth the fetching/caching work now, or after the dataset grows?
4. **Counters:** "searches today" (TAAFT [1]) is a lovely live number but implies tracking — a local-first counter is fine (never leaves the tab) but do we want to imply "everyone is searching" on an honesty-first product? Alternative: "X startups · Y verified · Z dead", all from existing stats.
5. **The signed footer:** TAAFT signs "— Andrei" [2]. Is the single admin comfortable being publicly "the Curator" with a name attached? It's the strongest trust signal available and costs nothing.
