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

**Prerequisites:** Python 3.11+, Node.js 23+ (`scripts/sort-check.ts` runs on native type stripping).

```bash
# 1. Backend (FastAPI on :8020)
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env                             # set ADMIN_TOKEN + OPENCODE_GO_API_KEY
uvicorn app.main:app --port 8020 --workers 1     # --workers 1: the job queue is in-process

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
| `ADMIN_TOKEN` | — (**required**) | Owner token. Gates the admin panel and every mutating endpoint. The app **refuses to start** without it (see `MUTATION_AUTH`) |
| `OPENCODE_GO_API_KEY` | — (required to seed) | LLM provider key for profile generation |
| `LLM_BASE_URL` | `https://opencode.ai/zen/go/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `deepseek-v4-flash` | Model used for profiles |
| `GITHUB_TOKEN` | empty | Optional — raises GitHub API limits from 60 to 5,000 req/hr |
| `DB_PATH` | `backend/data/ideasexist.db` | SQLite file location (`/data/ideasexist.db` in Docker) |
| `FRONTEND_ORIGIN` | `http://localhost:3023` | CORS allow-origin |
| `VERIFY_AUTO_STALE_DAYS` | `7` | Verification threshold — a pass is enqueued at boot and every 24h when entries are older than this (`0` disables) |
| `MUTATION_AUTH` | `1` (**on**) | Requires the admin token on status-flip / seed / verify-run endpoints. Set `0` only for a throwaway local instance. With it on and `ADMIN_TOKEN` empty, startup fails loudly rather than 403-ing every write |
| `RATE_LIMIT_ENABLED` | `1` | Per-IP rate limits on the admin gate + mutations (`0` disables) |
| `FORWARDED_ALLOW_IPS` | empty | Reverse-proxy address, so uvicorn resolves the real client IP for rate limiting. Empty = trust no forwarded headers. **Never `*` on a public host** — that lets any caller spoof `X-Forwarded-For` and bypass the limits |
| `LOG_LEVEL` | `INFO` | Log level; output goes to stdout |

### Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8020` | Backend origin |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3023` | Canonical site origin (SEO metadata) |

## API

Public reads — no token:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness + model/db echo |
| `GET /api/startups` | list (`?q=` `?category=` `?limit=` `?offset=`; `limit` defaults to 3000, max 5000) |
| `GET /api/startups/{slug}` | one product by slug — its teardown fields, its `evidence` rows, and the two trust signals as explicit `admin_verified` / `machine_verified` (`+ _at`) fields. A **pure read**: it never triggers a capture |
| `GET /api/search` | search with a per-result `reason` from the eight-reason ladder; an empty query is `200 []` |
| `GET /api/categories` | category counts |
| `GET /api/stats` | counts + freshness |
| `POST /api/compare` | the gap table: `{you, competitors[]}` → the five bands, every cell sourced or `unknown` |
| `GET /api/export/{markdown\|json\|csv}` | a comparison as a file (`?you=` `&competitors=`) |

Founder endpoints — a draft is owned by the one-time `founder_token` it is created
with, sent as `X-Founder-Token`; a read, confirm, publish, compare or export
without it is refused:

| Endpoint | Purpose |
|---|---|
| `POST /api/founder-app` | draft your own app from a URL, a form, or the agent-JSON shape → the draft plus its one-time token |
| `GET /api/founder-app/{id}` | read the draft (token required) |
| `POST /api/founder-app/{id}/confirm` | confirm the draft — the gap table will not run before this |
| `POST /api/founder-app/{id}/publish` | submit it to the archive queue (a link is required; consent is the second gate) |

Writes — require `X-Admin-Token` (`MUTATION_AUTH` defaults on) and are rate-limited:

| Endpoint | Purpose |
|---|---|
| `POST /api/seed/github` `{github_url}` | fetch repo + LLM profile → upsert |
| `POST /api/seed/website` `{website_url, name?}` | fetch homepage + a date source + LLM profile → upsert |
| `POST /api/verify/run` | enqueue a verification pass → `{job_id}` |
| `POST /api/startups/{id}/verify` | human: mark verified (also revives + resets strikes) |
| `POST /api/startups/{id}/unverify` | human: revoke the stamp |
| `POST /api/startups/{id}/dead` | human: file as dead |

Admin routes are prefixed `/api/admin` and require the `X-Admin-Token` header:

| Endpoint | Purpose |
|---|---|
| `GET /api/admin/check` | token check (200 / 403) |
| `POST /api/admin/seed` `{source, params}` | start a seed job → `{job_id}` |
| `GET /api/admin/seed/status/{job_id}` | job progress |
| `GET /api/admin/seed/jobs` | all jobs (live + persisted history) |
| `GET /api/admin/verify/status/{job_id}` | pass progress + bucket results |
| `GET /api/admin/verify/current` | the active pass, or `null` |
| `GET /api/admin/verify/suggested` | human-approval queue |
| `POST /api/admin/verify/approve` | stamp verified: `{ids}` · `{approve_all: true}` · `{created_after, created_before}` (per-batch) |
| `POST /api/admin/funnel/import` | apply a completed liveness-funnel run (`{run, dry_run}`): admit the clean LIVE majority under the machine stamp, queue the exceptions for the human path. Admission only — it never deletes (dry-run is the default) |
| `POST /api/admin/capture/{startup_id}` | capture a teardown by hand (the panel's button) |
| `GET /api/admin/capture/status/{job_id}` | capture progress |
| `GET /api/admin/founder/submissions` | the publish queue (founder submissions and archive rows) |
| `POST /api/admin/founder/submissions/{id}/approve` | approve a publish request → the archive row, linked |
| `POST /api/admin/founder/submissions/{id}/reject` | reject it with a note the founder can read |
| `GET /api/admin/settings/gateways` | the LLM gateway registry (active, ready, `key_hint` — never the key) |
| `PUT /api/admin/settings/gateways/{id}` | set a gateway's key / model / base URL |
| `POST /api/admin/settings/gateways/active` | switch the active gateway |
| `POST /api/admin/settings/gateways/active/reset` | back to the environment default |
| `POST /api/admin/settings/gateways/{id}/test` | test a gateway's key |

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

### The two badges

- **Admin Verified** — a person stamped the record. This is the entry gate.
- **Machine Verified** — the automated pass last found it alive. It **decays**: a
  stale check reads "lapsed" while the record stays Admin Verified.

Both attach to the **record**, never to a claim. Every competitor claim carries
its own "per their pricing page, captured <date>" source line, and neither badge
says anything about whether a competitor's statement is true.

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

Five steps, in order:

1. **backend smoke** (`backend/tests/smoke.py`) — in-process against a throwaway
   SQLite DB: no live server, no network.
2. **backend functional** (`backend/tests/functional.py` — the gate) —
   `F-01`–`F-24` plus the trust and store-separation invariants, with the fetcher,
   both LLM prompts and both date sources stubbed: **270 checks** (now including
   the liveness-funnel contract: the shared rules module, the content-aware
   website check, and run import — admit / queue / never delete).
3. **frontend sort check** (`scripts/sort-check.ts`) — runs the real frontend
   module for all five sort keys.
4. **frontend lint + production build**.
5. **frontend e2e** (`scripts/e2e-verify.mjs`) — the real components rendered
   against stubbed HTTP: **239 checks** across twelve areas plus the non-happy
   states.

Together they pin the API surface, the admin gate, queue serialization, dedup
upsert, the tri-state verify logic, restart recovery, the human-gate invariants,
the teardown / compare / export contract, search reasons, and the security layer
(auth gating, the founder-draft token, the SSRF guards, rate limiting,
LLM-output bounds, LIKE-wildcard escaping).

Note: the runner is **Windows-only** — it invokes `backend/.venv/Scripts/python.exe`
and shells through `cmd.exe` — and needs **Node ≥23 first on PATH**, because the
sort check runs TypeScript through Node's native type stripping. If a bundled
Node 22 shadows the system Node, prepend the real one:

```powershell
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm test
```

There is no CI.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) — container build, volume/backup handling,
rollback, and the pre-deploy checklist.

The backend ships as a container ([backend/Dockerfile](backend/Dockerfile),
[docker-compose.yml](docker-compose.yml)) and **requires a persistent writable
volume** at `/data`: the archive is a SQLite file, verification runs for minutes
in background threads, and the job queue lives in process memory — so it cannot
run on a serverless host, and it must run with `--workers 1`. The frontend is a
normal Next.js build for Vercel/Netlify/CF Pages.

**Before hosting:** set `ADMIN_TOKEN` on the host (startup fails without it),
set `FRONTEND_ORIGIN`, set `FORWARDED_ALLOW_IPS` if behind a reverse proxy, and
pin `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_SITE_URL` at build time. Recent
readiness and security reports:
[deploy-readiness-report.md](deploy-readiness-report.md).

## Contributing

This is a personal project, but issues and pull requests are welcome —
[open an issue](https://github.com/unfoldingdimensions/Does-This-Idea-Exist/issues)
if something breaks or an entry looks wrong. Changes keep the local-first
posture: no accounts, no tracking, no favicon fetching, and no feature that
regresses the privacy line.

## License

[MIT](LICENSE) © 2026 unfoldingdimensions
