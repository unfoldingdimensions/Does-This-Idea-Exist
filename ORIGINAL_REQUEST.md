# Original User Request

## Initial Request — 2026-08-13T18:25:51Z

Revitalize the IdeaExists ("Does this Startup Exist") web archive with living animations, rich micro-interactions, bespoke animated celestial sun/moon systems, and modern tactile interface polish while preserving the warm-paper / cool-charcoal color identity and glass aesthetic.

Working directory: `e:\New-Personal-Projects\Does this Startup Exist\frontend`

## Requirements

### R1. Living Celestial Sky & Custom Sun/Moon Engine
Enhance the background atmosphere with organic, multi-layered custom SVG sun and moon celestial bodies.
- Light mode (Sunset): Sun with solar rays, subtle orbital/mouse parallax, warm pulsating corona, and dynamic atmospheric dusk shifts.
- Dark mode (Moon Night): Detailed luminous moon with organic crater topography, ethereal halo glow, multi-layered parallax starfield with occasional shooting star streaks and twinkling constellations.
- Ambient idle breathing and continuous subtle life so the viewport never feels frozen when the user stops scrolling.

### R2. Bespoke Animated Celestial Theme Toggle
Replace the standard icon-swap theme button with a signature, tactile morphing celestial toggle:
- Animated transition where the sun's rays fluidly retract and morph into a glowing crescent moon, accompanied by micro-burst stardust sparks.
- Smooth tactile hover state (magnetic pull, subtle glow flare, springy press).

### R3. Fluid Micro-Interactions & Spotlight Glass Cards
Elevate all startup cards and interactive elements with modern, tactile feedback:
- Mouse-following radial spotlight highlight and subtle 3D tilt on card hover (`translateY` + glass rim illumination).
- Springy, tactile hover states on Action buttons (Website, Code, Details), HueAvatars, and Category badges.
- Enhanced Verification / Trust Stamp animation with a satisfying archival stamp impact, ripple glow, and status tooltip polish.

### R4. Discovery Bar & Interactive Atmosphere Polish
Infuse the search and filter bar with responsive visual feedback:
- Subtle focus beam / shimmering glass ring on the search pill when active.
- Fluid morphing and tactile spring physics on category chip selection.
- Keyboard shortcut indicators (`/` or `Cmd+K`) with interactive press states.

## Acceptance Criteria

### Celestial & Visual Liveliness
- [ ] Sun and moon feature custom multi-layered SVG graphics with active ambient animations (corona shimmer, rotation/breathing, starfield depth) that run smoothly even when idle.
- [ ] Theme toggle morphs between sun and moon with custom SVG path/motion transitions instead of standard icon swapping.
- [ ] Background sky responds to gentle mouse parallax or scroll with 60fps compositor-friendly transforms.

### Card & UI Micro-Interactions
- [ ] Startup cards feature dynamic hover lighting (spotlight border / glass reflection) without layout shift.
- [ ] Badges, avatars, and action buttons respond to hover and active tap states with springy, tactile feedback.
- [ ] Status pills and verification transitions have animated visual feedback (ripple/stamp bounce).

### Performance & Accessibility
- [ ] All animations maintain a 60fps frame rate without heavy CPU re-paints.
- [ ] Full compliance with `prefers-reduced-motion` (graceful fallback to calm, static visuals).
- [ ] No regression in keyboard accessibility, focus rings, or screen reader announcements.
