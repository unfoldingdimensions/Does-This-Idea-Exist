---
name: IdeaExists
description: A human-kept archive of what exists — warm glass directory of startups with verification status.
colors:
  warm-paper: "oklch(0.953 0.016 82)"
  archive-navy: "oklch(0.27 0.052 262)"
  archive-navy-deep: "oklch(0.32 0.055 262)"
  glass-white: "oklch(1 0 0 / 0.55)"
  deep-beige: "oklch(0.885 0.022 82)"
  warm-grey: "oklch(0.5 0.02 78)"
  warm-grey-soft: "oklch(0.92 0.018 82)"
  hairline: "oklch(0.85 0.02 80 / 0.65)"
  sage-verified: "oklch(0.49 0.09 150)"
  brick-dead: "oklch(0.53 0.135 30)"
  charcoal: "oklch(0.212 0.012 60)"
  warm-beige-text: "oklch(0.93 0.024 85)"
  beige-primary: "oklch(0.88 0.03 85)"
typography:
  display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Plus Jakarta Sans, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 500
    lineHeight: 1.5
  label:
    fontFamily: "Geist Mono, monospace"
    fontSize: "0.6875rem"
    fontWeight: 700
    letterSpacing: "0.14em"
    textTransform: "uppercase"
rounded:
  sm: "0.45rem"
  md: "0.6rem"
  lg: "0.75rem"
  xl: "1.05rem"
  full: "9999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2.5rem"
components:
  button-primary:
    backgroundColor: "{colors.archive-navy-deep}"
    textColor: "{colors.warm-paper}"
    rounded: "{rounded.full}"
    padding: "0.5rem 1rem"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.archive-navy}"
    rounded: "{rounded.lg}"
    padding: "0.375rem 0.75rem"
  chip-category:
    backgroundColor: "transparent"
    textColor: "{colors.archive-navy}"
    rounded: "{rounded.full}"
    padding: "0.5rem 0.875rem"
  chip-category-active:
    backgroundColor: "{colors.archive-navy-deep}"
    textColor: "{colors.warm-paper}"
    rounded: "{rounded.full}"
    padding: "0.5rem 0.875rem"
  status-pill:
    backgroundColor: "{colors.warm-grey-soft}"
    textColor: "{colors.warm-grey}"
    rounded: "{rounded.full}"
    padding: "0.125rem 0.625rem"
  input-search:
    backgroundColor: "oklch(1 0 0 / 0.8)"
    textColor: "{colors.archive-navy}"
    rounded: "{rounded.full}"
    padding: "0 1rem"
  card-glass:
    backgroundColor: "{colors.glass-white}"
    textColor: "{colors.archive-navy}"
    rounded: "1.5rem"
    padding: "1rem"
---

# Design System: IdeaExists

## Overview

**Creative North Star: "The Archive Behind Frosted Glass"**

IdeaExists is a verification-first directory of startups — the product answers one question: *does this startup exist?* The Warm Glass world makes that archive literal: the data lives behind frosted panels you can see dimly before you open them, and every surface reads like a hand-kept card catalog touched by warm light. Light mode is a warm beige desk under deep navy ink; dark mode is a charcoal reading room where the beige comes back as candlelit text. The glass is never cold 2021-dashboard blue-white — it is translucent warmth over calm bases, hairline-bordered, with a soft top-edge highlight like light catching a pane.

The system is deliberately restrained: glass without blob gradients, ease-out motion without bounce, one morphing hero interaction, cards that expand with shared-layout motion. Personality lives in the details — mono "ledger" data runs, deterministic-hue initial avatars, worded status tooltips, and dry-warm curator copy — never in decoration. The interface recedes so the archive and its trust layer lead.

**Key Characteristics:**
- Frosted glass panels on warm bases (beige/navy light, charcoal/beige dark) — no cold blue-white glass, no blob gradients
- The Sky: a scroll-linked background layer — sunset (light) / moon night (dark), subtle, behind the glass, never louder than content
- Two genuine themes, not a flip: each mode inverts the other's identity (navy-on-beige ⇄ beige-on-charcoal)
- Editorial contrast: Space Grotesk display + Plus Jakarta Sans body + Geist Mono for all evidence data
- Status as a trust layer with a voice: dot + label + worded tooltip, color never the only signal
- One signature interaction: the morphing discovery bar; one signature motion system: ease-out only, reduced-motion safe

## Colors

The palette is warm-neutral with a single deep navy anchor (light) that inverts to a beige anchor (dark). Saturation lives in the *status* colors, not the chrome.

### Primary
- **Archive Navy** (oklch(0.32 0.055 262)): the anchor ink. Buttons, active category pill, focus rings, light-mode brand. Deep enough to feel archival, not corporate blue.
- **Beige Primary** (oklch(0.88 0.03 85)): dark mode's inverted anchor — beige buttons with charcoal text, the theme flip made literal.

### Neutral
- **Warm Paper** (oklch(0.953 0.016 82)): light background — warm desk beige, never white-white.
- **Glass White** (oklch(1 0 0 / 0.55)): the light-mode card/panel surface, translucent so the beige breathes through.
- **Warm Grey** (oklch(0.5 0.02 78)): secondary text — the "filed" voice for metadata.
- **Warm Grey Soft** (oklch(0.92 0.018 82)): muted fills, hover beds.
- **Deep Beige** (oklch(0.885 0.022 82)): accent/hover tint.
- **Hairline** (oklch(0.85 0.02 80 / 0.65)): borders and dividers — the glass edge.
- **Charcoal** (oklch(0.212 0.012 60)): dark background — warm charcoal, not black.
- **Warm Beige Text** (oklch(0.93 0.024 85)): dark-mode foreground.

### Named Rules
**The Status-Is-Sacred Rule.** Only three colors may carry semantic meaning — sage (verified), brick (dead), warm grey (unverified) — and they must always appear with a label and/or icon, never as color alone. No decorative use of these three, ever.

**The One Anchor Rule.** Saturation is reserved for the status layer. The chrome is warm neutrals + one anchor hue per theme; introducing a second loud accent breaks the archive's calm and is a smell.

## Typography

**Display Font:** Space Grotesk (sans-serif)
**Body Font:** Plus Jakarta Sans (sans-serif)
**Label/Mono Font:** Geist Mono (monospace)

**Character:** Three-voice editorial system — a grotesque display face for the archive's questions and section titles, a warm readable body, and a mono "ledger" voice for everything evidential (dates, stars, counts, check stamps). The mono data runs are the signature: they make the verification layer look measured and filed, like stamped records.

### Hierarchy
- **Display** (Space Grotesk 700, clamp(2.25rem, 5vw, 3rem), lh 1.1, -0.02em): hero question only ("A human-kept archive of what exists."). Never used for body or UI text.
- **Title** (Jakarta 700, 0.875rem, lh 1.25): card names, dialog titles — bold but small, archival.
- **Body** (Jakarta 500, 0.95rem, lh 1.5): descriptions and prose, ≤52ch in hero, relaxed in cards.
- **Label** (Geist Mono 700, 0.6875rem, lh 1, 0.14em uppercase): ledger headers ("Just added"), section rules, footer stamps.
- **Data** (Geist Mono 500, 0.6875rem, tabular-nums): every date, star count, check stamp, and counter on the page.

### Named Rules
**The Ledger Rule.** If it is a fact with a number or a date, it is set in Geist Mono with tabular figures. If it is prose, it is Jakarta. If it is the hero or a section title, it is Space Grotesk. Three voices, no exceptions.

## Scrollbars

Every scrollable surface carries the themed bar — no native default scrollbars anywhere. Styled globally in globals.css (applies to `*`, so the page, dropdowns, admin panels, and any overflow container all inherit it):

- **Look:** slim 10px WebKit bar with an inset "floating pill" thumb (transparent 2px border + `background-clip: padding-box`), fully rounded, hover darkens. Firefox gets `scrollbar-width: thin` + the same tokens via `scrollbar-color`.
- **Light:** warm grey thumb (`--scrollbar-thumb` oklch(0.62 0.02 78 / 0.4)) on a paper track.
- **Dark:** warm beige thumb (oklch(0.93 0.024 85 / 0.22)) on a faint charcoal track.
- **Exception:** the discovery-bar chip row keeps its own 4px horizontal bar (`.chip-scroll`) — the thin affordance that signals "more to scroll" is intentional and overrides the global rule.

## The Sky (background layer)

A fixed, scroll-linked sky sits behind the archive at `z-[-1]` (`sky-background.tsx` + the `--sky-*` tokens in globals.css). It is the one sanctioned gradient in the system — an authored atmosphere, not a decoration:

- **Light — sunset archive:** a yellow-gold dawn wash at the top of the page. As you scroll, an orange evening wash (`--sky-wash-evening`) crossfades in (0 → 0.75 → 1) so the sky visibly shifts from yellow to orange; the sun disc (`--sky-sun-glow`, 44vmin, near-white-warm core `oklch(0.99 0.09 88 / 1)` with a tight halo) sinks ~36vh and stays hot (opacity 1 → 0.92); a dusk band (`--sky-dusk-glow`, bottom 55vh) deepens from 0.45 → 1. The archive travels from dawn to evening.
- **Dark — moon night:** the wash sinks from warm charcoal into deep indigo. The moon glow (24vmin, `--sky-moon-glow`) **sinks 42vh as you scroll and sets behind the ridge** (0.8 → 1 brightening as it descends); 12 deterministic stars (`--sky-star`) fade in 0.15 → 0.9 as night deepens.
- **The ridge (both themes):** hand-drawn mountain SVGs anchor the bottom 42vh — `mountain-sunset.svg` (warm halo above the peaks, for the light-mode sun) and `mountain-night.svg` (no halo, cool moonlit rim, swapped in under `.dark`). The sun sets behind it in light mode; the moon sets behind it in dark mode. Both fade in over the final scroll stretch (0.45 → 1 progress).
- **Theme switch:** both washes stay mounted, gated by `.dark` with `transition-opacity duration-700` — the sky crossfades with the theme like every other surface.
- **Rules:** transform/opacity only (compositor-friendly, no repaint); sun travel ≤36vh, other amplitudes small; `prefers-reduced-motion` → fully static sky (fixed opacities, no scroll mapping); `pointer-events-none` + `aria-hidden`; all color via `--sky-*` tokens, never literals in TSX. The sky never competes with content — glass cards blur it further via backdrop-filter, so it reads as atmosphere, not imagery.

## Motion

One authored moment per interaction, exponential ease-out (`[0.22, 1, 0.36, 1]`), transform/opacity/blur only. Every open/close animates (dropdowns fade+scale+blur ~180ms, dialogs via tw-animate-css, theme-toggle icon crossfades ~220ms), cards lift on hover (`translateY(-2px)`), and page scroll is inertial via Lenis (lerp 0.09, stopped while modals lock scroll). Everything respects `prefers-reduced-motion` — zero-duration or no effect. No bounce, no springs.

## Layout

Single centered column, max-w-6xl (72rem) container with px-4 gutters. The hero is a centered cluster — deliberately, because the search bar is the product's genuine focal point; asymmetry arrives below via left-aligned ledger section headers. Card grid uses `repeat(auto-fill, minmax(280px, 1fr))` with 1rem gaps — cards stretch to equal heights per row (fixed tagline box enforces uniform 311px rows). Freshness strips are horizontal scroll rows (thin visible chip-scrollbar = affordance). Header and footer are sticky/static frosted bars with backdrop-blur-xl over the page. Content max-widths: hero text 52ch, glass panels max-w-md for dialogs/empty states. Spacing rhythm: 0.25/0.5/1/1.5/2.5rem scale, generous vertical breathing (pb-20 page bottom).

## Elevation & Depth

Depth is **glass, not shadow.** Surfaces float on translucency + blur + a hairline border + an inset top highlight (simulating light catching the pane's top edge). The shared shadow is a soft ambient pool (`0 8px 32px` at ~7% navy tint in light, 45% black in dark). Overlays (detail panel, add dialog) use stronger glass: higher opacity + heavier blur (28px). No hard drop shadows, no stacking elevation — the archive is one layer deep, and modals read as "the same pane, more opaque."

### Shadow Vocabulary
- **Ambient Glass** (`0 8px 32px oklch(0.2 0.03 262 / 0.07)` light / `0 8px 32px oklch(0 0 0 / 0.45)` dark): every glass surface at rest.
- **Inset Highlight** (`inset 0 1px 0 0 var(--glass-highlight)`): the top-edge light catch — what makes glass read as glass rather than flat translucent.

### Named Rules
**The No-Spooky-Shadow Rule.** Shadow is ambient pooling, never a hard cast. No `shadow-lg`-style drop shadows, no elevation ladder — a panel is either glass or overlay-glass, and nothing floats above glass.

## Shapes

The form language is **pill + soft card.** Everything interactive that sits in a bar — search field, category chips, status pills, filter selects, primary buttons — is a full pill (9999px radius). Content containers — cards, strips, dialogs, empty states — are softly rounded rectangles (1.5rem cards, 1.05rem strips). The hue avatar breaks the pill monotony with a `rounded-md` square chip — the one sharp-cornered element, deliberately, as the card's "stamp." Hairline borders (1px at 65–85% opacity) define every glass edge; `rounded-full` on pill elements, never sharp corners on interactive chrome.

## Components

### Buttons
- **Shape:** pills for primary, rounded-lg (0.75rem) for outline/ghost; h-8 sm / h-9 default.
- **Primary:** Archive Navy bg (light) / Beige bg (dark), warm paper text (light) / charcoal text (dark), px-4; hover darkens via opacity/color transition; focus ring `ring/50`.
- **Hover / Focus:** color transitions only (no scale, no bounce); `outline-ring/50` global focus; focus-visible ring 2px.
- **Outline:** transparent glass bg, hairline border, archive-navy text; the standard secondary ("Website", "Code", "Details", "Run verification").
- **Ghost:** text-only, used for "Clear all" in filter bar.

### Category Chips
- **Style:** transparent, archive-navy text, full pill; active state = sliding Archive Navy pill (shared-layout `layoutId` morph) with warm paper text + count in `primary-foreground/70`. Icons allowed (lucide, one set).
- **State:** `aria-pressed` on the active chip; wraps to a second row on desktop, scrolls on mobile; the active chip auto-scrolls into view.

### Status Pill (the trust layer)
- **Style:** dot (6px) + label (+ icon for Verified/Dead); verified = sage tint bg + sage text, dead = brick tint + brick text, unverified = grey.
- **State:** **The unverified pill is a two-step button** — first click arms it ("Confirm?" with a navy dot, tooltip "Click again to confirm — this stamps the entry as human-verified"), second click fires mark-verified; auto-disarms after 4s. The human gate never flips on a stray click.
- **Tooltip:** worded microcopy on every status ("A human checked this on <date> — it's alive." / "Checked 3 times, link dead each time. Filed, never deleted.").

### Search Field
- **Style:** full pill inside the discovery bar, glass-white field, mono text, placeholder "Search the archive…", `focus-within:ring-2 ring/50`.
- **State:** when a query is active, a clear-× button (size-5, bg-muted circle, aria-label "Clear search") appears inside the field — the stale-query escape hatch.

### Cards / Containers
- **Startup Card:** glass panel, 1.5rem radius, 1rem padding, internal gap 0.625rem; header row = hue avatar + name/founded·checked mono line + status pill; tagline 2-line clamped (min-h-9); description line-clamp-3 with "Show more" toggle; footer row = category/language badges + stars (mono) then action row (Website/Code/Details) under a hairline divider. Dead cards: `opacity-85 saturate-[0.55]` — filed, not hidden.
- **Hue Avatar:** rounded-md square, deterministic hue from name hash (pastel chip + dark letter, theme-stable), sizes 6/8/12.

### Inputs / Fields
- **Search:** full pill, glass-white field inside the discovery bar, mono text, placeholder "Search the archive…", `focus-within:ring-2 ring/50`, no visible border (the pill container carries it).
- **Selects (filter bar):** glass pill triggers (h-8 w-32/36, rounded-full), native shadcn dropdown content; labels via aria-label (icon-free).

### Navigation
- **Header:** sticky frosted bar (bg-background/55 + backdrop-blur-xl, hairline bottom border), h-14, max-w-6xl; brand wordmark "IdeaExists" in Space Grotesk bold + tagline (sm+); right cluster = split "Add startup" button + theme toggle.
- **Footer:** frosted bar, mono stamps (startups/verified counts with live dots), mantra "Dead is a status, not an erasure. Kept by a human, checked weekly.", privacy line, admin gear + "Run verification" on the right.

### Signature Component: Morphing Discovery Bar
The product's focal interaction: a single glass panel (max-w-3xl, rounded-[1.75rem] — a 28px radius that reads as a pill on one row and stays correct when chips wrap) containing (a) an always-visible search input (h-11, glass-white field, mono, with a clear-× when a query is active) and (b) a category chip row whose active pill **morphs** between chips via shared-layout motion (ease-out 0.35s, zero-duration under reduced motion). Chips **wrap to a second row on desktop** so no category hides behind scroll; on mobile the row scrolls horizontally (thin visible scrollbar + wheel + drag), and the active chip auto-scrolls into view on selection. LayoutGroup-wrapped so the panel transitions smoothly; this is the one hero moment and it must stay the only one.

## Do's and Don'ts

### Do:
- **Do** set every date, count, star, and check stamp in Geist Mono with tabular-nums — evidence is ledgered.
- **Do** give every status a dot + label + worded tooltip; the trust layer is visible card copy, not hidden metadata.
- **Do** keep dead entries on the page — filed treatment (desaturate/fade), never deleted, never joked about.
- **Do** use ease-out `[0.22, 1, 0.36, 1]` for motion, 0.35s, transform/opacity only; respect `prefers-reduced-motion` (opacity-only or zero-duration).
- **Do** let the warm base show through — cards are translucent glass on beige/charcoal, not opaque white boxes.

### Don't:
- **Don't** add decorative gradients, blob backdrops, or cold blue-white glass — the antislop tell this world exists to avoid. The single exception is the authored Sky layer (see above): an atmosphere with its own tokens and motion rules, never a random gradient.
- **Don't** use bounce or spring easing anywhere in this project.
- **Don't** use the status colors (sage/brick/grey) decoratively, or without their label/icon.
- **Don't** fetch favicons or external avatars for cards — the archive is local and the privacy line is a brand promise.
- **Don't** center more elements to "fix" the hero — asymmetry comes from left-aligned ledger rules, not more centering.
- **Don't** put emoji in status pills — status semantics stay icon/label-only; emoji (one per concept) is reserved for strips/actions ("Add startup 👋" register).
