# UI Personality Pass v2 — "Warm Glass" (supersedes v1 direction)

> **Status: IMPLEMENTED + VERIFIED 2026-08-09.** All tasks shipped: tokens (beige/navy light, charcoal/beige dark, glass utilities), Space Grotesk + Geist Mono, morphing discovery bar (hero), expandable detail (shared-layout, replaces Dialog), glass add-dialog (controlled, Escape+focus), split-button (lucide, ease-out, AnimatePresence), windowed continuous pagination (?page=), hue avatars, status dot + worded tooltip, graveyard "filed" dead treatment, curator microcopy + signed footer, AutoAnimate grid reflow, CountUp (NumberFlow dropped — React 19 incompatibility). Verification: `npm run test` ALL PASS; browser-verified both themes (tokens, geometry 311px equal heights, interactions: morph, filter/URL, pagination, expand+similar+Escape, split→dialog tab, tooltip, contrast math 4.5:1+, reduced-motion wiring). Console clean after CountUp swap. Known notes: dead-card styling code-verified but no dead entries in DB to exercise live; mobile = standard responsive utilities (desktop-verified).
> **For Hermes:** implement after user confirms Open Questions. Antislop diagnosis (`.hermes/design/smell-report.md`) stays binding: glassmorphism must NOT re-create tell #5 ("frosted glass over blobs") — **glass without blob/gradient backgrounds**, restrained blur, calm beige/charcoal bases.

## Direction: WARM GLASS — minimal, frosted, beige/navy ⇄ charcoal/beige

Glassmorphism done *warm*: frosted panels with hairline borders and soft light, on warm beige (light) / warm charcoal (dark) — not the cold blue-white glass of 2021 dashboards. Minimalism means: fewer borders, more translucency + shadow; one morphing hero interaction; cards that expand with shared-layout motion.

**Why it fits this product:** the glass layer reads as "archive behind frosted glass" — you can see the data, dimly, before you open the drawer. The morphing search bar literally dramatizes the core question ("does this startup exist?" → you expand the search). And the beige/navy ⇄ charcoal/beige flip is a genuine two-theme identity, satisfying the user's both-themes QA standard.

## Palette (tokens only — variables in globals.css, both themes)

### Light — beige (main) + navy
- `--background`: warm beige `oklch(0.96 0.018 80)` (#F5F0E6) — main
- `--foreground`: deep navy `oklch(0.27 0.05 260)` (#1B2A4A)
- `--primary`: navy `oklch(0.32 0.055 260)`; `--primary-foreground`: warm off-white
- `--card`: glass — `oklch(1 0 0 / 0.55)` + `backdrop-blur`; `--card-border`: `oklch(0.88 0.02 80 / 0.7)`
- `--muted`: beige-rose `oklch(0.93 0.015 80)`; `--muted-foreground`: warm grey `oklch(0.52 0.02 80)`
- `--accent`: deeper beige `oklch(0.9 0.02 80)`; hover = navy-tint
- Status: verified = warm sage `oklch(0.55 0.09 150)`; dead = brick `oklch(0.5 0.13 30)`; unverified = warm grey
- Glass tokens: `--glass-bg: oklch(1 0 0 / 0.55)`, `--glass-border: oklch(1 0 0 / 0.6)`, `--glass-highlight: oklch(1 0 0 / 0.35)` (top edge light), `--glass-shadow: 0 8px 32px oklch(0.2 0.02 260 / 0.08)`

### Dark — charcoal (main) + beige
- `--background`: warm charcoal `oklch(0.21 0.012 60)` (#1E1D19) — main
- `--foreground`: beige `oklch(0.93 0.022 85)` (#EDE5D0)
- `--primary`: beige `oklch(0.88 0.03 85)`; `--primary-foreground`: charcoal (beige buttons, charcoal text — the invert)
- `--card`: `oklch(1 0 0 / 0.05)` glass; `--card-border`: `oklch(1 0 0 / 0.1)`
- `--muted`: `oklch(1 0 0 / 0.06)`; `--muted-foreground`: warm grey-beige `oklch(0.72 0.02 80)`
- `--accent`: `oklch(1 0 0 / 0.08)`; hover = beige-tint
- Status: verified = bright sage; dead = terracotta; unverified = grey-beige
- Glass tokens: `--glass-bg: oklch(1 0 0 / 0.05)`, `--glass-border: oklch(1 0 0 / 0.12)`, `--glass-highlight: oklch(1 0 0 / 0.08)`, `--glass-shadow: 0 8px 32px oklch(0 0 0 / 0.4)`

**No hardcoded colors in components** — every Watermelon component below gets re-tokened (they ship neutral-900/white/gray-500 hardcodes). Status semantics stay locked (green/red/grey) + colorblind-checked; icons/labels carry meaning, color never alone.

## Typography (carry-over from v1, minimalism-adjusted)

- Body/UI: Plus Jakarta Sans (unchanged).
- Display: **Space Grotesk** (clean grotesque — minimalism register) for hero question + section headers; serif (Fraunces/Source Serif 4) optional per Q3.
- Mono: Geist Mono (token already wired, globals.css:11 — just load it) for all data runs (dates, stars, counts, check dates).
- Scale: display `clamp(2.5rem, 5vw, 3.5rem)` → h2 1.25rem → body 0.95rem → caption 0.8rem; ≥1.3 ratio; body ≤76ch.

## Watermelon UI components (MIT — verified in `ui-component-sourcing` audit) + mapping

All installed via `npx shadcn@latest add @url:https://registry.watermelon.sh/r/<name>.json` (registry files already fetched to `wm_registry/` for reference). **Requires `npm i motion`** (4 of 5 need it).

| Component | What it is (read from source) | Maps to | Adaptations needed |
|---|---|---|---|
| `morphing-discovery-bar` | Glass pill: search icon ⇄ expanding input; category pills with sliding shared-layout pill-bg; `motion/react`, lucide, `backdrop-blur-md` | **Hero**: merge search + category chips into one morphing glass bar — the signature interaction | Re-token colors (ships white/neutral-900); tight spring `stiffness:520/damping:32` → keep (barely bouncy) or ease-out per antislop; feed real categories; wire input → existing `query` state + URL params |
| `expandable-profile-card` | Card with shared-layout (`layoutId`) expansion into full-screen frosted detail panel (`bg-background/80 backdrop-blur-md`) | **Card → detail**: replace shadcn Dialog with shared-layout expand (card click = the card grows into the modal — strongest personality move) | Swap hardcoded Unsplash image → hue avatar; add metadata grid + Website/Code links + Similar block (existing detail content); keep `pr-12` close-button clearance; Escape + focus trap (Radix Dialog may still wrap it) |
| `create-community` | Frosted modal (`backdrop-blur-2xl`, rounded-4xl, thick border, animated entrance) with form + segmented pricing tabs | **AddStartupDialog**: restyle the add form as this glass modal (name, website/GitHub URL, tagline) | Re-token; adapt fields to startup shape (website + GitHub + name + tagline); keep existing submit/validation/toast logic; `framer-motion` import → `motion/react` |
| `split-button` | Main button morphs (scale/blur) into back + option row | **"Add startup 👋"** button (Add by website / Add by GitHub / Paste list) and/or **"Run verification"** (Verify / Verify + report) | Swap `@hugeicons` → lucide (icons.md: one set per app); **bounce: 0.55 spring → ease-out** (antislop: bounce banned); re-token |
| `continuous-pagination` | Animated page transitions + page buttons; `framer-motion` + `next-themes` | **Grid pagination** at 1,259 entries (page ~24) — currently all rendered client-side; pagination keeps DOM light + gives the grid a pulse | `framer-motion` → `motion/react`; decide page-size + URL `?page=` sync (replaceState, back-button-safe); re-token |

**Order of build:** tokens → motion dep → morphing bar (hero) → expandable card (detail) → glass add-dialog → split-button → pagination → voice/copy → QA.

## Additional animation / micro-animation libraries (explored — all MIT unless noted)

| Library | License (audited) | What it gives us | Use here |
|---|---|---|---|
| **motion** (`npm i motion`) | MIT | Layout + presence animations; `AnimatePresence`, `layoutId` shared elements, `useReducedMotion` | REQUIRED by 4/5 Watermelon components; card→modal expand; filter reflow |
| **@number-flow/react** | MIT, dependency-free, accessible | Animated number counts | Stars, stats, "N startups" — count-up on view |
| **@formkit/auto-animate** | MIT | Zero-config layout animation: any parent animates children moving in/out | Filter/sort changes — cards glide, no snap |
| **lenis** | MIT | Inertial smooth scrolling | Premium glass feel on the one-pager (optional, subtle) |
| **tw-animate-css** | MIT (already in app) | shadcn base animations | Keep as the CSS fallback layer |
| Motion Primitives core | MIT (CLI) | Extra motion components if needed | Optional, only if a gap appears |
| React Bits | MIT + Commons Clause (in-app use fine, keep notice) | Animated accents (text effects, hover tiles) | Optional, restraint-checked |
| Aceternity UI | Free tier (custom terms, no resale) | Glassmorphism cards, spotlight | Optional — we're already doing glass natively |

**Skip deliberately:** GSAP (overkill for one-pager), `framer-motion` package (renamed → `motion`), paid tiers of everything above.

**Motion spec (carry-over, binding):** ease-out `[0.22,1,0.36,1]` default; entrance stagger 40–80ms; hover lift `translateY(-2px)`; **no bounce easing** (antislop) — adapt Watermelon springs; `prefers-reduced-motion` → opacity-only (motion's `useReducedMotion` + CSS); transform/opacity only; nothing loops >3s.

## Carry-over from v1 (research + antislop — still binding)

- **Status treatment:** 6px dot + worded tooltip — "A human checked this link on <date>. It's alive." / "Checked 3 times, link dead each time. Filed, never deleted." [R-1][R-24]; dead cards = quiet "filed" treatment (sepia/saturate-50 on glass) [R-12]
- **Avatars:** deterministic-hue initials (GitHub Identicons precedent [R-21]); hue chosen to sit well on glass
- **Emoji accents:** one per concept in strips/actions only — 🆕 ✅ ⚰️ headers, "Add startup 👋"; never in status pills [R-5]
- **Microcopy:** hero "A human-kept archive of what exists." · search placeholder "Search the archive…" · footer "Dead is a status, not an erasure. — The Curator" · no-tracking line · empty state "Nothing in the archive matches. Want it added? Ask the curator." [R-1][R-2][R-20]
- **Voice rule:** joke about the curator's process, never about the entries [R-3]
- **No favicon fetching** (privacy); **no new backend work**

## Open questions (defaults in bold)

1. Direction confirmed: **Warm Glass** (this plan) — build it? (v1 Warm Archive stays archived.)
2. Display font: **Space Grotesk** (minimalism) / Fraunces / Source Serif 4 (editorial glass) / none (keep Jakarta bold).
3. Morphing bar replaces the current hero search + chips: **yes, merged** / keep chips as-is, only search morphs.
4. Detail view: **shared-layout expand (Watermelon pattern, replaces Dialog)** / keep Radix Dialog, add motion entrance only.
5. Pagination: **add continuous pagination (24/page, `?page=` sync)** / keep single-scroll grid this pass.
6. Split-button target: **"Add startup"** / "Run verification" / both.
7. Extra libs: **motion + Number Flow + AutoAnimate** / + Lenis too / motion only.
8. Glass intensity: **subtle (blur-sm/md, hairline borders)** / bolder (blur-2xl, thicker borders, more translucency).
9. Voice intensity + signed footer: **dry-warm, signed "— The Curator"** (carry-over from v1).

## Files touched (complete list)

- `frontend/app/globals.css` — full token re-theme (beige/navy, charcoal/beige, glass tokens, fonts, texture removal → glass)
- `frontend/app/layout.tsx` — add Space Grotesk + Geist Mono via next/font/google
- `frontend/package.json` — add `motion`, `@number-flow/react`, `@formkit/auto-animate` (per Q7), optional `lenis`
- `frontend/components/watermelon-ui/*.tsx` — 5 new components (installed via shadcn CLI, then adapted)
- `frontend/components/startup-card.tsx` — glass card, hue avatars, status dot + tooltips, dead treatment
- `frontend/components/startup-detail.tsx` — replaced by expandable-profile-card pattern (or Dialog + motion)
- `frontend/app/page.tsx` — morphing bar wiring, pagination state + `?page=`, copy, footer
- `frontend/components/add-startup-dialog.tsx` — create-community-style glass modal
- `frontend/components/home-sections.tsx` — glass strips, emoji headers
- `frontend/components/filter-bar.tsx` — token restyle + AutoAnimate reflow
- Backend: **no changes** (smoke must stay ALL PASS)

## Verification (unchanged standard)

`npm run test` green; browser both themes with computed styles (glass contrast on beige AND charcoal — white-on-white/beige-on-beige checks); measured equal-height cards; reduced-motion emulation; antislop smell re-check (no blob gradients, no bounce, no new tells); keyboard/a11y pass (expandable card Escape + focus, morphing bar labels, pagination landmarks); colorblind simulation on status pairs.
