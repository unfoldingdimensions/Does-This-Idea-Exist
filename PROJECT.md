# Project: IdeaExists Web Archive Revitalization

## Architecture
- **Framework**: Next.js 16.3.0 (App Router) + React 19.2.8 + Motion 13 (`motion/react`) + Tailwind CSS v4 + `next-themes`
- **Color Identity**: Warm Paper Base (`oklch(0.953 0.016 82)`) & Cool Charcoal Base (`oklch(0.215 0.014 262)`) with Glass Specular Highlights
- **Performance Standard**: 60fps compositor-friendly hardware-accelerated transforms (`transform: translate3d(...)`, `opacity`), zero Layout Shift (CLS = 0)
- **Accessibility Standard**: Full `prefers-reduced-motion` compliance, focus-visible rings (WCAG 2.1 3:1 contrast), screen reader `aria-live` announcements, keyboard shortcut traps/handlers (`Ctrl+K` / `⌘K` / `Esc`)

## Code Layout
- `frontend/app/layout.tsx`: Root Layout wrapping `<SkyBackground />`, `<ThemeProvider>`, `<LenisWrapper>`, `<Toaster>`
- `frontend/app/page.tsx`: Single-page app root layout
- `frontend/app/globals.css`: Theme colors, `@property --beam-angle`, CSS keyframes, reduced-motion rules
- `frontend/components/sky-background.tsx`: Living Celestial Sky & Custom Sun/Moon Engine
- `frontend/components/theme-toggle.tsx`: Bespoke Animated Celestial Theme Toggle
- `frontend/components/startup-card.tsx`: Spotlight Glass Cards & Verification Stamp animations
- `frontend/components/ui/morphing-discovery-bar.tsx`: Discovery Bar with Focus Beam Glass Ring & Keyboard shortcut handling
- `frontend/components/filter-bar.tsx`: Category chips with tactile spring physics
- `scripts/verify.mjs`: Test suite runner (`npm test`)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Multi-Layered Custom SVG Sun Engine | Warm golden core, concentric corona, rotating solar rays | M1 | R1 |
| 2 | Multi-Layered Custom SVG Moon Engine | Lunar crater geometry, crescent shadow layer, lunar dust halo | M1 | R1 |
| 3 | Living Celestial Sky Parallax & Breathing | Mouse/scroll parallax (±20px), ambient idle breathing keyframes | M1 | R1 |
| 4 | Deep Starfield & Shooting Stars Engine | Multi-tier starfield depth layers with deterministic twinkle & meteor streaks | M1 | R1 |
| 5 | Fluid Morphing Celestial Theme Toggle | Sun to Crescent Moon SVG morphing with path/ray transformation | M2 | R2 |
| 6 | Celestial Stardust Spark Particles | Radial burst of 8 stardust spark particles on toggle click | M2 | R2 |
| 7 | Tactile Hover & Press Spring Physics | Springy hover/press feedback on toggle, buttons, avatars, badges | M2, M3 | R2, R3 |
| 8 | Mouse-Following Radial Spotlight Highlight | `--spotlight-x`, `--spotlight-y` radial gradient highlight on glass cards | M3 | R3 |
| 9 | Zero-CLS 3D Tilt Card Physics | Perspective 1000px 3D tilt (max 5 deg) with zero layout shift & spring settle | M3 | R3 |
| 10 | Verification Stamp Ripple Glow | Multi-ring sage expansion ripple glow animation on verified badges | M3 | R3 |
| 11 | Focus Beam Shimmering Glass Ring | Hardware-accelerated `@property --beam-angle` conic gradient focus ring | M4 | R4 |
| 12 | Tactile Spring Physics Category Chips | Spring selection animations for filter/category chips | M4 | R4 |
| 13 | Interactive Keyboard Shortcut Indicators | OS-aware `⌘K` / `Ctrl+K` shortcuts, focus routing, and `Escape` handlers | M4 | R4 |
| 14 | E2E Testing Suite & Test Harness | Opaque-box test runner covering Tiers 1-4 feature scenarios | M5 | Acceptance |
| 15 | Adversarial Coverage Hardening | White-box edge-case and performance testing under Tier 5 Challenger loop | M5 | Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Living Celestial Sky Engine | Custom SVG Sun/Moon, solar rays/craters, starfield, parallax, breathing | None | PLANNED |
| M2 | Bespoke Celestial Theme Toggle | Morphing SVG Sun/Moon, stardust sparks, tactile hover/press, next-themes | None | PLANNED |
| M3 | Spotlight Glass Cards & Micro-Interactions | Mouse spotlight, 0-CLS 3D tilt, spring hovers, verification stamp glow | None | PLANNED |
| M4 | Discovery Bar & Atmosphere Polish | Focus beam shimmering ring, tactile category chips, keyboard shortcuts | None | PLANNED |
| M5 | E2E Test Suite & Adversarial Hardening | E2E opaque-box test suite (Tiers 1-4) + Tier 5 Adversarial Coverage Hardening | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### `sky-background.tsx`
- Exports default `SkyBackground` React component.
- Reads `useTheme()` from `next-themes` (`"light"` vs `"dark"`).
- Reads window scroll via `motion/react` `useScroll` and mouse movement for parallax.
- Respects `prefers-reduced-motion: reduce`.

### `theme-toggle.tsx`
- Exports default `ThemeToggle` React component.
- Reads/writes `theme`, `setTheme` from `next-themes`.
- Triggers particle burst state internally with auto-cleanup after 600ms.

### `startup-card.tsx`
- Props: `startup: StartupItem`.
- Tracks relative mouse `(x, y)` on container bounding rect for CSS variables `--spotlight-x` and `--spotlight-y`.
- Internal state for 3D tilt matrix or CSS transforms.

### `morphing-discovery-bar.tsx`
- Ref for input focus. Global `keydown` event listener for `Ctrl+K` / `⌘K` and `Escape`.
- Displays dynamic platform shortcut badge (`⌘K` on Mac, `Ctrl+K` on Windows/Linux).
