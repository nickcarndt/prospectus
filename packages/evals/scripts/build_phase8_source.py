"""Rebuild apps/web phase8_report_source.json from a full eval JSON.

Usage (from repo root, venv active):
  PYTHONPATH=packages/evals python packages/evals/scripts/build_phase8_source.py \\
    data/eval/results/latest.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "apps/web/src/data/phase8_report_source.json"


def _agg(summary: dict[str, Any], name: str) -> dict[str, Any]:
    return summary["strategies"][name]["aggregate"]


def build(summary: dict[str, Any], source_path: str) -> dict[str, Any]:
    """Map full eval aggregates into the web report source schema."""
    dense = _agg(summary, "dense")
    hybrid = _agg(summary, "hybrid")
    rerank = _agg(summary, "hybrid_rerank")

    def triple(key: str) -> dict[str, float]:
        return {
            "dense": dense[key],
            "hybrid": hybrid[key],
            "hybrid_rerank": rerank[key],
        }

    return {
        "report": "EVAL_REPORT.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_depth": summary.get("candidate_depth", 50),
        "eval_set_n": summary.get("case_count", 35),
        "sources": {
            "full_generation_eval": source_path,
        },
        "limitations": {
            "generation_incomplete": False,
            "anthropic_credits_exhausted": False,
            "recall_at_5_equals_recall_at_10": (
                "Corpus/gold artifact, not a scorer bug: binary section hit-rate — "
                "when gold is found it is almost always already in top-5, so R@10 "
                "adds no new hits. Use MRR to compare ranking quality."
            ),
        },
        "retrieval_only": {
            name: {
                "n": agg["n"],
                "recall_at_5": agg["recall_at_5"],
                "recall_at_10": agg["recall_at_10"],
                "mrr": agg["mrr"],
                "latency_ms_mean": None,
                "latency_ms_p95": None,
                "cost_usd_mean_retrieval": None,
                "note": "Retrieval scores taken from full e2e run (same gold hit logic).",
            }
            for name, agg in (
                ("dense", dense),
                ("hybrid", hybrid),
                ("hybrid_rerank", rerank),
            )
        },
        "generation_complete": {
            name: {
                "n": agg["n"],
                "citation_accuracy": agg["citation_accuracy"],
                "faithfulness": agg["faithfulness"],
                "latency_ms_mean": agg["latency_ms_mean"],
                "latency_ms_p95": agg["latency_ms_p95"],
                "cost_usd_mean": agg["cost_usd_mean"],
            }
            for name, agg in (
                ("dense", dense),
                ("hybrid", hybrid),
                ("hybrid_rerank", rerank),
            )
        },
        "table_display": {
            "recall_at_5": triple("recall_at_5"),
            "recall_at_10": triple("recall_at_10"),
            "mrr": triple("mrr"),
            "citation_accuracy": triple("citation_accuracy"),
            "faithfulness": {
                "dense": dense["faithfulness"],
                "hybrid": hybrid["faithfulness"],
                "hybrid_rerank": rerank["faithfulness"],
            },
            "p95_latency_ms_e2e": triple("latency_ms_p95"),
            "cost_usd_per_query_e2e": triple("cost_usd_mean"),
            # Keep retrieval columns populated from prior retrieval-only where
            # available; e2e latency/cost replace generation appendix.
            "p95_latency_ms_retrieval": {
                "dense": 676.0,
                "hybrid": 435.0,
                "hybrid_rerank": 1725.6019999913406,
            },
            "cost_usd_per_query_retrieval": {
                "dense": 5.2e-06,
                "hybrid": 5.2e-06,
                "hybrid_rerank": 0.0010052,
            },
        },
        "qualitative_demos": {
            "phase4_cowos": {
                "query": "What is CoWoS packaging and which filers discuss it?",
                "finding": (
                    "Dense often under-ranks rare exact tokens; hybrid surfaces NVDA."
                ),
            },
            "phase5_cowos_rerank": {
                "finding": (
                    "Rerank can reorder the hybrid pool; check live with Exact-token win."
                ),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "eval_json",
        type=Path,
        help="Path to eval_*.json / latest.json from prospectus_evals run",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    eval_path = args.eval_json.resolve()
    summary = json.loads(eval_path.read_text(encoding="utf-8"))
    for required in ("dense", "hybrid", "hybrid_rerank"):
        if required not in summary.get("strategies", {}):
            raise SystemExit(f"missing strategy in eval JSON: {required}")
        faith = summary["strategies"][required]["aggregate"].get("faithfulness")
        if faith is None:
            raise SystemExit(
                f"{required} missing faithfulness; re-run without --no-faithfulness"
            )
    try:
        source_rel = str(eval_path.relative_to(REPO_ROOT))
    except ValueError:
        source_rel = str(eval_path)
    payload = build(summary, source_rel)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
