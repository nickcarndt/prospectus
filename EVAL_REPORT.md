# Prospectus — Eval Report

Reproducible head-to-head of three retrieval configs on the labeled SEC eval set
(`data/eval/cases.json`, n=35). Every number below is sourced from measured run
artifacts; the combined snapshot is
[`data/eval/results/phase8_report_source.json`](data/eval/results/phase8_report_source.json).

| Artifact | What it contains |
|----------|------------------|
| `data/eval/results/partial_dense_hybrid.json` | dense + hybrid **retrieval-only** aggregates |
| `data/eval/results/latest_retrieval_only.json` | hybrid_rerank **retrieval-only** aggregates (same as `retrieval_only_20260714T203034Z.json`) |
| `data/eval/results/run_full.log` | partial dense **generation** lines (cite / faith / e2e latency) before Anthropic credit exhaustion |

**Settings:** `candidate_depth=50`, RRF `k=60`, embeddings `text-embedding-3-large`,
reranker Cohere Rerank. Retrieval latency/cost below are **retrieval stage only**
(no Claude). Generation metrics are **dense only, n=29** — see Limitations.

---

## Configurations compared

| Config | Pipeline |
|--------|----------|
| dense | Dense (pgvector) top-k |
| hybrid | Dense + keyword → RRF (k=60) → top-k |
| hybrid_rerank | Hybrid fuse at `candidate_depth` → Cohere Rerank → top 5–8 |

---

## Metrics

Rounded for display; full floats live in the source JSON.

| Metric | dense | hybrid | hybrid_rerank |
|--------|------:|-------:|--------------:|
| Recall@5 | 0.829 | 0.829 | 0.829 |
| Recall@10 | 0.829 | 0.829 | 0.829 |
| MRR | 0.684 | 0.624 | 0.620 |
| Faithfulness | **0.862** (n=29) | n/a (API credits) | n/a (API credits) |
| Citation accuracy | **1.000** (n=29) | n/a (API credits) | n/a (API credits) |
| p95 latency — retrieval (ms) | 676 | 435 | 1726 |
| p95 latency — e2e (ms) | **31201** (n=29) | n/a (API credits) | n/a (API credits) |
| Cost $/q — retrieval | ~0.000005 | ~0.000005 | 0.00101 |
| Cost $/q — e2e | n/a (not persisted for n=29) | n/a (API credits) | n/a (API credits) |

**Retrieval means (for context):** dense mean latency 536 ms; hybrid 359 ms;
hybrid_rerank 1055 ms. Dense e2e mean latency on the n=29 subset: **17646 ms**.

**Retrieval cost note:** dense/hybrid are embedding-only
(`embedding_usd=5.2e-06` from the eval cost breakdown on hybrid_rerank rows).
hybrid_rerank adds Cohere (~$0.001/query) → measured mean **$0.0010052**.

---

## Limitations (read before drawing conclusions)

1. **Recall@5 == Recall@10 for all three configs** on this set. Gold chunk either
   lands in top-5 or misses top-10 entirely — so R@10 cannot differentiate configs here.
2. **Generation incomplete.** Full e2e + faithfulness ran for **dense only through
   case `crm-ai-29` (n=29/35)**. Anthropic then returned
   `credit balance is too low` (`run_full.log`). Hybrid and hybrid_rerank
   generation cells are intentionally **n/a (API credits)** — not zeros.
3. **Dense e2e $/q** was not written to a results JSON for the n=29 partial; only
   per-case cite/faith/latency appear in the log. Do not invent a dollar figure.
4. Aggregate recall ties **do not** mean hybrid/rerank are useless — see qualitative
   CoWoS demos below (exact rare tokens).

---

## Analysis

### What improved (and what did not)

On this labeled set, **hybrid and hybrid_rerank did not lift Recall@5/10 vs dense**.
All three scored **0.829**. That is an honest null on the primary retrieval hit rate
metric for this gold labeling — not a win for fusion/rerank on aggregate recall.

**MRR went the other way:** dense **0.684** > hybrid **0.624** ≈ hybrid_rerank **0.620**.
RRF and Cohere reshuffle ranks; on this set they slightly **hurt** average reciprocal
rank of the gold chunk relative to dense-alone. Possible causes: gold labels that
favor dense-friendly semantic hits; RRF diluting a strong dense #1 with keyword
noise; rerank optimizing a different relevance surface than our gold chunk ids.

**Generation (dense subset only):** citation accuracy **1.000** — every cited claim
passed structural grounding checks. Faithfulness **≈0.862** — mostly grounded, with
some partial/failed judge scores (e.g. faith=0.0 or 0.5 on a handful of cases in the
log). These numbers are **not** comparable across strategies until hybrid /
hybrid_rerank generation is rerun.

### Qualitative counterexample: CoWoS (Phase 4 / 5)

Aggregate recall tied, but exact-token behavior still matters:

| Demo | Result |
|------|--------|
| Phase 4 — query `CoWoS packaging` | **dense:** CoWoS not in top-10 (nor top-50). **keyword:** #1. **hybrid:** #2. |
| Phase 5 — CoWoS + supply-chain phrasing | **hybrid** top-8: no CoWoS. **hybrid_rerank:** CoWoS chunks at **#1 / #2**. |

So hybrid/rerank can still win on rare financial tokens even when labeled Recall@k
does not move. The eval set’s gold distribution may under-weight that failure mode.

### What it cost

| Stage | Latency | Dollars |
|-------|---------|---------|
| Retrieval dense | p95 **676 ms** | ~$0.000005 /q |
| Retrieval hybrid | p95 **435 ms** (fastest) | ~$0.000005 /q |
| Retrieval hybrid_rerank | p95 **1726 ms** (~2.5–4× hybrid) | **~$0.00101 /q** (Cohere) |
| E2E dense (n=29) | mean **~17.6 s**, p95 **~31.2 s** | generation dominates; $/q not persisted |

On this set, **hybrid_rerank paid ~$0.001/query and ~1.3–1.7 s p95** for **no recall
gain** and a slight MRR regression vs dense. That is a poor latency/$ tradeoff *for
this gold set and these metrics* — keep the Stage 4/5 CoWoS evidence in mind before
scrapping rerank entirely.

### What we'd optimize next

1. **Harder / better gold labels** — more exact-token cases (CoWoS-class), section-
   precise golds, and cases where dense fails so Recall@k can actually separate configs.
2. **Exact-token eval subset** reported separately from the full 35.
3. **`candidate_depth` 20 vs 50** A/B (Phase 5 knob) — measure recall/MRR/latency/$
   before locking depth=50.
4. **Top up Anthropic credits** and finish full 35×3 generation (faithfulness,
   citation accuracy, e2e latency, e2e $/q) for all three strategies.
5. **Section-aware ranking** — boost same-ticker / gold-section priors when metadata
   matches the query’s company/section intent (several misses look section-wrong,
   not “no evidence”).

---

## How to reproduce

```bash
# Retrieval-only (all strategies; no Claude)
python -m prospectus_evals run --retrieval-only --no-braintrust

# Full e2e (needs Anthropic credits for generation + faithfulness judge)
python -m prospectus_evals run --no-braintrust

# Combined numbers used for this report
cat data/eval/results/phase8_report_source.json
```

Regenerate the report source after new runs by re-aggregating the JSON/log paths
listed at the top — do not hand-edit metrics into this file.
