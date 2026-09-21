# Phase 0 — The Concierge Proof (25 hand-made briefs)

**Status:** draft for owner sign-off · **Date:** 2026-09-19
**Tests:** falsification plan test 2 (`research/04-market-saturation-verdict.md`) — "concierge value".
**Companions:** `research/04` (the thresholds) · `docs/teardown-spec.md` (the fields and the trust model) ·
`docs/gap-table-format.md` (the output shape) · `docs/discussion-record.md` §9 Round 2 (the pivot to teardowns).

---

## 1. What this is

Twenty-five evidenced prior-art briefs for twenty-five real, scoped ideas — produced **by hand**, given
**free**, and measured against a pre-registered threshold. No new code. No website. No launch.

The thing being proved is not "the idea is good". It is narrower and more falsifiable:

> **Can a builder produce, for a real founder, an evidenced competitor teardown and a you-vs-them gap
> table that is good enough to change what they do next?**

If twenty-five of these cannot be produced at a quality nobody else offers, the product cannot be
either — `research/04` says exactly this, and it is the cheapest possible test of the core claim.

### The pre-registered bar (do not move it after the fact)

| Threshold | PASS | FAIL |
|---|---|---|
| Asked for a second brief | **>= 40% (10 of 25)** | **< 20% (fewer than 5)** |
| Reported a changed decision | **>= 8 of 25** | **< 4 of 25** |
| Volunteered to pay anything | **>= 5 of 25** | — (no FAIL threshold alone) |

**Kill rule (from `research/04`):** if test 1 (segment reality) and test 2 both fail, the market thesis
is dead — stop. If both pass but test 4 (evidence beats opinion) fails, the product survives only as a
directory and the differentiation case in `research/03` must be rewritten.

Record every number in the ledger (§10) **before** reading them as a verdict. The failure mode this
script exists to prevent is a concierge run that "felt successful" and therefore proved nothing.

---

## 2. The one rule: no code

This phase adds no schema, no endpoint, no route. The manual pipeline in §7 (`enrich.py`'s existing
website draft, a by-hand capture, evidence rows typed into a sheet) is allowed; building the batch
driver, the compare flow, or the `/products/<slug>` route is not. The point is to learn whether the
*artifact* is worth building — building the artifact first inverts the test and spends the budget the
test was meant to protect.

If a brief cannot be produced by hand in the §3 budget, that is a finding, not a justification to
automate it mid-run. Record it and keep going.

---

## 3. Scope, time-box, and the funnel math

| Item | Value |
|---|---|
| Briefs to deliver | **25** |
| Ideas to screen to net 25 | assume ~2.5x drop-off → **~60 solid intakes** |
| Outreach to net 60 intakes | assume 12–15% reply on a cold, specific message → **~400–500 targeted contacts** |
| Per-brief production budget | **90 minutes** of builder time, hard cap |
| Brief turnaround promised to the founder | **72 hours** from a complete intake |
| Window | **4 weeks** end to end, including the 7-day follow-up |
| Cash cost | ~zero (existing tools; no paid data, no ads) |

**If a brief runs past the 90-minute cap, ship it degraded and honest** — mark the unsupportable cells
`unknown` per the gap-table rules — and log the overrun. A degraded-but-honest brief is a valid data
point; a padded brief produced by guessing is a corrupted one.

**Per-brief budget (90 min):** intake + founder confirm 15 · capture the 3–5 closest neighbours 25 ·
evidence + gap table 35 · export + write-up 15.

---

## 4. The artifact each founder receives

One document, built to the existing contracts — this is a rehearsal for the product's own output, so it
must not invent a new shape.

1. **The closest-neighbours set** — 3–5 archive entries, each with a date-stamped liveness status.
2. **The teardowns** — the six MVP fields per `docs/teardown-spec.md` §2: pricing (plan-by-plan + free
   tier), features (flat 5–10), positioning (one line), what they don't do (3–5), activity/liveness.
3. **The gap table** — the four bands of `docs/gap-table-format.md` §1: *you have — they don't* ·
   *they have — you don't* · *both have* · *their users ask for it*. Every cell sourced or `unknown`.
4. **Export** — Markdown (the pasteable artifact) plus JSON per `gap-table-format.md` §5.

**Non-negotiables carried from the trust model (`teardown-spec.md` §2, §8):**

- Every positive claim carries a URL and a capture date. Competitor claims are taken at face value
  *because* the link is there — the brief attributes, it does not adjudicate.
- **Every "they don't do X" is an observation about a page that enumerates**, never a verdict. A 404 on
  a guessed URL is not evidence of absence; an unreadable page is `unknown`, not "no".
- **No verdict line.** The brief may invite the founder to draw the conclusion ("does that look like a
  gap you can win?") and must not print one. Same for reviews: "3 reviewers asked for offline mode",
  never "you should build offline mode".
- No badge sits next to a claim.

---

## 5. Recruitment

**Who (from `research/04` §"underserved segment"):** a solo or two-person technical founder with an
**already-scoped** idea — not "give me ideas" — typically in software, dev tools, or design-adjacent
SaaS, currently deciding whether to spend a weekend or a quarter building it.

**Where:** founder and indie communities; dev-tool forums; and the two warm lists already on hand —
the 201-site curated design library and the GitHub-linked rows in the archive. The warm lists are the
higher-yield start; the communities are for volume.

**The confidentiality line is part of the pitch, not a footnote.** The founder is handing over their
idea. Say plainly: *"Your idea stays with me — it is not published, not added to the archive, and not
shown to anyone else. If you later ask me to publish it, that is a separate, explicit step."* This is
the same posture the product claims (local-first, no accounts) and it is the reason a technical founder
replies at all.

### Outreach message (cold, one-to-one)

```text
Subject: a hand-built competitor teardown for your idea (free, no strings)

Hi <name> —

I saw <specific thing: their post / repo / launch>. You're working on <their product in their words>.

I'm building a tool that answers "does this already exist, and what would I actually do differently?"
Before I build any of it, I'm making 25 of these by hand to find out whether they're worth anything.

What you'd get, free, in ~72h: the 3-5 closest products to yours, each torn down (pricing plan-by-plan,
features, positioning, what they don't do), every claim linked to the page it came from with a capture
date — and a you-vs-them gap table: what you have that they don't, what they have that you lack.

What I'd get: 20 minutes to see whether it's useful.

No account, no email list, nothing published. Your idea stays with me unless you tell me otherwise.
Reply "yes" and I'll send three questions.

— <you>
```

**Do not** promise it is good, do not call it research, do not mention the product's future pricing.
The message sells the *outcome* ("what would I actually do differently"), not the virtue of research —
the framing the research settled on (`discussion-record.md` §9, Q9).

### Screening rule

Take the idea if it is **scoped** (names a product and a user) and the founder can describe their own
app. Decline politely if it is a category ("an AI app for X") or a browsing-for-inspiration request —
those are the wrong segment and will corrupt the sample. Log declines with the reason; the decline
pattern is itself segment data.

---

## 6. Intake

Three paths, mirroring the product's own (`teardown-spec.md` §3). Keep the founder's app in a separate
record from the archive, exactly as the two-store rule requires.

1. **URL** — they have a site; draft from it.
2. **Form** — name · one-line description · target user · category · **features (flat 5–10, required)** ·
   pricing (free tier + plans) · links (website / GitHub / App Store / Play Store).
3. **Agent-JSON** — hand them the copy-paste prompt from `teardown-spec.md` §3 and take the JSON back.

**Confirm before diff.** Send the drafted "you" profile back to the founder and have them correct it
*before* producing the gap table. This is both the product's rule (F-13) and the thing that stops a
wrong founder profile from producing a confidently wrong brief.

**Intake questions (three, sent once they say yes):**

1. What is the app, in one sentence, and who is it for?
2. List 5–10 things it does, one capability per line.
3. Initial pricing — free tier, and the plan names/numbers you have in mind (all of them "planned" is a
   fine answer; write "planned").

---

## 7. Production (the manual pipeline)

Per brief, in order — this is the sequence the product must eventually mechanise, run by hand first:

1. **Screen the archive** for the nearest neighbours (search + manual read; note the lexical-similarity
   limitation from `research/03` and correct for it by hand).
2. **Capture** each neighbour: homepage, `/pricing`, docs index, footer. Four fetches max.
3. **Record evidence as you go** — one row per claim: source URL · captured_at · claim · value ·
   confidence. If a cell cannot be traced to a page, it becomes `unknown`; it never becomes a guess.
4. **Write the negatives** only from pages that enumerate the whole set (pricing page, docs index,
   footer). This is the strictest rule and the one most likely to be violated when moving fast.
5. **Diff** the founder's confirmed profile against each neighbour; assemble the four bands.
6. **Export** Markdown + JSON.
7. **Liveness-stamp** every neighbour with its last-verified date.

**Quality gate before a brief ships (all must be true):**

- [ ] Every "they" cell has a URL; every pricing cell has a `captured_at`
- [ ] Every "they don't do X" traces to an enumerating page, or reads `unknown`
- [ ] Every "you" cell came from the founder, not from us
- [ ] No verdict line anywhere; no badge beside a claim
- [ ] At least one band is non-empty and at least one cell is honest `unknown` (a brief with no
      unknowns is a brief that guessed)

---

## 8. Delivery

Hand over the Markdown, then run the script below. Ask nothing about payment or future use in this
exchange — that is measured by observation in §9, not by asking now.

```text
Here's your brief for <idea>: <link/paste>.

It's three parts — the 3-5 closest products, each torn down with every claim linked to the page it came
from; then the you-vs-them table, grouped into what you have that they don't, what they have that you
lack, and what's parity. Anything I couldn't trace is marked "unknown" rather than guessed.

Two things worth flagging before you read it: <one specific finding>, and <one named unknown>.

Read it, then let's talk for 20 minutes. I want to know whether this changes anything, or whether it's
just a nice document.
```

The `unknown` cells are not an embarrassment to apologise for — they are the product's honesty, stated
plainly. A brief that names its own gaps is the brief we are testing.

---

## 9. Measurement (this is the experiment)

**Do not ask leading questions.** "Would you pay for this?" produces a polite yes and destroys the
test. The three thresholds are measured by **observation and coding**, not by asking for a verdict.

### The 20-minute call

1. *Walk me through what you were planning to do before you read this.* (baseline intent)
2. *What, if anything, will you do differently now?* (open; then code the answer, §below)
3. *What's missing or wrong in it?* (quality signal, and the honest input that improves the product)
4. *What would you have done instead if this didn't exist?* (substitute baseline; feeds test 1)
5. Then, and only then: *Anything you want to ask me?*

### How each threshold is coded

| Threshold | Coded from | Rule |
|---|---|---|
| Asked for a second brief | The 7-day follow-up **and** any call where they name another idea they want torn down | Only counts if they **initiate** it. A "want another?" prompt from us does not count |
| Changed decision | Q2, coded against Q1 | Counts only for a **concrete** change: narrowed scope, changed a feature, changed pricing, dropped a competitor angle, killed the idea. "Very useful" does not count |
| Volunteered to pay | Any unprompted mention of paying, price, budget, or "how much will this cost when it's real" | Must be **initiated by them**. If we say a price first, it is void |

### The 7-day follow-up (sent to all 25, verbatim)

```text
Quick one, 7 days on: did the brief change anything you're actually building or planning?
A one-line answer is perfect — including "no, not really", which is the most useful answer I can get.
And if there's another idea you'd want the same thing for, just say so.
```

### What must be logged per founder (the ledger)

- intake date · segment · idea (kept private, one-line) · brief shipped date
- changed-decision (yes/no + the coded change) · asked-for-second (yes/no + who initiated)
- volunteered-to-pay (yes/no + the quote) · missing/wrong feedback · substitute they'd have used instead
- honest optional: what they said it was worth in *time* saved, if they offer it

---

## 10. Ledger template

```text
| # | Date | Segment | Idea (private) | Shipped | Changed? | Change (coded) | 2nd brief? | Initiated by | Offered to pay? | Quote | Missing/wrong | Substitute baseline |
|---|------|---------|----------------|---------|----------|----------------|------------|--------------|-----------------|-------|---------------|---------------------|
| 1 |      |         |                |         | Y/N      |                | Y/N        | them/us      | Y/N             |       |               |                     |
```

Rolling tally (update after every brief, not at the end): `delivered / 25` · `asked-again %` ·
`changed-decision n` · `volunteered-to-pay n`.

---

## 11. Verdict rules and what each outcome means

| Outcome | Reading | Next move |
|---|---|---|
| All three bars cleared | The artifact is real and the segment feels it | Proceed to test 3 (landing page) and test 6 (embedded check); the evidence table and compare flow are now justified builds |
| Two of three cleared | Partial signal — read the ledger before deciding | The most decision-bearing miss is the one that matters: no second-brief demand says the job is infrequent; no changed decision says the artifact doesn't land at the moment of consequence; no voluntary payment says the wedge is a feature, not a product |
| Fewer than two cleared | **Test 2 failed** | If test 1 also failed, the market thesis is dead — stop. If test 1 passed, the problem is the artifact, not the segment: rewrite the brief shape and re-run with a fresh 25, not a re-scored 25 |
| Briefs can't be produced in the 90-min budget | The artifact may be good but the operation is not viable by hand | Report it as a finding. Do **not** automate to rescue the run — that spends the budget the run protects |

**Pre-registration honesty:** the thresholds in §1 are copied from `research/04` and were set *before*
any brief was written. If a threshold is changed mid-run, the run is void and restarts — the same
discipline the repo applies to fixtures and to the drop brakes.

---

## 12. How this proof lies to you (anti-patterns)

- **The friendly sample.** Recruiting only people who already like the project manufactures a pass.
  Recruit cold, and log declines. A high decline rate on cold outreach *is* the segment finding.
- **The polite yes.** "This is great, thanks!" is not a changed decision and not a second-brief request.
  Code only concrete behaviour.
- **The padded brief.** Filling an untraceable cell with an inference is the exact failure the whole
  trust model exists to prevent. `unknown` is a valid cell and the better answer.
- **The rescued run.** Automating mid-run to hit 25 briefs at quality corrupts the test. Degrade and log.
- **The leading ask.** Any mention of price, subscriptions, or "would you use this?" before the 7-day
  follow-up voids the willingness-to-pay signal.
- **The rewritten threshold.** See §11; a moved bar is a void run.

---

## 13. What this run produces, regardless of verdict

- **25 real founder profiles** with confirmed feature lists and pricing intent — warm, specific, and the
  beginning of the segment list (`research/04` §"first user").
- **A by-hand evidence corpus** in the exact shape of the `evidence` table — the rows the product will
  eventually write automatically, available today as labels for the Phase D enrichment pilot.
- **A substitute baseline** from 25 people (what they would have done instead) — test 1's raw material,
  collected for free alongside test 2.
- **A measured answer to the one question the research could not settle:** whether founders change
  behaviour for provenance, or merely appreciate it.
