# Handoff — resume this project from a clean orchestrator chat

**For:** a new orchestrator chat with no memory of prior conversations.
**One-sentence mission:** implement the IdeaExists competitor-teardown product backend-first, gate frontend on a green backend, and record every phase in the ledger.

---

## 1. Start here (read in this order)

1. `IMPLEMENTATION-PLAN.md` — the phase list, order, and exit gates. **This is the contract.**
2. `docs/codebase-comprehension.md` — what the code actually is today.
3. `reworked-revamp-plan.md` — what to build and why (product decisions are already made).
4. `docs/teardown-spec.md` + `docs/gap-table-format.md` — the exact teardown input/output shapes.
5. `docs/backend-checklist.md` — the itemized feature + test spec (`F-01`–`F-18`).
6. `docs/frontend-plan.md` and `docs/e2e-test-plan.md` — gated on the backend gate.
7. `docs/phase-ledger.md` — current status of every phase. **Gating decisions come from here.**

## 2. The hard rules

- **Order is fixed:** backend build (Phases 1–4) → backend functional test gate (Phase 5) → frontend (6) → frontend tests (7) → end-to-end (8).
- **Frontend is `blocked` until Phase 5 is `PASS`.** Do not create/edit anything under `frontend/` before that.
- **Every phase writes to `docs/phase-ledger.md`** (status + evidence + date). No "in my head" state.
- **A phase is PASS only with recorded evidence**, not an assertion.

## 3. Decisions already made (do not re-litigate)

- Product = competitor teardown + you-vs-them gap table; "does this startup exist?" stays the entry point.
- Teardown MVP fields: pricing (full plan-by-plan) · flat 5–10 features · one-line positioning · 3–5 sourced "doesn't do" claims · gap table.
- Founder's own app: URL / form / agent-prompt, **always confirm before diff**.
- Gap table is facts only, every cell sourced or `unknown`; no AI verdict.
- Local-first, no accounts, no tracking; human-gate/verification semantics unchanged.
- Stack is fixed by the repo: FastAPI + SQLite + Next.js 16 + shadcn.

## 4. Stack & commands

- Backend: `cd backend` → `.venv/Scripts/python.exe` (Windows) · run `python -m tests.smoke` for the existing suite · server: `uvicorn app.main:app --port 8020 --workers 1`.
- Frontend: `cd frontend` → `npm run dev` (port 3023).
- Root test runner: `npm test` (Windows-only; runs backend smoke + sort check + frontend lint/build + e2e-verify).
- DB: `backend/data/ideasexist.db` (git-ignored). Never run a migration against it without a backup first.

## 5. Environment

- `backend/.env` needs `ADMIN_TOKEN` and `OPENCODE_GO_API_KEY` (LLM). `GITHUB_TOKEN` optional.
- Baseline data (expected): ~1,282 filings · 1,278 verified · 0 dead · 57 repos.

## 6. Resume checklist (what to do first)

1. Open `docs/phase-ledger.md` and find the first phase that is not `PASS`.
2. Re-read that phase in `IMPLEMENTATION-PLAN.md`.
3. Execute its tasks; run its exit-gate evidence; record `PASS`/`FAIL` in the ledger.
4. Repeat. Never jump a gate.
