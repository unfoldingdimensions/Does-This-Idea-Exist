# IdeaExists — frontend

Next.js 16 + shadcn/ui single-page app for the IdeaExists archive. Runs on
**http://127.0.0.1:3023** (`npm run dev`); expects the FastAPI backend on
:8020 (see the [root README](../README.md) for full setup, env vars, and the
admin panel).

```bash
npm install
npm run dev          # dev server on :3023
npm run lint         # eslint
npm run build        # production build
```

`NEXT_PUBLIC_API_BASE` (default `http://localhost:8020`) and
`NEXT_PUBLIC_SITE_URL` (default `http://localhost:3023`) are the only env vars.
