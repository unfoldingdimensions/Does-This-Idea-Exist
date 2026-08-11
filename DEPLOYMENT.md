# Deployment Runbook — IdeaExists

How to ship IdeaExists and, more importantly, how to undo it. Read this BEFORE
the first deploy.

## 0. Shape of the deployment (read this first)

Two separate deployables, and they do **not** go to the same kind of host:

| Piece | What it is | Where it can run |
|---|---|---|
| `backend/` | FastAPI + **SQLite file** + in-process job queue (threads) | A container or VM with a **persistent writable volume** — Fly, Railway, Render, a VPS. |
| `frontend/` | Next.js 16 static/SSR build | Vercel, Netlify, Cloudflare Pages — pointed at the backend via `NEXT_PUBLIC_API_BASE`. |

The backend **cannot** run on a serverless/static host. The archive is a file on
disk (WAL-mode SQLite), verification passes run for minutes in background
threads, and the job queue lives in process memory. No volume means the archive
resets on every deploy.

**`--workers 1` is a correctness constraint.** Worker threads start at module
import and `JOBS`/`QUEUES` are per-process, so the "one verify pass at a time"
guard only sees its own process. A second worker gives you two concurrent verify
passes competing for the GitHub rate limit, two startup auto-verifies, and two
writers on one SQLite file. Scale with more machines behind a load balancer, not
more workers. The Dockerfile `CMD` already pins this — don't "optimize" it.

## 1. Pre-deploy checklist (hard gates)

- [ ] `npm test` at the repo root passes (backend smoke + frontend sort check + lint + build)
- [ ] All work committed (conventional commits, co-author trailer per repo convention)
- [ ] **Volume backup taken** — see §5. Do this BEFORE anything else.
- [ ] `ADMIN_TOKEN` is a strong random value, set on the host and nowhere in git
- [ ] `.env` files are untracked (`git check-ignore .env backend/.env` → both ignored)
- [ ] `npm audit` clean; `pip-audit` clean (`backend/.venv/Scripts/pip-audit.exe`)

## 2. Environment

Set on the host, never committed. The backend **refuses to start** if
`MUTATION_AUTH` is on (the default) and `ADMIN_TOKEN` is empty — a deliberate
fail-closed guard, so a misconfigured deploy dies loudly instead of serving an
API that 403s every write with no explanation.

### Backend

| Variable | Required | Notes |
|---|---|---|
| `ADMIN_TOKEN` | **yes** | Owner token. Gates the admin router and every mutating endpoint. |
| `FRONTEND_ORIGIN` | yes | Exact frontend origin for CORS, e.g. `https://ideasexist.example.com`. |
| `OPENCODE_GO_API_KEY` | for seeding | LLM gateway key. Seeding fails without it; reads are unaffected. |
| `DB_PATH` | no | Defaults to `/data/ideasexist.db` in the image. Must be on the volume. |
| `FORWARDED_ALLOW_IPS` | behind a proxy | The reverse proxy's address. **Never `*` on a public host** — that lets any caller spoof `X-Forwarded-For` and walk past the per-IP rate limits. Empty (default) = trust no forwarded headers. |
| `MUTATION_AUTH` | no | Defaults **on**. Only set `0` for a throwaway local instance. |
| `RATE_LIMIT_ENABLED` | no | Defaults on. |
| `GITHUB_TOKEN` | no | Raises the GitHub API rate limit for seeding/verification. |
| `VERIFY_AUTO_STALE_DAYS` | no | Default 7. `0` disables scheduled verification. |
| `LOG_LEVEL` | no | Default `INFO`. Logs go to stdout for the container runtime to collect. |

### Frontend (build-time — changing these needs a rebuild, not a restart)

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_BASE` | Backend origin. Also feeds the CSP `connect-src` in `next.config.ts` — wrong value means the page loads but the browser blocks every request. |
| `NEXT_PUBLIC_SITE_URL` | This site's public origin. Feeds canonical, OG, `robots.txt`, `sitemap.xml`. |

See `frontend/.env.example`. Serve HTTPS at the edge; the backend sends HSTS and
the production CSP is gated on `NODE_ENV=production`.

## 3. Deploy the backend

```bash
docker compose up --build -d
```

`docker-compose.yml` reads a `.env` beside it (git-ignored) and mounts the named
volume `ideasexist-data` at `/data`. Verify:

```bash
docker compose ps          # healthcheck should report healthy
curl -fsS http://localhost:8020/api/health
docker compose logs backend | grep starting   # confirm mutation_auth=True admin=True
```

For a PaaS, push the same `backend/Dockerfile` and attach a volume at `/data`:

| Host | Volume step |
|---|---|
| Fly.io | `fly volumes create ideasexist_data --size 1`, then a `[mounts]` block with `destination = "/data"`. Keep one machine, and don't let it auto-stop mid-verification. |
| Railway | Add a Volume to the service, mount path `/data`. |
| Render | Add a Disk, mount path `/data`. |
| VPS | `docker compose up -d` behind nginx/Caddy; set `FORWARDED_ALLOW_IPS` to the proxy address. |

## 4. Rollback

**Backend** — images are immutable, the volume is not. Roll the image back and
the archive stays as it is:

```bash
docker compose down
docker compose up -d --no-build   # or deploy the previous image tag
```

If a bad **migration or data change** is the problem, restore the volume from
the §5 backup — a code rollback alone will not undo data changes. Schema policy
is additive-only (`backend/app/db.py`), so a code rollback is normally safe on a
newer DB.

**Frontend** — Netlify: Deploys → previous deploy → "Publish Deploy" (use "Lock
deploys", or git-connected auto-publish overwrites the rollback). Vercel:
Production Deployment → "Instant Rollback" (env vars stay at current values).
Cloudflare Pages: Deployments → target → "Rollback to this deployment".

## 5. Backups (the archive is the product)

The DB is one file plus its WAL sidecars. Back it up **before every deploy**:

```bash
docker compose exec backend python -c "import sqlite3,os; \
  src=sqlite3.connect(os.environ['DB_PATH']); dst=sqlite3.connect('/data/backup.db'); \
  src.backup(dst); dst.close(); src.close(); print('ok')"
docker compose cp backend:/data/backup.db ./ideasexist.db.bak-$(date +%Y%m%d-%H%M)
```

Use `.backup` (above) rather than copying the file — a plain `cp` of a live
WAL-mode database can capture a torn state.

## 6. Scheduled verification

Handled **in-process**: `_auto_verify_loop` in `backend/app/main.py` re-checks
staleness at startup and every 24h, enqueuing a pass when any entry is older
than `VERIFY_AUTO_STALE_DAYS`. No cron, no external scheduler, no token to
manage. `start_verification` refuses a second concurrent pass, so a manual run
from the admin panel and a scheduled tick can't collide.

Consequences worth knowing: verification only advances while the process is
running, so don't let a PaaS scale the machine to zero. Keep the backup schedule
ahead of the weekly pass.

## 7. Post-deploy verification

1. `GET /api/health` returns 200; container healthcheck is healthy
2. Write endpoints reject anonymous callers:
   `curl -X POST .../api/startups/1/verify` → **403**; same call with
   `-H "X-Admin-Token: …"` → 200/404
3. `curl -sD- -o/dev/null .../api/health | grep -i strict-transport` → HSTS present
4. Frontend, no token in `sessionStorage`: no Add button, no status-pill menu;
   browse/search/filter/detail all work. Unlock in the admin panel → controls appear.
5. `/robots.txt`, `/sitemap.xml`, canonical + OG tags reflect `NEXT_PUBLIC_SITE_URL`
6. Lighthouse on the live URL: LCP < 2.5s observed, CLS < 0.1
7. Restart the backend and confirm the archive is still there (volume is wired)
8. Cross-browser + real-device pass (Firefox, Safari, Android, iPhone)

## 8. DNS (frontend)

| Host | Apex | www/subdomain |
|---|---|---|
| Netlify | ALIAS `apex-loadbalancer.netlify.com` or A `75.2.60.5` | CNAME `{site}.netlify.app` |
| Vercel | A `76.76.21.21` | CNAME `cname.vercel-dns-0.com` |
| Cloudflare Pages | Domain must be a CF zone (CF auto-creates the CNAME) | CNAME `{site}.pages.dev` |

Point the backend at its own hostname (e.g. `api.ideasexist.example.com`) and set
`FRONTEND_ORIGIN` + `NEXT_PUBLIC_API_BASE` to match. No wildcard records.
Propagation can take up to 48h — re-verify after, not during.
