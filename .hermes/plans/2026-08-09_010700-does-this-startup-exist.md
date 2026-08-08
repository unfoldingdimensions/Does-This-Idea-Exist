# Does This Startup Exist — Validation Memo + Implementation Plan

> **For Hermes:** This plan is GATED — read Part 0 (research verdict) and the decision block before any execution. If the user's gate rule triggers (idea dropped), Part 2 is void. If the user chooses PROCEED-RENAMED, implement Part 2 task-by-task with the `subagent-driven-development` skill (fresh subagent per task, spec-compliance then code-quality review).

**Goal:** Turn IDEA.md ("a simple landing page that consolidates which startups already exist, what they do, their website/GitHub repo") into a shipped product — *after* a market-validation gate that can kill the idea.

**Architecture:** Static-first Next.js one-pager. Startup data lives as versioned, schema-validated JSON in the repo ("data-as-code") — git is the audit trail. A small verification pipeline (link health + GitHub API + human review + scheduled freshness cron) keeps entries honest, with verified/unverified/archived badges in the UI. Client-side search (Fuse.js) over name/tagline/description/tags answers the core question "does this startup exist?" with zero backend. Privacy-first by default: no analytics, no cookies, no PII.

**Tech Stack:** Next.js 16 + shadcn/ui (warm-minimal, both themes), TypeScript, zod (schema), Fuse.js (search), Node script `scripts/verify.mjs` (verification), GitHub Actions (scheduled freshness), Vercel static export (deploy).

**Status:** 🟢 **EXECUTING (local backend build)** — gate passed 2026-08-09: user chose **PROCEED-RENAMED → IdeaExists**, added requirements: keep it local, seed-by-GitHub-link feature, backend-fetched descriptions/created-dates, LLM = opencode.go `deepseek-v4-flash`, weekly website verification. **Part 2's static-only approach is superseded by Part 3** (local FastAPI + SQLite + LLM enrichment).

---

# Part 0 — Research Verdict (THE GATE)

## 0.1 Method

Validation research ran 2026-08-09 (background agent + direct browser verification of the decisive find). Candidates were actually visited (curl with browser UA / browser_navigate / Wayback CDX); bot-blocked or dead sites are flagged, nothing assumed from memory.

## 0.2 Evidence table

| Name | URL | What it does (verified) | Closeness | GitHub links? |
|---|---|---|---|---|
| **doesthisstartupexist.com** | https://doesthisstartupexist.com/ | **Exact brand + tagline "Verify Your Startup Ideas" — LIVE but a Wix template shell**: logo is a Wix ad ("Go from idea to live site in minutes"), page = contact form + email-list signup + cookie banner. Wayback: domain 301'd since 2021-11-30, snapshots since 2022-01. **No directory, no search, no product.** | ESSENTIALLY IDENTICAL **BRAND** (product absent) | ❌ (no product) |
| There's An AI For That | https://theresanaiforthat.com/ | Live. "The #1 website for AI tools. Used by 90M people." Searchable directory answering "is there an AI for X" — the exact idea-checker format, AI vertical only. Homepage carries ~64 GitHub mentions (tool cards include repo links for open-source tools). | VERY CLOSE (format), vertical-siloed | ✅ (incidental, AI tools) |
| There's An App For That | https://thereisanappforthat.com/ | **DEAD** — SSL error on live check. | — | — |
| There's A Website For That | https://tawft.com/ | **DEAD** — DNS does not resolve. | — | — |
| YC Companies Directory | https://ycombinator.com/companies | Live. YC startup pages with description + website + (incidentally) GitHub links (Stripe's page: 2 github.com links). YC-only cohort. | PARTIAL OVERLAP (registry, YC-only) | ✅ (incidental) |
| Crunchbase | https://crunchbase.com | Company/startup registry of record: descriptions, websites, funding. Paid, no GitHub focus, not an idea-checker. | PARTIAL OVERLAP (different job) | ❌ |
| AlternativeTo / Product Hunt | https://alternativeto.net, https://producthunt.com | App/software alternatives + launch feed. Not startup existence checkers. | PARTIAL OVERLAP | ❌ |
| namechk / knowem / instantdomainsearch | https://namechk.com (403/CAPTCHA), https://knowem.com (unreachable), https://instantdomainsearch.com | Handle/domain availability checkers — a **different job** (name availability, not "does this startup exist"). | DIFFERENT | — |
| "Made in X" / awesome-country lists | e.g. slowernews/awesome-open-source-by-country-or-region, made-in-bulgaria (GitHub) | Country/region open-source project lists. Not startup directories with descriptions. | DIFFERENT | ✅ (but not startups) |
| GitHub API search "does this startup exist" | api.github.com | total: 0 — no existing repo/product named this on GitHub. | — | — |

## 0.3 Verdict

**(B) VERY CLOSE PRODUCTS EXIST — no essentially-identical product, but the exact brand is taken.**

- **No working product** has the core value prop "does this startup exist?" with name + one-liner + website + **GitHub repo** as core fields, across all industries. TAAFT proves the idea-checker format but is AI-only; Crunchbase/YC are registries, not checkers; the app/website variants (TIAFAT, TAWFT) are dead.
- **However, the exact brand "Does This Startup Exist" is taken and live** (doesthisstartupexist.com, a Wix placeholder claiming the name + tagline "Verify Your Startup Ideas" since ~2021). The domain is unavailable. Shipping under the same name would be confusing at best, squat-adjacent at worst.
- Residual gap the idea *could* defensibly fill (if renamed): a **general-purpose, verification-first startup existence checker** — idea-in → "exists or not" with website + GitHub links, verified/archived badges, freshness guarantees. TAAFT-for-startups, minus the AI silo, plus honesty about dead startups.

## 0.4 Decision block — **user must choose**

| Option | What it means | Fit with user's rule |
|---|---|---|
| **KILL (recommended)** | Drop the idea. Brand is taken, close analogues cover the core need, and the user's stated gate is "if something absolutely like this exists, drop." The name is gone regardless. | ✅ honors the rule as stated |
| **PROCEED-RENAMED** | Ship the gap-filling version under a new name (e.g. **IdeaExists**, StartupExists, DoesItExist, ExistCheck — name + domain availability check is a pre-task) with the sharper angle: verification badges, GitHub links, archived/dead tracking. | ⚠️ rule bent — brand collision is real; only defensible because no working product exists and the user gets a personal tool either way |

> If KILL: stop here — Part 1 stays as reference, Part 2 is void. If PROCEED-RENAMED: everything below is live, and Task 1 is the rename/domain check.

---

# Part 1 — Product Design (the molded product)

The raw one-liner in IDEA.md → this shaped product, decided via sequential-thinking chain (11 thoughts):

## 1.1 Use case

- **Primary user: the user themself.** Recurring pain: "did someone already build this?" while generating project ideas. The site answers it in <30s.
- **Secondary:** indie hackers doing idea validation / competitor discovery.
- **Three jobs-to-be-done:** (1) **ASK** — type an idea ("AI resume builder for devs") → matching existing startups; (2) **BROWSE** — scan a category to see what exists and what they do; (3) **VERIFY** — for a given name, confirm it's real, find website + GitHub.
- **Non-goals (YAGNI):** funding data, founders, valuations, reviews — Crunchbase's job, not ours.
- **Definition of done:** the user can type any of their past idea names and get a correct exists/doesn't-exist answer with links in <30 seconds.

## 1.2 Data model (schema v1)

Every entry in `data/startups.json`:

```json
{
  "schema_version": 1,
  "startups": [
    {
      "id": "notion",
      "name": "Notion",
      "tagline": "All-in-one workspace for notes, docs, and projects",
      "description": "Notes, wikis, databases, and project management in one collaborative workspace.",
      "category": "productivity",
      "website_url": "https://www.notion.so",
      "github_url": null,
      "status": "active",
      "verified": true,
      "verified_at": "2026-08-09",
      "last_checked": "2026-08-09",
      "source": "curated"
    }
  ]
}
```

- `github_url` is **optional** — many real startups have no public repo; requiring it would skew the directory dev-only (a known failure mode of this genre).
- `status`: `active | pivoted | dead` (stale entries are the #1 directory killer).
- `verified` + `verified_at` + `last_checked`: first-class verification state (see 1.5).
- `source`: `curated | submitted | api`. Schema is versioned so future fields are additive (user's non-destructive preference).
- Logo: skipped for MVP — initials avatar instead (YAGNI).

## 1.3 Data fetching

Tiered, additive — MVP only does Tier 1+2:

1. **Tier 1 (MVP): manual curation** — the user (with AI drafting help) adds startups from their own idea backlog and browsing. Seed ~50–100 entries across the categories the user actually works in: productivity tools, AI apps, desktop/Tauri apps, dev tools, freelance/GHL services, resume builders.
2. **Tier 2 (MVP): enrichment via GitHub REST API** — auto-confirm `github_url` exists (repo 404 → flag), pull stars/language/description. Unauth rate limit (60/hr) is fine at this scale; a token lifts it to 5k/hr. Website URLs get HEAD-checked by the verify script.
3. **Tier 3 (later, optional): public submission form** → GitHub issue template (zero backend) or a small endpoint. **Never scrape Crunchbase/YC** (ToS risk). If ingestion is ever wanted: Product Hunt official API + GitHub Search API are legitimate.

## 1.4 Data storage

**Data-as-code**: versioned JSON in the repo (`data/startups.json`). Git history = audit trail; diffs reviewable; no backend; static export stays possible; matches the user's git-driven workflow.

- Build-time typed loader: zod schema validates the file — schema drift fails the build loudly.
- **Rejected:** SQLite/backend (overkill for "simple landing page"; revisit only if submissions+moderation become real), headless CMS (cloud — against privacy-first), spreadsheet (not code-reviewable).
- **Growth path (additive):** if the dataset outgrows client-side search (~2–3k entries), migrate to a build-time Fuse.js index or a serverless API route. Not a rewrite.

## 1.5 Data verification (the differentiator)

Layered pipeline, automated except the final human gate:

1. **Submit-time:** every new entry lands as `verified: false`. `scripts/verify.mjs` runs HEAD/GET on `website_url` (non-200 → flag) + GitHub API lookup (repo 404 → flag; record stars, archived status).
2. **Human gate:** the user reviews each new entry once and sets `verified: true` + `verified_at`. This is the "absolutely exists" seal.
3. **Freshness:** scheduled GitHub Actions workflow (weekly) re-checks all entries. 3 consecutive failures → flip `status` to `dead`/`pivoted` automatically. **No auto-delete** — non-destructive: flip a flag, keep the data.
4. **UI expression:** badges — **Verified** (checked + human-approved) vs **Unchecked** (awaiting review); dead/pivoted entries get a muted **Archived** chip and sink to the bottom of results. The site never silently lies about a startup.

## 1.6 Visitor tracking (privacy-first)

1. **MVP default: NO tracking at all.** Personal tool — YAGNI. Server logs (or Vercel's anonymous analytics if deployed there) are enough to know it's alive.
2. **If published publicly later:** add **GoatCounter** (free tier, cookie-less, single script tag, self-hostable, GDPR-friendly) — additive, default stays off.
3. Plausible/Umami self-hosted only if dashboards are ever wanted on the user's own infra — overkill for a landing page.
4. By construction: all JS local, no outbound trackers, plain `<a>` links.

## 1.7 Design + layout

Warm-minimal one-pager, shadcn/ui, light + dark themes both QA'd (user's standard), equal-height cards.

- **Header (sticky):** site name + tagline ("Searchable directory of startups — what they do, their website, their code"), right: theme toggle + "Submit a startup" link.
- **Hero search:** large centered input — the ASK mode, placeholder "e.g. AI resume builder for developers". Debounced client-side Fuse.js search over name + tagline + description + tags (no backend).
- **Category chips:** Productivity, AI, Dev Tools, Desktop Apps, Freelance/GHL, Resume Builders, …
- **Results grid:** equal-height cards (`grid`, `repeat(auto-fill, minmax(280px, 1fr))`). Card = name row (initials avatar, name, verified badge), tagline, tags, footer row: website + GitHub icon links (+ star count if repo). Archived entries dimmed with **Archived** chip, sorted last.
- **Empty state (the emotional payoff):** "Nothing found for 'X' — maybe you build this?" — converts a dead-end search into the site's reason to exist.
- **Footer:** about, "how verification works", data freshness date, submit link, total-entry count.

## 1.8 Idea → product molding (the path)

Stage 0: validation gate (this doc). → Stage 1: scaffold. → Stage 2: data layer. → Stage 3: seed data. → Stage 4: UI + search. → Stage 5: verification tooling. → Stage 6: submission path. → Stage 7: deploy + both-theme QA. → Stage 8: publish decision. (Details in Part 2.)

---

# Part 2 — Implementation Plan (LIVE ONLY IF PROCEED-RENAMED)

> **Windows/git-bash notes for the implementer:** use POSIX syntax in terminal; E:\ drive — use terminal `ls`/`find`, not search_files (known quirk); npm dev wrappers orphan children that hold ports on this host (EADDRINUSE on restart — kill listeners via `Get-NetTCPConnection -LocalPort <port> -State Listen | Stop-Process`); no global git config — set local identity before first commit; CRLF-safe: keep scripts as `.mjs` and commit with LF. Next.js 16: `proxy.ts` replaces `middleware.ts`, `next lint` removed → use `eslint`.

**Pre-req (one-time):** decide rename (default: **IdeaExists**), check domain availability (namecheap/instantdomainsearch), set git identity:
```bash
git init
git config user.name "unfoldingdimensions"
git config user.email "unfoldingdimensions@gmail.com"
```
All commits use Conventional Commits + `Co-Authored-By: Hermes Agent <hermes@nousresearch.com>` trailer (user's global AGENTS.md rule).

### Task 1: Scaffold Next.js 16 + shadcn + git

**Files:** project root; `package.json`; `app/`; `components.json`; `.gitignore`

**Steps:**
1. `npx create-next-app@latest . --typescript --eslint --tailwind --app --src-dir=false` (accept defaults; project dir is the repo root).
2. `npx shadcn@latest init` then add `button`, `input`, `badge`, `card`, `dropdown-menu`, `avatar` (theme toggle needs dropdown-menu).
3. Set up both-theme baseline (shadcn dark mode via `next-themes`), minimal placeholder page.
4. Commit: `chore: scaffold next.js 16 + shadcn` with Co-Authored-By trailer.

### Task 2: Data layer — schema + loader + validation test

**Files:** Create `data/startups.json` (empty array + `schema_version: 1`), `lib/startups.ts` (zod schema + typed loader), Test: `lib/__tests__/startups.test.ts` (vitest)

**Step 1 — write failing test:** loader parses a valid fixture; rejects an entry missing `name`; rejects unknown `status`.
**Step 2 — run:** `npx vitest run lib/__tests__/startups.test.ts` → FAIL (no loader yet).
**Step 3 — implement:** zod schema mirroring §1.2 (all fields; `github_url` nullable; `status` enum; `verified` boolean + `verified_at`/`last_checked` dates), loader reads `data/startups.json` with `node:fs`.
**Step 4 — run:** same command → PASS.
**Step 5 — commit:** `feat: add zod-validated startup data model` (+ trailer).

### Task 3: Seed data — ~50–100 real startups

**Files:** Modify `data/startups.json`

**Steps:**
1. Seed the user's own domains (productivity, AI, desktop/Tauri, dev tools, freelance/GHL, resume builders). Each entry human-reviewed at add time — this rehearses the verification pipeline (§1.5). Add `verified: false` until the review pass in Task 6.
2. Commit in batches: `feat(seed): add productivity category (n entries)` … one commit per category.

### Task 4: UI — hero search + chips + card grid + empty state

**Files:** Modify `app/page.tsx`; Create `components/startup-card.tsx`, `components/category-chips.tsx`, `lib/search.ts` (Fuse.js wrapper); Modify `app/layout.tsx` (header + footer + theme toggle)

**Steps:**
1. Add Fuse.js: `npm i fuse.js`.
2. Card grid with equal heights (`grid` + `minmax(280px,1fr)`), initials avatar, verified badge, website/GitHub icon links, star count if repo, archived dimming.
3. Debounced search (300ms) over name/tagline/description/tags; category chips filter; empty state per §1.7.
4. Verify: `npm run dev` → search "resume" filters live; both themes look right; cards equal height in a row (user's standard — check measured geometry, not screenshots).
5. Commit: `feat: add searchable startup directory UI` (+ trailer).

### Task 5: Verification tooling

**Files:** Create `scripts/verify.mjs`; Create `.github/workflows/freshness.yml`

**Steps:**
1. `scripts/verify.mjs`: for each entry — HEAD/GET `website_url` (non-200 → flag), GitHub API repo lookup when `github_url` set (404 → flag; record stars/archived), write `last_checked`; exit non-zero on new flags. Runs on `node scripts/verify.mjs`.
2. Add `npm run verify` script.
3. `freshness.yml`: weekly cron (`cron: 0 6 * * 1`), runs verify, opens an issue summarizing flags; auto-flips `status` to `dead` after 3 consecutive failures (script keeps a failure counter in `data/.verify-state.json`). No deletes, ever.
4. Test locally: `npm run verify` on seed data → expect flags for any broken URLs you seeded deliberately (seed 2–3 known-bad URLs in Task 3 to prove the pipeline).
5. Commit: `feat: add link/repo verification pipeline + weekly freshness cron` (+ trailer).

### Task 6: Human review pass (verification gate)

**Files:** Modify `data/startups.json`

**Steps:**
1. Review every seeded entry: visit website, confirm existence, set `verified: true` + `verified_at`; fix/flag anything dead.
2. `npm run verify` → clean. Commit: `chore: verify seed data (n entries)` (+ trailer).

### Task 7: Submission path (zero backend)

**Files:** Create `.github/ISSUE_TEMPLATE/submit-a-startup.md`; footer "Submit a startup" → repo issues link

**Steps:**
1. Issue template: name, tagline, description, website, GitHub repo (optional), category. Label `submission`.
2. Commit: `feat: add startup submission issue template` (+ trailer).

### Task 8: Deploy + final QA

**Files:** Vercel project config

**Steps:**
1. `npm run build` → clean static export. Deploy to Vercel (user's account) — no analytics installed (default OFF per §1.6).
2. Final QA: search accuracy, both themes, equal-height cards, empty state, archived sorting, responsive down to mobile.
3. Commit if fixes needed; tag `v1.0.0`.

### Task 9: Publish decision (open question, default: local-first)

- Default: keep it private/local for personal use; decide later whether to publish publicly.
- If public: add GoatCounter (additive, default-off) + revisit name/domain (pre-req block).

---

# Risks, Tradeoffs, Open Questions

**Risks:**
1. **Staleness** — directory death by decay. Mitigated: weekly freshness cron, verified/archived flags, no silent lies (§1.5).
2. **Dataset size vs client-side search** — fine to ~2–3k entries; additive path to build-time index / serverless API (§1.4).
3. **Legal** — linking is fine; never scrape Crunchbase/YC; GitHub API within ToS (§1.3).
4. **Dev-only skew** — `github_url` optional + seed a non-dev mix (§1.2, Task 3).
5. **Brand collision** — the original name is taken; only PROCEED-RENAMED avoids it (Part 0).

**Accepted tradeoff:** manual curation (quality + verification) over API ingestion (coverage + staleness). This is a personal tool; curation happens naturally during the user's own idea-validation flow.

**Open questions (defaults in bold):**
- Q1 Gate decision: **KILL** vs PROCEED-RENAMED (user must choose — Part 0.4).
- Q2 If proceeding: rename — **IdeaExists** vs StartupExists / DoesItExist / ExistCheck (domain check first).
- Q3 Publish: **local-first** vs public later (with GoatCounter).
- Q4 Submission path: **GitHub issue template** vs form+backend later.
- Q5 Seed scope: **user's own domains (~50–100)** vs broad coverage.

**Definition of done (from §1.1):** user types any of their past idea names → correct exists/doesn't-exist answer with website + GitHub links in <30 seconds, verified and fresh.

---

# Part 3 — REVISED ARCHITECTURE (user decisions, 2026-08-09) — SUPERSEDES Part 2's static approach

User decisions: **keep it local** (no Vercel), **seed-a-startup-via-GitHub-link** feature (backend fetches ALL details), **manual website seeds** (backend fetches "what they do" + "when created"), **LLM = opencode.go deepseek-v4-flash key** for enrichment, **weekly verification** of websites after the site is live.

## 3.1 Stack (local-first)

| Layer | Choice | Port | Notes |
|---|---|---|---|
| Backend | FastAPI + uvicorn (venv in `backend/`) | **:8020** | deps: fastapi, uvicorn[standard], httpx, python-dotenv |
| Storage | SQLite stdlib (`backend/data/ideasexist.db`, git-ignored) | — | plain sqlite3, row factory, WAL |
| LLM | `https://opencode.ai/zen/go/v1` + `OPENCODE_GO_API_KEY` (from Hermes `.env`, copied to git-ignored `backend/.env`), model `deepseek-v4-flash` | — | verified live 2026-08-09 (PROBE_OK) |
| Frontend | Next.js 16 + shadcn/ui (`frontend/`) | **:3023** | `NEXT_PUBLIC_API_BASE=http://localhost:8020`, Fuse.js client search |
| Verification | `POST /api/verify/run` + Hermes weekly cronjob (created once server is live) | — | cron curls the local endpoint |

Ports deliberately avoid collisions: plus-v2 (:8001/:3123), OmniRoute gateway (:20128).

## 3.2 Schema (startups table)

`id, name, tagline, description, category, website_url, github_url, founded, stars, language, status (active|pivoted|dead), verified (0/1), verified_at, last_checked, check_failures, source (github|website), created_at, updated_at` + `verify_log` (per-check history). Unique indexes on `github_url`/`website_url` → re-seeding **updates** an existing entry (additive, never duplicates). Non-destructive rule: `status=dead` after 3 consecutive failed checks — never delete.

## 3.3 Seed flows

- **GitHub link** (`POST /api/seed/github {github_url}`): GitHub API repo fetch (name, description, created_at→founded, stars, language, topics, homepage, archived) → LLM generates tagline + category + description (JSON) → upsert, `verified=0`.
- **Website** (`POST /api/seed/website {name?, website_url}`): homepage fetch (browser UA) + title/meta/text extraction (~8k chars) → **Wayback CDX** first-snapshot date → founded proxy → LLM name (if absent) + tagline + category + description → upsert, `verified=0`.
- Human gate unchanged: user reviews → marks verified (badge).

## 3.4 Verification (weekly, after live)

HEAD/GET website (browser UA, redirects, 15s) + GitHub API repo re-check (404/archived → flag) → `check_failures`±, `last_checked`, `verify_log` row; 3 strikes → `status=dead` (dimmed + Archived chip, sorted last). Endpoint + Hermes cronjob (weekly) created once the server is running.

## 3.5 LLM pitfalls (from verified opencode.go reference)

`deepseek-v4-flash` is a reasoning model: **`max_tokens` ≥ 8000** (else empty content, `finish_reason=length`), **timeout ≥ 180s**, `response_format: json_object` with **one retry without it on HTTP 400**, tolerant JSON parse (strip fences), one retry per call. GitHub API: unauth 60 req/hr is plenty at ~30 entries; optional `GITHUB_TOKEN` for headroom.

## 3.6 Repo layout

```
root/  IDEA.md, README.md, .gitignore, .hermes/plans/
  backend/  app/{main,config,db,llm,github,website,enrich,verify}.py, requirements.txt, .env (ignored)
  frontend/ Next.js 16 + shadcn
```
