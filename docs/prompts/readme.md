# Phase Prompts — how to use them

Each file in this folder is a **copy-paste prompt** you hand to a fresh chat (Claude Code, Cursor, AutoClaw, etc.) to execute one phase of `IMPLEMENTATION-PLAN.md`. The chat should be running **inside this repo** so it can read the referenced files and run commands.

## Standing rule (applies to every phase prompt, going forward)

1. **Branch off `main`** — never commit to `main` directly.
2. **Open its own pull request** into `main` at the end of the phase, with a clear title and description.
3. **Conventional Commits** for commit messages, plus AI attribution:
   ```
   Co-Authored-By: <agent model name and attribution byline>
   ```
4. **Backend-first** — no phase may touch `frontend/` until the Phase 5 gate in `docs/phase-ledger.md` is PASS.
5. **Record the result** — each phase updates `docs/phase-ledger.md` (status + evidence + date) before the PR is opened.

## Naming convention

- Branch: `phase/<NN>-<slug>`, e.g. `phase/01-schema-evidence-foundation`.
- PR title: `Phase <NN>: <short description>`.
- Commit prefix: `feat:` / `fix:` / `test:` / `chore:` as appropriate.

## Files

| File | Phase |
|---|---|
| `phase-00-onboarding-baseline.md` | 0 — onboarding & baseline |
| `phase-01-schema-evidence-foundation.md` | 1 — schema & evidence foundation |
