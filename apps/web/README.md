# Prospectus web

Next.js App Router UI for the Prospectus research instrument.

Use the **root** [`README.md`](../../README.md) for local setup (API, Postgres, env).

```bash
cd apps/web
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install --legacy-peer-deps
npm run dev
```

Routes: `/` research workspace · `/eval` published metrics.
