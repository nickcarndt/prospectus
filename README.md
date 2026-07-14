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

> GitHub user is **`nickcarndt`**. The Vercel hostname uses the Vercel team slug
> `nickarndt` — that is not a typo in the GitHub URL.

Retrieval (dense / hybrid / hybrid+rerank) is free for the public demo. Cited
generation is opt-in and budgeted on the API (`GENERATE_PER_IP_PER_DAY=3`,
`GENERATE_GLOBAL_PER_DAY=12` by default).

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI (`services/api`) |
| Ingest | EDGAR fetch → extract → structure-aware chunk (`services/ingest`) |
| Retrieval | Postgres + pgvector + FTS · OpenAI embeddings · Cohere Rerank |
| Generation | Claude structured output + grounding |
| Frontend | Next.js App Router · Vercel AI SDK (`streamObject`) · shadcn/ui · Recharts |
| Evals | Braintrust (optional tracing) · local JSON runners in `packages/evals` |
| Deploy | API → Railway · Web → Vercel |

Staff-level portfolio review: [`docs/STAFF_AUDIT.md`](docs/STAFF_AUDIT.md).

## Local run (clean clone → working tool)

Run every command from the **repo root** unless noted. Requires Docker, Python **3.11+**,
and Node 20+.

### 1. Postgres + schema

```bash
docker compose -f infra/docker-compose.yml up -d
./infra/apply_schema.sh
```

`apply_schema.sh` applies `infra/schema.sql` + `infra/schema_fts.sql`.
**Warning:** `schema.sql` drops and recreates the `chunks` table — only run on a
fresh local DB (or when you intend to wipe embeddings).

Default `DATABASE_URL` (matches compose):

```text
postgresql://prospectus:prospectus@localhost:5432/prospectus
```

### 2. Env

```bash
cp .env.example .env
# Edit .env — at minimum for a working research tool:
#   DATABASE_URL, SEC_USER_AGENT, OPENAI_API_KEY
# Also set for full features:
#   COHERE_API_KEY (hybrid_rerank), ANTHROPIC_API_KEY (cited answers)
```

`SEC_USER_AGENT` must identify you to EDGAR, e.g. `Prospectus Research you@example.com`.

Frontend env (separate file):

```bash
cp apps/web/.env.local.example apps/web/.env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
# ANTHROPIC_API_KEY=...          # required for streamed cited answers (Next /api/answer)
# PROSPECTUS_API_URL=http://localhost:8000   # server-side ground/reserve calls (defaults to NEXT_PUBLIC_API_URL)
```

### 3. Python venv + packages

Create the venv **before** activating it:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r services/ingest/requirements.txt
pip install -r services/api/requirements.txt
pip install -e packages/shared -e packages/retrieval -e packages/generation
```

### 4. Ingest filings → chunks → embeddings

This is required. An empty Postgres yields an empty research tool.

```bash
# Still in the activated venv, from repo root:
export PYTHONPATH=services/ingest

# Download latest 10-K + 10-Q per ticker (~15 issuers). Takes several minutes.
python -m prospectus_ingest fetch

# Optional smoke (one issuer): python -m prospectus_ingest fetch --tickers NVDA

python -m prospectus_ingest extract
python -m prospectus_ingest chunk

# Embed + upsert into pgvector (needs OPENAI_API_KEY). Full corpus ~6k chunks.
export PYTHONPATH=packages/retrieval
python -m prospectus_retrieval embed

# Optional smoke: python -m prospectus_retrieval embed --limit 64
```

Sanity check retrieval without the API:

```bash
export PYTHONPATH=packages/retrieval
python -m prospectus_retrieval search "What is CoWoS packaging?" --strategy hybrid --k 5
```

You should see NVDA (or related) hits with section titles — not zero rows.

### 5. API

```bash
source .venv/bin/activate
uvicorn app.main:app --app-dir services/api --reload --port 8000
```

Smoke:

```bash
curl -s http://localhost:8000/health
# {"status":"ok"}

curl -s -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is CoWoS packaging?","strategy":"hybrid","generate":false,"top_k":3}'
```

### 6. Web

```bash
cd apps/web
npm install --legacy-peer-deps
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (research) and
[http://localhost:3000/eval](http://localhost:3000/eval) (report).

## Query API

`POST /query`

```json
{
  "query": "What did NVIDIA say about CoWoS packaging?",
  "strategy": "hybrid_rerank",
  "generate": false,
  "top_k": 8,
  "candidate_depth": 50
}
```

- `strategy`: `dense` | `hybrid` | `hybrid_rerank`
- `generate: false` — retrieval only (default for cost; UI searches this way first)
- `generate: true` — cited Claude answer (budgeted on the public API)

## Deploy

### API → Railway

1. `npm i -g @railway/cli` then `railway login`
2. From **repo root**: `railway link` (or `railway init`)
3. Set variables: `DATABASE_URL`, `OPENAI_API_KEY`, `COHERE_API_KEY`,
   `ANTHROPIC_API_KEY`, `SEC_USER_AGENT`, and optional `CORS_ORIGINS`
   (extras only — defaults already include production aliases; no `*.vercel.app` wildcard)
4. Load the same ingested embeddings into that Postgres (migrate or re-run embed)
5. `railway up` (root `Dockerfile` + `railway.toml`)
6. Health: `https://<service>.up.railway.app/health`

### Frontend → Vercel

```bash
cd apps/web
npx vercel login
npx vercel --yes
# NEXT_PUBLIC_API_URL=https://<your-railway-api>
npx vercel --prod
```

Root Directory = `apps/web` if connecting the GitHub repo in the Vercel UI.

## Tests + CI

Unit tests cover the logic that would actually break in an interview: RRF fusion,
rerank index mapping, strategy dispatch, eval scorers (Recall@k / MRR / citation
accuracy), structural grounding, API request caps, and generation budgets.
No live DB or provider keys required.

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

GitHub Actions runs the same suite on every push/PR (`.github/workflows/ci.yml`),
plus a Next.js production build for `apps/web`.

## Eval report

- Write-up: [`EVAL_REPORT.md`](EVAL_REPORT.md)
- UI source: `apps/web/src/data/phase8_report_source.json`
- Local run artifacts: `data/eval/results/` (gitignored)

## Project layout

```
packages/shared       # Chunk, Citation, Answer schemas
packages/retrieval    # dense · keyword · RRF · rerank
packages/generation   # Claude + structural grounding
packages/evals        # scorers + runners
services/ingest       # EDGAR fetch, extract, structure-aware chunk
services/api          # FastAPI /health + /query
apps/web              # Next.js research UI + /eval
infra/                # docker compose, schema.sql, schema_fts.sql
data/filings|chunks   # local artifacts (gitignored; produced by ingest)
docs/                 # PROJECT_SPEC, DESIGN_SPEC, STAFF_AUDIT
Dockerfile            # Railway API image
railway.toml
```
