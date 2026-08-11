# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### UX — correctness & accessibility

- **Pagination shows the page it means.** The control now takes the clamped page (`currentPage`), so a deep link like `?page=999` renders the real last page with the active pill and `aria-current` instead of a dead control.
- **Detail modal traps focus and Escape works everywhere.** Tab/Shift+Tab cycles inside the dialog (it used to walk out into the footer); Escape is handled at document level so it closes even after focus escapes; focus returns to the triggering card on close (WCAG 2.4.3).
- **The "More" categories dropdown has keyboard parity** — Escape closes and returns focus, ArrowUp/Down cycle the items (WCAG 2.1.1).
- **Admin section headers collapse** instead of teleporting the view to Seeding.
- **Read-only status pills are buttons now** — keyboard- and touch-reachable, opening a popover with the worded hint + how verification works (the old span-tooltip was unreachable).
- **Honest sort label while searching:** the select shows "Relevance" instead of claiming "Top (stars)" — and the option is no longer a silent no-op.
- **Hero copy no longer overclaims:** "Kept by a human — checked one at a time." (317 of 1,292 verified — the old "Every listing checked by a human" contradicted the trust legend beneath it).
- **"More like this" is actual similarity** (shared language / trust state / tagline tokens), not the alphabetically-first four in a category.
- **Search is finally debounced and index-cached** — the Fuse index is built once per data load (memoised by array identity) and typing is debounced 150ms; measured per-keystroke jank dropped from ~120-180ms to near-instant.
- **CountUp counts from the previous value** (a verify no longer recounts the archive from zero) and reduced-motion readers always see the current number.
- **Show-more threshold raised** (140 → 200 chars): 21/24 cards instead of 24/24.

### UX — archival whimsy (the personality pass)

- **Cards deal in** — 380ms rise + straighten with an alternating ±0.7° tilt, 45ms stagger capped at index 12; skeletons mirror real card anatomy at real height (a CLS win) with a composited sweep.
- **The verify stamp lands** — pill settle + shield icon spring (the one sanctioned overshoot) + a one-shot sage ring, armed by the curator's confirm.
- **Dead entries are filed, not faded** — card opacity removed (an a11y win: text contrast), avatar greyscales, a rotated FILED watermark stamps the face.
- **Hero reveals in stages** (the h1 stays instant — it's the LCP element); the live dots wave once; the header firms up under scroll; the sky breathes (star twinkle, sun/moon pulse) under paper grain.
- **FilterBar signals state** — active facets get a dot + tint + per-facet clear-×, the count is an animated CountUp (aria-hidden digits, sr-only final number), "Clear all" animates in.
- **The pagination pill finally slides** between pages (the shared-layout pill its docstring always promised).
- **Offline banner became a fixed Retry pill** (no layout shift) with the dev command hidden outside development.
- **Toasts speak the curator:** "X — checked and alive", "Couldn't file that one", "The stamp didn't take", "Session expired — the drawer locked itself". No HTTP verbs anywhere.
- **Two easter eggs:** searching "does this startup exist" answers "Yes. You're looking at it." with a Verified pill; three clicks on the footer mantra gets the Curator's sign-off.
- All motion is `prefers-reduced-motion` safe (single CSS kill switch + `useReducedMotion` gates) and transform/opacity only.

### Scale — pagination guardrails

- **`LIST_LIMIT_DEFAULT` 2000 → 3000** (the measured Fuse knee: 22ms/term @1,292 rows → 70ms @5,000; MAX stays 5000 as an explicit opt-in). The false "roughly 10x compression" comment is corrected (measured 4.2x).
- **Truncation is now detectable and honest:** the frontend compares the list against `/api/stats` and banners both real numbers ("Showing 1,000 of 1,292 filings…") — no more silent short bodies with three counters telling two truths.
- **SQL sinks `pivoted` alongside `dead`** (the client always did; the ORDER BY didn't — load-bearing once the LIMIT bites).
- **Status toggles and adds refresh counts only** (categories + stats) instead of refetching the whole 225 KiB archive; seed completion still refetches everything.
- Smoke suite pins the truncation contract, disjoint offsets, past-the-end `[]`, and the dead+pivoted SQL sink; sort-check gained a pivoted fixture (half of `DEAD_ORDER` was untested).

### Data — duplicate merge

- **`backend/scripts/merge_duplicates.py`** groups filings by identity key (registrable domain; GitHub hosts get owner/repo granularity), keeps the verified row + best URL, folds missing fields, deletes the rest. Dry-run by default; `--apply` takes a WAL-safe SQLite backup first. Same-name/different-home pairs (Bird, Bun, Cal.com, Fathom, Motion, Stability AI) are flagged for human review, never auto-merged.
- **Applied:** 10 clear-cut same-home groups merged (Vue.js, GitLab, OpenAI, Apple, Tailwind CSS, Hugging Face, LangChain, Mistral, HashiCorp, Netography) — 1,292 → 1,282 rows.
- **"×2 filings" chip** on cards whose name has multiple filings, linking to the name search — the disambiguation directory admits overlap instead of hiding it.

### Design contract

- `DESIGN.md` + `.impeccable/design.json`: **One Anchor + One Wink** (one non-status `stamp-gold` accent), two sanctioned springs (`spring-settle`, `spring-stamp`), the Micro-Delight Rule, paper-grain exception, chips-wrap doc drift fixed, Loading section, toast-voice Do. Shared motion language lives in `frontend/lib/motion.ts` (the seven duplicated EASE tuples are gone).

### Security

- **Mutating endpoints now fail closed.** `MUTATION_AUTH` defaults to **on**, so
  all six write endpoints require the owner token. Previously the default was
  off and hosting was expected to remember `MUTATION_AUTH=1` — one forgotten env
  var let anyone reachable rewrite the human-verified trail and burn the LLM and
  GitHub quotas. With auth on and `ADMIN_TOKEN` empty the app now **refuses to
  start** rather than serving an API that 403s every write with no explanation.
- The LLM category whitelist is actually applied. `CATEGORIES` was defined and
  referenced nowhere, so arbitrary model output became a facet value in the
  frontend filter bar despite two comments asserting otherwise. Off-list values
  now resolve to `other`.
- GitHub's `homepage` field is validated before it becomes `website_url`. It is
  owner-controlled text that the UI renders straight into an `href`, so a
  `javascript:` value was a click-to-execute sink and a bare `example.com` a
  broken relative link. Only `http(s)` survives; bare hosts get `https://`.
- `?q=` escapes LIKE metacharacters. The value was parameterized (no injection)
  but `%`/`_` were still interpreted, so `q=%` dumped the whole table.
- Verify job telemetry (`/api/verify/status/{id}`, `/api/verify/current`) moved
  behind the admin gate as `/api/admin/verify/…`. Both were unauthenticated;
  `current` scanned the entire jobs table and the payloads leak job error
  strings and seeded URLs.
- Added `Strict-Transport-Security` to the backend responses.
- Rate-limiter keys are evicted once their window expires (the per-IP maps
  previously leaked one entry per source address for the process lifetime).

### Added

- **Container deployment**: `backend/Dockerfile` (python:3.11-slim, non-root,
  stdlib healthcheck), `docker-compose.yml` (named volume for the SQLite
  archive, env passthrough), `backend/.dockerignore`. `--workers 1` is pinned
  and commented as a correctness constraint — the job queue is in-process, so a
  second worker means concurrent verify passes and two writers on one DB file.
- **Scheduled verification actually runs.** `_auto_verify_loop` re-checks
  staleness at boot and every 24h. The previous mechanism fired only at process
  start and relied on a cron script living outside the repo, so a long-running
  server never re-verified.
- Logging is configured. Four modules held an `ideasexist` logger and nothing
  ever called `basicConfig`, so every `log.info` was discarded and errors fell
  through to `lastResort` (bare stderr, no timestamp or level). Adds `LOG_LEVEL`,
  stdout output, a module logger for `verify.py`, and a `log.exception` on
  job-level verify crashes.
- Security-layer test coverage in `backend/tests/smoke.py` (80 assertions total):
  auth gating on all six write endpoints, the startup refusal, netguard SSRF
  blocking, 429 rate limiting and failed-auth throttling, key eviction, the
  category whitelist, URL validation, and LIKE escaping.
- `scripts/sort-check.ts` — sort regression check run against the real frontend
  module by `npm test` (Node strips the types natively).
- `FORWARDED_ALLOW_IPS` so uvicorn's proxy-header handling resolves the real
  client IP for rate limiting. Defaults to trusting nothing; `*` would let any
  caller spoof `X-Forwarded-For` and bypass the limits entirely.
- `frontend/.env.example`, and gzip compression on API responses.
- SEO foundations: `app/robots.txt` (allow-all + sitemap), `app/sitemap.xml`
  (homepage route), canonical link, and OpenGraph/Twitter metadata — driven by
  `NEXT_PUBLIC_SITE_URL` (defaults to the local dev origin, same pattern as
  `NEXT_PUBLIC_API_BASE`).
- `DEPLOYMENT.md` — release/rollback runbook (host rollback click-paths, DNS
  records per platform, pre-deploy env checklist).
- `scripts/contrast_lab.py` + `scripts/reflow-check.mjs` — a11y measurement
  helpers (WCAG contrast incl. CSS `lab()` colors, CDP 320px reflow check).
- Batch human approval at the seed-run boundary: `approve` accepts a
  `created_after`/`created_before` window and the Approve tab groups the
  suggested queue by creation day with one "Approve batch" action per group
  (the 970-entry topstartups batch is one click, not a marathon).
- `backend/scripts/restore_false_dead.py` — trust-layer repair tool: revives
  dead/pivoted rows and zeroes strike counters by name or id, keeping
  `verified` untouched.

### Fixed

- **`sortStartups` discarded its dead-last ordering.** `DEAD_ORDER` ran as a
  separate pre-sort pass that every subsequent `arr.sort()` threw away (sort
  stability only preserves order between elements the *new* comparator calls
  equal), so dead entries interleaved with live ones under `name`, `newest` and
  `founded` — and landed mid-list even under `top`. `DEAD_ORDER` now leads each
  comparator; `scripts/sort-check.ts` pins it for all five keys.
- The health-check poller no longer hangs forever on a failed request. `poll` was
  `async` with no try/catch and re-armed via `setTimeout`, so one 404 (backend
  restart, evicted job) produced an unhandled rejection that silently ended
  polling and left the button disabled with nothing shown to the user.
- Status mutations route through `adminJson`, so a 403 surfaces as
  `AdminUnauthorized` and re-prompts for the token instead of an opaque toast.
- Write controls (Add-startup split button, empty-state action, status-pill menu)
  are hidden while locked, so a public visitor never sees a control that 403s.
- Log output no longer dies on non-Latin-1 text. The stream is reconfigured to
  UTF-8 with replacement — startup names are international and our own notes
  carry symbols (`repo ok, 12★`), which raised inside the log handler on a
  cp1252 Windows console. Same fix in the test suite, which was crashing
  mid-run on an arrow character.
- Pinned `backend/requirements.txt` to exact versions (four `>=` bounds with no
  lockfile meant no reproducible build) and declared `pydantic`, which
  `app/main.py` imports directly but only received transitively.
- `.gitignore` no longer contradicts itself: `dogfood-output/` was ignored while
  six files under it were tracked, so the rule silently did nothing. Also ignores
  the root `.env` that docker-compose reads.
- `verify_log` has a 90-day retention sweep. It grew ~1,300 rows per weekly pass
  and no code ever read it.
- Corrected `deploy-readiness-report.md`, which cited a committed
  `seed_topstartups_all.py` that was never committed; removed two dead one-shot
  scripts (`poll_seed.py` pinned to a hardcoded job id, `verify_fixes.py` to an
  absolute machine path and a port nothing serves).
- Moved `shadcn` (a codegen CLI) from `dependencies` to `devDependencies`.
- **False dead-flips (real incident): the website liveness check treated bot-wall
  403s as strikes, dead-filing healthy Cloudflare-fronted companies — Capterra
  and WHOOP were filed dead, Product Hunt (human-verified) sat one 403 from the
  same. `check_url_ok` is now tri-state like the GitHub check: only a genuine
  404/410 earns a strike; 401/403/429, 5xx and network errors are SKIPs that
  never accumulate. `scripts/restore_false_dead.py` revived the victims and
  cleared the bogus strike counters (verified stamps untouched).
- Verified rows are now protected from automation: a `verified=1` entry never
  accumulates auto-strikes and never auto-flips — a failed check surfaces in
  the run's failed_list as a human re-check item instead.
- Human revive (`POST /api/startups/{id}/verify`) now resets `check_failures=0`
  — the human stamp is a fresh start, not a continuation of the old streak.
- Category icon map in the discovery bar now mirrors the backend whitelist
  (devtools, finance, ecommerce, social, media, desktop, freelance were all
  falling back to the generic Sparkles).
- "Top (stars)" sort is trust-weighted: verified entries first, then stars,
  then name (the archive is ~96% website-seeded with no stars).
- Accessibility: the search input now shows a visible keyboard-focus ring
  (SC 2.4.7 Focus Visible). Root cause: framer-motion's `layout` projection
  writes an inline transparent `box-shadow` on motion elements, clobbering any
  ring on the search pill (Tailwind `ring-*` utilities there computed to
  `oklab(0 0 0 / 0)` regardless of opacity). Fix: hand-written
  `.search-focus-ring` (`box-shadow: 0 0 0 2px var(--ring)`) on a plain
  non-motion wrapper that owns the input.
- Performance: Lenis (smooth scroll) split out of the critical hydration path —
  `scrollPageToTop`/`lenisRef` moved to `components/scroll-utils.ts` (type-only
  `lenis` import, no runtime dependency) and `LenisProvider` is now
  `next/dynamic` with `ssr: false` via `components/lenis-wrapper.tsx`.
- Removed unreferenced `create-next-app` template assets from `public/`
  (`next.svg`, `vercel.svg`, `window.svg`, `file.svg`, `globe.svg`).

### Security

- Readiness sweep (2026-08-10): secrets clean in tree + full git history, npm
  audit 0 vulnerabilities, fresh DB backup taken
  (`ideasexist.db.bak-predeploy-20260810-2134`). The shared venv's
  `cryptography` stays at 48.0.1 — pinned by hermes-agent; the transitive CVE
  is LOW and not in the app tree.
