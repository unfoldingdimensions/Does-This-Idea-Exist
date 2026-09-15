# Phase 0 Prompt — Onboarding & Baseline

Copy everything below the line into a fresh chat that is running **inside this repo** (`E:\New-Personal-Projects\Does this Startup Exist`).

---

You are the **project orchestrator** for **IdeaExists**, starting a backend-first, phase-by-phase implementation. Phase 0 is onboarding and baseline: you read the plan, measure the current state, and open the audit trail. **You change no application code in this phase.**

## Standing rule (applies to this and every phase)
Work on a branch off `main` — never commit to `main` directly. At the end, push your branch and open a pull request into `main` with a clear title and description. Use Conventional Commits, and include AI attribution on every commit:

```
Co-Authored-By: <your model name and attribution byline>
```

## Step 0 — orient (do not skip)
Read these files, in this order:
1. `IMPLEMENTATION-PLAN.md` — the phase list, the strict order, and every exit gate. **This is the contract.**
2. `docs/handoff.md` — how to resume and the decisions already made (do not re-litigate them).
3. `docs/codebase-comprehension.md` — what the code actually is today.
4. `reworked-revamp-plan.md` — what to build and why.
5. `docs/teardown-spec.md` + `docs/gap-table-format.md` — the exact teardown input/output shapes.
6. `docs/backend-checklist.md` — the itemized backend features (`F-01`–`F-18`).
7. `docs/phase-ledger.md` — the audit trail you will maintain.

## Git setup
```
git fetch && git checkout main && git pull
git checkout -b phase/00-onboarding-baseline
```

## The work (documentation + measurement only — no application code)

1. **Restate the mission in 2–3 lines**: goal, the strict order (backend 1–4 → backend test 5 → frontend 6 → frontend test 7 → E2E 8), and done-when.
2. **Capture the test baseline.** Run the existing suite and record its actual pass/fail:
   ```
   npm test
   ```
   (If `npm test` does not run on this machine, fall back to the in-process suite:
   `cd backend` then `..\backend\.venv\Scripts\python.exe -m tests.smoke`.)
   Record the exact result — do not assert; paste the output summary.
3. **Capture the data baseline.** Run the read-only baseline reporter:
   ```
   backend\.venv\Scripts\python.exe scripts\phase0-baseline.py
   ```
   (fallback: `python scripts\phase0-baseline.py`).
   It prints the archive totals, tables, categories and sources, then either
   `[baseline] matches expected baseline` or a `[baseline] DRIFT` block.
   Expected: ~1,282 filings · 1,278 verified · 0 dead · 57 with a GitHub repo · tables `startups, verify_log, jobs`.
   **If it reports drift, say so first** — a difference is information, not a failure.
   The script is read-only (it opens the DB with `mode=ro`) and cannot modify the archive.
4. **Open the audit trail.** Confirm `docs/phase-ledger.md` exists; fill the **Phase 0** row with `PASS`, the evidence (the two commands above + their real outputs + date), and leave Phases 1–5 `pending` and Phases 6–8 `blocked`.
5. **Report the current state honestly.** If anything you found contradicts the plan (a missing file, a failing test, a different row count), that is the first sentence of your report.

## Verification you must record (the exit gate)
The Phase 0 row in `docs/phase-ledger.md` must contain: the test-baseline command + real output, the data-baseline command + real numbers, and the date.

## Done-when
- Branch `phase/00-onboarding-baseline` is pushed and a PR is open into `main` (title `Phase 0: onboarding & baseline`), and it is merged before Phase 1 starts (Phase 1 depends on the ledger being on `main`).
- `docs/phase-ledger.md` Phase 0 row = `PASS` with baseline evidence.
- No application code was changed.

## Do not
- Change any file under `backend/app/` or `frontend/`.
- Commit to `main`.
- Start Phase 1 (or any later phase) work.
- Make product decisions — they are already made and recorded in `reworked-revamp-plan.md` and `docs/discussion-record.md`.
