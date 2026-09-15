# Teardown Spec — MVP

**Version:** 1.0 · **Date:** 2026-09-15
**Owner-confirmed scope:** a competitor teardown that a founder uses to line up their own app against a competitor and get a concrete gap. This is the MVP shape; anything beyond these six fields is post-MVP.
**Companion docs:** `docs/gap-table-format.md` (the output table) · `reworked-revamp-plan.md` §6, §10, §11 · `docs/codebase-comprehension.md` (what exists today).

---

## 1. What a teardown is

A teardown is a **structured, sourced snapshot** of one competitor, built from the archive plus the evidence table. It is *not* an essay and *not* an AI opinion. Every field is either sourced or marked **unknown**; nothing is inferred silently.

The product already produces most of the *identity* fields (name, tagline, description, category, founded, URLs, liveness). A teardown **adds** the six fields below. So a teardown = existing dossier + these six.

---

## 2. The six MVP fields

| # | Field | What it captures | Source | Evidence rule | Completeness bar |
|---|---|---|---|---|---|
| 1 | **Pricing** | Full plan-by-plan breakdown: each plan's name, price, billing period, and the free tier (or "no free tier") | pricing page / `/pricing`, docs | one `evidence` row per plan with `captured_at` + source URL; staleness shown to the user | At least the list price and the free-tier flag; full plan rows where reachable |
| 2 | **Features (5–10, flat list)** | A flat list of what the product actually does, in the founder's terms, not marketing terms — one capability per item, no grouping in MVP | homepage, docs, demo | each feature traces to a page or doc section | 5–10; "unknown" if a source can't support even 5 |
| 3 | **Positioning (one line)** | How they describe themselves / who they say it's for | homepage hero / meta description | sourced quote or paraphrase with URL | one line; always available (homepage exists for 100% of rows) |
| 4 | **What they don't do (3–5)** | Explicit negative claims: no API, no free tier, no mobile, no self-host, no offline | absence in pricing/docs/features | **the strictest rule in the product**: each negative claim must trace to a source (their pricing page lists no free tier; their docs have no API reference) or be marked unknown — never asserted from silence alone | 3–5 sourced; if fewer are sourceable, show fewer and mark the rest unknown |
| 5 | **Activity** (already exists) | Liveness: last check, dead/alive, repo activity | the weekly verify pass | existing `verify_log` / `last_checked` | always present |
| 6 | **Gap table** (the output) | You vs them, two-sided, sourced | the fields above + the founder's own app | every cell sourced or unknown | see `docs/gap-table-format.md` |

**The two rules that make this defensible rather than another AI validator:**

1. **Every positive claim is sourced** (a URL + a capture date).
2. **Every negative claim is sourced or marked unknown** — a "doesn't do" that can't be traced is *not* printed as fact. Negative evidence is the gap report's payload and the easiest thing to fake, so it gets the strictest handling.

---

## 3. The founder's own app (the "you" side)

Owner-confirmed: the founder describes their app via **three paths**, and the flow is always **ingest → confirm → diff** (never auto-diff).

1. **URL path.** If the founder has a site, run it through the existing `seed_from_website` pipeline (`backend/app/enrich.py`) — the same path that ingests competitors — to draft name, tagline, category, description, and founded. This is a **new mode of an existing primitive**, not new backend code.
2. **Form path (no URL).** A short form — *name · one-line description · target user · category (from the existing 12-value whitelist) · **features (required, flat 5–10)** · pricing (free tier + plans) · website URL (optional)*. A good feature list is required because the gap table compares feature-by-feature; without it the comparison is hollow.
3. **Agent-prompt path.** The founder can paste a structured payload produced by their own agent (ChatGPT/Claude/etc.) from the copy-paste prompt below — same fields, same JSON shape, zero manual typing.

**Copy-paste AI prompt (give this to your agent):**

```text
Describe my app in a strict JSON object with exactly these keys, no extra prose:

{
  "name": "string — display name",
  "description": "string — 2-3 sentences: what it is, who it's for, what problem it solves",
  "target_user": "string — one sentence naming the primary user",
  "category": "one of: productivity, ai, devtools, desktop, freelance, finance, health, education, ecommerce, social, media, other",
  "features": ["5 to 10 short capability strings, one per item, e.g. 'local files', 'real-time collaboration', 'public API'"],
  "positioning": "string — one line: how you describe yourselves and who it's for",
  "pricing": {
    "free_tier": "string — e.g. 'Free up to 3 docs', or 'No free tier'",
    "plans": [{"name": "string", "price": "string — e.g. '$8/mo' or 'custom'", "period": "monthly|annual|one-time"}]
  }
}

Rules: use only facts about my app. Keep features to 5-10 items. Do not invent a feature
or a price I did not state. If a field is unknown, use "" or []. Output JSON only.
```

**Confirm-before-diff (owner-confirmed):** after any of the three paths, the founder **reviews and confirms** the auto-drafted profile before the gap table runs — they can edit fields inline, then confirm. The gap table never renders against an unconfirmed profile.

**Result:** the "you" side is held in the same `startups` shape (a temporary/private filing), so the gap table can diff two like-for-like records.

Privacy note: the founder's own app never has to leave the machine — consistent with the local-first posture.

---

## 4. What is deliberately NOT in the MVP

- No generated "you will beat them because…" paragraph (facts only — see §18 of the plan).
- No sentiment/NPS/review scoring, no headcount/funding, no SEO/traffic panel.
- No automatic *web-wide* feature extraction. MVP captures these fields through the existing ingestion (homepage fetch + LLM draft + human confirm), one competitor at a time.
- No "alternatives ranking" or scores. The gap table compares, it does not rank.

---

## 5. Schema mapping (what to build, in order)

The teardown fields land in two places, both already described in the plan:

- `startups` gains: `features` (JSON array), `pricing` (JSON array of `{plan, price, period, free_tier}`), `positioning` (short text), and a `pricing_captured_at` + `pricing_source_url`.
- `evidence` rows back every feature, pricing plan, positioning line and negative claim with `evidence_type`, `source_url`, `captured_at`, `claim`, `value`, `provenance`, `confidence`.

Build order (matches plan §16): `entity_type` + provenance flag → `evidence` table → the four teardown fields → comparison → gap table → export.

---

## 6. Worked example (skeleton, not shipped data)

**Competitor:** a fictional dev-tool "Noted".

- **Pricing:** Free (up to 3 docs) · Pro $8/mo annual · Team $12/user/mo · *no self-host tier* — captured 2026-09-15, source `noted.app/pricing`.
- **Features (7):** markdown notes · backlinks · graph view · local files · plugins · sync (paid) · publish.
- **Positioning:** "A private, local-first note app that links your thinking." (homepage hero).
- **Doesn't do (4, all sourced):** no API (docs have no API section) · no mobile app (no mobile page, no store link) · no self-host (pricing page lists no self-host) · no real-time collaboration (homepage does not claim it).
- **Activity:** alive, last checked 2026-09-14.
- **Gap table:** against the founder's app (e.g. an online-first note app with an API) — see `docs/gap-table-format.md` for the rendered form.

---

## 7. Open questions

Resolved in Round 4 (2026-09-15): features are a **flat 5–10 list**; the form fields are fixed with a **required feature list** plus an **agent-prompt path**; the flow is **always confirm-before-diff**.

Still open, when the owner wants to go there:

1. The concrete change list for `backend/app/enrich.py` — which existing functions extend to populate `features`, `pricing`, `positioning`, and negative claims (vs. what the LLM profile already drafts).
2. Whether the founder's confirmed profile is stored as a separate `startups` row flagged as the founder's own app, or a distinct local-only record type.
3. How the "doesn't do" negative claims are *captured* at scale for competitors (manual curator notes vs. an LLM pass that must be human-confirmed before any negative is printed).
