# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
