# IdeaExists — UI/UX Review & Liveliness Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task. This plan is a *review + recommendation* document: nothing here is implemented yet.

**Goal:** Fix every identified UI/UX issue, bug, wrong placement, and illogical behavior in the IdeaExists frontend, then add a layer of measured, restrained "aliveness" (motion, micro-interactions, breathing atmosphere) without breaking the Warm Glass identity or reduced-motion safety.

**Architecture:** Single Next.js 16 app-router one-pager (`frontend/`) with client-side filtering over a FastAPI archive (1,292 entries). All UI lives in `frontend/components/` + `frontend/app/`. Motion stack: `motion/react` + Lenis smooth scroll; tokens in `frontend/app/globals.css` (Warm Glass beige/navy ⇄ charcoal/beige, both themes). Fixes are additive and reversible; no migrations; no backend changes except one optional dedupe script.

**Tech Stack:** Next.js 16 (webpack dev), React 19, Tailwind v4, motion/react, Lenis, shadcn/ui, lucide-react. Verify with `npm run test` (lint + build) and the live-QA script embedded in this plan.

---

## Evidence Basis

Review performed **2026-08-11** on commit `4f39b45` + staged working tree:

- **Source read:** every UI component, `globals.css`, `lib/` (search/api/format/types), admin sections.
- **Live QA:** Playwright against `http://localhost:3023` (frontend) + `:8020` (backend, started for this session) — measured geometry, computed styles, focus trails, keystroke latency, both themes, 404, empty state, admin gate, mobile 375px viewport.
- **Data QA:** SQLite inspection of `backend/data/ideasexist.db` (1,292 rows).
- **Honest limits:** the browser-use harness (CDP :9333) was down (known venv collision — per design-scope skill, never assume it's healthy); the vision aux model was rate-limited mid-session — all geometry claims below are measured, not eyeballed. One screenshot (`final-fixed-home.png` in dogfood-output) decoded as a solid black image and was not used.

### Verified FIXED since the 2026-08-10 dogfood report (do not re-litigate)

| Prior issue | Status | Evidence |
|---|---|---|
| Search ranks fuzzy hits above exact-name match | ✅ Fixed | Live: "obsidian" → Obsidian #1; `search.ts:148` keeps Fuse relevance on default sort |
| Add-form silent disabled button / no URL validation | ✅ Fixed | `add-startup-dialog.tsx:45-52,86-120` inline errors + `urlValid()` |
| 404 dead end | ✅ Fixed | Themed `app/not-found.tsx`, live-verified with back link |
| Detail modal loses focus on close | ✅ Fixed | `startup-detail.tsx:43-59` restores to trigger; live `INPUT` restore confirmed |
| Grid row-height variance (293 vs 311px) | ✅ Fixed | Live: 8 rows × 3 cards, all uniform 304px |
| Missing trust legend | ✅ Fixed | Ledger line under hero (`page.tsx:348-364`) |

---

## Issue Inventory (all found, ranked)

### 🟡 M1 — Search input lag: the "debounced" search is not debounced
- **Location:** `frontend/lib/search.ts:4-18,50` + `frontend/app/page.tsx:136-149`
- **Evidence:** `page.tsx:136` comment says *"Debounced client-side search"* — no debounce exists. `filterStartups` rebuilds a **full Fuse index on every keystroke** over 1,292 rows × 4 weighted keys. Live-measured: **~120–180 ms extra per keystroke** (avg 223 ms incl. fixed delays). Typing fast produces visible lag; on slower machines this compounds with the Lenis scroll.
- **Fix:** debounce the query state ~150 ms in `changeQuery` (`page.tsx:171-174`), and/or memoize the `Fuse` instance per dataset (rebuild only when `startups` changes, not per keystroke).

### 🟡 M2 — Sort select misrepresents ordering while searching
- **Location:** `frontend/components/filter-bar.tsx:16` + `frontend/lib/search.ts:144-149`
- **Evidence:** With a query active, results are relevance-ranked (search.ts:148), but the select reads **"Top (stars)"**. Picking "Top (stars)" while searching is a **no-op** (same `sort === "top"` branch) — an option that does nothing, labeled with the wrong ordering. Live-verified.
- **Fix:** when `query.trim()` is non-empty, present a "Relevance" sort state (label swap, e.g. `SORT_LABELS.relevance` shown as the value), or hide the sort select while searching. Default in Open Questions.

### 🟡 M3 — "More like this" is arbitrary first-N, not similarity
- **Location:** `frontend/components/startup-detail.tsx:61-66`
- **Evidence:** `startups.filter(same category).slice(0, 4)` = the first 4 same-category rows in API order. Live: opening **CodeCrafters** (Education) showed BloomTech, Brightwheel, Brilliant, Buildspace — alphabetically the first Education entries, no shared language/tagline/verified signal. The label promises similarity; the list is coincidence.
- **Fix:** rank candidates by overlap (shared `language`, verified status, token overlap between taglines/descriptions), tiebreak stars desc. Cheap: one scoring pass in the existing `useMemo`.

### 🟡 M4 — Duplicate entries break the disambiguation promise (data surfacing as UI)
- **Location:** data — `backend/data/ideasexist.db`; surfaced by `startup-card.tsx` / search
- **Evidence:** **10 name-groups ×2 filings**: Vue.js (v2.vuejs.org vs vuejs.org, both verified), Tailwind CSS, Stability AI, Motion, LangChain, GitLab (one website link is a subpage: `about.gitlab.com/getting-help/`), Fathom, Cal.com, Bun, Bird (bird.com vs bird.co — possibly genuinely different companies). A directory whose whole job is "which startup is this?" shows identical cards twice. The 2026-08-10 reports flagged Zoom/Pogo; the dup class is still live.
- **Fix (3 parts, all reversible):**
  1. One-time merge script (`backend/scripts/merge_duplicates.py`): group by normalized registrable domain (publicsuffix2 or a small hand list); keep the verified row + best URL/tagline; merge or flag the rest.
  2. Seeder dedupe by normalized `website_url`/`github_url` (verify existing upsert; the memory notes the seeder was capped at 500 and uncapped later — check `seeder.py`).
  3. **UI affordance (recommended, small):** when ≥2 filings share a name, render a muted "2 filings" chip on both cards (`startup-card.tsx`) so the archive admits the overlap instead of hiding it — honesty is the product.
- **Out of scope for UI:** merging rows themselves is backend; the UI chip is frontend.

### 🔵 L1 — Detail modal has no focus trap; Escape becomes dead once focus escapes
- **Location:** `frontend/components/startup-detail.tsx:88` (Escape on panel only; no trap)
- **Evidence (live):** Tab trail from a freshly opened modal: `Close details[in] → Website[in] → Code[in] → 4× More-like-this[in] → Admin panel[OUT] → portal[OUT] → BODY[OUT]`. Focus walks out of an `aria-modal` dialog (WCAG 2.4.3), and because Escape is handled on the panel's `onKeyDown`, **Escape stops working** once focus is outside — the user is trapped by an overlay that blocks all clicks except the overlay itself.
- **Fix:** cycle Tab/Shift+Tab within the panel (small trap util, ~15 lines) + a document-level `keydown` Escape listener while open. Reuse the pattern the add-dialog already approximates.

### 🔵 L2 — Admin section toggle jumps to "Seeding" instead of collapsing
- **Location:** `frontend/components/admin-panel.tsx:214`
- **Evidence:** `onToggle={() => setSection(section === s.key ? "seed" : s.key)}` — clicking the **already-open** header (e.g. "Verification") teleports the user to the Seeding section. Expected: collapse (or no-op).
- **Fix:** allow `section === null` (collapsed); active header click → `setSection(null)`.

### 🔵 L3 — Category chips nearly invisible on mobile
- **Location:** `frontend/components/ui/morphing-discovery-bar.tsx:124,159-209`
- **Evidence (live, 375px viewport):** chip scroll row is **63 px visible of 369 px** content — the fixed `w-44` search pill + "More" button crowd the row to ~2 chips of peeking width; the thin 4px scrollbar + drag is undiscoverable. The category bar — a core discovery surface — effectively vanishes on phones.
- **Fix:** below `sm`, stack the bar: search pill full-width row, chips row full-width underneath (scrollable). Desktop unchanged.

### 🔵 L4 — Hero copy contradicts the trust legend
- **Location:** `frontend/app/page.tsx:329-332` vs `348-364`
- **Evidence:** Hero says *"Every listing checked by a human, not a crawler."* Legend says *"Unverified — filed, awaiting a human."* With **317 / 1,292 verified**, the hero overpromises exactly what the legend explains away — an illogical pair for a trust product. (Adversarial persona: "half the files are blank and you say everything is checked?")
- **Fix (copy):** *"Kept by a human — checked one at a time."* or *"Filed by humans, verified by humans — weekly."* Keep the voice.

### 🔵 L5 — Card density: "Show more" on every card + three open-detail affordances
- **Location:** `frontend/components/startup-card.tsx:255,329-338` (threshold 140 chars); name button `:284-291` + Details `:375-383`
- **Evidence (live):** **24/24 cards** on page 1 render the "Show more" toggle (all LLM descriptions > 140 chars). Combined with name-click and a Details button, the card has three expand surfaces; the adversarial report (T-5) flagged the affordance clash.
- **Fix (default):** raise the toggle threshold to ~200 chars and clamp to 3 lines regardless; card keeps name-click + Details; full description lives in the modal. Keeps the in-card expand for genuinely long entries, drops the noise for typical ones.

### 🔵 L6 — "More" dropdown: no Escape, no arrow-key nav, hover-gated
- **Location:** `frontend/components/ui/morphing-discovery-bar.tsx:66-96,213-293`
- **Evidence:** Escape press leaves the dropdown open (live-verified: no keydown handler); opening is mouse-hover on desktop (click works, but items are unreachable by keyboard until opened, and there's no focus management). Hover-open dropdowns without keyboard parity are an a11y gap (WCAG 2.1.1).
- **Fix:** Escape closes; on open, focus the first item; ArrowUp/Down moves; on close, return focus to the More button. ~20 lines.

### 🔵 L7 — Read-only status pill tooltip is keyboard-unreachable
- **Location:** `frontend/components/startup-card.tsx:122-147`
- **Evidence:** the non-admin path renders a `Badge` (a `span`) as tooltip trigger — not focusable, so the "A human checked this on …" hint never appears for keyboard users.
- **Fix:** add `tabIndex={0}` + `onFocus`/`onBlur` (or render the trigger as a disabled button). One line.

### 🔵 L8 — Pagination comment promises a sliding pill that isn't there
- **Location:** `frontend/components/ui/continuous-pagination.tsx:7-9` vs `:58-76`
- **Evidence:** header comment says *"sliding active pill (shared-layout)"*; the active page is a plain `bg-primary` style with no `layoutId`. Either implement the sliding pill (good motion win — see R6) or fix the comment. Default: implement (trivial, uses the same shared-layout pattern as the discovery bar).

### 🟢 Info — Verified-good (keep, don't regress)
Uniform grid rows (304px, measured) · both themes pass contrast (dark verified pill measured visible) · relevance-first search · trust legend · themed 404 · footer voice · add-form validation · focus restore · console clean on load (only a dev-404 resource log) · reduced-motion respected everywhere (useReducedMotion + CSS gates) · sticky header glass · scrollbar-gutter stable (no modal-open jitter) · scroll-lock/Lenis sync via MutationObserver.

---

## Recommendations — Making It Lively (motion discipline: transform/opacity only, EASE [0.22,1,0.36,1], ≤0.35s, everything gated by `useReducedMotion` — the app's established language)

All sources MIT-safe per ui-component-sourcing audit (2026-08): `motion/react` primitives (installed), Watermelon UI patterns (MIT — already the app's adaptation source), reactbits (MIT + Commons Clause — fine inside the app), motion-primitives core (MIT CLI) if a component is needed. **No new dependencies required for R1–R8.**

### R1 — Card entrance stagger (highest life-per-line)
`startup-card.tsx` / `page.tsx` grid: `motion.div` `initial={{opacity:0, y:12}}` + `whileInView` (viewport once) with a 30 ms stagger via `transition-delay` per index; 0.3 s. Reduced-motion → no entrance. Cheap, transforms only, no layout shift.

### R2 — Grid change feedback: results morph, don't snap
`page.tsx`: wrap the grid in `AnimatePresence mode="popLayout"` keyed by the results identity so re-ranking/filtering animates removals (auto-animate already handles layout; popLayout handles exit). Bonus: when a search query is active, briefly highlight the #1 result card (fade-out ring, 1.2 s) — *this* is why it's first (answers M2 visually).

### R3 — Breathing sky: stars twinkle, sun/moon glow pulse
`frontend/app/globals.css` + `sky-background.tsx`: CSS keyframes on `.sky-star` (opacity 0.4→1, random `animation-delay` via inline style, 3–5 s) and a slow 6 s glow breathe on `.sky-sun`/`.sky-moon` (scale 1→1.03, opacity). Gated under `@media (prefers-reduced-motion: no-preference)`. The sky is the app's signature — this is the cheapest "alive" win in dark mode.

### R4 — "New this week" heartbeat
`home-sections.tsx`: on the "Just added" strip, when any item's `created_at` is < 7 days old, render a small pulsing dot in the ledger header (CSS pulse, reduced-motion off). Tells the story the strip is about.

### R5 — Status-change micro-feedback
`startup-card.tsx` StatusPill: after a successful verify/unverify/dead mutation, animate the pill: `motion.span` keyed by status with a pop (scale 0.85→1, 0.22 s) and color transition via `layout` — the stamp lands visibly. Currently the pill just swaps.

### R6 — Pagination sliding pill (also fixes L8)
`continuous-pagination.tsx`: give the active page button's background `layoutId="pagination-pill"` inside the existing buttons row (same shared-layout pattern as `discovery-pill-bg`). The pill slides between pages instead of blinking.

### R7 — Hero entrance + rotating search placeholder
`page.tsx` hero: fade-up entrance for h1/sub (0.4 s, delay 50/120 ms, once) — currently the hero snaps in under the sky. `morphing-discovery-bar.tsx`: rotate the placeholder through 3 curator-voiced queries (e.g. "Search the archive…" → "Try 'obsidian'" → "Try 'notion'") every 4 s, only when the input is empty and unfocused. Alive without noise.

### R8 — Living empty/offline states
`page.tsx` offline banner + empty state: gentle 2 s float (y 0→-3px) on the `ServerCrash` / `Building2` icons; the banner gets a slow pulse on the status dot. Reduced-motion off.

### R9 — Hover depth on cards & actions
`startup-card.tsx`: extend hover from `y:-2` to `y:-2 + shadow lift + border tint` (box-shadow via existing `--glass-shadow` + `border-primary/20`), 0.25 s. The Website/Code outline buttons gain `hover:border-primary/40 hover:text-primary` (currently they only darken). Keep it subtle — glass stays glass.

### R10 — Verified-count heartbeat in footer (optional, tiny)
`page.tsx` footer: the `CountUp` already animates on mount; add a one-time count-up whenever `stats.verified` changes (it already re-runs on value change — verify the effect; if yes, this is free).

---

## Implementation Tasks (bite-sized, ordered)

> Each task ends with `git add` + Conventional Commit (repo convention: "Co-Authored-By: Hermes Agent <hermes@nousresearch.com>").

### Phase 1 — Functional fixes (M1–M4)

**Task 1.1 — Debounce search input**
- Modify: `frontend/app/page.tsx:171-174` (`changeQuery`) — debounce 150 ms (store timer in a ref; flush on unmount), `frontend/lib/search.ts:50` — memoize the Fuse instance on `out` identity.
- Verify: live keystroke latency < 80 ms/keystroke; relevance unchanged; `npm run test` green.

**Task 1.2 — Honest sort label during search**
- Modify: `frontend/components/filter-bar.tsx` — accept `searching` prop; when true and sort is `top`, display "Relevance" (value stays `top`); add a `relevance` option shown only while searching. `frontend/app/page.tsx` passes `searching={query.trim().length>0}`.
- Verify: live — typing shows "Relevance"; picking "Top (stars)" while searching actually stars-sorts (set `sort=top` explicitly via the option; adjust `search.ts:148` condition to honor an explicit user choice — see Open Question Q1).

**Task 1.3 — Real "More like this" ranking**
- Modify: `frontend/components/startup-detail.tsx:61-66` — score same-category candidates: +2 shared language, +1 same verified, +1 per shared significant word in tagline (stopword-filtered), tiebreak stars desc; keep `.slice(0,4)`.
- Verify: live — CodeCrafters' list is no longer alphabetical-first-4; open 3 modals, sanity-check.

**Task 1.4 — Duplicate handling**
- Create: `backend/scripts/merge_duplicates.py` (dry-run flag default; group by normalized registrable domain; keep verified row + longest description + canonical URL; report diff).
- Modify (UI): `frontend/components/startup-card.tsx` — if another filing shares the name, render a muted "×2 filings" chip linking to `/?q=<name>` (or a tooltip listing both).
- Verify: script dry-run shows ≤10 groups; run in **dry-run only** (open question Q3 decides the real merge); live UI shows the chip on Vue.js/GitLab/etc.

### Phase 2 — Accessibility & behavior (L1–L8)

**Task 2.1 — Focus trap + global Escape in detail modal**
- Modify: `frontend/components/startup-detail.tsx` — trap util (Tab cycle over panel focusables), document-level Escape, keep focus restore.
- Verify: live — Tab trail stays `[in]` for 12 tabs; Escape closes from anywhere; trigger focus restored.

**Task 2.2 — Admin section collapse**
- Modify: `frontend/components/admin-panel.tsx:214` — `section` may be `null`; active header click collapses.
- Verify: click Verification header twice → collapses/expands in place.

**Task 2.3 — Mobile discovery bar stacking**
- Modify: `frontend/components/ui/morphing-discovery-bar.tsx` — below `sm`: search pill full width, chips row full width (both inside the same glass container is fine; container becomes `flex-col sm:flex-row`).
- Verify: 375px viewport — chips row ≥ 300 px visible; scroll + drag still work; 1440px unchanged.

**Task 2.4 — Hero copy honesty**
- Modify: `frontend/app/page.tsx:329-332` — adopt "Kept by a human — checked one at a time." (or Q4 alternative).
- Verify: copy renders; no other text mentions "crawler".

**Task 2.5 — "Show more" threshold + dropdown keyboard parity**
- Modify: `frontend/components/startup-card.tsx:255` (200-char threshold), `morphing-discovery-bar.tsx` (Escape/arrows/focus return on More dropdown).
- Verify: live — some cards lack the toggle; keyboard: Tab→More→Enter→ArrowDown→Enter selects; Escape closes and returns focus.

**Task 2.6 — Tooltip focusability + pagination pill (with R6)**
- Modify: `startup-card.tsx:122-147` (tabIndex 0 on read-only pill), `continuous-pagination.tsx` (shared-layout active pill).
- Verify: keyboard reaches the tooltip; pagination pill slides between pages (live, both themes).

### Phase 3 — Liveliness (R1–R10)

**Task 3.1 — Card entrance stagger** (R1) + **R2** grid `popLayout` + #1-result highlight.
**Task 3.2 — Sky breathing** (R3): keyframes in `globals.css`, inline delays in `sky-background.tsx`.
**Task 3.3 — Heartbeat dot** (R4) + **status pill pop** (R5).
**Task 3.4 — Hero entrance + rotating placeholder** (R7) + **pagination pill** (already in 2.6).
**Task 3.5 — Living states** (R8) + **hover depth** (R9). **R10** folded into 3.5 if the CountUp effect re-runs on change (verify first).

Each task: implement → live-verify both themes + reduced motion (Chrome DevTools emulation) → `npm run test`.

### Phase 4 — QA gate (before any commit batch is final)

1. `npm run test` (lint + build) green.
2. Live-QA script (embedded below) — run from the design-scope library env (has Playwright) or any Playwright-capable venv; the browser-use harness is NOT reliable on this machine.
3. Both themes + `prefers-reduced-motion: reduce` pass (no motion, sky static).
4. 375/768/1440 px viewports: no horizontal overflow on header/footer/bar.
5. Update `CHANGELOG.md` + this plan's issue table with ✅ per item.

### Live-QA script (save as `scripts/qa-ui.mjs` or run ad hoc — evidence harness for this plan)

```python
# qa-live-ui.py — run with any playwright-capable python (e.g. the Ui Design MCP venv)
# python qa-live-ui.py   → prints measured checks; fail-loud on regressions
import json
from playwright.sync_api import sync_playwright
BASE = "http://localhost:3023"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE, wait_until="domcontentloaded"); pg.wait_for_timeout(2200)
    # 1. grid uniformity
    geom = pg.evaluate("""() => [...document.querySelectorAll('main .rounded-2xl')].map(e => { const r = e.getBoundingClientRect(); return {top: Math.round(r.top), h: Math.round(r.height)}; })""")
    rows = {}
    for g in geom: rows.setdefault(g["top"], []).append(g["h"])
    assert all(len(set(v)) == 1 for v in rows.values()), f"non-uniform rows: {rows}"
    print("grid uniform:", {f"y{t}": hs for t, hs in rows.items()})
    # 2. search relevance + latency
    t0 = __import__("time").perf_counter()
    pg.fill("input[aria-label='Search startups']", "obsidian"); pg.wait_for_timeout(800)
    first = pg.evaluate("""() => { const c = [...document.querySelectorAll('main .rounded-2xl')][0]; const n = c.querySelector('button[title="View details"]'); return n ? n.textContent.trim() : null; }""")
    assert first == "Obsidian", f"relevance broken: {first}"
    print("search first:", first, "| total ms:", round((__import__("time").perf_counter()-t0)*1000))
    # 3. modal focus trap
    pg.fill("input[aria-label='Search startups']", ""); pg.wait_for_timeout(500)
    pg.evaluate("""() => { [...document.querySelectorAll('main .rounded-2xl button[title="View details"]')][0].click(); }""")
    pg.wait_for_timeout(1200)
    trail = []
    for _ in range(12):
        pg.keyboard.press("Tab"); pg.wait_for_timeout(80)
        trail.append(pg.evaluate("!!document.activeElement.closest('[role=dialog]')"))
    assert all(trail), f"focus escaped: {trail}"
    pg.keyboard.press("Escape"); pg.wait_for_timeout(800)
    assert pg.locator("[role='dialog']").count() == 0, "Escape did not close"
    print("focus trap + escape: ok")
    # 4. dark theme pill visible
    pg.evaluate("document.documentElement.classList.add('dark')"); pg.wait_for_timeout(600)
    print("dark bg:", pg.evaluate("getComputedStyle(document.body).backgroundColor"))
    pg.evaluate("document.documentElement.classList.remove('dark')")
    # 5. mobile chips visible
    pg.set_viewport_size({"width": 375, "height": 812}); pg.goto(BASE, wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
    vis = pg.evaluate("""() => { const r = document.querySelector('[class*="chip-scroll"]'); return r ? {clientW: r.clientWidth, scrollW: r.scrollWidth} : null; }""")
    assert vis and vis["clientW"] > 250, f"mobile chips hidden: {vis}"
    print("mobile chips visible:", vis)
    print("console errors:", errs[:5])
    b.close()
print("ALL CHECKS PASSED")
```

---

## Risks & Tradeoffs

- **Motion scope creep:** every liveliness item is gated by `useReducedMotion` and uses transform/opacity only — the app's own discipline. If any R-item feels loud in QA, drop it; the remaining set still delivers.
- **Debounce (1.1):** 150 ms adds perceived latency to filtering; acceptable vs 120 ms+ input jank. Measure both ways; 100 ms is the floor.
- **Dedupe (1.4):** merging is the only destructive step — dry-run first, keep the merge script's report, and only merge groups that share a registrable domain (Bird stays split). The UI "×2 filings" chip is the safe default if Q3 defers merging.
- **Relevance-vs-sort (1.2):** honoring an explicit "Top (stars)" pick during search changes current behavior (currently impossible) — additive, not a regression.
- **Mobile bar restack (2.3):** the morphing pill's `layoutId` spans the bar; restacking changes layout geometry — QA the pill morph after restack on mobile.
- **Performance:** R1 stagger + R2 popLayout over 24 cards is trivial; the Fuse memo (1.1) is the real perf fix.

## Open Questions (defaults in bold — proceed with defaults if no answer)

1. **Sort during search:** swap label to "Relevance" only (**default**), or add a real "Top (stars)" option that overrides relevance while searching?
2. **"Show more" threshold:** 200 chars (**default**) vs removing the in-card toggle entirely (description lives only in the modal)?
3. **Dedupe:** run the merge in dry-run + UI chip only (**default**), or actually merge the 10 groups now?
4. **Hero copy:** "Kept by a human — checked one at a time." (**default**) vs "Filed by humans, verified by humans — weekly." vs keep current?
5. **Liveliness scope for the first pass:** R1+R2+R3+R7 (**default** — cheapest, highest life-per-line) vs all R1–R10 in one pass?

## Files likely to change

- `frontend/app/page.tsx` — debounce, sort prop, hero copy, popLayout, entrance, offline/empty pulse
- `frontend/components/startup-card.tsx` — threshold, pill pop, filings chip, tooltip tabIndex, hover depth
- `frontend/components/startup-detail.tsx` — focus trap, global Escape, similarity ranking
- `frontend/components/ui/morphing-discovery-bar.tsx` — mobile stack, placeholder rotation, dropdown keyboard
- `frontend/components/ui/continuous-pagination.tsx` — sliding pill
- `frontend/components/filter-bar.tsx` — searching-aware sort
- `frontend/components/admin-panel.tsx` — section collapse
- `frontend/components/home-sections.tsx` — heartbeat dot
- `frontend/components/sky-background.tsx` + `frontend/app/globals.css` — star twinkle/glow breathe
- `backend/scripts/merge_duplicates.py` (new, dry-run by default)
