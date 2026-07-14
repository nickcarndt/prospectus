# Cursor Phase Prompts

Copy-paste one prompt per phase. Do not build ahead.

---

## Phase 1 — Skeleton

> Read `docs/PROJECT_SPEC.md` and `.cursorrules`. **Phase 1 only** — do not build ahead. Build: (1) the monorepo structure exactly as in the spec, (2) docker-compose in /infra with Postgres + pgvector, (3) a FastAPI shell in /services/api with /health, (4) a bare Next.js App Router app in /apps/web with shadcn/ui initialized and the DESIGN_SPEC palette, font (Geist), and 6px radius applied. Walk me through your plan first, then build one piece at a time, explaining as you go, and pause after each piece.

---

## Phase 2 — Ingest + chunking

> Read the spec and rules. **Phase 2 only.** Build /services/ingest: fetch 10-K/10-Q filings for ~15 companies from SEC EDGAR, extract text and tables, and implement **structure-aware chunking** (split on headings/sections, 256–512 tokens, preserve section metadata on every chunk — we need it for citations). Define the shared schemas (Chunk with filing/section/date metadata, Citation, RetrievalResult, Answer) in /packages/shared. Explain your chunking strategy and why structure-aware beats naive fixed-size for this corpus. Pause when done.

---

## Phase 3 — Dense retrieval

> Read the spec and rules. **Phase 3 only.** Embed the chunks (OpenAI text-embedding-3-large) and store in pgvector. Implement dense retrieval (top-k cosine similarity) in /packages/retrieval as an **independently testable module**. Per the architectural rules: retrieval strategy must be a parameter, not a hardcoded path — set up that abstraction now. Explain the embedding choice and the pgvector index setup. Pause when done.

---

## Phase 4 — Keyword retrieval + RRF fusion

> Read the spec and rules. **Phase 4 only.** Add a keyword retrieval path using Postgres full-text search, then implement Reciprocal Rank Fusion (k=60) to fuse the dense and keyword ranked lists. Keep each strategy independently callable. Explain RRF — why rank-based fusion works and why we're not just averaging similarity scores. Then **show me a specific query where dense-only fails and hybrid succeeds** (hint: exact financial terms, ticker symbols, specific numbers — dense embeddings are weak on rare exact tokens). Pause when done.

---

## Phase 5 — Reranking

> Read the spec and rules. **Phase 5 only.** Add Cohere Rerank as a cross-encoder reranking stage over the fused top-50, cutting to top 5–8. Explain the difference between a bi-encoder (embeddings — fast, approximate) and a cross-encoder (reranker — slow, accurate) and why we retrieve wide then rerank narrow. Make candidate depth a parameter (we'll test 20 vs 50). Pause when done.

---

## Phase 6 — Cited generation

> Read the spec and rules. **Phase 6 only.** Implement answer generation with Claude using **structured output** so every claim carries a citation to filing + section. Add the **insufficient-evidence fallback**: below a confidence threshold, the system abstains rather than guessing. Explain how you're enforcing citation grounding structurally (not just prompting for it). Pause when done.

---

## Phase 7 — THE EVAL HARNESS (the whole point — take your time)

> Read the spec and rules. **Phase 7 only.** Build /packages/evals: (1) a labeled eval set of 30–40 Q/A pairs in /data/eval, each with the known gold source section, (2) Braintrust scorers for recall@5, recall@10, MRR, faithfulness (LLM-as-judge), and citation accuracy, (3) an experiment runner that executes **all three retrieval configs** (dense-only, hybrid, hybrid+rerank) against the same eval set, capturing latency and cost per query. Explain each scorer and what it actually measures — I need to be able to defend these in an interview. This phase is why the project exists. Pause when done.

---

## Phase 8 — Report + UI + deploy

> Read the spec, rules, and `docs/DESIGN_SPEC.md`. **Phase 8 only.** (1) Generate `EVAL_REPORT.md` with the real measured numbers from all three configs plus honest written analysis of the tradeoffs — what improved, what it cost in latency and dollars, what you'd optimize next. (2) Build the query UI per DESIGN_SPEC: premium research-tool feel, prominent inline citations, the citation drawer with highlighted source passage, the insufficient-evidence state, and the **live retrieval-config toggle**. (3) Add the eval report page with Tremor comparison charts. (4) Deploy API to Railway, frontend to Vercel. Pause after each piece.

---

## The discipline gate

After **every** phase: narrate back in 2–3 sentences what it built and why. Can't? Read until you can. Log every "oh, that's how that works" in `docs/learning-log.md` — that file is your interview prep.

**The three things you must be able to explain cold when this ships:**
1. Why hybrid beats dense-only (rare exact tokens — tickers, dollar figures, section numbers — are where dense embeddings fail and keyword search wins)
2. Why the reranker helps (cross-encoder sees query+doc together; bi-encoder embeds them separately — accuracy vs. cost tradeoff)
3. What each eval metric actually measures and why you chose it
