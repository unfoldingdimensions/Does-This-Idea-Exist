# §7.4 — LLM metering + the spend brake: plan and resume notes

**Status:** in progress — Tasks 1-3 of 9 done (Phase 1 complete). Tasks 4-9 remain.
**Branch:** `feat/liveness-admission` · **Last commit at time of writing:** `57b8f35` + Task 3
**Working copy:** `.hermes/plans/2026-09-24_llm-metering.md` (gitignored — THIS file is the copy that travels between machines; keep them in step.)

**Trigger:** scale-plan §7.4 ("token accounting, $/row, concurrency cap, per-batch hard budget"). Phase D's entire output is a measured $/row, and `docs/llm-gateways.md` §6 used to state, in writing, that usage/cost accounting was deliberately not included.

---

## Resume here

Everything below is on `feat/liveness-admission`, pushed. To continue on another machine:

```bash
git clone git@github.com:unfoldingdimensions/Does-This-Idea-Exist.git
cd Does-This-Idea-Exist
git checkout feat/liveness-admission          # main does NOT have any of this yet
cd backend && python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements.txt
cd .. && npm ci
./backend/.venv/Scripts/python.exe -m tests.functional     # expect 402 passed
node scripts/verify.mjs                                    # full gate
```

Next task: **Task 4 — the budget setting + `BudgetExceeded`** (Phase 2 begins there).

---

## What has shipped

| Task | Commit | What it delivers | Gate |
|---|---|---|---|
| 1 | `7a039f8` | `backend/app/meter.py` + the `llm_usage` table (one additive table; `db.init_db()` runs its DDL by late import). `record()` never raises but never swallows; reads: `spend_usd`, `rows`, `by_purpose`, `by_model`, `job_summary`, `count`, `table_present`. | functional 341→**358**; live-archive additivity probe PASS (1,258 rows / 43 cols / identical digest → +1 table) |
| 2 | `57b8f35` | `llm_json` records **one row per ATTEMPT** (finally block: a failed attempt, empty content and unparseable JSON are all billed and all recorded). `meter.usage_from_response` tolerates OpenAI + DeepSeek cache shapes and returns NULL for junk. Attribution by ContextVar: seeder stamps `job_id`, enrich stamps `purpose`, capture stamps `startup_id`. | functional 358→**382**; smoke ALL PASS |
| 3 | `27bccb2` | The rate table: cited built-in defaults in `meter.DEFAULT_RATES`, operator edits stored in the settings store (`load_rates`/`save_rates`/`clear_rates`/`rates_source`), `cost_of`/`price_attempt` returning `(cost_usd, price_used)` where `price_used` is `<model>@<version>` or `unpriced:<reason>`. `gateways.get_setting/set_setting` are the public settings accessors. | functional 382→**402**; smoke ALL PASS |
| 4 | *(this commit)* | **The spend brake.** `llm_budget_usd` in the settings store (NULL default = unlimited), a per-job `params["budget_usd"]` override, `meter.BudgetExceeded` raised by `meter.check_budget()` **before every attempt and before any socket**, `GET`/`PUT /api/admin/llm/budget`. Seeder and capture job loops refuse to count a braked candidate as a failure and stop the batch instead, recording `result.stop_reason="budget"` + spend/cap/rate version. | functional 402→**429**; smoke ALL PASS |

### Task 4's interim status (Task 5 will change this)

A braked job currently ends as `status="failed"` with `result.stop_reason="budget"` and the figures in `result` (+ an `errors` entry starting `budget: `). That is an honest stop, not a lie about what happened — but **Task 5 replaces it with the parked `paused` state** that an operator can Resume. Everything already written stays in both versions; nothing rolls back.

## The three rules the ledger keeps (each pinned by a test)

1. **`record()` never raises** — a ledger write must not fail an enrichment — but a failure bumps `failure_count()`, which the log, the response and (Task 7) the panel surface. A quiet hole in a cost ledger is the failure mode this feature exists to close.
2. **Rows are per ATTEMPT, not per call.** `llm_json` retries once and the provider bills both attempts. `job_summary` reports attempts, retried attempts and DISTINCT rows touched separately, so a retry cannot inflate $/row.
3. **NULL means "not known", never zero.** No usage block → NULL tokens + `usage_missing=1`. Unknown/unfilled model → NULL cost + a stated reason. Nothing is ever estimated into a number that looks measured.

## Rate provenance (read 2026-09-28)

| Model | Input | Output | Cached read | Source |
|---|---|---|---|---|
| deepseek-v4-flash | $0.14 | $0.28 | $0.028 | opencode.ai/docs/zen |
| deepseek-v4-pro | $1.74 | $3.48 | $0.145 | opencode.ai/docs/zen |
| glm-5.3-flash | $0.15 | $0.50 | $0.03 | opencode.ai/docs/zen |
| glm-5.3 | $1.40 | $4.40 | $0.26 | opencode.ai/docs/zen |
| kimi-k2.5 | $0.60 | $3.00 | $0.10 | opencode.ai/docs/zen |
| qwen3.7-plus | $0.40 | $1.60 | $0.04 | opencode.ai/docs/zen |
| claude-sonnet-4-5 | $3.00 | $15.00 | $0.30 | opencode.ai/docs/zen (≤200K tier only) |
| gemini-3.5-flash | $1.50 | $9.00 | $0.15 | opencode.ai/docs/zen |
| **gemini-2.5-flash** | **unpriced** | **unpriced** | **unpriced** | **Google's pricing page no longer names 2.5 Flash in its tables — seeded NULL + `verified: false` + a note rather than a guessed number** |

Per 1M tokens, USD. Every row stores its source and the date it was read.

**Two caveats the panel and the report must repeat:**
- A $ figure from this table is the **marginal cost at published list prices, not an invoice.** OpenCode Go is a flat-rate $10/month subscription, so a Go-routed call bills nothing per token; provider discounts, batch tiers and routed fallbacks do not appear here.
- The live install's active gateway is **Google Gemini / `gemini-2.5-flash`**, whose rate row is deliberately empty. Until it is filled in, Gemini-routed calls are recorded **unpriced** (`unpriced:empty-rate`) — honest, and visibly actionable in the panel.

## Architecture decisions (all confirmed with the user 2026-09-24)

1. Meter at the choke point (`llm.llm_json`), attribute by context — not per call site.
2. Metering never breaks a call, and never silently swallows a failure.
3. Rates are data; an unknown model costs NULL, never a guess; every row stores the rate it used.
4. The budget is per job, NULL by default, and it **PARKS — it does not fail**: `paused` at the next per-candidate boundary, keeping rows already written. (Task 4-5.)
5. `paused` counts as active for exclusivity — a paused job holds its kind's slot. (Task 5.)
6. Cancel is a live, persisted flag the running worker checks each iteration. (Task 6.)
7. Phase D's deliverable is a first-class read: `meter.job_summary(job_id)`. (Task 8.)

## Remaining tasks

- [ ] **Task 4 — budget setting + `BudgetExceeded`.** `llm_budget_usd` in the settings store (NULL default = unlimited, so an install that configures nothing behaves exactly as today), `meter.check_budget(job_id)` before every attempt, an optional per-job `params["budget_usd"]` override, admin read/write endpoints. Acceptance: NULL budget pinned identical to today; an exceeded budget refuses **without opening a socket**; the refusal names spend, cap and rate version.
- [ ] **Task 5 — the `paused` state.** Seeder + capture loops catch `BudgetExceeded` at the candidate boundary and persist `status="paused"` with spend/cap/reason, keeping everything written. `recover_interrupted_jobs()` must leave paused jobs alone; `has_active_job`/`try_enqueue_exclusive` treat paused as active.
- [ ] **Task 6 — cancel + resume.** Persisted cancel flag checked each iteration (queued/paused jobs cancel immediately), `POST /api/admin/seed/{job_id}/cancel`, `POST /api/admin/seed/{job_id}/resume` re-enqueuing the remaining work (already-filed candidates are skipped, never re-billed).
- [ ] **Task 7 — `/api/admin/usage` + a new Usage tab.** Totals (today / 7d / all), per-purpose and per-model breakdowns, last-job tokens/row + $/row, metering-failure count, the budget control, the RATE EDITOR (with each row's source/date), and a parked-job banner with Resume/Cancel.
- [ ] **Task 8 — the $/row report Phase D will quote.** Calls/attempts, rows, tokens/row, cached share, $/row, retried share, metering-failure share, rate version used. A ledger with `usage_missing` rows must say so instead of printing a confident number.
- [ ] **Task 9 — docs.** `docs/llm-gateways.md` §6 loses "no usage/cost accounting"; README API table; scale-plan §7.4 struck with measured numbers; CHANGELOG; phase-ledger; the job-status vocabulary documented (`queued | running | paused | cancelled | done | failed`).

## Known gaps carried forward

- **Seed-path `startup_id` is NULL by design.** On the seed path the row is upserted *from* the profile the LLM call produces, so the id genuinely does not exist yet. Teardown is fully row-attributed. Phase D's $/row denominator for seed jobs must come from the job's own candidate tally, and Task 8 must say so rather than dividing by a smaller number.
- **The gateway's `usage` block is still unverified** (no paid probe, by decision). `usage_missing` is stored and will be shown as a share; ask for a probe only if Phase D's first real batch is entirely missing.
- Every attempt is priced with one settings-store read plus one small ledger insert. If a 10k batch shows the writes as a bottleneck, Task 8's report measures writes/sec and the fallback is per-job batching (at the cost of a crash's tail).

## Verification, every task

- `backend/.venv/Scripts/python.exe -m tests.functional` and `-m tests.smoke`
- `node scripts/verify.mjs` at checkpoints (adds sort check, lint, prod build, e2e)
- `python scripts/site_liveness_audit.py selftest` at checkpoints (50/50 — metering changes no liveness rule)
- One commit per task; push after each
