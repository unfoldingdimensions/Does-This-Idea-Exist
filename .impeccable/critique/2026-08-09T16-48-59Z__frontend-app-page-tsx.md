---
target: homepage
total_score: 33
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
timestamp: 2026-08-09T16-48-59Z
slug: frontend-app-page-tsx
---
# Impeccable Critique — IdeaExists Homepage

**Method: dual-agent (A: design review · B: detector + browser evidence)**

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | aria-live result count, skeleton grid, per-action toasts, worded status tooltips, offline banner with exact fix command |
| 2 | Match System / Real World | 4 | "the archive", "filed", "human checked it" — only leak: "deepseek-v4-flash" in add-dialog helper copy |
| 3 | User Control and Freedom | 3 | Escape/overlay close + back-button-safe URL + Clear all — BUT no × in search field; Clear all hidden for query/category-only filters |
| 4 | Consistency and Standards | 4 | One glass language, uniform pills, ledger mono for evidence, hairline + ambient-pool shadow rule everywhere |
| 5 | Error Prevention | 3 | http(s) URL validation with inline guidance; gap: "Mark verified" is a permanent trust action firing on a single unconfirmed click |
| 6 | Recognition Rather Than Recall | 4 | Worded status tooltips, hero legend, count chips, named selects, inline "Show more" |
| 7 | Flexibility and Efficiency of Use | 2 | Keyboard flow complete, but no shortcuts (/ search, v verify), no search-field clear, no batch-verify queue |
| 8 | Aesthetic and Minimalist Design | 3 | Three-band hero (search / count / legend) + 11-chip row + 3 filter selects compete in first viewport |
| 9 | Error Recovery | 3 | Inline URL validation aria-wired; toasts; no undo path for mark-verified |
| 10 | Help and Documentation | 3 | Tooltips + legend + voice copy everywhere; no "how this archive is kept" explainer |
| **Total** | | **33/40** | **Good** |

## Design Specificity Verdict

**AUTHORED-FOR-THIS-PRODUCT.** Not category-interchangeable. Evidence: (1) Warm Glass literalizes the brief — "the archive behind frosted glass" — frosted panels, hairline borders, top-edge light catch, warm beige/charcoal bases, no cold SaaS blue-white. (2) Three-voice typography enforces the Ledger Rule (Space Grotesk hero / Geist Mono data / Jakarta prose). (3) The trust layer is the visual spine: dot + label + worded tooltip everywhere, hero trust legend, "Mark verified" embedded in the unverified pill. (4) Curator voice throughout ("Search the archive…", "Dead is a status, not an erasure"). (5) No favicons — privacy promise honored. Dead-card desaturation (opacity-85 saturate-[0.55]) is semantics, not decoration.

**Deterministic scan:** `detect.mjs --json` on `frontend/app/page.tsx frontend/components` → exit 0, `[]` — zero rules fired. The detector has nothing to say; the implementation is clean of the slop families it guards.

**Browser evidence (Assessment B):** console clean at every checkpoint (only React DevTools info + HMR noise), zero JS errors, zero failed fetches, no hydration warnings. 156 interactive elements, 0 overlapping controls, 0 invisible controls, no horizontal overflow (1262 = 1262). Detail dialog opens/closes cleanly (fully unmounted on Escape). **B caught what source scanning cannot: a dark-mode contrast failure (below).**

## Overall Impression

This is a genuinely authored, disciplined interface — the Warm Glass world, the trust layer, the voice, and the edge states are all product-specific and coherent. The single biggest opportunity is the same one the reviewer kept hitting: **the first viewport asks too many questions at once**, and a real WCAG failure hides in the dark-mode card meta text that everything else got right.

## What's Working

1. **The trust layer is visible card copy, not metadata** — dot + label + worded tooltip on every status pill, hero legend, "Mark verified" as the unverified pill itself. The product's core differentiator is its most glanceable element.
2. **Disciplined, signature motion** — one morphing hero interaction, shared-layout card→dossier expansion, ease-out only, reduced-motion respected. Restraint that reads as craft.
3. **Edge states genuinely authored** — voice-matched empty state with dual recovery actions, offline banner with the exact restart command, aria-wired inline validation, back-button-safe URL model.

## Priority Issues

### [P1] Dark-mode card meta + description fail WCAG AA contrast (3.88:1)
- **What**: In dark theme, the card meta line ("founded 2018 · checked Aug 9", 11px, `muted-foreground` oklch(0.72 0.02 80)) and card description (13px) measure **3.88:1** against the alpha-composited glass card background (oklch(1 0 0 / 0.05) over charcoal) — below the 4.5:1 AA threshold for normal text. Light mode passes (5.62:1).
- **Why it matters**: The meta line IS the verification evidence (the product's reason to exist); at 3.88:1 it fails Sam, and in a directory built on trust labels, illegible evidence undermines the premise.
- **Fix**: Raise dark-mode `--muted-foreground` lightness/chroma (e.g. oklch(0.72→0.78 0.02 80)) or bump card description to `foreground/80`; re-measure composited over glass in both themes.
- **Suggested command**: `$impeccable polish` (token-level fix)

### [P1] No way to clear an active search or category
- **What**: The search field has no × button, and "Clear all" only renders when year/status filters are set (`hasFilters = year!=='all' || status!=='all'`); an active query or category alone shows no clear affordance.
- **Why it matters**: The primary task is look-up; the most common correction (remove the query) forces select-all+delete in a narrow 200px mono field, and a stale query silently shadows every subsequent browse.
- **Fix**: Add a clear-× inside the search pill when query is non-empty (aria-label "Clear search"); include query/category in the "Clear all" visibility condition.
- **Suggested command**: `$impeccable clarify`

### [P1] 11+ category chips hidden behind a 494px horizontal scroll
- **What**: The chip row scrolls (1153px content vs 494px client at 1262px viewport) — the first ~7 categories are invisible without discovering the thin 4px scrollbar, and the morphing active pill can sit off-screen while selected.
- **Why it matters**: The browsing surface is partly hidden behind an affordance many users won't discover; on a verification directory, categories are how visitors find "their" kind of startup.
- **Fix**: Wrap chips to a second row on desktop (or cap visible + "More" disclosure); auto-scroll the active chip into view on selection.
- **Suggested command**: `$impeccable layout`

### [P2] "Mark verified" fires on a single unconfirmed click — no undo
- **What**: The product's core, semi-permanent trust action (card pill + dialog button) flips an entry's status on one click with no confirmation or undo path.
- **Why it matters**: A misclick or accidental Enter silently rewrites the human gate — the exact trust the product sells.
- **Fix**: Lightweight confirm (or 5s undo toast) on mark-verified; pass `onMarkVerified` into the detail modal's StatusPill so both affordances behave identically.
- **Suggested command**: `$impeccable harden`

### [P2] Hero is a three-band stack competing with the chip row
- **What**: Hero = search bar + "94 startups · last checked" mono line + 10px trust legend, then the 11-chip row, then the filter bar's 3 selects — five layers of "what do I do here / how do I trust it / how do I narrow it".
- **Why it matters**: The display headline's power is diluted; the discovery bar (the signature interaction) loses focus.
- **Fix**: Merge the count into the discovery bar (it already shows "All 94"), fold the legend into one muted line or the footer.
- **Suggested command**: `$impeccable distill`

### [P3] Split-button open state is cryptic
- **What**: The Add-startup main pill blurs away; a circular back-arrow (aria-label only) appears beside "By GitHub / By website". The close affordance is unlabeled visually.
- **Fix**: Visible label/tooltip ("Cancel") on the collapse control, or click-outside/options-row-click to collapse.
- **Suggested command**: `$impeccable clarify`

## Persona Red Flags

**ALEX (power user):** No keyboard shortcuts (no / to focus search, no v to verify). Must select-all+delete to clear search (no ×). "Mark verified" is one-card-at-a-time — no batch path outside the token-wrapped admin seeder. The blur morph on the split button costs him a beat if he clicks fast twice.

**JORDAN (first-timer):** (1) Category chips beyond ~7 are invisible unless he discovers horizontal scroll — he'll think categories are limited. (2) The unverified pill reads as a static label, not a button — "Unverified" with hover-only tooltip doesn't say "click me to do the human check". (3) The add-dialog helper leaks "deepseek-v4-flash", breaking the plain-language contract exactly at the moment he's deciding to contribute.

**SAM (accessibility):** Strong overall — AA contrast passes except the P1 dark-mode meta text; status never color-only; keyboard-complete flow; aria-wired errors. Fails for Sam: (1) the 10px mono trust legend is below comfortable reading size; (2) hue avatars carry no name text for screen readers (SR reads "DD" not "Duolingo"); (3) the chip row has no "scroll for more" announcement.

## Minor Observations

1. "Dead recently" strip conditionally renders — with zero dead entries today, the landing shows 2 of 3 strips, breaking the three-rhythm.
2. Footer "36 verified" count is not set in Geist Mono/tabular — violates the Ledger Rule the system itself declares; adjacent stats are mono but not the counts.
3. Card has two expansion patterns for similar content: inline "Show more" (long description) and "Details" (modal) — both correct, but a minor consistency question.
4. Search input is only 200px (w-44) at desktop — feels secondary inside a max-w-3xl pill dominated by chips, given search is the stated focal point.
5. Page-2+ on fresh load after filtering can land on a clamped last page without the URL updating.
6. "Run verification" (h-7) sits adjacent to the admin gear (h-7) — easy to hit accidentally; both owner-only, so minor.
7. Tab title/meta well-authored — good for later hosting.

## Questions to Consider

- What if search were the only hero element — chips living fully inside the discovery bar's scroll — collapsing the three-band hero into a single gestalt?
- The trust legend insists statuses read as human acts; if the proof is the worded tooltip, does the hero still need a legend, or would one "Every listing checked by a human, not a crawler." line free the pixels for the archive?
- For the Curator, "Mark verified" is the daily loop — what would a keyboard-driven verify queue (scroll → v → next) do for the weekly pass?
