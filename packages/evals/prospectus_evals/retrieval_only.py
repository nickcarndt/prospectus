"""Retrieval-only experiment (no Claude) — used when generation API is unavailable.

Still produces reproducible Recall@k, MRR, retrieval latency, and retrieval-stage cost
for dense / hybrid / hybrid_rerank.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prospectus_retrieval.retrieve import retrieve
from prospectus_shared import RetrievalStrategy

from prospectus_evals.cost import RERANK_PER_QUERY, estimate_cost
from prospectus_evals.dataset import load_eval_cases
from prospectus_evals.runner import EVAL_STRATEGIES, RESULTS_DIR
from prospectus_evals.scorers import mean_reciprocal_rank, recall_at_k

# Cohere trial keys allow ~10 rerank calls/minute.
_RERANK_PACING_S = 7.0


def _retrieve_with_retry(
    query: str,
    *,
    strategy: RetrievalStrategy,
    top_k: int,
    candidate_depth: int,
    retries: int = 5,
):
    """Call retrieve; on Cohere 429, wait and retry."""
    from cohere.errors import TooManyRequestsError

    delay = 65.0
    for attempt in range(retries):
        try:
            return retrieve(
                query,
                strategy=strategy,
                top_k=top_k,
                candidate_depth=candidate_depth,
            )
        except TooManyRequestsError:
            if attempt + 1 >= retries:
                raise
            print(f"Cohere rate limit — sleeping {delay:.0f}s (attempt {attempt + 1})")
            time.sleep(delay)


def run_retrieval_only(
    *,
    strategies: tuple[RetrievalStrategy, ...] = EVAL_STRATEGIES,
    candidate_depth: int = 50,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run retrieve-only eval for each strategy; write JSON under data/eval/results/."""
    cases = load_eval_cases()
    if limit is not None:
        cases = cases[:limit]

    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for strategy in strategies:
        rows: list[dict[str, Any]] = []
        if strategy is RetrievalStrategy.HYBRID_RERANK:
            # Clear any residual trial-key window from prior bursts.
            print("Pacing for Cohere trial limit (sleep 65s before hybrid_rerank)...")
            time.sleep(65.0)
        for case in cases:
            if strategy is RetrievalStrategy.HYBRID_RERANK and rows:
                time.sleep(_RERANK_PACING_S)
            started = time.perf_counter()
            result = _retrieve_with_retry(
                case.query,
                strategy=strategy,
                top_k=10 if strategy is not RetrievalStrategy.HYBRID_RERANK else 8,
                candidate_depth=candidate_depth,
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            chunks = result.chunks
            # Generation cost = 0 in this mode; still count embed/rerank.
            cost = estimate_cost(strategy, answer_chars=0, context_chars=0)
            # estimate_cost still adds tiny generation floor — zero it for retrieval-only.
            cost_dict = cost.as_dict()
            cost_dict["generation_usd"] = 0.0
            if strategy is not RetrievalStrategy.HYBRID_RERANK:
                cost_dict["rerank_usd"] = 0.0
            else:
                cost_dict["rerank_usd"] = RERANK_PER_QUERY
            cost_dict["total_usd"] = (
                cost_dict["embedding_usd"] + cost_dict["rerank_usd"]
            )

            scores = {
                "recall_at_5": recall_at_k(
                    chunks,
                    gold_ticker=case.gold_ticker,
                    gold_section_id=case.gold_section_id,
                    gold_chunk_id=case.gold_chunk_id,
                    k=5,
                ),
                "recall_at_10": recall_at_k(
                    chunks,
                    gold_ticker=case.gold_ticker,
                    gold_section_id=case.gold_section_id,
                    gold_chunk_id=case.gold_chunk_id,
                    k=10,
                ),
                "mrr": mean_reciprocal_rank(
                    chunks,
                    gold_ticker=case.gold_ticker,
                    gold_section_id=case.gold_section_id,
                    gold_chunk_id=case.gold_chunk_id,
                ),
            }
            row = {
                "case_id": case.id,
                "query": case.query,
                "strategy": strategy.value,
                "latency_ms": latency_ms,
                "cost": cost_dict,
                "scores": scores,
            }
            rows.append(row)
            print(
                f"[{strategy.value}] {case.id}: "
                f"r@5={scores['recall_at_5']:.0f} "
                f"r@10={scores['recall_at_10']:.0f} "
                f"mrr={scores['mrr']:.3f} "
                f"lat={latency_ms:.0f}ms"
            )
        by_strategy[strategy.value] = rows

    def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
        def mean(key: str) -> float:
            return statistics.fmean(r["scores"][key] for r in rows)

        latencies = sorted(r["latency_ms"] for r in rows)
        p95 = latencies[max(0, int(round(0.95 * (len(latencies) - 1))))]
        return {
            "n": len(rows),
            "recall_at_5": mean("recall_at_5"),
            "recall_at_10": mean("recall_at_10"),
            "mrr": mean("mrr"),
            "latency_ms_mean": statistics.fmean(latencies),
            "latency_ms_p95": p95,
            "cost_usd_mean": statistics.fmean(r["cost"]["total_usd"] for r in rows),
        }

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "retrieval_only",
        "candidate_depth": candidate_depth,
        "case_count": len(cases),
        "strategies": {
            name: {"aggregate": agg(rows), "rows": rows}
            for name, rows in by_strategy.items()
        },
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"retrieval_only_{stamp}.json"
    payload = json.dumps(summary, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    (RESULTS_DIR / "latest_retrieval_only.json").write_text(payload, encoding="utf-8")
    print(f"Wrote {path}")
    return summary
