# IdeaExists — Final Production & UI/UX Plan (merged, phase-by-phase)

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task. This is the *final* plan — it supersedes both `.hermes/plans/claude_ui_plan.md` (the direction: **archival whimsy** with pervasive micro-delight) and `.hermes/plans/2026-08-11_221500-ui-ux-review-liveliness.md` (the evidence base: Playwright-measured M1–M4/L1–L8 inventory). All of the spine's load-bearing claims were re-verified against the repo on 2026-08-11 — see "Verification of the spine" below.

**Goal:** Take IdeaExists from "polished but inert" to production-ready and alive: fix every measured UI/UX bug, honor the correctness/a11y debt, then land the **archival whimsy** personality layer (rubber stamps, card-catalog, the Curator) with pervasive micro-delight — while keeping status hues sacred, reduced-motion intact, and the two themes clean. Finish with a cross-platform test runner, CI (including the never-built Docker image), and a duplicate-merge pass.

**Architecture:** Single Next.js 16 one-pager (`frontend/`) + FastAPI archive (`backend/`, 1,292 rows) + `scripts/` root test runner. Motion: `motion/react` + Lenis; tokens in `frontend/app/globals.css` (Warm Glass beige/navy ⇄ charcoal/beige). Design contract lives in `DESIGN.md` + `.impeccable/design.json` (DesignSync hook is live — see P8 warning). All changes additive and reversible; the only destructive step is the duplicate merge (P13), behind backup + dry-run.

**Tech Stack:** Next.js 16 (webpack dev), React 19, Tailwind v4, motion/react, Lenis, shadcn/ui, Radix, lucide-react, Fuse.js; Python 3.11 + FastAPI + SQLite; Node 24 (pinned in P14). Verify: `npm test` at root (backend smoke + sort check + lint + build).

**Commit convention (repo-wide):** Conventional Commits with `Co-Authored-By: Hermes Agent <hermes@nousresearch.com>` (user's global AGENTS.md). Commit after every task.

---

## Direction (locked — not open for re-litigation)

- **Personality:** archival whimsy — rubber stamps, card-catalog, ink, the Curator as a character. **Micro-delight rule:** many ≤500ms responses, each bound to a real state change; nothing plays without user action; nothing runs forever.
- **Motion contract loosened deliberately:** `EASE [0.22,1,0.36,1]` stays the default; **two named spring tokens** join it — `spring-settle` (critically damped, no visible overshoot) for shared-layout pills + admin accordion, `spring-stamp` (the one sanctioned overshoot) for the verify stamp only. Never on hover, never on grid entrances.
- **One Anchor → One Anchor + One Wink:** one non-status accent (`stamp-gold`, from the Sky's existing gold family) for chrome delight only — never near a status, never the sole carrier of meaning.
- **Status-Is-Sacred stays verbatim:** sage/brick/grey only for status, always with label/icon (WCAG 1.4.1); decorative stamps may carry a status hue only when `aria-hidden` and the card still shows its pill.
- **Pagination is guardrails, not pagination** (P12): the cliff gets a banner + limit moved to the measured knee; no envelope, no new endpoint, no offset UI.
- **Duplicates are merged** (P13), behind a backup and a dry-run report.
- **Node 24** pinned; **Python 3.11** everywhere (matches the Dockerfile).

## Verification of the spine (all spot-checked 2026-08-11 — the plan's claims hold)

| Claim in spine | Verified |
|---|---|
| `DESIGN.md` motion rules "No bounce, no springs" | ✅ `DESIGN.md:166` |
| One Anchor Rule `:125`, Status-Is-Sacred `:123`, Don'ts `:243-249` | ✅ exact |
| Doc drift: chips "wrap to a second row on desktop" claimed twice | ✅ `:198` + `:232` — implementation is All+top-3 inline + More dropdown |
| `.impeccable/design.json` exists; hook cache exists | ✅ `.impeccable/{design.json,hook.cache.json}`; `hook.cache.json` recorded an edit to `scripts/sort-check.ts` at 21:38 today → **DesignSync hook is live; parallel-session caution applies — re-read the repo before executing** |
| design.json drift: Status Pill describes two-step arm/confirm | ✅ `components[]` entry says "first click arms 'Confirm?'" — replaced in code by popover → confirm dialog |
| `extensions.motion.entrance-stagger` documented, implemented nowhere | ✅ value "40-80ms per card"; no implementation in code |
| main.py:127 "compresses roughly 10x" comment | ✅ present (measured reality: 4.2x — corrected in P12) |
| `LIST_LIMIT_DEFAULT, LIST_LIMIT_MAX = 2000, 5000` | ✅ `main.py:321`; endpoint returns `list[dict]` (`:340`) with "growth ceiling" docstring (`:341`) |
| SQL sinks only `dead`, not `pivoted` | ✅ `main.py:358` ORDER BY CASE |
| Seeder cap 1–500 | ✅ `seeder.py` `CAP_MIN, CAP_MAX = 1, 500` (~line 33) |
| `page.tsx:436` passes unclamped `page` to pagination | ✅ `<ContinuousPagination page={page} …>` — the grid clamps via `currentPage`, the control doesn't |
| CountUp restarts from 0 + reduced-motion freeze | ✅ `count-up.tsx:22-37` |
| Focus trap/Escape dead-zone in detail modal | ✅ live Tab trail exits to footer gear; Escape bound to panel `onKeyDown` only (`startup-detail.tsx:88`) |
| More dropdown: no Escape/arrows/focus return | ✅ `morphing-discovery-bar.tsx:66-96` |
| Admin toggle teleport | ✅ `admin-panel.tsx:214` |
| Read-only pill = span tooltip trigger | ✅ `startup-card.tsx:122-147` |
| Hero copy overclaim + sort label + More-like-this + no debounce + mobile chips (63/369px) + 24/24 "Show more" | ✅ all live-measured 2026-08-11 |
| verify.mjs is Windows-only despite header claim | ✅ hardcoded `Scripts\python.exe`; "Node ≥23 strips types" comment at `:32` |
| No `engines` in either package.json | ✅ both undefined |
| sort-check.ts imports `search.ts` → `fuse.js` at module scope; no `pivoted` fixture | ✅ `sort-check.ts:14`; fixtures have `status: "dead"` only |
| smoke.py print-and-collect style; pagination check only asserts `limit=1` | ✅ tail block; new assertions in P12 fit the existing `check()` pattern |
| No `.github/` yet (CI is new) | ✅ absent |

---

# Phase 8 — Design contract + motion foundations

Docs **first**, so everything after is compliant rather than retro-justified. Then the shared motion module so no file writes its own easing.

### Task 8.1 — Amend `DESIGN.md`
**Modify:** `DESIGN.md`
- **Motion principles** (`:164-166`): "No bounce, no springs" → ease-out default + the two named springs (`spring-settle`, `spring-stamp`), with the *never on hover / never on grid entrances* clause.
- **One Anchor Rule** (`:125`) → **One Anchor + One Wink**: chrome = warm neutrals + one anchor + one non-status accent (`stamp-gold`, derived from the Sky's gold family); never on/near a status, never sole carrier of meaning.
- **Status-Is-Sacred** (`:123`): unchanged verbatim + the `aria-hidden` decorative-stamp clause.
- **Don'ts** (`:243-249`): the no-decorative-gradients rule gains the paper-grain exception; the no-bounce don't rewritten per above; no-emoji-in-status-pills stays.
- **New Micro-Delight Rule** (as in Direction above).
- **Doc drift fix:** `:198` and `:232` chip-wrap claims → "All + top 3 inline + More dropdown".
- **New Loading section:** skeletons mirror real card anatomy + height, no `backdrop-filter`.

### Task 8.2 — Amend `.impeccable/design.json`
**Modify:** `.impeccable/design.json` — mirror 8.1 in `narrative.rules`/`donts`; `extensions.motion`: `entrance-stagger` → true (`45ms per card, capped at index 12`), add `spring-settle`, `spring-stamp`, `deal-tilt`, `live-ring`; add `stamp-gold` to `colorMeta` with an 8-step `tonalRamp` in the existing style; fix the `components[]` Status Pill entry (two-step arm/confirm → popover → confirm dialog).
> ⚠️ **DesignSync hook is live** (`hook.cache.json` exists, records edits). Check whether `design.json` is hook-generated before hand-editing — if it is, amend the generator/source and re-run, or the edit gets clobbered on the next sync. Verify post-edit by touching a file and confirming the hook doesn't rewrite the fields you changed.

### Task 8.3 — Shared motion module
**Create:** `frontend/lib/motion.ts` — exports `EASE`, `DUR`, `tween()`, `SPRING_SETTLE`, `SPRING_STAMP`, `STAGGER`/`dealDelay(i)`, `STILL`, and `m(reduce, transition)` (the reduced-motion one-liner). The six existing copies die: `add-startup-dialog.tsx:14`, `startup-detail.tsx:12`, `theme-toggle.tsx:9`, `continuous-pagination.tsx:18`, `morphing-discovery-bar.tsx:29`, inline at `startup-card.tsx:277`.
> Do **not** build a reduced-motion context/provider — `useReducedMotion()` already subscribes live in 6 components; a context would desync from the 3 `matchMedia` guards (`lenis-provider.tsx:20`, `scroll-utils.ts:26`, `count-up.tsx:25`). Only the ternaries collapse.

### Task 8.4 — CSS tokens + keyframes
**Modify:** `frontend/app/globals.css` — add `--ease-archive` to the existing `@theme inline` block; `--stamp-gold` + `--grain-opacity` to `:root`/`.dark`; `@keyframes deal-in / reveal-in / live-ring / skeleton-sweep`. **Extend the existing reduced-motion block (`:387-393`)** — it becomes the single CSS kill switch. Leave `.search-focus-ring` (`:395-402`) alone.

**Verify P8:** `npm test` green; `grep -rn "0.22, 1, 0.36" frontend/components` → only `motion.ts`; design.json hook doesn't clobber 8.2; both themes still build.

---

# Phase 9 — Correctness and accessibility first

Bugs, not polish. Ship before any visual work. All 12 items live-verified (see table above).

**Real bugs:**
1. **Pagination shows the wrong page** — `page.tsx:436` passes `page={page}` (unclamped). Rename the prop to `currentPage` in `continuous-pagination.tsx:13` so TS makes it unrepeatable; pass the clamp.
2. **CountUp double bug** (`count-up.tsx`) — always restarts from 0 (footer re-counts 0→N on every verify), and the reduced-motion branch freezes display forever. Track previous value in a ref; reduced-motion branch → `setDisplay(value)`.
3. **Focus trap doesn't trap** (`startup-detail.tsx:43-59,88`) — add Tab/Shift+Tab cycle + document-level Escape listener. (Part 1's "trap works" claim was about restore, not trapping.)
4. **More dropdown keyboard parity** (`morphing-discovery-bar.tsx:66-96`) — Escape, arrow keys, focus return (WCAG 2.1.1).
5. **Admin toggle teleport** (`admin-panel.tsx:214`) — allow `section === null`; active-header click collapses.
6. **Read-only status pill keyboard-unreachable** (`startup-card.tsx:122-147`) — span tooltip trigger. P10 reworks it into a popover (fixes it properly).

**Honesty / correctness of claims:**
7. **Hero copy** (`page.tsx:329`) — "Every listing checked by a human, not a crawler" vs 317/1,292 verified. → **"Kept by a human — checked one at a time."**
8. **Sort select lies while searching** (`filter-bar.tsx:16` + `search.ts:148`) — show a "Relevance" state while a query is active.
9. **"More like this" isn't similarity** (`startup-detail.tsx:61-66`) — score by shared language / verified / tagline token overlap, tiebreak stars.
10. **Search isn't debounced** (`page.tsx:136` comment lies; `search.ts:50`) — ~150ms debounce + memoise the Fuse instance per dataset. **Re-measure keystroke latency after this lands** (was ~120–180ms over 1,292 rows; gates P12's knee).
11. **Mobile category row is 63px visible of 369px** (`morphing-discovery-bar.tsx:124`) — stack below `sm`: search full-width, chips full-width beneath.
12. **Card density** (`startup-card.tsx:255`) — "Show more" on 24/24 cards (140-char threshold). Raise to ~200 chars, clamp to 3 lines.

**Verify P9:** `npm test`; live: `?page=40` shows active pill on clamped page; reduced-motion user sees updated footer counts; Tab trail stays `[in]`; Escape closes from anywhere; typing "obsidian" → Obsidian #1 with no per-keystroke jank; mobile chips row ≥ 250px.

---

# Phase 10 — Archival whimsy, pervasive

Concrete mechanics. All transform/opacity/filter; no new dependencies. (Merge map: R1 dealing = my card-entrance stagger; R5 stamp = my status-pop; R6 pagination pill = my L8; R7 hero reveal = my entrance; R3 sky breathing = my star/moon pulse; R8 offline/empty = my living states; R4 heartbeat = my "Just added" pulse.)

- **Card "dealing"** — CSS `@keyframes deal-in` (opacity + `translateY(10px)` + alternating `rotate(±0.7deg)`), 380ms, `animation-delay: calc(var(--i) * 45ms)` capped at index 12, on a **wrapper div** in the grid (`page.tsx:427`) — never the card's own `motion.div` (CSS animations outrank inline styles → would suppress `whileHover` and fight `layoutId` projection).
  > **Remove `useAutoAnimate`** (`page.tsx:4,111,424`) — WAAPI outranks CSS keyframes per-property; one animation system.
- **Skeletons that tell the truth** (`page.tsx:388-392`) — `CardSkeleton` mirroring real card anatomy, `min-h` matched to real cards (304–311px, measured) → **CLS win**; render 12; **drop `.glass`** (12 `backdrop-filter` surfaces in the LCP window); one composited `translateX` sweep.
- **Verify stamp** in `StatusPill` (grid + modal from one place): on verified transition — pill `scale [1,1.06,1]`, `ShieldCheck` lands `rotate:-12, scale:0.6` on `SPRING_STAMP`, one `aria-hidden` sage ring pulse that unmounts itself (~600ms total).
- **Dead = filed, not faded** (`startup-card.tsx:278`) — **drop card `opacity-85`** (a11y win: text contrast), keep `saturate-[0.6]`, `grayscale` the `HueAvatar`, add rotated `FILED` stamp (`aria-hidden`, mono, `-rotate-6`); hover lift drops to `y:-1`.
- **Read-only pill becomes informative** — locked path becomes a real `<button>` opening the same Popover with the worded hint + how verification works (fixes P9-6 for keyboard *and* touch).
  > ⚠️ Nested Radix Tooltip+Popover on one trigger is the fiddliest bit — if it misbehaves, go popover-only.
- **Hero reveal** — staged `.reveal-in` (opacity + `translateY(6px)`, 45ms steps) on subhead, discovery bar, ledger line. **The `<h1>` does not animate** — it's the LCP element; an `opacity:0` h1 is a self-inflicted LCP regression.
- **Live dot waves once** — Verified legend dot (`page.tsx:353`) + footer online dot get a `::after` ring, **capped at 3 iterations**. Unverified/Dead dots stay static.
- **Header reacts to scroll** — one `IntersectionObserver` on a 1px sentinel → `data-scrolled` (~12 lines; no second `useScroll` rig). Background/border firm up; tagline crossfades to a live ledger stamp. **No height change** (CLS).
- **FilterBar finally signals state** (`filter-bar.tsx:54-105`) — off-default facets get `border-primary/50 bg-primary/10` + a dot, per-facet clear-×, "Clear all" under `AnimatePresence`, count becomes `CountUp`.
  > ⚠️ Border + background only, **no `ring-*`/`box-shadow`** (collides with `SelectTrigger`'s focus ring); **do not tint the Status trigger** sage/brick (leaks reserved hues). ⚠️ Count lives in `aria-live="polite"` — animated digits go in `aria-hidden`, live region gets an `sr-only` span with the final number.
- **`HomeSections` stop hard-cutting** (`page.tsx:382`) — `AnimatePresence` opacity + y (no height); 12 mini-cards deal in per-strip.
- **Pagination gets its promised pill** — `layoutId="pagination-pill"` on a **sibling span**, never the button (`layoutId` on a focusable element clobbers its focus ring).
- **Paper grain** — one layer inside `sky-background.tsx`'s `aria-hidden` wrapper: inline `feTurbulence` SVG data URI (~350B CSS, zero requests), 3.5–5% opacity. **No `mix-blend-mode`**; **never inside `.glass`**.
- **Offline banner → fixed pill with Retry** (`page.tsx:315-321`) — fixed bottom pill can't shift layout (CLS); raw `uvicorn` command becomes dev-only.
- **Admin accordion animates** (`admin-panel.tsx:221`) — height + opacity on `SPRING_SETTLE`; height animation acceptable **only here** (dialog's own scroll container, admin-only); chevrons rotate instead of swapping (`admin-shared.tsx:47-51`).
- **Sky breathing** — star twinkle via staggered CSS delays, slow glow pulse on sun/moon, under `prefers-reduced-motion: no-preference`.

**Two optional extras from the absorbed review** (add if the micro-delight pass has appetite; both trivial):
- **#1-result relevance pulse** — after a query resolves, the top card gets a 1.2s fading ring: *this* is why it's first (pairs with P9-8).
- **Rotating search placeholder** — "Search the archive…" → "Try 'obsidian'" → "Try 'notion'", every 4s, only when empty + unfocused.

**Deliberately not doing** (flagged, not built): confetti, konami code, cursor trails, mouse-tilt cards, a marquee on "Just added" (infinite animation contradicts Micro-Delight), ASCII `console.log`.

**Verify P10:** `npm test`; reduced-motion walk of all 10 guard sites (no deal-in/reveal/ring/stamp/shimmer; static sky+grain; pagination pill teleports — and footer counts still update); achromatopsia emulation: status always reads via label/icon/`FILED` word; Lighthouse LCP < 2.5s, CLS < 0.1; `backdrop-filter` count doesn't grow; no infinite animations.

---

# Phase 11 — Copy pass and two easter eggs

- **`DESIGN.md` rule:** *toasts speak the curator's voice — name the thing and what happened to it, never the HTTP verb; errors say what didn't happen, not that something "failed".*
- **Rewrites (~14 sites):** `page.tsx:248-259`, `add-startup-dialog.tsx:99-131`, three admin sections — "Seed failed" → "Couldn't file that one"; "Status update failed" → "The stamp didn't take"; "X marked verified" → "X — checked and alive" (+ "Stamped today. Reversible."); "Admin session expired" → "Session expired — the drawer locked itself". Empty states + 404 untouched (best writing in the repo).
- **Easter egg 1 — the self-referential query:** searching "does this startup exist" / "ideaexists" renders "Yes. You're looking at it." with a real Verified pill in the empty-state branch (~8 lines; it *is* the product thesis).
- **Easter egg 2 — the Curator signs off:** three clicks on the footer mantra toasts "Filed by hand. Checked the dead ones twice. — The Curator". `<span onClick>` with **no `role`** — a tab stop for a joke is worse a11y than omitting it (note that reasoning in a comment).

**Verify P11:** `npm test`; both easter eggs trigger; toasts read naturally; no HTTP verbs in user-facing strings (`grep -riE "failed|error" frontend/components | grep -v "//"` sanity pass).

---

# Phase 12 — Pagination: kill the cliff, don't paginate

**Measured (2026-08-11):** payload at 1,292 rows = 950 KiB raw → **225 KiB gzipped (4.2x — the "roughly 10x" comment at `main.py:127` is wrong, fix it)**; `JSON.parse` 1.02ms; memory ~3–5MB vs ~50MB React baseline — none are the bottleneck. **Fuse is linear in rows:** 22ms/term at 1,292 → 35ms at 2,500 → 70ms at 5,000 (desktop; ~4x on mid-tier phone). Knee ≈ **3,000 rows**. `seeder.py` caps a run at 500 → headroom from 1,292 to the 2,000 default is **1.4 seed runs**; when the cliff trips, `fetchStartups()` gets a short body with HTTP 200 and no signal while `/api/stats` reports the true total — three counters, two truths, no error.

**Six additive changes, no envelope, no new endpoint:**
1. **Truncation is detectable on the wire** — `loadAll` (`page.tsx:113`) already fetches `/api/stats`; `startups.length < stats.total` *is* the signal. Banner honestly naming both numbers ("Showing 3,000 of 3,412 filings — search and filters only cover the 3,000 shown"), conditioned on `online && !loading`. `main.py`'s `list[dict]` untouched → no smoke-assertion risk.
2. **`LIST_LIMIT_DEFAULT` 2000 → 3000** (`main.py:321`) — headroom 1.4 → 3.4 seed runs; MAX stays 5000 (explicit opt-in).
3. **Fix stale comments** — the 10x claim (`:127`) and the "growth ceiling" docstring (`:341`, say what happens at the ceiling). Record measured numbers + a `ponytail:` marker naming the upgrade path (SQLite FTS5 + bm25 for server-side *search*, not offset pagination).
4. **Sink `pivoted` in SQL too** (`main.py:358`) — client sinks both, SQL only `dead`; load-bearing the moment `LIMIT` bites.
5. **The `page`/`currentPage` bug** (P9-1).
6. **Stop refetching 225 KiB on every status toggle** — `markVerified`/`markUnverified`/`markDead` return the updated row and `page.tsx:255` patches it in; add a `refreshCounts` (categories + stats) helper for `:237`/`:257`. **Keep `loadAll()` at `:485`** (a seed run inserts up to 500 rows — full refetch is correct there).

**Documented in three existing places:** `main.py:341` docstring, README API table, README architecture ("client holds everything, ceiling ~3,000 rows").

**New smoke assertions** (append as the **last** `TestClient` block — bulk-inserts into the shared DB, print-and-collect style per `backend/tests/smoke.py`): truncation is detectable (`short list < stats.total` — pins the contract the banner depends on); default limit truncates while stats reports the true total (assert against `main_mod.LIST_LIMIT_DEFAULT`, not hardcoded 3000); `offset` pages disjointly and past-the-end returns `[]`; **SQL sinks `pivoted` as well as `dead` — this one fails against current code**. **`sort-check.ts`:** add a `pivoted` fixture row (half of `DEAD_ORDER` is currently untested; P12 gives it a second implementation in SQL).

**Verify P12:** new smoke assertions pass (incl. the previously-failing pivoted one); `npm test`; banner appears with `LIST_LIMIT_DEFAULT` temporarily lowered and disappears when restored; toggle status → footer counts update with one small request (network tab), not a 225 KiB refetch; re-measure keystroke latency (P9-10).

---

# Phase 13 — Merge the duplicate filings

**Verified:** 10 name-groups filed twice in `backend/data/ideasexist.db` — Vue.js (v2.vuejs.org / vuejs.org), Tailwind CSS, Stability AI, Motion, LangChain, GitLab (one link is `about.gitlab.com/getting-help/` — a scrape artifact), Fathom, Cal.com, Bun, Bird. A directory whose job is "which startup is this?" shows identical cards twice.

**Sequence (only destructive step in the plan):** timestamped `sqlite3 .backup` (not `cp` — a live WAL copy can be torn) → `backend/scripts/merge_duplicates.py` in **dry-run (the default)** → review the report → apply.

**Merge rule:** group by **normalised registrable domain**; keep the verified row + best URL/description; merge the rest. On the real data this does the right thing automatically — `v2.vuejs.org`/`vuejs.org` and `about.gitlab.com/...`/`gitlab.com` share a registrable domain and merge; **Bird (`bird.com` vs `bird.co`) does not — flagged for manual review, not merged** (possibly genuinely different companies).

**UI affordance regardless (the honest one):** when ≥2 filings share a name, render a muted "×2 filings" chip on both cards. Verify the seeder's upsert dedupe still holds so the class doesn't return.

**Verify P13:** dry-run report reviewed before applying; Bird flagged, not merged; chip disappears for merged groups, remains for genuinely distinct ones; `npm test` green after.

---

# Phase 14 — Cross-platform runner and CI

- **Rewrite `scripts/verify.mjs`** (header claims "cross-shell, no path games" and is neither — verified): per-platform interpreter (`Scripts/python.exe` vs `bin/python`) + `PYTHON=` env override; spawn npm as `spawnSync("npm", ["test"], { cwd, shell: true })` (`shell: true` required post-CVE-2024-27980 for `.cmd`/`.bat`; safe here because argv is two literals and the directory travels as `cwd`, never shell text); portable missing-venv message; report `r.error` so ENOENT doesn't print "exit null".
- **Pin Node 24:** `engines: { node: ">=24" }` in **both** `package.json` files (Vercel/Netlify read the frontend one; `npm test` cannot run below Node 23 — native TS type stripping in the sort-check leg). Python stays 3.11. Fix README prerequisites (`:32` says "Node.js 20+") and delete the now-false "There is no CI" note.
- **`.github/workflows/ci.yml` (new)** — two jobs, three runners, proportionate:
  1. **test** on `[ubuntu-latest, windows-latest]`, `shell: bash` defaults, Python 3.11 + Node 24 with pip/npm caching, **no venv** (`PYTHON=python`), then `npm test`. Plus `ruff check backend` on Linux only (default rules, no new config file).
     > ⚠️ `npm ci` in `frontend/` must run **before** `npm test` — `scripts/sort-check.ts` imports `frontend/lib/search.ts` → `fuse.js` at module scope. The single most likely naive-CI failure.
     > Both non-npm suites are fully offline (smoke monkeypatches `httpx`; `next build` is client-side with defaulted env) — CI needs no secrets.
  2. **docker** — build `backend/Dockerfile`, poll `docker inspect` until the container's own `HEALTHCHECK` reports healthy, dump health JSON + logs on failure. **Earns its place: the image has never been built and its healthcheck has never executed.** Needs `ADMIN_TOKEN` (app refuses to start without it) + `VERIFY_AUTO_STALE_DAYS=0` (no outbound calls).
- **Not adding** (flagged): macOS runner, Node version matrix, pytest, buildx/registry cache, `tsc --noEmit` (redundant — `noEmit: true` + `next build` runs full type-checking), Codecov, Dependabot, pre-commit, `scripts/reflow-check.mjs` (hardcoded Chrome path + needs live server).
- **Expected first-run surprises, in likelihood order:** the `npm ci` ordering; a case-sensitive-filesystem import failure on Linux (exactly what the ubuntu leg exists to find); timing-sensitive queue/rate-limit sleeps in `smoke.py` flaking on a loaded runner (raise the specific sleep, no retry wrapper); ruff finding something.

**Verify P14:** `npm test` green on this machine (Windows, Node ≥24); push → both jobs pass on ubuntu *and* windows; docker job reports healthy (first real build of that image).

---

## Verification (ordered; each gates the next)

1. **Automated** — `npm test` at root green throughout (backend smoke + sort check + lint + build), incl. new assertions (P12: truncation contract, limit knee, disjoint offsets, SQL sinks `pivoted`; sort-check: `pivoted` fixture).
2. **Reduced motion** — OS toggle on; walk all 10 guard sites: no deal-in/reveal/ring/stamp/shimmer, static grain + sky, pagination pill teleports (correct), **footer counts still update** (the count-up fix).
3. **Focus & keyboard** — `.search-focus-ring` still shows its 2px ring (wrapper at `morphing-discovery-bar.tsx:131` stays a plain `div`); active-filter styling doesn't eat the select's focus ring; pagination buttons keep their rings; detail modal Tab×12 stays `[in]`, Escape closes from outside, focus returns to trigger; More dropdown: Escape/arrows/focus return.
4. **Colour-alone** — DevTools achromatopsia: every status signal still reads via label/icon/`FILED`.
5. **Contrast** — `scripts/contrast_lab.py` on dead-card body text (improves — opacity removed), active-filter styling both themes, `stamp-gold` usage.
6. **Performance** — Lighthouse before/after: LCP < 2.5s, CLS < 0.1 (net-positive expected: 12 `backdrop-filter` surfaces out of the LCP window, matched skeleton heights, offline banner no longer shifts layout, auto-animate out of the bundle).
7. **Live QA** — reuse the Playwright script embedded in the absorbed review (grid uniformity 304px rows, "obsidian" → Obsidian #1, modal focus trail, mobile chips `clientWidth > 250`). Run from a Playwright-capable env — the browser-use CDP harness on this machine is unreliable.
8. **Responsive** — 375/768/1440px, no horizontal overflow; morphing pill's `layoutId` behaves after the mobile restack.
9. **Truncation banner** — `LIST_LIMIT_DEFAULT` temporarily below row count → banner shows both real numbers; raised back → gone.
10. **CI** — both jobs pass ubuntu + windows; docker job reports healthy (first real build).
11. **Duplicate merge** — dry-run reviewed; Bird flagged; "×2 filings" chip behavior verified.

## Risks & Tradeoffs

- **Motion scope creep** — every item gated by `useReducedMotion`, transform/opacity/filter only, springs sanctioned only where named. If anything feels loud in QA, drop it; the set still lands.
- **DesignSync hook** — if `design.json` is hook-generated, P8's edit must go through the generator or be re-applied; verify post-edit (Task 8.2).
- **Parallel sessions** — `hook.cache.json` recorded an edit to `sort-check.ts` today; the repo has staged-but-uncommitted work. **Re-read the repo (git status + touched files) before executing each phase.**
- **Debounce** (P9-10) — 150ms adds perceived latency; measured alternative: 100ms. Verify both.
- **Dedupe** (P13) — the only destructive step; dry-run + backup + Bird manual review are mandatory gates.
- **Relevance-vs-sort** (P9-8) — additive (explicit "Top (stars)" during search was previously impossible); not a regression.
- **Mobile restack** (P9-11) — the morphing pill's `layoutId` spans the bar; re-QA the morph after restack.
- **Docker** — not installed locally; the CI docker job is first-contact validation (expected to surface Dockerfile/healthcheck issues — that's the point).

## Open items (micro-decisions with defaults)

1. **Optional extras** (P10): include the #1-result relevance pulse + rotating placeholder? **Default: yes** if the micro-delight pass has appetite, both are < 1hr.
2. **Bird pair** (P13): genuinely different companies (bird.com email vs bird.co scooters)? **Default: manual review, leave both, keep the "×2 filings" chip.**
3. **Spring tokens in code** (P8): only where named (pills, accordion, stamp) — **default: strictly, no expansion**.
4. **Debounce value**: 150ms (**default**) vs 100ms.

## Files likely to change

- `DESIGN.md`, `.impeccable/design.json` — P8
- `frontend/lib/motion.ts` (new), `frontend/app/globals.css` — P8
- `frontend/app/page.tsx`, `frontend/components/startup-card.tsx`, `startup-detail.tsx`, `filter-bar.tsx`, `home-sections.tsx`, `admin-panel.tsx`, `admin-shared.tsx`, `sky-background.tsx`, `count-up.tsx`, `ui/morphing-discovery-bar.tsx`, `ui/continuous-pagination.tsx` — P9/P10/P11/P12
- `frontend/lib/search.ts`, `frontend/lib/api.ts` — P9/P12
- `backend/app/main.py`, `backend/scripts/merge_duplicates.py` (new), `backend/tests/smoke.py` — P12/P13
- `scripts/verify.mjs`, `scripts/sort-check.ts`, `package.json` (root + frontend), `README.md`, `.github/workflows/ci.yml` (new) — P14
- `CHANGELOG.md`, this plan's checkboxes — throughout
