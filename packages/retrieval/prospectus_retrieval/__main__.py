"""CLI for retrieval package.

Usage:
  python -m prospectus_retrieval embed [--limit N]
  python -m prospectus_retrieval search "query" [--strategy dense] [--k 5]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _cmd_embed(args: argparse.Namespace) -> int:
    """Embed chunk JSONL and upsert into Postgres."""
    from prospectus_retrieval.embed_load import DEFAULT_CHUNKS_DIR, embed_corpus

    chunks_dir = Path(args.chunks_dir) if args.chunks_dir else DEFAULT_CHUNKS_DIR
    count = embed_corpus(
        chunks_dir=chunks_dir,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    print(f"Embedded and upserted {count} chunks from {chunks_dir}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    """Run retrieval for a query (strategy is a parameter)."""
    from prospectus_shared import RetrievalStrategy

    from prospectus_retrieval.retrieve import retrieve

    strategy = RetrievalStrategy(args.strategy)
    result = retrieve(
        args.query,
        strategy=strategy,
        top_k=args.k,
        candidate_depth=args.candidate_depth,
    )
    latency = f"{result.latency_ms:.0f}ms" if result.latency_ms is not None else "?"
    print(
        f"strategy={result.strategy.value} hits={len(result.chunks)} "
        f"candidate_depth={args.candidate_depth} latency={latency}"
    )
    for rank, (chunk, score) in enumerate(
        zip(result.chunks, result.scores, strict=True), start=1
    ):
        print(
            f"{rank:2}. score={score:.4f}  {chunk.ticker} {chunk.form_type}  "
            f"{chunk.section_title}"
        )
        preview = chunk.text.replace("\n", " ")[:140]
        print(f"    {preview}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and dispatch."""
    parser = argparse.ArgumentParser(description="Prospectus retrieval")
    sub = parser.add_subparsers(dest="command", required=True)

    embed_p = sub.add_parser("embed", help="Embed chunks and load into pgvector")
    embed_p.add_argument("--chunks-dir", default=None)
    embed_p.add_argument("--batch-size", type=int, default=64)
    embed_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap for smoke tests",
    )
    embed_p.set_defaults(func=_cmd_embed)

    search_p = sub.add_parser("search", help="Retrieve top-k chunks for a query")
    search_p.add_argument("query", help="Natural-language query")
    search_p.add_argument(
        "--strategy",
        default="dense",
        choices=["dense", "keyword", "hybrid", "hybrid_rerank"],
        help="Retrieval strategy parameter",
    )
    search_p.add_argument(
        "--k",
        type=int,
        default=None,
        help="Top-k results (default 10, or 8 for hybrid_rerank)",
    )
    search_p.add_argument(
        "--candidate-depth",
        type=int,
        default=50,
        help="Wide retrieve depth before fusion/rerank (try 20 vs 50)",
    )
    search_p.set_defaults(func=_cmd_search)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
