# Prospectus

Hybrid-retrieval research system over SEC filings: dense · hybrid (RRF) · hybrid+rerank,
with cited generation (or abstention) and a published eval report.

## Live

| Surface | URL |
|---------|-----|
| App | https://prospectus-nickarndt.vercel.app |
| Eval report | https://prospectus-nickarndt.vercel.app/eval |
| API health | https://api-production-0bd1.up.railway.app/health |
| Source | https://github.com/nickcarndt/prospectus |

Generation requires Anthropic credits on the API; retrieval (dense / hybrid / hybrid+rerank) works without them.

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI (`services/api`) |
| Retrieval | Postgres + pgvector + FTS · OpenAI embeddings · Cohere Rerank |
| Generation | Claude structured output + grounding |
| Frontend | Next.js App Router · shadcn/ui · Tremor (eval charts) |
| Deploy | API → Railway · Web → Vercel |

## Local run

### 1. Postgres

```bash
cd infra && docker compose up -d
./apply_schema.sh
```

### 2. Env

Copy `.env.example` → `.env` and fill keys:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `COHERE_API_KEY`
- `ANTHROPIC_API_KEY`
- `SEC_USER_AGENT`

Frontend (`apps/web/.env.local`):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Python API

```bash
# from repo root
source .venv/bin/activate   # or python -m venv .venv
pip install -e packages/shared -e packages/retrieval -e packages/generation
pip install -r services/api/requirements.txt

cd services/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Smoke: `curl -s http://localhost:8000/health`

### 4. Web

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (research) and [/eval](http://localhost:3000/eval) (report).

### Query API

`POST /query`

```json
{
  "query": "What did NVIDIA say about CoWoS packaging?",
  "strategy": "hybrid_rerank",
  "generate": true,
  "top_k": 8,
  "candidate_depth": 50
}
```

- `strategy`: `dense` | `hybrid` | `hybrid_rerank`
- `generate: false` — retrieval only (UI uses this when switching strategy)

Response matches the Answer schema plus `latency_ms`, `generate`, and optional `error`
(e.g. Anthropic credits exhausted — chunks still returned).

## Deploy

### API → Railway

1. Install CLI: `npm i -g @railway/cli` then `railway login`
2. From **repo root**: `railway init` → link project
3. Set variables (Railway dashboard or `railway variables set`):

   | Variable | Notes |
   |----------|--------|
   | `DATABASE_URL` | Postgres with pgvector (Railway Postgres + extension, or external) |
   | `OPENAI_API_KEY` | embeddings |
   | `COHERE_API_KEY` | rerank |
   | `ANTHROPIC_API_KEY` | generation |
   | `SEC_USER_AGENT` | EDGAR UA string |
   | `CORS_ORIGINS` | e.g. `https://your-app.vercel.app` |

4. Deploy: `railway up` (uses root `Dockerfile` + `railway.toml`)
5. Health: `https://<service>.up.railway.app/health`

**Note:** The DB must already contain ingested chunks/embeddings (same as local).

### Frontend → Vercel

```bash
cd apps/web
npx vercel login
npx vercel --yes
# set env in Vercel project:
#   NEXT_PUBLIC_API_URL=https://<your-railway-api>
npx vercel --prod
```

Or connect the GitHub repo in the Vercel dashboard with **Root Directory** = `apps/web`.

## Eval report

- Write-up: [`EVAL_REPORT.md`](EVAL_REPORT.md)
- Machine-readable source (also bundled for `/eval`):  
  `apps/web/src/data/phase8_report_source.json`  
  (canonical run artifacts under `data/eval/results/` locally)

## Project layout

```
packages/shared|retrieval|generation|evals
services/api          # FastAPI
apps/web              # Next.js UI
infra/                # docker compose + schema
Dockerfile            # Railway API image
railway.toml
```
