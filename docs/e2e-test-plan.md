# End-to-End Test Plan

**Status:** `run` — Phase 8 executed this plan end to end on 2026-09-17 and is **PASS** in `docs/phase-ledger.md` (see §Phase 8 evidence). The three corrections in the boxed note below were applied in the same branch, after the run falsified the step statements they replace. **Purpose:** one complete backend→frontend journey, run once in sequence, with every step's actual output recorded — the final release gate.

---

## 1. The journey (run in this exact order)

Run against the full stack (backend on `:8020`, frontend on `:3023`, real DB), and record each step's output verbatim in `docs/phase-ledger.md`.

> **Phase 8 correction (2026-09-17).** Three statements below predated the code they describe and were corrected against the running stack. (a) Step 3 said a `GET /api/startups/{slug}` **triggers** the capture; the slug endpoint is a **pure read** — the just-in-time trigger is `POST /api/compare` (F-22) or the admin capture button, both calling `capture.start_capture()`. (b) Steps 4–6 predated the **per-draft founder token**: `POST /api/founder-app` returns a one-time `founder_token`, and every later read / confirm / publish / compare / export for that draft must send it as `X-Founder-Token` or the call is `403`. (c) Step 6's export needs `?you=<id>&competitors=<ref>` and the same token. What follows is the corrected journey.

1. **Seed a competitor.** `POST /api/seed/website` with a real URL → record the returned profile and its `provenance` flags. (A URL already in the archive **updates** the existing row: `_inserted: false`. A URL not present **adds** a row.)
2. **Verify liveness.** Trigger a verification pass and record that the entry's `last_checked` updates, that the two trust signals read correctly (admin-verified from the human stamp, machine-verified from the pass), and that a live entry does not dead-file.
3. **Open the teardown (just-in-time).** `GET /api/startups/{slug}` twice for a competitor never captured → record that the read is idempotent and does **not** capture; then trigger the capture through its real trigger (`POST /api/compare` on the founder's first request, or `POST /api/admin/capture/{id}`) and record that a second trigger inside the window is served `cached` (the cache window is **7 days**). Record pricing plan-by-plan, features, positioning, and the sourced "doesn't do" list — each entry an observation naming the page it came from. Confirm **no badge is rendered against a claim** and that `machine_verified` / `machine_verified_at` are explicit fields. Record the review-derived items that will become dimension 7.
4. **Enter the founder's app.** Submit via one of the three paths (URL / form / agent-JSON) → record the draft (and the one-time `founder_token`, never printed) → **confirm** → record the confirmed state and that the record lives in the founder store, not the archive. Record the checkbox case: absent for a link-less profile (comparison only, stated plainly), present when a link exists → **pending** in the admin queue → **approved**.
5. **Run comparison.** `POST /api/compare` with `{you: {...}, competitors: [...]}` (plus `X-Founder-Token`) → record the gap table's groups, including **dimension 7** ("their users ask for it") and confirm sourced cells and `unknown` handling.
6. **Export.** Fetch `/api/export/{markdown|json|csv}?you=<id>&competitors=<ref>` (plus `X-Founder-Token`) → record that each parses.
7. **Search-with-reasons.** Query `/api/search` → record a result with its `reason`.
8. **Frontend pass-through.** Load `/`, `/products/<slug>`, run the founder-app flow in the browser UI, view the gap table, click export → record the visible results.

## 2. Pass criteria (the final gate)

Every step returns the expected result with **no failures, no skipped steps, and no "mostly works"**:
- The gap table is correct and sourced; `unknown` is shown as unknown.
- Every negative in the run traces to a page that enumerates; no negative was printed from a 404 on a guessed URL.
- The trust signals are distinct and correct: no badge appears against a claim, and a stale check shows Machine Verified as lapsed while the record stays Admin Verified.
- No founder-store record appears in `/api/startups`, `/api/stats` or `/api/categories` at any point in the run.
- Export files parse.
- The frontend renders the same data the backend returned (no drift).
- Zero console errors on the key pages.

## 3. Record

`docs/phase-ledger.md`, Phase 8 row: `PASS` + the full step-by-step output + date.

---

## 4. Failures

If any step fails, the whole loop is re-run after a fix; a partial run is never recorded as `PASS`. A failure is reported as the first sentence of the close-out, with the exact step and output.
