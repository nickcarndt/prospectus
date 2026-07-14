# Prospectus — Staff Engineer Portfolio Audit

**Auditor stance:** Skeptical staff engineer at Ramp / Hebbia / Perplexity deciding advance / no-advance.  
**Date:** 2026-07-14  
**Repo:** `nickcarndt/prospectus` (~104 tracked files, 3 commits)  
**Verdict up front:** This helps more than it hurts — if you can defend it. It will not survive a hostile deep-dive without fixes. **Grade: B−** for competitive Applied AI / FDE. Not staff-bar.

---

## 1. First impression (30-second skim)

### What lands in 30 seconds

A hiring engineer opens GitHub and sees:

1. A short README with **live URLs**, a real eval report, and an explicit “strategy is a parameter” thesis.
2. A monorepo layout that looks intentional: `packages/{shared,retrieval,generation,evals}`, `services/{api,ingest}`, `apps/web`, `infra/`, `docs/`.
3. Commits that include **`Co-authored-by: Cursor <cursoragent@cursor.com>`** on the initial commit and subsequent work.

### What they conclude

**Mixed — tilted toward “serious junior / strong mid who shipped with heavy AI assist.”**

| Signal | Read |
|--------|------|
| Modular packages + shared schemas | Real engineer taste, not a single `app.py` notebook |
| Live Railway + Vercel + published null eval findings | Ships; doesn’t fake hybrid “wins” |
| `Co-authored-by: Cursor` in git history | Immediate “did you write this?” filter — they will probe hard |
| Zero tests, no CI, 3 commits | Weekend project velocity, not production discipline |
| README claims Vercel AI SDK; `package.json` has none | Spec/marketing drift — tutorial smell |
| `apps/web/README.md` still create-next-app boilerplate | Unreviewed scaffolding left in the tree |

**Specific tell:** The architecture principles in `.cursorrules` / `docs/PROJECT_SPEC.md` are sharper than the average commit message. Interviewers will assume the *spec* is you (or a good prompt) and the *gaps* (tests, citation rewrite, gold labels) are where the AI stopped being supervised.

---

## 2. Architecture assessment

### Coherent or accidental?

**Coherent.** This was designed, not grown. The core idea — retrieval strategy as a **parameter**, stages as independently callable modules, structural grounding after structured generation — is the right shape for an Applied AI portfolio piece. That is not accidental.

Evidence:

```21:68:packages/retrieval/prospectus_retrieval/retrieve.py
def retrieve(
    query: str,
    *,
    strategy: RetrievalStrategy = RetrievalStrategy.DENSE,
    ...
) -> RetrievalResult:
    if strategy is RetrievalStrategy.DENSE:
        return dense_retrieve(...)
    ...
    if strategy is RetrievalStrategy.HYBRID_RERANK:
        return hybrid_rerank_retrieve(...)
```

```136:140:packages/shared/prospectus_shared/schemas.py
    def citations_required_unless_abstained(self) -> Answer:
        """Architectural rule: answers without citations are bugs unless abstained."""
        if not self.abstained and not self.citations:
            raise ValueError("non-abstained Answer must include at least one Citation")
```

### Boundaries

| Layer | Responsibility | Clean? |
|-------|----------------|--------|
| `packages/shared` | Contracts | Yes |
| `packages/retrieval` | Dense / keyword / RRF / rerank | Mostly — hybrid not actually parallel |
| `packages/generation` | Claude + grounding | Yes, with a critical bug (marker rewrite) |
| `packages/evals` | Scorers + runners | Yes; gold quality weak |
| `services/api` | Thin HTTP + budgets | Thin is good; hardening missing |
| `services/ingest` | EDGAR → chunks | Fine for demo |
| `apps/web` | Research + eval UI | Underbuilt vs thesis |

### Design mistakes / smells

1. **Comment lies about citation rewrite** (see §3) — architecture claims structural UX correctness it doesn’t implement.
2. **“Parallel” hybrid is sequential** — docstring fiction.
3. **No connection pooling** despite `psycopg[pool]` dependency — demo wearing production clothes.
4. **Health check doesn’t check anything** — ops theater.
5. **Destructive `DROP TABLE` in schema.sql** — fine locally; not a migration story.
6. **Eval results gitignored** while README/EVAL_REPORT claim reproducibility from scripts — integrity gap for GitHub visitors.
7. **Public unauthenticated API** with unlimited retrieval — wallet as auth.

### Production-patterned or demo clothes?

**Demo wearing a tailored jacket.** Parameterized strategies, grounding, budgets, live deploy — jacket. No tests, no CI, in-memory rate limits, spoofable XFF, phrase-matched gold labels, incomplete generation evals — demo underneath.

### What I would architect differently

1. **Entity/ticker routing before dense** — SEC corpus without issuer filters is asking for cross-ticker contamination.
2. **Parallel hybrid legs + shared pool** — latency is a product feature for Hebbia-class tools.
3. **Eval set as first-class product** — human-verified golds with abstain-positive / abstain-negative / exact-token slices *before* claiming hybrid didn’t help.
4. **Auth’d demo token or Cloudflare in front of `/query`** — LinkedIn traffic + OpenAI embeddings without a retrieval rate limit is reckless.
5. **Prompt + schema versioning** (`prompts/v1.yaml` or similar) — inline strings are fine at n=1; not interview-proof for “how do you iterate prompts.”

---

## 3. Code smells & hygiene

### Critical: citation markers never rewritten

```127:130:packages/generation/prospectus_generation/grounding.py
    # Rewrite citation markers in answer_text to match issued citation_ids.
    answer_text = structured.answer_text.strip() or _compose_answer_from_claims(
        structured
    )
```

The comment asserts a rewrite. There is **no rewrite**. `citation_id` is assigned from the raw claim enumerate index (`c{index}` at line 107). If claim 1 fails the excerpt check and claim 2 passes, the answer may still say `[c1]` while the only issued citation is `c2`. **This is an interview-ending “you didn’t read your own comment” moment.**

### Docstring lies: hybrid “parallel”

```30:50:packages/retrieval/prospectus_retrieval/hybrid.py
    """Run dense and keyword in parallel depth, fuse with RRF, return top_k.
    ...
    dense = dense_retrieve(query, top_k=candidate_depth, embedder=embedder)
    keyword = keyword_retrieve(query, top_k=candidate_depth)
```

Sequential. At `candidate_depth=50`, you pay dense latency + keyword latency every hybrid call.

### `min_tokens` accepted, unused

```131:145:services/ingest/prospectus_ingest/chunk.py
def _pack_section(
    section_text: str,
    *,
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> list[str]:
    """Pack a section into windows targeting [min_tokens, max_tokens]."""
    if count_tokens(section_text) <= max_tokens:
        return [section_text]
```

`min_tokens` never constrains packing. Spec claims 256–512; short sections ship as-is (OK) but the parameter is dead API surface.

### Vacuous citation accuracy on abstain

```119:121:packages/evals/prospectus_evals/scorers.py
    if answer.abstained:
        # Abstention with no citations is vacuously correct for this metric.
        return 1.0 if not answer.citations else 0.0
```

Abstain-everything agent scores perfect citation accuracy. Easy to game; you should know that.

### Phrase-first gold labeling

```240:251:packages/evals/scripts/build_eval_set.py
def lookup_gold(ticker: str, phrase: str) -> dict | None:
    ...
            WHERE ticker = %s AND text ILIKE %s
            ORDER BY chunk_index
            LIMIT 1
```

Committed poison example — query asks Item 1A, gold is Business:

```json
{"id": "nvda-risk-supply-03", "query": "... in Item 1A?", "gold_section_id": "item_1_business", ...}
```

Only ~22 unique gold chunks across 35 cases. Paraphrase padding. Soft golds → soft “hybrid didn’t help” headline.

### Other hygiene

| Issue | Location |
|-------|----------|
| Broad `except Exception` leaking `str(exc)` to clients | `services/api/app/main.py` |
| Budget consumed before Claude succeeds | `main.py` `check_and_consume` then `answer_query` |
| Retrieve-only abuses `Answer` abstain with empty reason | API demo convenience polluting domain model |
| Faithfulness judge = same model family as generator | `scorers.py` |
| Frontend Zod validates request, casts response | `apps/web/src/lib/api.ts` |
| `startTransition(async () => …)` | `research-workspace.tsx` |
| Stack claims Vercel AI SDK; not in deps | README / PROJECT_SPEC vs `package.json` |
| Glass/blur header vs DESIGN_SPEC anti-slop | `site-header.tsx` |
| Dead `apps/web/README.md` boilerplate | unreviewed |
| Magic numbers: confidence 0.55, RRF k=60, candidate_depth 50 | scattered; some documented, none sensitivity-tested in report |

### AI-generated / unreviewed tells

1. **`Co-authored-by: Cursor`** in git history — smoking gun.
2. Comment that describes work not present (citation rewrite).
3. Docstring “parallel” without `asyncio`/`ThreadPool`.
4. Spec/stack drift (AI SDK, reproduce CLI flags wrong in EVAL_REPORT).
5. Boilerplate Next README left behind.
6. Over-complete `.cursorrules` relative to missing tests — process theater.

---

## 4. Robustness & error handling

### Unhappy paths

| Scenario | Behavior | Acceptable? |
|----------|----------|-------------|
| Empty retrieval | Deterministic abstain, no Claude call | Good |
| Hallucinated chunk_id | Dropped in grounding | Good |
| Excerpt not in chunk | Dropped | Good |
| Anthropic credits exhausted | Friendly error + chunks returned | Good |
| Generation daily budget hit | Soft deny + retrieval | Good |
| OpenAI/Cohere failure on retrieve | 503 with exception string | Leaky |
| DB down | Same | Leaky |
| Malformed JSON body | FastAPI/Pydantic 422 | OK |
| Provider timeout | No explicit timeouts configured | Bad |
| Embed mid-corpus crash | No resume | Costly |
| EDGAR 429 | Sleep-only, no backoff | Fragile |
| Faithfulness judge fails | Score omitted / error path | Quietly degrades aggregates |

### Retries / timeouts / degradation

- **Cohere 429 retry:** only in eval `retrieval_only` path — not in production `rerank.py`.
- **OpenAI / Anthropic:** no retries, no explicit client timeouts in app code.
- **Graceful degradation:** generation path is thoughtfully degraded; **retrieval path is not rate-limited** and has no circuit breaker.

### Observability

- Latency returned on `/query` — good for demos.
- No request IDs, no structured logs, no Braintrust required in prod.
- Cost estimator uses hand-waved rates, not provider `usage` fields.
- Health endpoint: liveness only — will not catch a broken DATABASE_URL until `/query`.

### Trust boundaries

- Query length capped at 4000 — OK.
- SQL parameterized — good.
- FTS via `websearch_to_tsquery` — acceptable.
- Response schema not validated on the client — weak.
- No auth — anyone on the internet is a trust boundary.

---

## 5. Security

### Secrets

- `.env` gitignored; not in `git ls-files`.
- `.env.example` uses placeholders (`sk-...`).
- No evidence of real keys committed in history from this scan.
- **Local `.env` on disk** — fine; never force-add.

### Public surface (live)

1. **Unauthenticated `/query`** — burns OpenAI (+ Cohere on hybrid_rerank) without a retrieval budget. Generation is capped; embeddings are not. **This is the real LinkedIn risk.**
2. **`X-Forwarded-For` trusted for generate budget** — spoofable if the edge doesn’t overwrite it.
3. **CORS `allow_origin_regex=r"https://.*\.vercel\.app"`** — any Vercel app can call your API from a browser.
4. **`allow_credentials=True`** unnecessarily with broad origins.
5. In-memory budgets reset on redeploy; multi-instance multiplies quota.

### Injection

- SQL: parameterized — good.
- Prompt injection: closed chunk_id set + excerpt membership helps; no claim↔answer consistency check; user text is interpolated into the prompt — standard RAG risk, not specially mitigated.
- Command injection: none seen.

### Least privilege

- Postgres local password `prospectus/prospectus` — fine for docker compose only.
- API keys on Railway — correct pattern.
- No tool-calling agents — smaller attack surface (good).

---

## 6. Testing & verifiability

### Coverage

**Zero first-party Python tests. Zero frontend tests. No `.github/workflows`.**

Modules are *designed* to be testable (`fusion`, `grounding`, injectable clients) and then never tested. That is the opposite of portfolio signal — it reads as “I knew what good looked like and didn’t do it.”

### Important paths untested

- RRF ordering / k constant
- Grounding reject paths + marker alignment
- Answer schema invariants
- Chunker Item-boundary split
- API generate budget soft-deny
- Strategy toggle contract (`generate: false`)

### Clone & run (literal README)

| Step | Result |
|------|--------|
| `source .venv/bin/activate` before create | **Fails** on clean machine |
| docker compose + schema | OK |
| Start API | OK with empty DB |
| Query UI | Empty / useless without ingest+embed — **not documented in Local run** |
| Deploy note | Admits DB must be prefilled; no how-to |
| `apps/web/README.md` | Points at Next.js tutorial, not Prospectus |

### Reproducibility of EVAL_REPORT

- Claim: every number reproducible from a script.
- Reality: `data/eval/results/` gitignored; regenerate commands in the report include wrong CLI shapes; generation metrics incomplete (credits).
- Bundled `apps/web/src/data/phase8_report_source.json` helps the `/eval` page but is a snapshot, not a pipeline proof for clones.

---

## 7. AI / LLM-specific engineering

### Prompts

- Inline strings in `generate.py` — versioned only by git.
- No prompt A/B, no registry, no golden traces.

### Evaluation

- **Not vibes-only** — you have Recall@k, MRR, citation accuracy, faithfulness, latency, cost estimates. That is real.
- **But:** soft golds, R@5==R@10 for all configs, incomplete generation evals, same-family judge, vacuous abstain citation score.
- Honesty about null hybrid lift is a **strength**. Soft methodology undercutting that honesty is the **weakness**.

### Observability / tracing

- Braintrust optional in eval runner — good intent.
- Production `/query` has no tracing of LLM calls, tokens, or grounding drop rates.

### Cost management

- Public demo: retrieve-first UI + generate budgets + max_tokens 1024 + top_k cap 6 — **serious and interviewable.**
- Missing: retrieval rate limit, measured token usage, budget remaining in API response / UI.

### Guardrails

| Guardrail | Present? |
|-----------|----------|
| Structured output schema | Yes |
| Closed chunk_id set | Yes |
| Excerpt ⊆ chunk | Yes |
| Confidence threshold → abstain | Yes (uncalibrated 0.55) |
| Citation required unless abstain | Yes (schema) |
| Claim↔answer consistency | No |
| Marker rewrite after filtering | **Claimed, not implemented** |
| Cross-ticker filter | No |

### Model choice

- `claude-sonnet-4-5` default — reasonable; not justified in code beyond “Claude with structured output.”
- No comparison to Haiku for cost, no judge/generator separation.

### Retrieval quality

- Structure-aware chunking (Item headings) — correct for SEC.
- Hybrid RRF k=60 — standard, undocumented sensitivity.
- Rerank with Cohere — correct pattern; **no lift on this gold set** (honest).
- Dense unfiltered across 15 issuers — contamination risk unmeasured.
- Qualitative CoWoS win is real and should be the UI’s hero demo; it is buried in JSON.

---

## 8. Interview attack surface

### 10 hardest questions

1. **`grounding.py:127` says you rewrite citation markers. Walk me through the rewrite.** What if claim 1 is rejected and claim 2 kept?
2. **`hybrid.py` says parallel. Show me the concurrency.** What’s p95 impact of sequential legs at depth 50?
3. You depend on `psycopg[pool]` but open a new connection per query. Why?
4. **`nvda-risk-supply-03` asks Item 1A; gold is `item_1_business`.** How did that get into `cases.jsonl`? Does Recall@k overstate hybrid?
5. Citation accuracy returns **1.0 on abstention**. How do I game your leaderboard?
6. Confidence threshold is **0.55 on self-reported model confidence**. Calibrate it. What does a confident wrong excerpt look like?
7. Public `/query`, unlimited retrieval. Estimate OpenAI burn at 5 qps. Where do you put the limit?
8. Dense SQL has no ticker filter. How often does an AAPL chunk answer an NVDA question? Did you measure?
9. EVAL_REPORT claims reproducibility; `data/eval/results/` is gitignored and the CLI in the report is wrong. Defend that.
10. Faithfulness uses Claude to judge Claude. Why not a different judge, NLI, or a 20-case human agreement sample?

### 5 places that reveal shallow understanding (if you can’t defend them)

1. Citation rewrite comment with no code.
2. Soft golds + strong “hybrid didn’t help” narrative without a hard slice.
3. Vacuous abstain citation metric.
4. Stack/README claiming AI SDK you didn’t use.
5. “Independently testable modules” with **zero tests**.

### Decisions you’d struggle to justify cold

- Why RRF k=60 and never ablated while candidate_depth 20 vs 50 is “next.”
- Why generation evals shipped as n/a on the public `/eval` page.
- Why CORS allows all `*.vercel.app`.
- Why `min_tokens` exists if unused.
- Why commits are co-authored by Cursor if you’re claiming sole authorship.

### What I’d probe to see if you built it

- Ask you to write a failing unit test for RRF on a whiteboard, then point at `fusion.py`.
- Ask you to fix the citation marker bug live (10 minutes).
- Ask for the CoWoS story without looking at notes — dense miss, keyword hit, rerank promotion.
- Ask what breaks if Railway runs 2 API replicas (budget ×2).
- Ask you to explain `tsv` weighted ranks in `schema_fts.sql` from memory.

---

## 9. What’s missing

Staff / FDE bar expectations **not present**:

1. Unit + API tests with CI green on every PR  
2. Finished 35×3 generation evals or a sealed smaller set with complete numbers  
3. Human-verified gold slice (section-correct, abstain cases, exact-token)  
4. Retrieval rate limiting + tighter CORS + non-spoofable client identity  
5. Request IDs + token/cost from provider usage  
6. Prompt/schema versioning  
7. Parallel hybrid + connection pool  
8. Metadata filters / ticker routing  
9. README that literally works: venv create order, ingest, embed  
10. Frontend: starter queries, clickable evidence as the product, no glassmorphism, response Zod  
11. Remove or explain Cursor co-authorship before LinkedIn  
12. Open Graph / social metadata for the LinkedIn post  

---

## 10. Verdict

### Help or hurt?

**Helps — conditionally.**  
Against a generic “I fine-tuned a chatbot” applicant, this repo is a clear yes-interview. Against a strong Applied AI / FDE pool at Ramp/Hebbia/Perplexity, it is **not yet differentiating on rigor**. The architecture taste and honest null results buy you the screen; the missing tests, soft golds, citation bug, and Cursor trail decide the loop.

### Grade: **B−**

| Lens | Grade |
|------|-------|
| Early-career demo that ships | A− |
| Competitive Applied AI / FDE portfolio | **B−** |
| Staff engineer bar | C+ / B− |

### Top 5 changes by impact on hiring perception

1. **Fix citation marker rewrite + add unit tests for `fusion` and `grounding` + CI** — proves ownership.  
2. **Hard gold slice + finish or reframe `/eval`** — stop leading with “n/a (API credits)”; make CoWoS + MRR the story.  
3. **Rate-limit retrieval + pin CORS + stop trusting raw XFF** — shows you can ship a public demo without lighting money on fire.  
4. **Rewrite README for literal clone→query** (venv, ingest, embed) and delete boilerplate / AI SDK claim.  
5. **Clean git authorship narrative** — new commits without Cursor trailer, or own the AI-assist story explicitly in the README (“pair-programmed with Cursor; I own X/Y/Z”).

### Single biggest thing that makes a skeptical interviewer doubt you

**The citation-rewrite comment with no rewrite — combined with `Co-authored-by: Cursor` on the root commit.**  
That pairing reads as: an AI wrote a plan, left a TODO as a comment, and you shipped it. Fix that before you post LinkedIn.

---

## Appendix A — Offending patterns (quick reference)

```python
# BAD: comment claims rewrite; none happens
# packages/generation/prospectus_generation/grounding.py:127-130
# Rewrite citation markers in answer_text to match issued citation_ids.
answer_text = structured.answer_text.strip() or _compose_answer_from_claims(structured)
```

```python
# BETTER: renumber after filtering
citation_id = f"c{len(citations) + 1}"
# ... append citation ...
# then rewrite answer_text [cN] markers to match kept claims, or regenerate markers from claims
```

```python
# BAD: sequential "parallel"
dense = dense_retrieve(...)
keyword = keyword_retrieve(...)

# BETTER
with ThreadPoolExecutor(max_workers=2) as ex:
    f_dense = ex.submit(dense_retrieve, query, top_k=candidate_depth, embedder=embedder)
    f_kw = ex.submit(keyword_retrieve, query, top_k=candidate_depth)
    dense, keyword = f_dense.result(), f_kw.result()
```

---

## Appendix B — Strengths worth defending in interview

Do not undersell these:

1. Strategy-as-parameter is real code, not a slide.  
2. Structural grounding (closed IDs + excerpt membership) is the right instinct.  
3. Publishing “hybrid didn’t lift Recall on this set” is rare honesty.  
4. Retrieve-first + generate budgets for a public demo is mature product thinking.  
5. Structure-aware SEC chunking + FTS + RRF + Cohere rerank is a complete retrieval story.  
6. Live system + eval page + GitHub in one weekend-class arc shows shipping instinct.

Own those. Fix the holes. Then this becomes an **A−** portfolio artifact.

---

*End of audit.*

---

## Post-audit patches (same day)

Addressed immediately after this review (see git history):

1. **Citation marker rewrite implemented** in `grounding.py` + unit tests in `packages/generation/tests/test_grounding.py`.
2. **Hybrid legs parallelized** via `ThreadPoolExecutor` in `hybrid.py`.
3. **UI upgraded** toward evidence-first instrument (starters, clickable chunks, split layout, no glass header).
4. **README** documents ingest/embed before query; links this audit.

Remaining open from §10 top-5: CI, retrieval rate limits, CORS pin, hard gold slice, authorship narrative.
