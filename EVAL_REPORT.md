# Prospectus Eval Report

Reproducible head-to-head of three retrieval configs on the labeled SEC eval set
(`data/eval/cases.jsonl`, n=35). Every number below is sourced from measured run
artifacts. Sealed digest:
[`data/eval/RESULTS_DIGEST.json`](data/eval/RESULTS_DIGEST.json)
(SHA-256 of the retrieval-only artifact + cases + aggregates). Web snapshot:
[`apps/web/src/data/phase8_report_source.json`](apps/web/src/data/phase8_report_source.json).

| Artifact | What it contains |
|----------|------------------|
| `data/eval/RESULTS_DIGEST.json` | Committed SHA-256 + aggregate snapshot (verify this) |
| `data/eval/results/latest_retrieval_only.json` | Post-gold-relabel retrieval metrics (Recall/MRR/latency/cost) |
| `data/eval/results/retrieval_only_20260714T231311Z.json` | Timestamped copy of that run |
| `data/eval/results/eval_20260714T222900Z.json` | Prior full e2e (cite/faithfulness); golds corrected after this run |

**Settings:** `candidate_depth=50`, RRF `k=60`, embeddings `text-embedding-3-large`,
reranker Cohere Rerank, generation Claude structured output + structural grounding.
Retrieval-only suite completed 2026-07-14 after section-correct gold relabel
(`EXIT:0`). Full generation re-run deferred (freeze).

---

## Configurations compared

| Config | Pipeline |
|--------|----------|
| dense (Semantic) | Dense (pgvector) top-k |
| hybrid (Keyword + semantic) | Dense + keyword → RRF (k=60) → top-k |
| hybrid_rerank (Best match) | Hybrid fuse at `candidate_depth` → Cohere Rerank → top 5–8 |

---

## Metrics

Rounded for display; full floats live in the digest / source JSON.

| Metric | dense | hybrid | hybrid_rerank |
|--------|------:|-------:|--------------:|
| Recall@5 | 0.971 | 0.971 | 0.943 |
| Recall@10 | 0.971 | 0.971 | 0.971 |
| MRR | 0.845 | 0.755 | 0.727 |
| Citation accuracy | 1.000 | 1.000 | 1.000 |
| Faithfulness | 0.900 | 0.857 | 1.000 |
| p95 latency, retrieval (ms) | 613 | 453 | 849 |
| p95 latency, e2e (ms) | 29567 | 30267 | 26328 |
| Cost $/q, retrieval | ~0.000005 | ~0.000005 | 0.00101 |
| Cost $/q, e2e (est.) | 0.0214 | 0.0215 | 0.0188 |

**Retrieval means (stage only, post-relabel):** dense mean 390 ms; hybrid 327 ms;
hybrid_rerank 762 ms.

**Retrieval cost note:** dense/hybrid are embedding-only (~`5.2e-06` $/q). hybrid_rerank
adds Cohere (~$0.001/query) → measured mean **$0.0010052**.

**Provenance:** Recall/MRR/retrieval latency+cost from
`latest_retrieval_only.json` (digest sha256
`7cc91ac42764aa133745b81de5e579e88134a7083e0797ad1fe7f6902f5750b0`).
Citation/faithfulness/e2e latency+cost from prior full e2e
`eval_20260714T222900Z.json` (pre-relabel golds for ~7 cases).

---

## Limitations

1. **Golds were corrected** (Item 1A/1C mismatches, invalid section ids like
   `item_1_linkedin`). Soft phrase-ILIKE padding was not used for the fix.
2. **Citation/faithfulness are from the prior full e2e**, not re-run after the
   relabel. Fresh generation suite is explicitly deferred.
3. Dense/hybrid still show **R@5 = R@10** on this set; hybrid_rerank separates
   slightly (0.943 vs 0.971). Prefer **MRR** for ranking comparisons.
4. Aggregate recall ties **do not** mean hybrid/rerank are useless. See qualitative
   CoWoS demos below (exact rare tokens).
5. E2e `$/q` is the eval harness cost estimate, not a Stripe invoice.

---

## Analysis

### What improved (and what did not)

After section-correct golds, **hit rate is high across configs** (R@10 = **0.971**
for all three). That is not a claim that retrieval is “solved” — it means this
35-case set is easier once labels match the asked section.

**Honest null on hybrid lift vs dense still holds for primary hit rate:** dense and
hybrid tie at R@5/R@10 **0.971**. hybrid_rerank is slightly lower at R@5 (**0.943**)
with the same R@10 — one gold lands outside top-5 after rerank.

**MRR still favors dense:** dense **0.845** > hybrid **0.755** > hybrid_rerank
**0.727**. RRF and Cohere reshuffle ranks; on this set they do not beat dense-alone
on average reciprocal rank of the gold chunk.

**Generation (prior full n=35 × 3):** citation accuracy **1.000** for every config.
Faithfulness: dense **0.900**, hybrid **0.857**, hybrid_rerank **1.000**.

### Qualitative counterexample: CoWoS

Aggregate MRR favors dense, but exact-token behavior still matters:

| Demo | Result |
|------|--------|
| Phase 4, query `CoWoS packaging` | dense: CoWoS not in top-10 (nor top-50). keyword: #1. hybrid: #2. |
| Phase 5, CoWoS + supply-chain phrasing | hybrid top-8: no CoWoS. hybrid_rerank: CoWoS chunks at #1 / #2. |

So hybrid/rerank can still win on rare financial tokens even when labeled Recall@k
does not move.

### What it cost

| Stage | Latency | Dollars |
|-------|---------|---------|
| Retrieval dense | p95 613 ms | ~$0.000005 /q |
| Retrieval hybrid | p95 453 ms (fastest) | ~$0.000005 /q |
| Retrieval hybrid_rerank | p95 849 ms | ~$0.00101 /q (Cohere) |
| E2E (prior full run) | p95 ~26–30 s | ~$0.019–0.022 /q est. |

On this set, **hybrid_rerank paid ~$0.001/query** for **no R@10 gain vs dense**, a
slight R@5 dip, and lower MRR, while prior e2e faithfulness was highest. Keep the
CoWoS evidence in mind before scrapping rerank.

### What we'd optimize next (deferred — freeze)

1. Fresh full generation suite on the corrected golds.
2. Exact-token eval subset reported separately from the full 35.
3. `candidate_depth` 20 vs 50 A/B before locking depth=50.
4. Section-aware ranking: boost same-ticker / gold-section priors when metadata
   matches the query intent.

---

## How to reproduce

```bash
# Retrieval-only (all strategies; no Claude) — sealed in RESULTS_DIGEST.json
python -m prospectus_evals retrieval-only

# Verify digest
PYTHONPATH=packages/evals python packages/evals/scripts/write_results_digest.py \
  data/eval/results/latest_retrieval_only.json

# Full e2e (needs Anthropic; deferred under freeze)
export EVAL_ANTHROPIC_MAX_TOKENS=2048
python -m prospectus_evals run --no-braintrust
```

Do not hand-edit metrics into `EVAL_REPORT.md` or `phase8_report_source.json`
without regenerating the digest.
