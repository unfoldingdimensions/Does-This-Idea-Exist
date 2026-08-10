# Deployment Runbook — IdeaExists

How to ship IdeaExists (FastAPI :8020 + Next.js :3023 + SQLite) and, more
importantly, how to undo it. Read this BEFORE the first deploy.

## 1. Pre-deploy checklist (hard gates)

- [ ] `npm run test` at the repo root passes (backend smoke + frontend lint + build)
- [ ] All work committed (conventional commits, co-author trailer per repo convention)
- [ ] Fresh DB backup taken: copy `backend/data/ideasexist.db` → `ideasexist.db.bak-<timestamp>` BEFORE any migration/deploy
- [ ] `docs/predeploy-readiness-2026-08-10.md` blockers closed (LCP observed < 2.5s, SEO files live, focus rings present)
- [ ] `.env` perms tight (600), no secrets in tracked files, `npm audit` clean

## 2. Host environment (set on the host, never commit)

| Variable | Value |
|---|---|
| `MUTATION_AUTH` | `1` |
| `ADMIN_TOKEN` | strong random value |
| `FRONTEND_ORIGIN` | the real origin (e.g. `https://ideasexist.example.com`) |
| `NEXT_PUBLIC_API_BASE` | the backend origin (build-time, frontend) |
| `NEXT_PUBLIC_SITE_URL` | the frontend origin (build-time, frontend — feeds canonical/sitemap/OG) |

The CSP `connect-src` in `next.config.ts` is built from `NEXT_PUBLIC_API_BASE`
— regenerate it with the real origin at build time. Serve HTTPS + HSTS at the
host; the CSP is production-gated in `next.config.ts`.

## 3. Rollback paths (know yours before clicking deploy)

| Host | Rollback click-path |
|---|---|
| Netlify | Deploys tab → previous successful deploy → detail → "Publish Deploy". Git-connected auto-publish overwrites a rollback — use "Lock deploys". |
| Vercel | Project → Production Deployment tile → "Instant Rollback" → select → Confirm. Hobby = previous deploy only; env vars stay at current values. Alt: Deployments → ellipsis → "Promote to Production". |
| Cloudflare Pages | Deployments → All deployments → target → ellipsis → "Rollback to this deployment". Production deployments only. |
| GitHub Pages | No one-click rollback: git revert the publishing branch, or re-run the workflow (same SHA). |

Local rollback (no host yet): `git revert`/`git checkout` of the last good
commit + restore the DB from the pre-deploy backup.

## 4. DNS records (verify with `nslookup` after the flip)

| Host | Apex | www/subdomain |
|---|---|---|
| Netlify | ALIAS `apex-loadbalancer.netlify.com` or A `75.2.60.5` | CNAME `{site}.netlify.app` |
| Vercel | A `76.76.21.21` | CNAME `cname.vercel-dns-0.com` |
| Cloudflare Pages | Domain must be a CF zone (CF auto-creates CNAME) | CNAME `{site}.pages.dev` |
| GitHub Pages | A `185.199.108.153` + `.109` `.110` `.111` (AAAA `2606:50c0:8000::153`…) | CNAME `{user}.github.io` |

No wildcard records. Propagation can take up to 48h — re-verify after, not during.

## 5. Post-deploy verification

1. Apex + www serve identical content (compare `sha256sum` of the HTML; no redirect loop)
2. `/robots.txt`, `/sitemap.xml`, canonical + OG tags live
3. Search Console: add the property (Domain = DNS TXT; URL-prefix = any method)
4. Lighthouse on the live URL: LCP < 2.5s observed, CLS < 0.1
5. Form E2E on the live URL with delivery confirmed out-of-band (DB row / backend log)
6. Cross-browser + real-device pass (Firefox, Safari, Android, iPhone)

## 6. Weekly maintenance

- Verification cron runs Mondays 06:00 (backend `verify.py` pipeline); keep the
  DB backup schedule ahead of it.
- Re-run the readiness report (`deploy-readiness-report.md`) before any major
  update; re-check links after any URL change.
