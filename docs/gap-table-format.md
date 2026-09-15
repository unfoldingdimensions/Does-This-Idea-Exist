# Gap Table Format — MVP

**Version:** 1.1 (rev. 2026-09-15 — Round 5 trust model applied)
**Owner-confirmed:** the gap table is **facts only** — every cell sourced or marked unknown, no generated verdict.
**Companion:** `docs/teardown-spec.md` (where the fields come from — §5.1 holds the canonical column names, §8 the trust model, §9 reviews) · `reworked-revamp-plan.md` §11.

---

## 1. The shape

One table, three sections, one row per comparison dimension. The two columns are **You** and **Competitor**, and every row carries a **source** so the reader can click through.

```
| Dimension | You (your app) | Competitor | Source |
|---|---|---|---|
| … | … | … | … |
```

### The outcome sections

The table is grouped into bands so the *gaps* jump out:

1. **You have — they don't** (your edges)
2. **They have — you don't** (your gaps / what to copy or counter)
3. **Both have** (parity — no differentiation here)
4. **Their users ask for it** (dimension 7 only) — demand signals from reviews. This group exists because neither side has the capability yet: it is not an edge for you, not a gap against you, and not parity. It sits outside the three comparison bands deliberately, and rows land here when a reviewer-requested capability is absent from **both** lists.

A dimension with no difference is *parity* and belongs in section 3 — it is not a gap. A dimension where a request is **already covered** by your declared features lands in section 1 instead (their users want it; you built it) — that is the most valuable row this product produces.

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
| 7 | What their users ask for (from reviews) | review evidence rows (`docs/teardown-spec.md` §9) | your declared feature list — covered → group 1; not covered → group 4 |

Dimension 7 is **owner-confirmed** (Round 5 follow-up): it is a dimension of this table, not a separate panel. It is the only dimension whose group can be 4 ("their users ask for it") as well as 1 (you already cover it).

Features are compared at the *capability* level, not the wording level: "local files" vs "cloud-only" is a real row; "markdown" vs "Markdown" is not. The same applies to dimension 7: reviewers asking for "offline mode", "work without internet" and "local files" are one row, not three.

---

## 3. The cell rules (this is the product, not decoration)

1. **Every "they" cell is sourced** — a URL, and where relevant a capture date. Pricing cells carry `captured_at` because pricing decays. Competitor claims are taken at face value *because* the link is right there: the product attributes, it does not adjudicate.
2. **A "they don't do X" cell is an observation about a page that enumerates**, never a verdict about the world: *"pricing page lists Free / Pro / Team — no self-host tier (captured 2026-09-15)"*, not *"they have no self-host"*. A 404 on a guessed URL is **not** evidence of absence; a page that returns an empty shell is "we could not read it", not "they don't have it". If no enumerating page can be traced, the cell reads **unknown**, not "no" (`docs/teardown-spec.md` §8.2).
3. **Every "you" cell comes from what the founder entered** (form or their ingested URL). The product does not invent the founder's features.
4. **Empty ≠ a gap.** A dimension with missing data on either side is shown as **unknown**, and the gap table says so rather than scoring it.
5. **No verdict line.** The table ends at the facts. The product may *invite* the founder to draw the conclusion ("does that look like a gap you can win?") but must not print one. This extends to reviews: `docs/teardown-spec.md` §9 allows "3 reviewers asked for offline mode", never "you should build offline mode".
6. **Badges attach to the record, never to a claim.** Admin Verified / Machine Verified describe the business, not its marketing — never render one beside a claim cell (`docs/teardown-spec.md` §8.1).

---

## 4. The "doesn't do" representation

Negative claims render as a short list under the competitor column, each an observation carrying the page it came from, e.g.:

> Competitor — doesn't do (observed on the pages that enumerate): no API *(docs index lists no API section)* · no mobile app *(footer lists no store link)* · no self-host *(pricing page lists Free / Pro / Team only)*.

Every entry is a fact about a page the reader can open, with its capture date. When a commonly-expected capability can't be confirmed either way, it is shown as **unknown**, which is itself useful signal for the founder ("go check whether they have an API").

---

## 5. Export formats

The gap table exports (plan §5, kept from v1):

- **Markdown** — the three-band table above, ready to paste into a founder's notes or a decision doc.
- **JSON** — `{you: {...}, them: {...}, rows: [{dimension, you, them, source, band}]}` so it can be re-processed.
- **CSV** — one row per dimension with `band, dimension, you, them, source_url, captured_at`.

Note the two id namespaces: the "you" record lives in the founder store (`FOUNDER_DB_PATH`) and the competitors in the archive, so the **request** namespaces the sides explicitly (`{you: {...}, competitors: [...]}`) rather than passing one flat list of ids — `id=7` is ambiguous across two files. The export `you`/`them` shape above is unchanged.

Dimension 7 is exported like every other dimension (owner-confirmed): its rows appear in all three formats, and `band` takes a fourth value — `asked_for` — alongside the three comparison bands.

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
| **Their users ask for it** | | | |
| Offline mode | yes *(declared feature: local files)* | no *(3 reviewers asked for it)* | g2.com/noted-reviews |
| Native mobile app | no | no *(7 reviewers asked for it)* | reddit.com/r/noted |

The table stops there. No "you should add local-first" — that is the founder's call to make with the evidence in front of them.
