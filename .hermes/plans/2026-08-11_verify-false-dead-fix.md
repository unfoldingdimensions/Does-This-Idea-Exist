# Fix: false dead-flips + trust-weighting + batch approval

Date: 2026-08-11 · Status: approved by user (walkthrough) · Scope: backend verify pipeline, human gate, search sort, category icons

## Background

The website liveness check counted ANY non-2xx/3xx as a strike. Cloudflare bot-walls (403) dead-flipped healthy companies: **Capterra** (cf=5→dead) and **WHOOP** (cf=3→dead, flipped 2026-08-11 06:45). Product Hunt (human-verified) sits at cf=2 — next pass would file a human-confirmed company dead. The 1,292-row archive now has a ~970-row suggested queue from the topstartups batch.

## Decisions (user-approved)

1. **What counts as dead:** only a genuine `404/410` earns a strike. 401/403/429/5xx, timeouts, DNS errors → **skip with note** (never a strike). `BlockedAddressError` stays a failure (junk data signal).
2. **Human stamp outranks automation:** `verified=1` rows never accumulate auto-strikes and never auto-flip; failed checks on them surface in `failed_list` as re-check items.
3. **Revive semantics:** `mark_verified` (and any revive) resets `check_failures=0` — human judgment resets the strike counter.
4. **Restore:** one-shot script revives WHOOP + Capterra (`status='active'`, `cf=0`, `verified` untouched) and zeroes bot-wall strikes on active flagged rows.
5. **Suggested queue:** batch approval at the created-day boundary — `approve` gains `created_after`/`created_before`; UI groups suggested by day with one "Approve batch (N)" action per group. Keep ids/approve_all.
6. **Top sort:** trust-weighted — verified first, then stars, then name.
7. **Icons:** remap `CATEGORY_ICONS` to the live backend whitelist (devtools, finance, ecommerce, social, media, desktop, freelance + existing matches).

## Files

- `backend/app/verify.py` — tri-state `check_url_ok`; no-strike verified rows; skip resets streak; `list_suggested` + `created_at`; `approve_suggested` window mode
- `backend/app/main.py` — `mark_verified` resets cf; `ApproveIn` window fields
- `backend/scripts/restore_false_dead.py` — new revive/zero-strike script (kept, trust-layer repair tool)
- `backend/tests/smoke.py` — stub updates (3-tuples) + pins: 403-never-strikes, verified-no-flip, window-approve
- `frontend/lib/types.ts` — `SuggestedStartup.created_at`
- `frontend/lib/api.ts` — `approveSuggested` window params
- `frontend/lib/search.ts` — top sort trust-weighted
- `frontend/app/page.tsx` — icon map remap + imports
- `frontend/components/admin-verify-section.tsx` — day-grouped batch approve UI
- `CHANGELOG.md`, `README.md` — semantics + API table

## Verification

- backend smoke: new pins green, old suite green
- full `npm test` at root
- DB: WHOOP + Capterra active cf=0; suggested queue unchanged in size; Product Hunt cf=0 (bot-wall strike cleared)

## Open questions (resolved)

- Skip resets the strike streak (consecutive-failure contract preserved) — lenient side.
- Verified-row failures keep `check_failures` untouched (never strike, never auto-clear).
