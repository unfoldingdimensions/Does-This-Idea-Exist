# IdeaExists (working title)

Does this startup exist? A local, verification-first directory of startups — what they do,
their website, their GitHub repo.

**Status:** in development (local backend + frontend). See `.hermes/plans/` for the full plan
and research memo.

## Architecture (local-first)

- `backend/` — FastAPI + SQLite + LLM enrichment (deepseek-v4-flash via opencode.go) on **:8020**
- `frontend/` — Next.js 16 + shadcn/ui on **:3023**
- Data: `backend/data/ideasexist.db` (git-ignored)

## Run

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env   # fill OPENCODE_GO_API_KEY
uvicorn app.main:app --port 8020

# frontend
cd frontend
npm install
npm run dev
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/startups` | list (optional `?q=` `?category=`) |
| `GET /api/categories` | category counts |
| `POST /api/seed/github` `{github_url}` | fetch repo + LLM profile → upsert |
| `POST /api/seed/website` `{website_url, name?}` | fetch homepage + Wayback date + LLM profile → upsert |
| `POST /api/verify/run` | weekly verification pass (3 strikes → `dead`, never deletes) |
| `GET /api/stats` | counts + freshness |
| `GET /api/admin/check` | admin token check (200 / 403) |
| `POST /api/admin/seed` `{source, params}` | start a seed job → `{job_id}` |
| `GET /api/admin/seed/status/{job_id}` | job progress (`total/done/ok/failed/errors`) |

## Admin seeder (owner-only)

The footer gear button opens the Admin panel. Unlock with `ADMIN_TOKEN` (set in `backend/.env`
locally, or as an environment variable on your host — **the same code works hosted; the token
never ships in the repo**). Then run batch seeds from three sources:

1. **Famous list** — bundled `backend/data/seed_famous.json` (~65 well-known startups). The
   one-click "initial incentive" seed for a fresh directory.
2. **GitHub search** — `search/repositories` by query (e.g. `stars:>50000`), sorted by stars.
3. **URL list** — paste websites/GitHub repos, one per line.
4. **Top Startups** — scrapes `topstartups.io` (~1,259 funded startups, ~20/page): company
   name + website per card, utm params stripped.

Per-run **cap** is a free-form input (default 30; pull 100+ in testing — server validates 1–500
and returns a loud 400 outside that, it never clamps silently). Re-runs skip the LLM for entries
already in the DB (`reuse_profile`), so re-seeding is idempotent and near-free.

**Failure policy: the seeder fails loudly.** Every failed entry is logged, listed in the panel's
error list (red "N failed" badge + details), and the finishing toast reports `done · failed`
explicitly. Nothing is swallowed. Batches >50 repos/hour need `GITHUB_TOKEN` (GitHub's unauth
limit is 60 repo fetches/hr, 10 searches/min).

Seeded entries land **unverified** — review them on the cards and use "Mark verified" (the human
gate stays the trust layer).
