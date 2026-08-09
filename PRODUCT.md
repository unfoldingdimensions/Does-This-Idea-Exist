# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary user today: **the owner ("the Curator")** — a single person running a local directory to settle the question "does this startup exist?" before spending time on an idea. They seed entries, review the LLM-drafted profiles, mark things verified, and run weekly link checks.

Future audience (when hosted): founders and indie hackers checking whether an idea, name, or project already exists — the audience the research memo's evidence was gathered for. They search, browse, and trust the verification labels; they do not seed or administer.

## Product Purpose

A local, verification-first directory of startups: what they do, their website, their GitHub repo. It answers the question in the title — *does this startup exist?* — with an answer a human can trust, because every listing carries a verification status backed by a human check, not a crawler.

Success means: the owner can look up any idea and get an accurate, current answer (exists / alive / dead), and trust the status layer because verification is a real human gate with a visible paper trail.

## Positioning

**Verification-first, honesty-as-feature.** Neighboring directories index loudly and verify softly; this one makes the human gate the product: "checked by a human, not a crawler", 3 strikes to Dead, **dead entries are archived, never deleted** ("Dead is a status, not an erasure"). Privacy is part of the position too — no accounts, no tracking, searches stay on the machine (until hosting happens, the code keeps that posture).

## Operating Context

- Local-first: FastAPI backend on **:8020** + Next.js 16/shadcn frontend on **:3023**, SQLite at `backend/data/ideasexist.db` (git-ignored).
- Weekly verification pass (`/api/verify/run`): re-checks links; 3 consecutive failures → `dead`; never deletes.
- Owner-only admin (footer gear → Admin panel, unlocked by `ADMIN_TOKEN` from `backend/.env`): batch seeding from a bundled famous list, GitHub search, pasted URL list, or topstartups.io scrape; per-run cap 1–500, fails loudly (nothing swallowed), idempotent re-runs (`reuse_profile`).
- Seeded entries land **unverified**; the human gate is "Mark verified" on the card.
- Voice register: dry-warm curator microcopy ("Search the archive…", "Filed, never deleted."), signed footer "— The Curator". Joke about the curator's process, never about the entries.

## Capabilities and Constraints

- Client-side Fuse search with relevance ranking (query wins over sort while sort is default; explicit sort still honored), category/founded-year/status filters, sort, windowed pagination (24/page, `?page=` back-button-safe URL state).
- Add flows: by GitHub repo or by website (homepage fetch + Wayback date + LLM profile via deepseek-v4-flash through opencode.go).
- Statuses: verified / unverified / dead, shown as dot + label + worded tooltip; color never the only signal.
- Constraints: no favicon fetching (privacy — must not regress); no bounce easing, ease-out only; reduced-motion respected; both themes (beige/navy light, charcoal/beige dark) must stay verified; status semantics locked (green/red/grey).
- LLM enrichment is the only cloud dependency today; `GITHUB_TOKEN` needed for >50 repo fetches/hr.
- Working title: **IdeaExists** — name is not final, so copy should not treat it as a locked brand claim.

## Brand Commitments

- Working title "IdeaExists" (not final — do not over-invest in the wordmark).
- Curator voice and sign-off ("— The Curator") as established in the UI personality pass.
- Mantra "Dead is a status, not an erasure." and hero line "A human-kept archive of what exists."
- No-tracking stance stated in the footer ("No accounts. No tracking. Searches stay on this machine.").

## Evidence on Hand

- `backend/data/seed_famous.json` (~65 well-known startups) and `seed_design_library.json`; live SQLite DB with seeded entries and `verify_log` history.
- `docs/research-features-ux.md` + `docs/research-ui-personality.md` — primary-source research (TAAFT, YC, madeinnigeria, svgl, killedbygoogle, etc.) with citations; the persona/voice guidance stays binding.
- `.hermes/design/smell-report.md` + `checkup-report.md` — antislop audits; the "what NOT to do" list stays binding.
- `dogfood-output/` — prior dogfood/adversarial review reports (6 bugs + 1 GREEN already fixed; see `.hermes/plans/2026-08-10_100000-fix-review-bugs.md`).
- `.hermes/plans/` — plan history incl. the implemented Warm Glass v2 plan.

## Product Principles

1. **Trust is the product.** The verification layer (human gate, 3 strikes, never delete) outranks any convenience; never blur or joke about verification facts.
2. **Local-first and honest about it.** No accounts, no tracking, no favicon fetching; privacy is a feature stated in the UI, and hosting later must not quietly drop this posture.
3. **Dead entries are archived, not erased.** The graveyard is first-class: quiet archival styling, never mockery.
4. **Fail loudly.** Seed and verify errors are surfaced, counted, and listed — nothing swallowed; a clear 400 beats a silent clamp.
5. **Additive and reversible.** Keep working defaults, add parallel options; changes must not destroy data or require migrations (DB backups before merges).

## Accessibility & Inclusion

- WCAG AA contrast (4.5:1) for text in both themes; status meaning carried by icon/label + color, never color alone (colorblind-safe pairs verified).
- Keyboard-complete primary flows (search, filters, expandable detail with Escape + focus restore, add dialog); visible focus indicators.
- `prefers-reduced-motion` respected (opacity-only reveals, backdrop-blur off).
