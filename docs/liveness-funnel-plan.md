# Liveness funnel — critique and implementation plan

**Date:** 2026-09-19 · **Status:** Sequences 1–3 **done** 2026-09-19, audit fixes landed 2026-09-21/22 — parity selftest 50/50, backend functional 283/283 (rules-shipping, content check, run import + path gate), `npm test` gate ALL PASS. The render stage is in-repo with an end-to-end proof run. Politeness is live and measured: full-archive audit (1,258 rows) under the defaults ran in **334s = 1.52× baseline** (budget 3×), capture 6.5/s; 21 rows became honest robots-refusal UNKNOWNs. Sequence 4 (sampled QA) is next
**Subject:** `scripts/site_liveness_audit.py` (the funnel, 2,182 lines), its
(non-)integration with the app, and the work between here and production standard.
**Method:** full read of the funnel, `backend/app/verify.py`, `backend/app/netguard.py`,
the 2026-09-18 audit review (Rounds 1–5), `docs/scale-to-10000-plan.md`, and the
backend functional suite. Findings marked **traced** come from reading code and have
not yet been executed; **ran** means executed this session.

## Verdict

The funnel is an excellent, honest, well-guarded instrument that the product it
exists to protect cannot hear. Every rule earned its place through a real incident,
every destructive step has a brake, and the drops were independently verified
reversible. But the funnel's decisions never reach the app: the weekly verify pass
still trusts HTTP status alone — the exact gap that kept four gambling-spam domains
in the archive as `verified=1` until a human noticed — and the one stage that can
settle client-rendered truth is unreproducible from the repo. The plan below closes
the loop first, then makes the remaining stages real.

## What is already production-grade

- **Doctrine as fixtures.** 47 selftest fixtures, each a real page that once produced
  a wrong answer; the reason for every rule lives in a comment next to the rule;
  `selftest` exits 4 on drift. The strongest part of the codebase.
- **The drop brakes, proven under fire.** Fresh evidence re-captured at drop time,
  sqlite backup API, manifest written *before* the delete, child-table history,
  `--max-drop-fraction`, refusal when evidence no longer demonstrates the verdict.
  The independent review confirmed every drop fully reversible
  (1,283 → 1,271 → 1,270 → 1,266 → 1,258).
- **The second-agent review culture.** The 2026-09-18 review re-verified everything
  with independent clients and caught four repurposed domains the audit missed.
- **Honest reporting.** UNKNOWN stays UNKNOWN; known imprecisions are recorded, not
  hidden (d3js.org filed COMPANY; English-centric vocabulary).

## The flaws

Severity is the production consequence, not the coding effort.

### F1 — The loop is open: the funnel and the product are disconnected (critical)

`verify.approve_machine()` (`backend/app/verify.py:211`) — the machine-admission
path Phase A built, guards and all — has **zero production callers**; only tests call
it. Nothing in the app can produce a Machine Approved row except direct DB surgery.
Meanwhile the weekly verify pass runs `check_url_ok` (`verify.py:33-60`), which is
**status-code-only**: 404/410 = strike, any 2xx/3xx = alive. That is precisely the
failure mode the review documented — Oribi, Helium Health, Creator and Raise sat in
the archive as `verified=1`, `status='active'` gambling sites because the app's
verifier recorded nothing but `website: HTTP 200`. Run today against the pre-audit
archive, the app's verify pass would re-bless every one of them. Phase B was a
dry-run by design and was executed twice with fingerprints — but its decisions were
never applied to anything. The scale plan's §2.4 names the missing piece ("emit
machine-approval output"); it is the keystone and it does not exist.

### F2 — The renderer stage is not a stage (high)

Round 4's browser pass settled 16 of 18 UNKNOWNs and was load-bearing: six of the
eight rows in the final drop were only visible to a renderer. That pass lives in
`.openclaw/tmp/browser/` — vendored `puppeteer-core` plus the machine's Chrome, run
by hand. It is not in the repo, not reproducible, and the tool cannot produce the
merged state file that `drop --states-file` consumes; a human does that join between
two steps. Adjacent footgun, **traced**: `verify` on a merged run directory rebuilds
`states.json` from `captures.jsonl` (`:1655-1697`, unconditional write at `:1692`),
which **clobbers the browser evidence** a drop would need, with no warning.
Production standard: every stage feeding a destructive decision must be reproducible
from the repo.

### F3 — MOVED fires vacuously for short brands (medium, traced)

`brand_tokens()` keeps only tokens of length ≥ 4 (`:495-498`). A brand like *Mux*,
*Bun* or *ixo* yields zero tokens, so `title_has_brand` / `text_has_brand` are
`None` (`:835-836`). The MOVED rule (`:1128`) is `redirected and not title_has_brand
and not text_has_brand` — and `not None` is `True` — so **any cross-domain redirect
for a short-brand company files MOVED with zero positive evidence**: "no token of
the company appears on the page" is vacuously true because the rule could not look
for tokens at all. Class B carries the `and toks` guard (`:942`); MOVED is missing
it. Class C (`:1102`) has the same shape but is defensible — the parking parameters
are independent evidence. At 1.3k rows this is queue noise; at 10k with
redirect-heavy channels it is queue-flooding. No fixture covers a short-brand
redirect.

### F4 — No per-host politeness (medium, scales badly)

Capture runs `--workers 12` (default, `:2247`) with at most a global `--min-delay`
sleep (`:707`). A corpus where one host appears 50 times — a GitHub channel, one
registrar parking many domains — is fetched with 12 concurrent connections. The
scale plan's §4 channel rules demand per-host politeness and robots.txt respect;
the tool implements neither. Harmless at 1,258 distinct domains; at 13,000
candidates from sources with ToS (Product Hunt, HN Algolia) it is hostile-crawling
territory and ban risk against the sources the plan depends on.

### F5 — The capture cache is unbounded and memory-resident (medium at 10k)

`Cache` loads the whole JSONL into memory at open (`:1366-1375`). Expired entries
are skipped on read but never evicted from the file, and every re-run appends —
the file only grows. Three UAs × 10k URLs × up to 30KB visible text each is on the
order of a gigabyte parsed at every startup. Fine at 1.3k; a liability at 10k.

### F6 — The 20KB body gate is an unmeasured blind spot (medium)

`default_page_body`, `soft404_body`, `challenge_body` and `seizure_body` fire only
when `bytes < 20000` (`:851`). A parked page padded past 20KB — SEO text, contact
form, captcha, the healthiq.com lander pattern — escapes body-level detection and
survives on title matching alone. The precision trade is defensible; the missing
part is that nobody has measured its false-negative rate.

### F7 — The error budget is aspirational (process)

Scale plan §6.2 proposes a <0.5% false-approval rate, measured by sampled human QA,
with stop-the-line on breach. Nothing implements it. Every validation to date was
manual hand-checking recorded in prose — good prose, but not a mechanism. Until
sampling exists, auto-approval at scale has no measured error rate and no line
that trips.

### F8 — One body decides content (low)

`classify` picks the single capture with the most visible text (`:1053`) and runs
all content rules on it alone; the other UA's body counts only for reachability.
Per-UA cloaking (parking networks do serve different bodies by UA) can file a
parked domain LIVE. Low probability; worth an all-captures merge or a comment.

### Smaller findings

- `signals()` recompiles ~100 phrase regexes per row — measurable at 10k, trivial
  to precompile.
- No CI (known gap #6): the selftest runs only when someone remembers, and every
  push routes through the Mimosa gate whose false positives must be adjudicated by
  hand (documented in PR #20).
- `--allow-private` disables the SSRF guard globally for a run — fine for a local
  operator, but nothing records in the run metadata that it was on (it does:
  `run.json` settings — verified; no action).

## Progress scorecard

| Phase | Claimed | Actual |
|---|---|---|
| A — approval model | done | Done correctly; guards pinned by tests. Plumbing to nowhere until F1 closes. |
| B — funnel dry-run | done | Ran twice, cleanly, nothing published. Its decisions were never applied. |
| C0 — company gate | done | Done, measured on 50 real candidates before trusted. |
| C — sourcing + staging | next | Blocked in practice: no staging table exists for the funnel to run against; GitHub needs a token; F4 makes volume crawling unsafe. The plan understates this. |

## Implementation plan — four sequences, each independently verifiable

Sequencing rule: close the loop before adding volume or stages. Sequence 1 makes
the funnel's existing decisions executable; 2 makes the renderer real; 3 makes
volume crawling safe; 4 makes the error rate measured. Each sequence has
acceptance criteria and a rollback.

### Sequence 1 (now) — close the loop: admission wiring

**Why first:** F1. Until the app can act on a funnel run, the archive's honesty
depends on an operator remembering to cross-check two worlds by hand.

1. **Extract the pure classifier core** — vocabulary (`DEFAULT_CONFIG`),
   `load_config`, text utilities, `signals`, `classify`, `company_gate`,
   `verdict_of`, `host_of`/`regdom`/`brand_tokens` — verbatim into
   `backend/app/liveness_rules.py` (the canonical copy lives in the app package
   so the container ships its own rules; the CLI loads it by path). One
   canonical rule set.
   **Parity proof:** the CLI selftest passes 47/47 unchanged.
2. **Fix F3** — add the missing `and sig["brand_tokens"]` guard to MOVED; add a
   short-brand redirect fixture. **Proof:** selftest 48/48.
3. **Content-aware `check_url_ok`** — new `backend/app/liveness.py` (loader +
   `classify_homepage`); the verify pass classifies the 2xx body it already
   fetched and maps: DEAD/REPURPOSED → a genuine strike (it is one);
   WALLED/UNKNOWN/MOVED/BANNED → skip with a named note (queue-worthy, not a
   strike); LIVE → unchanged. Flag `VERIFY_CONTENT_CHECK`, default on; any
   internal error fails open to today's behaviour. **Safe by architecture:** a
   false positive never auto-kills a row — human-verified rows never
   auto-dead-flip (they surface in `failed_list` as re-check items), and
   machine-admitted rows need three consecutive genuine failures.
4. **`backend/app/funnel.py` + `POST /api/admin/funnel/import`** — apply a
   completed run (`states.json`): admit `LIVE` rows whose company gate is
   `company`/`unverified` via the existing `approve_machine` (per-row
   `approval_note` carries the run, state and gate as the receipt; `by` is
   `funnel:render` when the row carries rendered evidence, else `funnel:http`);
   queue `WALLED`/`UNKNOWN`/`MOVED`/`BANNED` and gate `not_company`/`review` rows
   to the admin; **ignore `DEAD`/`REPURPOSED`** — deletion is the drop tool's
   jurisdiction, dead-flipping is the verify pass's. The endpoint never deletes
   and never dead-flips. `dry_run` defaults to true and reports what *would*
   match the admission guard.
5. **Functional tests** for all of the above (rules parity incl. the Oribi
   gambling page; the MOVED regression; check_url_ok strike/skip/ok mapping;
   import admit/queue/dry-run/idempotency), then the full `npm test` gate.
6. **Docs** — this file's status line, the scale plan §2.4 row, and a stacked PR
   (base: `feat/liveness-audit-funnel`, i.e. PR #20's branch).

**Acceptance:** a funnel run can be imported twice with the second import a
no-op; a machine-admitted row renders "Machine Approved" and never "Admin
Verified"; the weekly pass catches a planted 200-but-parked page as a strike.
**Rollback:** drop the new module/endpoint; `VERIFY_CONTENT_CHECK=0` restores
today's verify behaviour.

### Sequence 2 — the render subcommand (fixes F2) — **done 2026-09-19**

**Why second:** the only stage that settles client-rendered truth feeds
destructive decisions and is unreproducible; `drop` already accepts a merged
state file, so the missing piece is the producer.

- `render` subcommand in the tool + a vendored Node renderer
  (`scripts/render/render.mjs`, `puppeteer-core` + the installed Chrome — the
  Round-4 pattern, now in-repo, no downloads). Input: a run directory. Renders
  every row that is not clean LIVE; judges the rendered DOM with the **same**
  rules; writes `states-merged.json` with per-row `evidence_mode`.
- Fix the footgun: `verify` refuses to overwrite an existing merged file
  (writes `states-reverified.json` instead); `drop` prefers the merged file when
  present and says so in the plan line.
- Whatever the render pass teaches becomes fixtures (Round 4 taught three).

**Acceptance:** the Round-4 corpus (the 18 UNKNOWN of 2026-09-18, preserved in
the review) re-settles identically from the repo alone; `drop` runs end-to-end
with no manual join; selftest grows with any new rule. **Rollback:** additive
subcommand; `drop` without a merged file is unchanged.

### Sequence 3 — per-host politeness (fixes F4) — **done 2026-09-19**

**Why third:** volume crawling must not burn the sources the plan depends on;
Sequence 2's renderer adds a second fetch surface and inherits this too.

- Host-aware scheduler in `capture_all`/`recheck_all`: per-registrable-domain
  minimum interval (`--per-host-delay`, default 1.0s) and concurrency cap
  (`--per-host-concurrency`, default 2); idle workers fill other hosts' slots so
  global throughput survives. Optional `--respect-robots` (default on, stdlib
  parser, cached per host); per-host backoff on 429/403.

**Acceptance:** a single-host fixture corpus (50 URLs, one host) shows observed
inter-request gaps ≥ the configured delay (asserted in a test); the 1,266-row
archive re-run completes within 3× today's wall clock; rules untouched — selftest
stays 48/48. **Rollback:** `--per-host-delay 0` (documented escape hatch).

### Sequence 4 — sampled QA (fixes F7)

**Why last:** it measures the thing Sequence 1 automated. Auto-approval at scale
is only legitimate once its error rate is measured and a breach stops the line.

- `qa` subcommand: deterministic stratified sample (seeded) of a run — all
  DEAD/REPURPOSED/MOVED/BANNED, all WALLED/UNKNOWN, plus a random LIVE slice
  (default 2%, floor 30) — emitting a QA worksheet (MD + CSV) that carries each
  row's evidence and a verdict column. `qa --record` ingests completed verdicts
  into `qa-result.json` with the false-approval rate.
- The import endpoint (Sequence 1) reads `qa-result.json` when present and
  **refuses** admits above the 0.5% budget unless explicitly overridden and
  logged. A weekly sweep re-samples machine-admitted rows
  (`approval_source='machine'`, admitted in window). Rounds are recorded
  ledger-style.
- F6 is measured here for free: big-parked false negatives surface as LIVE rows
  in the sample; fix the 20KB gate only if the measured rate justifies it.

**Acceptance:** same seed → same sample; a planted bad verdict breaches the
budget and the import refuses with a named reason; a clean round passes; the
weekly machine-admitted sweep produces a worksheet. **Rollback:** refusing is the
safe direction; the budget is configuration and the override is explicit.

### Deferred, with triggers

| Item | Trigger |
|---|---|
| F5 cache bounds (rotate/shard, skip expired on load) | first run >5k rows or `captures.cache.jsonl` >200MB |
| F6 raise/replace the 20KB gate | Sequence 4's measured false-negative rate |
| F8 merge content evidence across captures | Sequence 2, when `classify` gains rendered captures |
| CI for the selftest | owner decision — the Mimosa false-positive burden is documented in PR #20 |

## Rules this plan must not break

The repo's own invariants, restated so a future sequence cannot quietly drop them:
never delete without a receipt, and dead rows are kept forever; precision beats
recall wherever a verdict can delete; badges attach to records while claims carry
their own sources; rule changes are recorded in the specs and plans, not only in
prompts; and every new real-world false positive becomes a fixture.
