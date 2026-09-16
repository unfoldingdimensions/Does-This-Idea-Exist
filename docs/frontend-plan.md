# Frontend Implementation & Test Plan

**Status:** `implemented` — Phase 6 is **PASS** in `docs/phase-ledger.md` (2026-09-16), and §2 below is the record of what was built.
**Rule (historical):** no frontend file may be created or edited, and no frontend task scheduled, while this plan is `blocked`. The orchestrator checks the ledger before touching `frontend/`. That gate was satisfied at Phase 5 `PASS` (2026-09-16).

> **Phase 6 correction (2026-09-16).** §1 listed the consumable surface as the endpoints, the two trust signals and the founder-store endpoints — but **the `evidence` rows were readable by nothing**. The only reader in the whole backend was the compare path's `them_side()`, and §2 item 1 needs those rows to render the sourced "doesn't do" list. The read was added on its own branch and PR (`fix/startup-evidence-endpoint`, #14: `GET /api/startups/{slug}` now carries `evidence`, +4 checks in `backend/tests/functional.py`) rather than inside the frontend branch, per the phase rule. `docs/teardown-spec.md` §2 field 4 was right; the endpoint list here was incomplete.

---

## 1. Precondition (hard gate)

Before any frontend work:
- `docs/phase-ledger.md` shows Phase 5 = `PASS`, with: all `F-01`–`F-24` tests green, the command output recorded, and a real-backend smoke pasted.
- The verified backend endpoints are documented (the frontend consumes exactly these, nothing else): `GET /api/search`, `GET /api/startups/{slug}`, `POST /api/founder-app`, `POST /api/founder-app/{id}/confirm`, `POST /api/compare`, `GET /api/export/{format}`, plus the two trust signals (`admin_verified`, `machine_verified`) and the founder-store endpoints.
- The **compare contract** is `{you: {...}, competitors: [...]}` — the two sides live in different databases (`docs/teardown-spec.md` §3.1), so the frontend never sends a flat id list.

---

## 2. Implementation (Phase 6) — in order

1. **Teardown dossier.** Evolve `components/startup-detail.tsx` into the teardown view. Built as `components/teardown-dossier.tsx` (the record view, reusable by `/products/<slug>`) plus the modal shell in `startup-detail.tsx`; it reads `GET /api/startups/{slug}` **by id** in the modal, so a same-name duplicate group can never resolve to a row the reader did not open: pricing plan-by-plan (with capture date), features (flat list), positioning, the sourced "doesn't do" list (each an observation with the page it came from), liveness, and the **two badges rendered distinctly** — Admin Verified (stable) and Machine Verified (decays, with its date). Badges attach to the record only; a claim cell carries its own source label instead. Reviews feed gap-table **dimension 7** ("What their users ask for") rather than a panel of their own. Renders from the new endpoints, not from the old flat `startups` shape.
1b. **`founded` display fix (backend half of F-04).** `startup-card.tsx` and `startup-detail.tsx` currently render "founded {year}" from a date that may be an RDAP domain registration, and `page.tsx:563` falls back to a hardcoded `"2021"` when the date is null — a fabricated fact. Use `date_source` to label approximated dates honestly, and drop the hardcoded fallback.
2. **Founder-app input.** New `components/founder-app-dialog.tsx` with three tabs — URL / form / paste-agent-JSON — and the **confirm-before-diff** step (the drafted profile is shown for review; the gap table renders only after confirm). Reuses the form field contract in `docs/teardown-spec.md` §3, now including the two store links. **The publish checkbox appears only when a fetchable link exists**, and a link-less submission is a working comparison that says plainly it is never published (no link → no archive entry). The dialog also shows the founder the **derived `archive_status`** (`local_only` / `pending` / `approved` / `rejected`) with the rejection note — there are no accounts to notify them any other way, so this view is the entire feedback loop.
3. **Gap table.** New `components/gap-table.tsx` rendering the groups from `/api/compare` — the three comparison bands plus the demand group (dimension 7, "their users ask for it"); sourced cells show a link, `unknown` cells are shown as unknown (not scored); no verdict line.
4. **Export.** Buttons for Markdown/JSON/CSV wired to `/api/export/{format}`.
5. **Stable routes.** `app/products/[slug]/page.tsx` + a matching route to `/api/startups/{slug}`; "Share Entity" points here instead of `?q=`.
6. **Search-with-reasons.** Show the `reason` string on each result card; keep the existing client-side Fuse path for the small-archive fast path, but render reasons from `/api/search`.
7. **Preserve identity.** WCAG AA in both themes; `prefers-reduced-motion` respected; keyboard/focus reachable; footer still "No accounts. No tracking. Searches stay on this machine."; status pill semantics untouched.
8. **Carry-over from two closed scan PRs (2026-09-15).** Both were real findings opened against the pre-refactor frontend, and both conflict with `main` (`startup-card.tsx` was restructured after they were written), so they were closed and are re-applied here instead:
   - **`rel="noopener"`** — every external-link anchor still carries `rel="noreferrer"` alone: `admin-shared.tsx` (the BucketItem "open" link), `startup-card.tsx` ×2 (Website / Code), `startup-detail.tsx` ×2. Change each to `rel="noopener noreferrer"`. Modern browsers add `noopener` implicitly for `target="_blank"`, so this is hardening rather than a live hole — but it is the declared standard and it is five attributes.
   - **`aria-label` on the four context-switching links** — a screen reader is not told that Website / Code open a new tab. Use the shape the scan proposed: ``aria-label={`Visit ${startup.name} website (opens in a new tab)`}`` and ``aria-label={`View ${startup.name} source code (opens in a new tab)`}``.
   - **Do not resurrect the scans' `.jules/` / `.Jules/` note files.** They are agent scan state, not product files, and neither spelling is in `.gitignore` — the repo keeps machine-local agent state out of the product tree.

**Exit gate:** all eight render against the verified backend in a running dev instance; no hardcoded/mock data.

---

## 3. Tests (Phase 7) — in order

| # | Test area | What it verifies |
|---|---|---|
| 1 | Search-with-reasons | reason strings show; exact-name first; empty-query contract |
| 2 | Dossier → teardown | pricing plan-by-plan + capture date; features; sourced "doesn't do" |
| 3 | Founder-app — URL / form / agent-JSON | each path drafts correctly; form rejected without a feature list |
| 4 | Confirm-before-diff | gap table **does not** render on an unconfirmed profile |
| 5 | Gap table | three bands correct; sourced cells link; `unknown` shown as unknown |
| 6 | Export | each format downloads and parses |
| 7 | `/products/<slug>` | loads the right product; 404 themed |
| 8 | Visual & a11y | light+dark, reduced-motion, mobile viewport, focus/aria, empty/loading/error states; **every external link carries `rel="noopener noreferrer"` and an `aria-label` naming what it opens (Phase 6 carry-over item 8)** |
| 9 | Trust badges | Admin vs Machine Verified render as two distinct signals; a stale `last_checked` shows Machine Verified as lapsed while the record stays admin-verified; **no badge appears against a claim cell** |
| 10 | Link eligibility & consent | the publish checkbox is absent for a link-less profile; a link-less submission still returns a comparison and states it is not published |
| 11 | Reviews / dimension 7 | "what their users ask for" renders as gap-table dimension 7 with sourced items linked to their review, correctly banded (covered by your features → group 1; covered by neither → group 4); **no score or aggregate exists anywhere in the UI** |
| 12 | `founded` honesty | an RDAP-sourced date is not labelled a founding year; no fabricated `"2021"` fallback renders |

**Exit gate:** the frontend test run is green with output recorded in the ledger.

---

## 4. What is explicitly not done in frontend

- No mocking of the backend (the frontend is tested against the verified real backend).
- No new data-fetching architecture — reuse `lib/api.ts` and the existing `Startup`/type surface, extended for the new fields.
- No visual redesign of the archive identity beyond what the teardown requires.
