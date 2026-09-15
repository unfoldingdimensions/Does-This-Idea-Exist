# Phase Ledger — IdeaExists implementation

**Purpose:** the single audit trail for backend-first gating. Every phase writes a row here; decisions about "can frontend start?" read only from this file.
**Rule:** Phases 6–8 may not be `running` while Phase 5 is not `PASS`.

| Phase | Status | Evidence (command + output summary) | Date |
|---|---|---|---|
| 0 — Onboarding & baseline | pending | | |
| 1 — Schema & evidence foundation | pending | | |
| 2 — Enrichment & teardown fields | pending | | |
| 3 — Comparison, gap table & export | pending | | |
| 4 — Search classification & match reasons | pending | | |
| 5 — Backend functional test gate | pending | | |
| 6 — Frontend implementation (blocked) | blocked | | |
| 7 — Frontend tests (blocked) | blocked | | |
| 8 — Full end-to-end test (blocked) | blocked | | |
| 9 — Handoff & close-out | pending | | |

**Baseline (record in Phase 0):** smoke result · DB counts · date.
