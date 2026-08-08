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
