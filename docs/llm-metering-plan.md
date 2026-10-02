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

Next task: **Task 7 — `/api/admin/usage` + a new Usage tab** (Phase 3: totals, per-purpose/per-model breakdowns, the rate editor, the budget control, and the parked-job banner with Resume/Cancel).

---

## What has shipped

| Task | Commit | What it delivers | Gate |
|---|---|---|---|
| 1 | `7a039f8` | `backend/app/meter.py` + the `llm_usage` table (one additive table; `db.init_db()` runs its DDL by late import). `record()` never raises but never swallows; reads: `spend_usd`, `rows`, `by_purpose`, `by_model`, `job_summary`, `count`, `table_present`. | functional 341→**358**; live-archive additivity probe PASS (1,258 rows / 43 cols / identical digest → +1 table) |
| 2 | `57b8f35` | `llm_json` records **one row per ATTEMPT** (finally block: a failed attempt, empty content and unparseable JSON are all billed and all recorded). `meter.usage_from_response` tolerates OpenAI + DeepSeek cache shapes and returns NULL for junk. Attribution by ContextVar: seeder stamps `job_id`, enrich stamps `purpose`, capture stamps `startup_id`. | functional 358→**382**; smoke ALL PASS |
| 3 | `27bccb2` | The rate table: cited built-in defaults in `meter.DEFAULT_RATES`, operator edits stored in the settings store (`load_rates`/`save_rates`/`clear_rates`/`rates_source`), `cost_of`/`price_attempt` returning `(cost_usd, price_used)` where `price_used` is `<model>@<version>` or `unpriced:<reason>`. `gateways.get_setting/set_setting` are the public settings accessors. | functional 382→**402**; smoke ALL PASS |
| 4 | `059a72b` | **The spend brake.** `llm_budget_usd` in the settings store (NULL default = unlimited), a per-job `params["budget_usd"]` override, `meter.BudgetExceeded` raised by `meter.check_budget()` **before every attempt and before any socket**, `GET`/`PUT /api/admin/llm/budget`. Seeder and capture job loops refuse to count a braked candidate as a failure and stop the batch instead, recording `result.stop_reason` + spend/cap/rate version. | functional 402→**429**; smoke ALL PASS |
| 4b | `7d1ae53` | A **blind brake fails closed**: an unreadable ledger raises `LedgerUnreadable` (`kind="metering"`) instead of leaking a raw sqlite error that would have been reported as a failed LLM attempt. `budget_status()` reports `ledger_error` rather than 500ing. | functional 429→**434** |
| 5 | `a06d342` | **The paused state.** `seeder.PAUSED` + the vocabulary in one place (`IN_FLIGHT` / `PAUSED` / `FINISHED`); both job loops park instead of failing; a parked job has **no `finished_at`**; `list_jobs()` files it in the active group (after running/queued); `recover_interrupted_jobs()` leaves it alone by construction and by test; `has_parked_job(kind)` is the panel's new predicate; the frontend's status union, `ACTIVE` set and seed list stop lying about a parked batch (`parkedReason()`), and `verifyResult()` narrows the widened job-result type. | functional 434→**447**; full `verify.mjs` **ALL PASS** (e2e 247) |
| 6 | *(this commit)* | **Cancel + resume.** `seeder.request_cancel` (a queued job is pulled from the queue and cancelled at once; a parked one is cancelled at once; a RUNNING one gets a flag the worker reads at a candidate boundary — never mid-write), `seeder.request_resume` (re-queues a parked job's remaining work, **skipping every candidate it already handled**, with an optional raised budget), `POST /api/admin/seed/{id}/cancel` and `/resume`. Cancel reaches all three job kinds, including the verify pass that walks the whole archive (which records a `partial: true` result). `cancelSeed`/`resumeSeed` + the `JobAction` type ship in the frontend client for task 7's buttons. | functional 447→**466**; full `verify.mjs` **ALL PASS** (e2e 247) |

**Checkpoint 2 (met with task 6):** full `npm test` green, and park / cancel / resume each proven end to end with a stubbed LLM and no network.

### The paused state (task 5), and one deliberate departure from this plan

Everything the plan promised is in: parked at the candidate boundary, rows kept, spend/cap/reason recorded, survives a restart, listed as in-progress.

**What changed while implementing it: a paused job does NOT block its kind.** The plan (and its own risk table) said `has_active_job`/`try_enqueue_exclusive` should treat paused as active. Implementing that before Resume/Cancel exist is a **deadlock** — the exact risk the plan flagged and gated on task 6. Two concrete cases: a parked *capture* would answer every later request for that competitor with "capture in progress" while nothing progressed (a founder waiting on a teardown, with no way to trigger resume); a parked *seed* would veto the operator's next run until they restarted the server.

And even with Resume shipped, blocking buys little: a fresh job has a fresh `params["budget_usd"]`, so it may legitimately run; and if the *global* cap is the reason, the new job simply parks with the same clear message — informative, not harmful. So: `has_active_job` keeps its in-flight meaning, `has_parked_job(kind)` is the new "needs an operator" predicate, and the tests pin that a twin of a parked job's key is still allowed. Task 6 therefore loses the "paused blocks" item.

## The three rules the ledger keeps (each pinned by a test)

1. **`record()` never raises** — a ledger write must not fail an enrichment — but a failure bumps `failure_count()`, which the log, the response and (Task 7) the panel surface. A quiet hole in a cost ledger is the failure mode this feature exists to close.
2. **Rows are per ATTEMPT, not per call.** `llm_json` retries once and the provider bills both attempts. `job_summary` reports attempts, retried attempts and DISTINCT rows touched separately, so a retry cannot inflate $/row.
3. **NULL means "not known", never zero.** No usage block → NULL tokens + `usage_missing=1`. Unknown/unfilled model → NULL cost + a stated reason. Nothing is ever estimated into a number that looks measured.

### The blind brake (found by booting the real app, 2026-10-02)

The live archive has not been booted since before §7.4 task 1, so its `llm_usage` table did not exist yet — and `spend_usd()` raised a raw `sqlite3.OperationalError` on it. Left raw inside `llm_json`, that would have been recorded as a **failed LLM attempt** (a lying error) and the per-candidate handler would have burned the whole batch on it.

Now: `check_budget()` catches an unreadable ledger and raises `LedgerUnreadable` (a `BudgetExceeded`, `kind="metering"`) — it **fails closed**, opens no socket, and the job records `stop_reason="metering"` so it is never confused with a genuine cap breach (`stop_reason="budget"`). `budget_status()` reports `ledger_error` instead of 500ing. A brake that silently disables itself when its meter is unreadable is not a brake.

## Live install state (checked 2026-10-02)

The running install had **not been booted since 2026-09-17**, so it is several migrations behind; the next boot runs them all, and a boot probe on copies of the real stores proved each one lands cleanly on the real data:

| Step | Effect on the real archive |
|---|---|
| Phase P FTS5 | creates `startups_fts`, `startups_vocab`, `app_search_word`, `app_meta`; logs `fts index rebuilt (schema version 2)` |
| §7.4 ledger | adds `llm_usage` (1258 startup rows untouched; `canonical_domain backfill: 1258 rows filled`) |
| Auto-verify | queues a **verify job over all 1,258 stale entries** on startup (deterministic, no LLM spend — but it does fetch every URL) |

Archive: 1,258 rows, all `active` (1,205 website / 52 github / 1 founder); `verified` 1,254; `dead` 0; last checked 2026-09-17. Jobs table: capture/done 3, verify/done 8, verify/failed 5, seed/failed 1. Settings: `active_gateway = gemini`, no per-gateway overrides, no budget set, no stored rate table (built-ins in use).

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

- [x] **Task 5 — the `paused` state.** Shipped: park at the candidate boundary keeping every row, `finished_at` left NULL, listed as in-progress, untouched by restart recovery, `has_parked_job(kind)` for the panel, and the seed list tells the truth about why it stopped. **Paused does NOT block its kind** (see the departure note above).
- [x] **Task 6 — cancel + resume.** Shipped: three cancel routes (queued / parked / running-at-the-boundary), resume that skips every already-handled candidate (never re-billed) with an optional raised budget, both endpoints, cancel wired into seed + capture + verify loops, `partial: true` on a cancelled verification, and the frontend client functions for task 7's buttons. A cancel request is deliberately NOT persisted — a restart kills every in-flight job anyway, so a stale flag would have nothing left to cancel (what survives is the cancelled status and the kept rows).
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
