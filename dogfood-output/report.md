# Dogfood QA Report

**Target:** http://localhost:3023 (IdeaExists — "Does this startup exist?" · FastAPI :8020 backend)
**Date:** 2026-08-10
**Scope:** Full-site exploratory QA — home, morphing search, filter bar (sort/year/status), URL sync, detail modal, add-startup dialog, pagination, admin panel, theme flip, empty states, console
**Tester:** Hermes Agent (automated exploratory QA, dogfood + adversarial-ux-test skills)

---

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 High | 1 |
| 🟡 Medium | 3 |
| 🔵 Low | 2 |
| **Total** | **6** |

**Overall Assessment:** A polished, genuinely well-built one-pager — both themes are clean, geometry is consistent, console is quiet, and the core flows (search→detail→verify, filters, pagination, URL sharing) all work. The one High is the most important flow in the app: **search relevance** — the exact-name match ranks below irrelevant fuzzy hits, which is the exact scenario ("does THIS startup exist?") the product exists for. Three Mediums: duplicate entries, lost focus after modal close, and mute validation feedback in the add form.

---

## Issues

### Issue #1: Search returns irrelevant fuzzy matches ranked above the exact-name match

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional / UX |
| **URL** | `http://localhost:3023/?q=obsidian` |

**Description:**
Searching "obsidian" returns 4 cards in this order: **Hugging Face Transformers** (163,473★), **Obsidian** (20,645★), **Avoca**, **Zoom**. Three of the four results contain zero "obsidian" text anywhere (verified against the API data for name/tagline/description/category). Two compounding causes in `frontend/lib/search.ts`:
1. Fuse.js is configured `threshold: 0.4, ignoreLocation: true` with `description` as a search key — pure character-fuzz matches on long descriptions produce false positives ("obsidian" → "Hugging Face Transformers", "Avoca", "Zoom").
2. After fuzzy matching, results are re-sorted by stars (`sortStartups(..., "top")` default), destroying relevance order — the exact name match ranks **#2**, buried under an irrelevant 163k-star repo.

For the product's core question ("does this startup exist?"), this is the wrong answer pattern: the user's exact match should be first, always.

**Steps to Reproduce:**
1. Load `http://localhost:3023/`
2. Type `obsidian` in the search box
3. Observe result order: Hugging Face Transformers → Obsidian → Avoca → Zoom

**Expected Behavior:**
Obsidian (exact name match, weight 3×) ranks first; irrelevant entries don't match at all.

**Actual Behavior:**
Hugging Face Transformers ranks first (most stars); Obsidian is #2; Avoca and Zoom (no "obsidian" text) also match.

**Screenshot:**
MEDIA:E:\New-Personal-Projects\Does this Startup Exist\dogfood-output\screenshots\search-obsidian-relevance.png

**Console Errors:** none

---

### Issue #2: Duplicate entries in the archive — Pogo ×2 and Zoom ×2 (one Verified, one Unverified)

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Content / Data quality |
| **URL** | `http://localhost:3023/?q=zoom` |

**Description:**
The API returns 49 records but only 47 unique names: **Pogo ×2** and **Zoom ×2** (seeded twice, once per source — one row Verified, one Unverified, same founded year and description). Searching "zoom" renders two identical "Zoom" cards side by side with **contradictory trust states** (green Verified vs grey Unverified). A directory whose entire purpose is disambiguation ("which startup is this?") shows the same company twice with opposite verification verdicts — the most confusing possible outcome for the trust-seeking user.

**Steps to Reproduce:**
1. Search `zoom` (or browse to page 3)
2. Observe two Zoom cards; open each — one says Verified, the other Unverified

**Expected Behavior:**
One entry per company; a single source of truth for verification state.

**Actual Behavior:**
Two Zoom cards (and two Pogo cards) with different verified flags.

**Screenshot:**
MEDIA:E:\New-Personal-Projects\Does this Startup Exist\dogfood-output\screenshots\dup-zoom-search.png

**Console Errors:** none

---

### Issue #3: Detail modal close does not restore focus to the triggering card

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Accessibility |
| **URL** | `http://localhost:3023/` (any card → Details) |

**Description:**
After pressing Escape (or closing via the close button) on the expandable detail modal, `document.activeElement` is `BODY` — focus is lost, not returned to the card that opened the modal. Keyboard/screen-reader users must Tab from the top of the document to resume where they were. The add-startup dialog does this correctly (it keeps a `lastFocused` ref and restores it); the detail modal doesn't. WCAG 2.4.3 / dialog pattern violation.

**Steps to Reproduce:**
1. Tab to a card, press Enter to open details
2. Press Escape
3. Inspect `document.activeElement` → BODY (should be the triggering card's button)

**Expected Behavior:**
Focus returns to the card's name/Details button that opened the modal.

**Actual Behavior:**
Focus lands on `BODY`; next Tab starts at the top of the document.

**Screenshot:** (state, not visual — measured via `document.activeElement`)

**Console Errors:** none

---

### Issue #4: Add-startup form gives zero feedback on invalid/empty input

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | `http://localhost:3023/` → Add startup → By website |

**Description:**
Two validation gaps in `add-startup-dialog.tsx`:
1. **Empty submit:** "Fetch & add" is `disabled={busy || !websiteUrl.trim()}` — a click does nothing, with no error message, no helper text, and only a subtle 50%-opacity dim on the button. A non-technical user clicks, nothing happens, no explanation.
2. **No URL-format validation:** typing `banana` enables the button (only `.trim()` is checked). The invalid request only fails later at the backend (FastAPI 422 → toast error), after the user waits.

**Steps to Reproduce:**
1. Add startup → By website
2. Click "Fetch & add" with empty fields → nothing, no message
3. Type `banana` → button becomes enabled (no format validation)

**Expected Behavior:**
Inline validation: "Enter a website URL" on empty; format check before enabling submit.

**Actual Behavior:**
Silent disabled button; garbage input enabled and deferred to a backend error toast.

**Screenshot:** (code-verified: `disabled={busy || !websiteUrl.trim()}`; DOM-verified: no `aria-invalid`, no error element, opacity 0.5)

**Console Errors:** none

---

### Issue #5: 404 page is the stock Next.js page

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Content / UX |
| **URL** | `http://localhost:3023/this-page-does-not-exist` |

**Description:**
Unknown routes render Next.js's default 404 ("404 / This page could not be found.") with no branding, no "back to the archive" link, and none of the app's voice. A visitor who follows a stale link lands in a dead end. Low severity for a one-pager, but trivial to fix with an `app/not-found.tsx` in the app's voice.

**Steps to Reproduce:**
1. Visit any non-existent path

**Expected Behavior:**
A themed 404 with a link home (e.g., "Nothing in the archive matches — even this page." → Back to the archive).

**Actual Behavior:**
Default Next.js 404, no navigation.

**Screenshot:** none (text-only page)

**Console Errors:** none

---

### Issue #6: Grid row heights vary across rows (293px vs 311px)

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Visual |
| **URL** | `http://localhost:3023/` (grid) |

**Description:**
Cards in rows 6–7 measure 293px vs 311px elsewhere. Within each row the three cards are perfectly equal (CSS grid stretch holds — the user's standing per-row standard passes), but rows containing 1-line taglines (PostHog, GitLab, Fly.io, etc.) are 18px shorter, producing a slightly ragged grid. Cosmetic; caused by tagline line-wrap variance.

**Steps to Reproduce:**
1. Measure card heights per row (`getBoundingClientRect`)

**Expected Behavior:**
Uniform row rhythm (or a `line-clamp-2` on taglines to normalize).

**Actual Behavior:**
Two rows at 293px, the rest at 311px.

**Screenshot:** see `home-initial.png` / `home-dark.png`

**Console Errors:** none

---

## Issues Summary Table

| # | Title | Severity | Category | URL |
|---|-------|----------|----------|-----|
| 1 | Search returns irrelevant fuzzy matches ranked above the exact-name match | 🟠 High | Functional | `/?q=obsidian` |
| 2 | Duplicate entries — Pogo ×2, Zoom ×2 (contradictory verification) | 🟡 Medium | Content | `/?q=zoom` |
| 3 | Detail modal close doesn't restore focus to trigger | 🟡 Medium | Accessibility | `/` (modal) |
| 4 | Add-startup form: no feedback on empty/invalid input | 🟡 Medium | UX | `/` (add dialog) |
| 5 | 404 page is stock Next.js, no way home | 🔵 Low | Content | any bad path |
| 6 | Grid row heights vary (293 vs 311px) | 🔵 Low | Visual | `/` (grid) |

## Testing Coverage

### Pages Tested
- `/` unfiltered (hero, morphing bar, strips, filter bar, grid, pagination, footer)
- `/?q=obsidian`, `/?q=zoom`, `/?q=ai&year=2020&status=verified&sort=founded` (deep-link, via JS navigation)
- `/?year=2020&status=verified&sort=founded`, `/?status=unverified&sort=name`, `/?sort=newest`, `/?page=2`
- `/this-page-does-not-exist` (404)
- Admin dialog (token gate), Add dialog (both tabs), detail modal (3 entries, similar-swap, Mark verified)

### Features Tested
- Morphing search + URL sync; category chips; sort/year/status filters + live count + Clear all
- Detail modal: metadata grid, Website/Code links, similar block swap, Escape, Mark verified (flow exercised end-to-end then reverted in DB)
- Add dialog: split-button, tabs, empty/invalid/valid input states, disabled logic
- Pagination (page 2, `?page=`, aria-current)
- Admin: wrong-token error path
- Theme flip light⇄dark: tokens, status pills, focus rings, equal-height rows (measured, not screenshots)
- Empty state ("Nothing in the archive matches.")
- Console on every page (clean on fresh load)

### Not Tested / Out of Scope
- **Run verification** button (POST `/api/verify/run` pings 49 sites + mutates `last_checked`; covered by weekly cron + backend smoke tests — intentionally not fired)
- **Admin seeder** beyond the token gate (no admin token available; wrong-token path verified: clean inline error)
- **Actual seed submission** (would hit LLM enrichment + write DB)
- Mobile/responsive viewport (desktop-only session; plan notes standard responsive utilities)
- Dead-status treatment (0 dead entries in DB — section correctly hides when empty; live dead-card visuals still unexercised)

### Blockers
- Vision aux model was down mid-session (provider rejected images); QA pivoted to measured DOM geometry + computed styles (the user's preferred standard) and screenshots were captured for evidence when vision recovered.
- **Browser tool artifact noted:** the automation tool strips all but the first query param when navigating (`?x=1&y=2&z=3` → `?x=1` on a static page). Two suspected app bugs ("Details button dead", "deep-link drops params") were investigated to root cause and **proven to be tool artifacts, not app bugs** — the app round-trips all URL params and the Details button correctly opens the modal via real clicks. Worth knowing for future sessions.

---

## Notes

- Console is clean on fresh load (only React DevTools info + HMR log; the "Encountered a script tag" warning appears only during Fast Refresh rebuilds — dev artifact, not app code).
- Both themes pass the user's standing checks: equal-height cards per row (311px, measured), visible status pills in light AND dark (sage-on-beige / sage-on-charcoal, measured computed styles), focus rings present, no white-on-white or beige-on-beige.
- Mark-verified flow works end-to-end (DB flip + live pill update + toast); DB row reverted after test.
- Search `q` is case-insensitive and fuzzy-friendly for multi-term AND matching — good; only the threshold/ranking needs work.
- Fix suggestion for #1: raise Fuse quality (threshold ≈ 0.3, `ignoreLocation: false`), and sort search results by relevance score when `q` is present instead of re-sorting by stars; keep stars sort only when no query.
- Fix suggestion for #2: dedupe in the seeder (normalize `website_url`/`github_url` before upsert) + a one-time merge pass for the 2 existing dupes.
