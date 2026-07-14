"""Run all three retrieval configs on the labeled eval set.

Always writes reproducible JSON under data/eval/results/.
Optionally logs a Braintrust experiment when BRAINTRUST_API_KEY is set.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prospectus_generation.answer import answer_query
from prospectus_shared import RetrievalStrategy

from prospectus_evals.cost import estimate_cost
from prospectus_evals.dataset import EvalCase, load_eval_cases
from prospectus_evals.scorers import (
    citation_accuracy,
    faithfulness,
    mean_reciprocal_rank,
    recall_at_k,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"

EVAL_STRATEGIES: tuple[RetrievalStrategy, ...] = (
    RetrievalStrategy.DENSE,
    RetrievalStrategy.HYBRID,
    RetrievalStrategy.HYBRID_RERANK,
)


def run_one_case(
    case: EvalCase,
    *,
    strategy: RetrievalStrategy,
    candidate_depth: int = 50,
    judge_faithfulness: bool = True,
) -> dict[str, Any]:
    """Execute retrieve+generate for one case and compute scorers."""
    started = time.perf_counter()
    # Eval answers can be longer than the public demo cap (1024).
    answer = answer_query(
        case.query,
        strategy=strategy,
        top_k=10 if strategy is not RetrievalStrategy.HYBRID_RERANK else 8,
        candidate_depth=candidate_depth,
        max_tokens=int(os.getenv("EVAL_ANTHROPIC_MAX_TOKENS", "2048")),
    )
    latency_ms = (time.perf_counter() - started) * 1000.0

    chunks = answer.retrieval.chunks if answer.retrieval else []
    context_chars = sum(len(c.text) for c in chunks)
    cost = estimate_cost(
        strategy,
        answer_chars=len(answer.answer_text),
        context_chars=context_chars,
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
        "citation_accuracy": citation_accuracy(answer),
    }
    if judge_faithfulness:
        try:
            scores["faithfulness"] = faithfulness(answer)
        except Exception as exc:  # noqa: BLE001 — keep experiment running
            scores["faithfulness_error"] = str(exc)

    return {
        "case_id": case.id,
        "query": case.query,
        "strategy": strategy.value,
        "gold": {
            "ticker": case.gold_ticker,
            "section_id": case.gold_section_id,
            "section_title": case.gold_section_title,
            "chunk_id": case.gold_chunk_id,
        },
        "abstained": answer.abstained,
        "confidence": answer.confidence,
        "latency_ms": latency_ms,
        "retrieval_latency_ms": (
            answer.retrieval.latency_ms if answer.retrieval else None
        ),
        "cost": cost.as_dict(),
        "scores": scores,
        "answer_text": answer.answer_text,
        "citation_count": len(answer.citations),
        "answer": answer.model_dump(mode="json"),
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean scores, p95 latency, mean cost for a strategy's rows."""
    ok = [r for r in rows if not r.get("error")]

    def mean(key: str) -> float:
        vals = [r["scores"][key] for r in ok if key in r["scores"]]
        return statistics.fmean(vals) if vals else 0.0

    latencies = sorted(r["latency_ms"] for r in ok)
    p95_index = max(0, int(round(0.95 * (len(latencies) - 1)))) if latencies else 0
    p95 = latencies[p95_index] if latencies else 0.0
    costs = [r["cost"]["total_usd"] for r in ok]

    has_faith = any("faithfulness" in r["scores"] for r in ok)
    return {
        "n": len(ok),
        "n_attempted": len(rows),
        "n_errors": len(rows) - len(ok),
        "recall_at_5": mean("recall_at_5"),
        "recall_at_10": mean("recall_at_10"),
        "mrr": mean("mrr"),
        "citation_accuracy": mean("citation_accuracy"),
        "faithfulness": mean("faithfulness") if has_faith else None,
        "latency_ms_mean": statistics.fmean(latencies) if latencies else 0.0,
        "latency_ms_p95": p95,
        "cost_usd_mean": statistics.fmean(costs) if costs else 0.0,
    }


def run_experiments(
    *,
    strategies: tuple[RetrievalStrategy, ...] = EVAL_STRATEGIES,
    candidate_depth: int = 50,
    limit: int | None = None,
    judge_faithfulness: bool = True,
    push_braintrust: bool = True,
) -> dict[str, Any]:
    """Run the full multi-config experiment suite.

    Args:
        strategies: Retrieval configs to compare.
        candidate_depth: Hybrid/rerank wide depth (20 vs 50 experiments).
        limit: Optional case cap for smoke tests.
        judge_faithfulness: If False, skip LLM judge (faster/cheaper debug).
        push_braintrust: Log to Braintrust when BRAINTRUST_API_KEY is set.

    Returns:
        Summary dict also written under data/eval/results/.
    """
    cases = load_eval_cases()
    if limit is not None:
        cases = cases[:limit]

    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for strategy in strategies:
        rows: list[dict[str, Any]] = []
        for case in cases:
            try:
                row = run_one_case(
                    case,
                    strategy=strategy,
                    candidate_depth=candidate_depth,
                    judge_faithfulness=judge_faithfulness,
                )
            except Exception as exc:  # noqa: BLE001 — keep the suite alive
                print(f"[{strategy.value}] {case.id}: ERROR {exc}")
                row = {
                    "case_id": case.id,
                    "query": case.query,
                    "strategy": strategy.value,
                    "gold": {
                        "ticker": case.gold_ticker,
                        "section_id": case.gold_section_id,
                        "section_title": case.gold_section_title,
                        "chunk_id": case.gold_chunk_id,
                    },
                    "abstained": True,
                    "confidence": 0.0,
                    "latency_ms": 0.0,
                    "retrieval_latency_ms": None,
                    "cost": {
                        "embedding_usd": 0.0,
                        "rerank_usd": 0.0,
                        "generation_usd": 0.0,
                        "total_usd": 0.0,
                    },
                    "scores": {
                        "recall_at_5": 0.0,
                        "recall_at_10": 0.0,
                        "mrr": 0.0,
                        "citation_accuracy": 0.0,
                        "error": str(exc),
                    },
                    "answer_text": "",
                    "citation_count": 0,
                    "answer": None,
                    "error": str(exc),
                }
            rows.append(row)
            faith = row["scores"].get("faithfulness")
            faith_s = f"{faith:.2f}" if faith is not None else "n/a"
            err = row.get("error")
            if err:
                continue
            print(
                f"[{strategy.value}] {case.id}: "
                f"r@5={row['scores']['recall_at_5']:.0f} "
                f"r@10={row['scores']['recall_at_10']:.0f} "
                f"mrr={row['scores']['mrr']:.3f} "
                f"cite={row['scores']['citation_accuracy']:.2f} "
                f"faith={faith_s} "
                f"lat={row['latency_ms']:.0f}ms"
            )
        by_strategy[strategy.value] = rows

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_depth": candidate_depth,
        "case_count": len(cases),
        "strategies": {
            name: {
                "aggregate": _aggregate(rows),
                "rows": rows,
            }
            for name, rows in by_strategy.items()
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"eval_{stamp}.json"
    payload = json.dumps(summary, indent=2) + "\n"
    out_path.write_text(payload, encoding="utf-8")
    (RESULTS_DIR / "latest.json").write_text(payload, encoding="utf-8")
    print(f"Wrote {out_path}")

    if push_braintrust:
        _maybe_log_braintrust(summary)

    return summary


def _maybe_log_braintrust(summary: dict[str, Any]) -> None:
    """Log aggregate + per-row scores to Braintrust when configured."""
    if not os.getenv("BRAINTRUST_API_KEY"):
        print("BRAINTRUST_API_KEY not set — local results only (still reproducible)")
        return

    from braintrust import init_experiment

    experiment = init_experiment(
        project="Prospectus",
        experiment=f"3-config-{summary['created_at']}",
    )
    try:
        for strategy_name, payload in summary["strategies"].items():
            for row in payload["rows"]:
                experiment.log(
                    input=row["query"],
                    output={
                        "answer_text": row["answer_text"],
                        "abstained": row["abstained"],
                        "citations": row["citation_count"],
                    },
                    expected=row["gold"],
                    scores=row["scores"],
                    metadata={
                        "case_id": row["case_id"],
                        "strategy": strategy_name,
                        "latency_ms": row["latency_ms"],
                        "cost_usd": row["cost"]["total_usd"],
                    },
                )
            experiment.log(
                input={"aggregate_for": strategy_name},
                output=payload["aggregate"],
                scores={
                    k: v
                    for k, v in payload["aggregate"].items()
                    if k
                    in {
                        "recall_at_5",
                        "recall_at_10",
                        "mrr",
                        "citation_accuracy",
                        "faithfulness",
                    }
                },
                metadata={"strategy": strategy_name, "kind": "aggregate"},
            )
        print("Logged experiment to Braintrust project 'Prospectus'")
    finally:
        experiment.flush()
