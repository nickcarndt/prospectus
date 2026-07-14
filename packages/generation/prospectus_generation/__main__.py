"""CLI for cited generation.

Usage:
  python -m prospectus_generation answer "What did NVIDIA say about CoWoS?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _cmd_answer(args: argparse.Namespace) -> int:
    """Retrieve + generate a grounded Answer."""
    from prospectus_shared import RetrievalStrategy

    from prospectus_generation.answer import answer_query

    strategy = RetrievalStrategy(args.strategy)
    answer = answer_query(
        args.query,
        strategy=strategy,
        top_k=args.k,
        candidate_depth=args.candidate_depth,
        confidence_threshold=args.confidence_threshold,
    )
    print(f"abstained={answer.abstained} confidence={answer.confidence:.2f}")
    print(f"strategy={answer.strategy.value}")
    print(answer.answer_text)
    if answer.citations:
        print("\nCitations:")
        for cite in answer.citations:
            print(
                f"  [{cite.citation_id}] {cite.ticker} {cite.form_type} "
                f"{cite.filing_date} — {cite.section_title}"
            )
            print(f"      {cite.excerpt[:160].replace(chr(10), ' ')}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and dispatch."""
    parser = argparse.ArgumentParser(description="Prospectus cited generation")
    sub = parser.add_subparsers(dest="command", required=True)

    answer_p = sub.add_parser("answer", help="Retrieve and generate a cited answer")
    answer_p.add_argument("query", help="Research question")
    answer_p.add_argument(
        "--strategy",
        default="hybrid_rerank",
        choices=["dense", "keyword", "hybrid", "hybrid_rerank"],
    )
    answer_p.add_argument("--k", type=int, default=None)
    answer_p.add_argument("--candidate-depth", type=int, default=50)
    answer_p.add_argument("--confidence-threshold", type=float, default=0.55)
    answer_p.set_defaults(func=_cmd_answer)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
