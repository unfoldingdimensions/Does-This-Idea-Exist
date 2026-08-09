# Smell Report — IdeaExists ("Does this startup exist?")

**Score: 7/10 · WEAK-MODERATE · 3 tells, all clustering in the first viewport**
Audit date: 2026-08-09. Method: full source read (globals.css, page.tsx, startup-card, home-sections, filter-bar, startup-detail, layout) + live rendered check at :3023 (computed styles, both themes' tokens).

## TL;DR

Three of the ten tells are present — **generic tech hue**, **no type system**, **centered everything** — and all three cluster in the first viewport (blue-tinted hero stack). Per the clustering rule this is an identity failure needing a new lane, not a patch. The good news: the app is otherwise clean (no gradient, no tile-grid marketing, no glassmorphism, no bounce motion, correct states everywhere). The personality pass is the deslop — the plan already replaces every tell with product-specific decisions.

## Heuristic scores (0 = tell present, 1 = clean)

| # | Heuristic | Score | Evidence |
|---|-----------|-------|----------|
| 1 | tech gradient | 1 | No gradients in globals.css or components |
| 2 | generic tech hue | **0** | globals.css:58 `--primary: oklch(0.546 0.245 262.881)` light, :93 `oklch(0.707 0.165 254.624)` dark — hue ≈255, indigo-blue family; rendered dark primary observed `oklch(0.707 0.165 254.624)` |
| 3 | feature tile grid | 1 | Card grid is content-driven directory data (49 rendered), not equal marketing tiles |
| 4 | accent rail | 1 | Absent |
| 5 | frosted glass over blobs | 1 | Absent |
| 6 | oversized statistics | 1 | Footer counts are 12px text |
| 7 | icon above heading | 1 | Absent (small inline icons in strip headers are fine) |
| 8 | generic motion | 1 | Near-zero motion; nothing bounces; nothing moves (also the problem) |
| 9 | no type system | **0** | Single family (Plus Jakarta Sans) everywhere; ad-hoc sizes: h1 text-3xl (rendered 30px), body text-sm, cards text-[13px], labels text-xs/text-[11px]; no display step, no data/ledger role, no mono; muted-foreground (0 chroma grey, oklch 0.556/0.708) on nearly all secondary text |
| 10 | centered everything | **0** | page.tsx:190–207 hero `mx-auto max-w-2xl text-center` (h1 rendered align=center, 672px wide); chips centered page.tsx:211; search centered; no focal asymmetry in first viewport |

## Priority issues

### P0 — The first viewport belongs to no product
Blue-tinted centered hero + flat single-font type + generic copy ("Searchable directory of startups — what they do, their website, their code."). Nothing here could only belong to a verification-first local startup archive.
**Fix:** recolor (product-specific hue replacing the template blue) + typeset (serif display step + mono ledger role) + texture/asymmetry details; then voice pass. The centered search hero becomes defensible **once the cluster is broken** — the search box is this product's genuine focal point; it is the centered-everything tell only in combination with the other two.

### P1 — Flat type hierarchy
30px h1 → 14px body with no intermediate steps; metadata undifferentiated from prose; all grey, all same face. The hierarchy is *present* but the roles aren't named (no display/caption/ledger distinction).
**Fix:** 1.3-ratio scale (display 2.75–3.5rem → h2 1.25rem → body 0.95rem → caption 0.8rem); mono for all data runs (dates, stars, counts, footers).

### P1 — Zero motion
Nothing reveals, nothing responds beyond shadcn defaults. A personality void, not a defect — but a page with no motion reads machine-static.
**Fix:** ease-out-only reveal system (staggered fade+rise, hover lift, stamp-on-verified), reduced-motion safe, transform/opacity only.

### P2 — Voice absent
Only wit in the whole app: the empty-state "Maybe you build this?". Every other string is functional.
**Fix:** dry-warm curator voice (hero subline, search placeholder, status tooltips, dead-recently footnote, footer honesty line).

## What NOT to do (new-smell guard)

- Do not swap blue → another saturated blue ("different default ≠ fix"); ink-green is a new lane, not a hue rotation.
- Do not add bounce/spring easing anywhere (motion.md's spring allowance is overridden for this project: ease-out only).
- Do not fetch favicons for cards (would trade a template look for a privacy leak in a no-tracking app).
- Do not center MORE things while fixing the cluster — add asymmetry via ruled left-aligned section headers, offset footer, texture.
- Do not introduce gradients/glassmorphism as "personality" — that is slop's other face.

## What would move the score

- 8/10: replace the blue with ink-green + warm neutrals (tell 2 gone).
- 9/10: + real type system (display serif + ledger mono, 1.3-ratio scale) (tell 9 gone).
- 10/10: + break the first-viewport centered cluster with texture/rules/asymmetry so the centered search reads as a focal decision (tell 10 gone).
