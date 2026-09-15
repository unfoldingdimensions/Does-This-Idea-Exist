# End-to-End Test Plan

**Status:** `blocked` until Phase 7 (frontend tests) is `PASS`.
**Purpose:** one complete backend→frontend journey, run once in sequence, with every step's actual output recorded — the final release gate.

---

## 1. The journey (run in this exact order)

Run against the full stack (backend on `:8020`, frontend on `:3023`, real DB), and record each step's output verbatim in `docs/phase-ledger.md`.

1. **Seed a competitor.** `POST /api/seed/website` with a real URL → record the returned profile and its `provenance` flags.
2. **Verify liveness.** Trigger a verification pass and record that the entry's `last_checked` updates and (for a live site) it does not dead-file.
3. **Open the teardown.** Fetch `/api/startups/{slug}` → record pricing plan-by-plan, features, positioning, sourced "doesn't do" list.
4. **Enter the founder's app.** Submit via one of the three paths (URL / form / agent-JSON) → record the draft → **confirm** → record the confirmed state.
5. **Run comparison.** `POST /api/compare` with the founder app + 1–2 competitors → record the three-band gap table and confirm sourced cells and `unknown` handling.
6. **Export.** Fetch `/api/export/{markdown|json|csv}` → record that each parses.
7. **Search-with-reasons.** Query `/api/search` → record a result with its `reason`.
8. **Frontend pass-through.** Load `/`, `/products/<slug>`, run the founder-app flow in the browser UI, view the gap table, click export → record the visible results.

## 2. Pass criteria (the final gate)

Every step returns the expected result with **no failures, no skipped steps, and no "mostly works"**:
- The gap table is correct and sourced; `unknown` is shown as unknown.
- Export files parse.
- The frontend renders the same data the backend returned (no drift).
- Zero console errors on the key pages.

## 3. Record

`docs/phase-ledger.md`, Phase 8 row: `PASS` + the full step-by-step output + date.

---

## 4. Failures

If any step fails, the whole loop is re-run after a fix; a partial run is never recorded as `PASS`. A failure is reported as the first sentence of the close-out, with the exact step and output.
