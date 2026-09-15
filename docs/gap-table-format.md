# Gap Table Format — MVP

**Version:** 1.0 · **Date:** 2026-09-15
**Owner-confirmed:** the gap table is **facts only** — every cell sourced or marked unknown, no generated verdict.
**Companion:** `docs/teardown-spec.md` (where the fields come from) · `reworked-revamp-plan.md` §11.

---

## 1. The shape

One table, three sections, one row per comparison dimension. The two columns are **You** and **Competitor**, and every row carries a **source** so the reader can click through.

```
| Dimension | You (your app) | Competitor | Source |
|---|---|---|---|
| … | … | … | … |
```

### The three outcome sections

The table is grouped into three bands so the *gaps* jump out:

1. **You have — they don't** (your edges)
2. **They have — you don't** (your gaps / what to copy or counter)
3. **Both have** (parity — no differentiation here)

A dimension with no difference is *parity* and belongs in section 3 — it is not a gap.

---

## 2. The dimensions

Owner-confirmed for MVP, in this order:

| # | Dimension | Source on "they" side | Source on "you" side |
|---|---|---|---|
| 1 | Pricing (plan-by-plan) | teardown field 1 | founder form/URL |
| 2 | Free tier | teardown field 1 | founder form/URL |
| 3 | Features (5–10) | teardown field 2 | founder form/URL |
| 4 | Positioning / target user | teardown field 3 | founder form/URL |
| 5 | What it doesn't do | teardown field 4 | n/a (your own app — mark what you lack honestly) |
| 6 | Activity / liveness | teardown field 5 | n/a |

Features are compared at the *capability* level, not the wording level: "local files" vs "cloud-only" is a real row; "markdown" vs "Markdown" is not.

---

## 3. The cell rules (this is the product, not decoration)

1. **Every "they" cell is sourced** — a URL, and where relevant a capture date. Pricing cells carry `captured_at` because pricing decays.
2. **A "they don't do X" cell must be sourced**, never asserted from silence. If it can't be traced, the cell reads **unknown**, not "no".
3. **Every "you" cell comes from what the founder entered** (form or their ingested URL). The product does not invent the founder's features.
4. **Empty ≠ a gap.** A dimension with missing data on either side is shown as **unknown**, and the gap table says so rather than scoring it.
5. **No verdict line.** The table ends at the facts. The product may *invite* the founder to draw the conclusion ("does that look like a gap you can win?") but must not print one.

---

## 4. The "doesn't do" representation

Negative claims render as a short list under the competitor column, each prefixed with its evidence, e.g.:

> Competitor — doesn't do (sourced): no API *(docs have no API reference)* · no mobile app *(no store link found)* · no self-host *(pricing lists no self-host)*.

When a commonly-expected capability can't be confirmed either way, it is shown as **unknown**, which is itself useful signal for the founder ("go check whether they have an API").

---

## 5. Export formats

The gap table exports (plan §5, kept from v1):

- **Markdown** — the three-band table above, ready to paste into a founder's notes or a decision doc.
- **JSON** — `{you: {...}, them: {...}, rows: [{dimension, you, them, source, band}]}` so it can be re-processed.
- **CSV** — one row per dimension with `band, dimension, you, them, source_url, captured_at`.

---

## 6. Worked example (skeleton)

**You:** "Loom-note", an online-first note app with an API and real-time collaboration.

| Dimension | You | Noted (competitor) | Source |
|---|---|---|---|
| **You have — they don't** | | | |
| Real-time collaboration | yes | no *(homepage does not claim it)* | noted.app |
| API | yes | no *(docs have no API section)* | noted.app/docs |
| **They have — you don't** | | | |
| Local-first / offline | no | yes *(markdown files, local-first)* | noted.app |
| Plugin ecosystem | no | yes *(plugins page)* | noted.app/plugins |
| Self-host | no | yes *(pricing lists self-host)* | noted.app/pricing |
| **Both have** | | | |
| Markdown notes | yes | yes | noted.app |
| Free tier | yes (5 docs) | yes (3 docs) | noted.app/pricing |
| **Unknown** | | | |
| Publishing | unknown | yes *(publish feature)* | noted.app |

The table stops there. No "you should add local-first" — that is the founder's call to make with the evidence in front of them.
