"""CLI for the Prospectus eval harness.

Usage:
  python -m prospectus_evals run --limit 2                 # smoke
  python -m prospectus_evals run                          # full 3-config
  python -m prospectus_evals run --no-faithfulness        # cheaper
  python -m prospectus_evals scorers                      # print scorer defs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _cmd_run(args: argparse.Namespace) -> int:
    """Run multi-config experiments."""
    from prospectus_shared import RetrievalStrategy

    from prospectus_evals.runner import run_experiments

    name_map = {
        "dense": RetrievalStrategy.DENSE,
        "hybrid": RetrievalStrategy.HYBRID,
        "hybrid_rerank": RetrievalStrategy.HYBRID_RERANK,
    }
    strategies = tuple(name_map[s] for s in args.strategies)
    summary = run_experiments(
        strategies=strategies,
        candidate_depth=args.candidate_depth,
        limit=args.limit,
        judge_faithfulness=not args.no_faithfulness,
        push_braintrust=not args.no_braintrust,
    )
    print("\n=== Aggregate ===")
    for name, payload in summary["strategies"].items():
        agg = payload["aggregate"]
        print(
            f"{name:14} r@5={agg['recall_at_5']:.3f} r@10={agg['recall_at_10']:.3f} "
            f"mrr={agg['mrr']:.3f} cite={agg['citation_accuracy']:.3f} "
            f"faith={agg.get('faithfulness', 0):.3f} "
            f"p95={agg['latency_ms_p95']:.0f}ms "
            f"$/q={agg['cost_usd_mean']:.4f}"
        )
    return 0


def _cmd_scorers(_: argparse.Namespace) -> int:
    """Print interview-ready scorer explanations."""
    from prospectus_evals import scorers

    print(scorers.__doc__)
    return 0


def _cmd_retrieval_only(args: argparse.Namespace) -> int:
    """Run retrieve-only eval (no Claude) for Recall/MRR/latency."""
    from prospectus_shared import RetrievalStrategy

    from prospectus_evals.retrieval_only import run_retrieval_only

    name_map = {
        "dense": RetrievalStrategy.DENSE,
        "hybrid": RetrievalStrategy.HYBRID,
        "hybrid_rerank": RetrievalStrategy.HYBRID_RERANK,
    }
    strategies = tuple(name_map[s] for s in args.strategies)
    summary = run_retrieval_only(
        strategies=strategies,
        candidate_depth=args.candidate_depth,
        limit=args.limit,
    )
    print("\n=== Aggregate (retrieval only) ===")
    for name, payload in summary["strategies"].items():
        agg = payload["aggregate"]
        print(
            f"{name:14} r@5={agg['recall_at_5']:.3f} r@10={agg['recall_at_10']:.3f} "
            f"mrr={agg['mrr']:.3f} p95={agg['latency_ms_p95']:.0f}ms "
            f"$/q={agg['cost_usd_mean']:.5f}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and dispatch."""
    parser = argparse.ArgumentParser(description="Prospectus eval harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run 3-config eval experiment")
    run_p.add_argument(
        "--strategies",
        nargs="+",
        default=["dense", "hybrid", "hybrid_rerank"],
        choices=["dense", "hybrid", "hybrid_rerank"],
    )
    run_p.add_argument("--candidate-depth", type=int, default=50)
    run_p.add_argument("--limit", type=int, default=None, help="Smoke-test case cap")
    run_p.add_argument(
        "--no-faithfulness",
        action="store_true",
        help="Skip LLM-as-judge (faster/cheaper)",
    )
    run_p.add_argument(
        "--no-braintrust",
        action="store_true",
        help="Skip Braintrust upload even if API key is set",
    )
    run_p.set_defaults(func=_cmd_run)

    scorers_p = sub.add_parser("scorers", help="Explain scorers (interview prep)")
    scorers_p.set_defaults(func=_cmd_scorers)

    ret_p = sub.add_parser(
        "retrieval-only",
        help="Retrieve-only eval (Recall/MRR/latency; no Claude generation)",
    )
    ret_p.add_argument(
        "--strategies",
        nargs="+",
        default=["dense", "hybrid", "hybrid_rerank"],
        choices=["dense", "hybrid", "hybrid_rerank"],
    )
    ret_p.add_argument("--candidate-depth", type=int, default=50)
    ret_p.add_argument("--limit", type=int, default=None)
    ret_p.set_defaults(func=_cmd_retrieval_only)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
