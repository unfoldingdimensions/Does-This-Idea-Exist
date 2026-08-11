# IdeaExists

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Does this startup exist? — a local startup directory (FastAPI backend + Next.js frontend).**

A verification-first directory of startups: what they do, where they live, and
whether they're still alive. Entries are seeded from curated sources and
**checked by a human, not a crawler** — automation only ever flags; a person
stamps the trust. Everything runs locally: SQLite file, no accounts, no
tracking, no favicon fetching. Searches stay on this machine.

**Status:** in development (local backend + frontend). The archive grows with
every seed; data lives in `backend/data/ideasexist.db` (git-ignored).

## Table of Contents

- [Quickstart](#quickstart)
- [Features](#features)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [API](#api)
- [Verification & the human gate](#verification--the-human-gate)
- [Admin seeder](#admin-seeder-owner-only)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Quickstart

**Prerequisites:** Python 3.11+, Node.js 20+.

```bash
# 1. Backend (FastAPI on :8020)
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env                             # then fill OPENCODE_GO_API_KEY
uvicorn app.main:app --port 8020

# 2. Frontend (Next.js on :3023, second terminal)
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:3023](http://127.0.0.1:3023). The footer gear button
opens the admin panel (see [Admin seeder](#admin-seeder-owner-only)).

## Features

- **Search + facets** — client-side Fuse fuzzy search (relevance-ranked,
  AND across terms) with category / founded-year / status filters and a
  trust-weighted default sort (verified first, then stars).
- **Seed from anywhere** — paste a GitHub repo URL or a website; the backend
  fetches metadata + homepage, calls the LLM for a profile, and upserts
  (re-seeds refresh, never duplicate).
- **Weekly liveness verification** — every entry is re-checked; only genuine
  `404/410`s count against it (bot-walls, rate limits and transient errors
  skip). Three consecutive failures file an entry as **dead** — filed, never
  deleted.
- **Human gate** — automation never stamps trust. The admin panel queues
  alive-but-unverified entries; you approve them one-by-one, per seed-batch,
  or in bulk. Verified rows are protected from automation entirely.
- **Local-first privacy** — SQLite (WAL), no accounts, no analytics, no
  external avatars; the privacy line is a brand promise, not a footnote.
- **Warm Glass UI** — Next.js 16 + shadcn/ui, beige/navy light ⇄
  charcoal/beige dark themes, inertial scrolling (Lenis), `prefers-reduced-motion`
  respected throughout, WCAG AA contrast in both themes.

## Architecture

```
backend/   FastAPI + SQLite (WAL) on :8020
           main.py    API routes · admin gate (ADMIN_TOKEN) · rate limits
           seeder.py  kind-scoped job queues (seed ∥ verify workers, serial within kind)
           verify.py  tri-state liveness checks · human-approval queue
           enrich.py  LLM profile generation (deepseek-v4-flash via opencode.go)
           netguard.py SSRF guard (per-hop IP validation, 2 MB body cap)
           data/      ideasexist.db (git-ignored) + bundled seed lists

frontend/  Next.js 16 + shadcn/ui on :3023
           app/        single-page archive (search bar, grid, detail dossier)
           components/ discovery bar · startup cards · admin panel (seed/verify/health)
           lib/        API client · Fuse search · formatting
```

Both run standalone; the frontend reads `NEXT_PUBLIC_API_BASE` (default
`http://localhost:8020`).

## Configuration

Copy `backend/.env.example` → `backend/.env` and fill in the API key. `.env`
is git-ignored — never commit secrets. The same variables work on a host;
local and hosted behavior are identical.

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `OPENCODE_GO_API_KEY` | — (required) | LLM provider key for profile generation |
| `ADMIN_TOKEN` | empty | Owner token for the admin panel; empty = panel disabled |
| `LLM_BASE_URL` | `https://opencode.ai/zen/go/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `deepseek-v4-flash` | Model used for profiles |
| `GITHUB_TOKEN` | empty | Optional — raises GitHub API limits from 60 to 5,000 req/hr |
| `DB_PATH` | `backend/data/ideasexist.db` | SQLite file location |
| `FRONTEND_ORIGIN` | `http://localhost:3023` | CORS allow-origin |
| `VERIFY_AUTO_STALE_DAYS` | `7` | Auto-start a verify pass at boot when entries are older than this (`0` disables) |
| `MUTATION_AUTH` | empty | `1` requires the admin token on status-flip / seed / verify endpoints — **hosting must set `1`** |
| `RATE_LIMIT_ENABLED` | `1` | Per-IP rate limits on the admin gate + mutations (`0` disables) |

### Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8020` | Backend origin |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3023` | Canonical site origin (SEO metadata) |

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness + model/db echo |
| `GET /api/startups` | list (`?q=` `?category=`) |
| `GET /api/categories` | category counts |
| `POST /api/seed/github` `{github_url}` | fetch repo + LLM profile → upsert |
| `POST /api/seed/website` `{website_url, name?}` | fetch homepage + Wayback date + LLM profile → upsert |
| `POST /api/verify/run` | enqueue a verification pass → `{job_id}` |
| `GET /api/verify/status/{job_id}` | pass progress + bucket results |
| `GET /api/verify/current` | the active pass, or `null` |
| `POST /api/startups/{id}/verify` | human: mark verified (also revives + resets strikes) |
| `POST /api/startups/{id}/unverify` | human: revoke the stamp |
| `POST /api/startups/{id}/dead` | human: file as dead |
| `GET /api/stats` | counts + freshness |

Admin routes are prefixed `/api/admin` and require the `X-Admin-Token` header:

| Endpoint | Purpose |
|---|---|
| `GET /admin/check` | token check (200 / 403) |
| `POST /admin/seed` `{source, params}` | start a seed job → `{job_id}` |
| `GET /admin/seed/status/{job_id}` | job progress |
| `GET /admin/seed/jobs` | all jobs (live + persisted history) |
| `GET /admin/verify/suggested` | human-approval queue |
| `POST /admin/verify/approve` | stamp verified: `{ids}` · `{approve_all: true}` · `{created_after, created_before}` (per-batch) |

## Verification & the human gate

The automated pass is **conservative by design**:

- **Only a genuine `404/410` earns a strike.** Bot-walls (`401/403`), rate
  limits (`429`), transient `5xx` and network errors are skips — three
  bot-walled runs can never dead-file a healthy company.
- **Three consecutive strikes** file an entry as `dead`. Filed, never deleted —
  dead is a status, not an erasure.
- **Verified rows are protected from automation**: a human-stamped entry never
  accumulates auto-strikes or auto-files; a failed check surfaces in the
  admin panel as a re-check item instead.
- The human revive (`POST /api/startups/{id}/verify`) resets the strike
  counter — human judgment outranks the machine.

The admin panel's **Verification** tab lists the suggested queue (alive,
unverified, zero strikes). Approve one at a time, an entire seed-batch (grouped
by creation day), or everything. Every approval is behind a confirm dialog and
reversible from the status pill.

## Admin seeder (owner-only)

The footer gear button opens the admin panel — unlock with `ADMIN_TOKEN` (set
in `backend/.env` locally, or as an environment variable on your host; the
token never ships in the repo). Seed from four sources:

1. **Famous list** — bundled `backend/data/seed_famous.json` (~65 well-known
   startups). The one-click "initial incentive" for a fresh directory.
2. **GitHub search** — `search/repositories` by query (e.g. `stars:>50000`),
   sorted by stars.
3. **URL list** — paste websites / GitHub repos, one per line.
4. **Design library** — bundled `backend/data/seed_design_library.json`
   (201 curated product sites).

Per-run **cap** is free-form (1–500; the server returns a loud 400 outside
that — it never clamps silently). Re-runs skip the LLM for entries already on
file (`reuse_profile`), so re-seeding is idempotent and near-free.

**Failure policy: the seeder fails loudly.** Every failed entry is logged,
listed in the panel's error list, and the finishing toast reports
`done · failed` explicitly. Batches over ~50 repos/hour need `GITHUB_TOKEN`.
Seeded entries land **unverified** — review them on the cards; the human gate
stays the trust layer.

## Testing

```bash
npm test
```

Runs the backend smoke suite (in-process, throwaway SQLite DB — no live server
or network needed) plus the frontend lint + production build. It pins the API
surface, admin gate, queue serialization, dedup upsert, the tri-state verify
logic, restart recovery, and the human-gate invariants.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) — release/rollback runbook, DNS records per
platform, and the pre-deploy checklist. **Before hosting:** set `MUTATION_AUTH=1`
and `ADMIN_TOKEN` on the host, and pin `NEXT_PUBLIC_API_BASE` /
`NEXT_PUBLIC_SITE_URL` at build time. Recent readiness and security reports:
[deploy-readiness-report.md](deploy-readiness-report.md).

## Contributing

This is a personal project, but issues and pull requests are welcome —
[open an issue](https://github.com/unfoldingdimensions/Does-This-Idea-Exist/issues)
if something breaks or an entry looks wrong. Changes keep the local-first
posture: no accounts, no tracking, no favicon fetching, and no feature that
regresses the privacy line.

## License

[MIT](LICENSE) © 2026 unfoldingdimensions
