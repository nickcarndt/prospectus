# Prospectus Eval Report

Reproducible head-to-head of three retrieval configs on the labeled SEC eval set
(`data/eval/cases.json`, n=35). Every number below is sourced from measured run
artifacts. Combined snapshot:
[`apps/web/src/data/phase8_report_source.json`](apps/web/src/data/phase8_report_source.json)
(also copied to `data/eval/results/phase8_report_source.json`).

| Artifact | What it contains |
|----------|------------------|
| `data/eval/results/latest.json` | Full e2e: retrieve + generate + faithfulness for all 3 configs (n=35 each) |
| `data/eval/results/eval_20260714T222900Z.json` | Timestamped copy of that run |
| `data/eval/results/latest_retrieval_only.json` | Prior retrieval-stage latency/cost for hybrid_rerank |
| `data/eval/results/partial_dense_hybrid.json` | Prior retrieval-stage latency/cost for dense + hybrid |

**Settings:** `candidate_depth=50`, RRF `k=60`, embeddings `text-embedding-3-large`,
reranker Cohere Rerank, generation Claude structured output + structural grounding.
Full generation suite completed 2026-07-14 (`EXIT:0`, zero case errors).

---

## Configurations compared

| Config | Pipeline |
|--------|----------|
| dense (Semantic) | Dense (pgvector) top-k |
| hybrid (Keyword + semantic) | Dense + keyword → RRF (k=60) → top-k |
| hybrid_rerank (Best match) | Hybrid fuse at `candidate_depth` → Cohere Rerank → top 5–8 |

---

## Metrics

Rounded for display; full floats live in the source JSON.

| Metric | dense | hybrid | hybrid_rerank |
|--------|------:|-------:|--------------:|
| Recall@5 | 0.829 | 0.829 | 0.829 |
| Recall@10 | 0.829 | 0.829 | 0.829 |
| MRR | 0.684 | 0.624 | 0.620 |
| Citation accuracy | 1.000 | 1.000 | 1.000 |
| Faithfulness | 0.900 | 0.857 | 1.000 |
| p95 latency, retrieval (ms) | 676 | 435 | 1726 |
| p95 latency, e2e (ms) | 29567 | 30267 | 26328 |
| Cost $/q, retrieval | ~0.000005 | ~0.000005 | 0.00101 |
| Cost $/q, e2e (est.) | 0.0214 | 0.0215 | 0.0188 |

**Retrieval means (stage only):** dense mean 536 ms; hybrid 359 ms; hybrid_rerank 1055 ms.

**Retrieval cost note:** dense/hybrid are embedding-only (~`5.2e-06` $/q). hybrid_rerank
adds Cohere (~$0.001/query) → measured mean **$0.0010052**.

---

## Limitations

1. **Recall@5 equals Recall@10** for all three configs on this set. Gold chunk either
   lands in top-5 or misses top-10 entirely, so R@10 cannot differentiate configs here.
2. Aggregate recall ties **do not** mean hybrid/rerank are useless. See qualitative
   CoWoS demos below (exact rare tokens).
3. E2e `$/q` is the eval harness cost estimate (embedding + rerank + generation token
   model), not a Stripe invoice.

---

## Analysis

### What improved (and what did not)

On this labeled set, **hybrid and hybrid_rerank did not lift Recall@5/10 vs dense**.
All three scored **0.829**. That is an honest null on primary retrieval hit rate for
this gold labeling.

**MRR went the other way:** dense **0.684** > hybrid **0.624** ≈ hybrid_rerank **0.620**.
RRF and Cohere reshuffle ranks; on this set they slightly hurt average reciprocal
rank of the gold section relative to dense-alone.

**Generation (full n=35 × 3):** citation accuracy is **1.000** for every config.
Faithfulness is strong across the board: dense **0.900**, hybrid **0.857**,
hybrid_rerank **1.000**. Structural grounding is holding; hybrid+rerank edges the
judge score on this run.

### Qualitative counterexample: CoWoS

Aggregate recall tied, but exact-token behavior still matters:

| Demo | Result |
|------|--------|
| Phase 4, query `CoWoS packaging` | dense: CoWoS not in top-10 (nor top-50). keyword: #1. hybrid: #2. |
| Phase 5, CoWoS + supply-chain phrasing | hybrid top-8: no CoWoS. hybrid_rerank: CoWoS chunks at #1 / #2. |

So hybrid/rerank can still win on rare financial tokens even when labeled Recall@k
does not move.

### What it cost

| Stage | Latency | Dollars |
|-------|---------|---------|
| Retrieval dense | p95 676 ms | ~$0.000005 /q |
| Retrieval hybrid | p95 435 ms (fastest) | ~$0.000005 /q |
| Retrieval hybrid_rerank | p95 1726 ms | ~$0.00101 /q (Cohere) |
| E2E (all configs, n=35) | p95 ~26–30 s | ~$0.019–0.022 /q est. |

On this set, **hybrid_rerank paid ~$0.001/query and ~1.3–1.7 s retrieval p95** for
**no recall gain** and a slight MRR regression vs dense, while e2e faithfulness was
highest. Keep the CoWoS evidence in mind before scrapping rerank.

### What we'd optimize next

1. Harder / better gold labels: more exact-token cases (CoWoS-class), section-precise
   golds, and cases where dense fails so Recall@k can separate configs.
2. Exact-token eval subset reported separately from the full 35.
3. `candidate_depth` 20 vs 50 A/B before locking depth=50.
4. Section-aware ranking: boost same-ticker / gold-section priors when metadata
   matches the query intent.

---

## How to reproduce

```bash
# Retrieval-only (all strategies; no Claude)
python -m prospectus_evals retrieval-only --no-braintrust

# Full e2e (needs Anthropic for generation + faithfulness judge)
export EVAL_ANTHROPIC_MAX_TOKENS=2048
python -m prospectus_evals run --no-braintrust

# Rebuild the web/report snapshot
PYTHONPATH=packages/evals python packages/evals/scripts/build_phase8_source.py \
  data/eval/results/latest.json
```

Do not hand-edit metrics into `EVAL_REPORT.md` or `phase8_report_source.json`.
