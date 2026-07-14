# Prospectus — Project Spec

**A hybrid-retrieval research system over SEC EDGAR filings that cites every claim
back to its source section — and publishes an eval report proving the retrieval works.**

## What this is
Ask a financial question ("What did NVIDIA say about supply chain risk in FY25?") and
get an answer grounded in the actual 10-K/10-Q text, with inline citations to the exact
filing and section. Below a confidence threshold, it says "insufficient evidence" rather
than guessing.

The real deliverable is `EVAL_REPORT.md`: a head-to-head measurement of three retrieval
configurations (dense-only, hybrid, hybrid+rerank) on a labeled eval set, with real
numbers for recall@k, faithfulness, citation accuracy, p95 latency, and cost per query.

## Why it exists (portfolio purpose)
Proves that **retrieval quality is an engineering discipline you can measure** — the single
most-tested competency in 2026 FDE/Applied-AI loops. "How do you know your system works?"
is the question that separates candidates, and this project is a 40-page answer.

Speaks directly to:
- **Perplexity** — retrieval at scale IS their product
- **Hebbia / Harvey** — document intelligence + citation grounding over financial/legal docs
- **Cohere** — you use their reranker; you can discuss it in their own interview
- **Ramp** — financial documents, structured extraction
- **OpenAI / Anthropic FDE** — evals are the highest-weighted technical signal

## The corpus
SEC EDGAR 10-K/10-Q filings for ~15 public companies. Chosen because: free and clean to use,
genuinely messy (tables, footnotes, inconsistent structure = real retrieval difficulty),
financially themed (ties to the fintech target list), and interpretable.

## Architecture
1. **Ingest** — fetch filings from EDGAR, extract text + tables
2. **Chunk** — structure-aware (split on headings/sections, 256–512 tokens, preserve section metadata)
3. **Embed** — dense vectors → Postgres + pgvector
4. **Index** — Postgres full-text (BM25-style keyword) index alongside
5. **Retrieve (hybrid)** — dense top-50 + keyword top-50 in parallel, fused with
   Reciprocal Rank Fusion (RRF, k=60)
6. **Rerank** — Cohere Rerank cross-encoder over fused candidates → top 5–8
7. **Generate** — cited answer via structured output; "insufficient evidence" fallback
8. **Evaluate** — labeled Q/A set, three configs head-to-head

## THE DELIVERABLE: `EVAL_REPORT.md`
For each of the three configs (dense-only / hybrid / hybrid+rerank), publish:
- **Recall@5, Recall@10** — did we retrieve the right chunk at all?
- **MRR** — how highly ranked was it?
- **Faithfulness** (LLM-as-judge) — is the answer grounded in retrieved context?
- **Citation accuracy** — do cited sections actually contain the claim?
- **p95 latency** (end-to-end)
- **Cost per query** (embedding + rerank + generation)
Plus honest written analysis: what improved, what it cost, the tradeoff, what you'd do next.

## Stack (locked)
- **Python**: ingest, retrieval, evals. **FastAPI** for the API.
- **Store**: Postgres + pgvector (dense) + Postgres full-text search (keyword)
- **Embeddings**: OpenAI text-embedding-3-large
- **Reranker**: Cohere Rerank
- **Fusion**: Reciprocal Rank Fusion, k=60
- **Generation**: Claude, structured output for citations
- **Evals + tracing**: Braintrust
- **Frontend**: Next.js App Router + Vercel AI SDK (`streamObject` for cited answers) + shadcn/ui (customized) + Tailwind
- **Deploy**: API on Railway, frontend on Vercel

## Repo structure
/services/api          # FastAPI: /query, /health
/services/ingest       # EDGAR fetch, parse, chunk, embed, index
/packages/retrieval    # dense | keyword | RRF fusion | rerank — each independently testable
/packages/evals        # Braintrust datasets, scorers, 3-config experiment runner
/packages/shared       # schemas (Chunk, Citation, RetrievalResult, Answer)
/apps/web              # Next.js query UI with citations
/data/eval             # labeled Q/A pairs with gold source sections
/infra                 # docker-compose (postgres + pgvector)
/docs                  # this spec, DESIGN_SPEC, learning-log
EVAL_REPORT.md         # THE deliverable

## Build phases (ship-today scope)
- **Phase 1**: Skeleton — repo, docker-compose (postgres+pgvector), FastAPI shell, Next.js shell
- **Phase 2**: Ingest + chunking + shared schemas
- **Phase 3**: Dense retrieval (embed → pgvector → top-k)
- **Phase 4**: Keyword retrieval + RRF fusion
- **Phase 5**: Cohere reranking
- **Phase 6**: Cited generation + insufficient-evidence fallback
- **Phase 7**: Eval harness — labeled set + scorers + 3-config runner  ← THE POINT
- **Phase 8**: EVAL_REPORT.md + query UI + deploy

## CRITICAL ARCHITECTURAL RULE
Retrieval strategy must be a **parameter, not a hardcoded path**. One retrieval function,
three configs. The entire project depends on making the comparison trivial to run.

## Out of scope
Auth, multi-tenancy, real-time filing updates, OCR of scanned PDFs.

## Definition of done
1. All three retrieval configs run and are measured
2. EVAL_REPORT.md published with real numbers + honest analysis
3. Live demo: ask a question, see cited answers
4. **I can explain, cold, why hybrid+rerank beat dense-only and what it cost**
