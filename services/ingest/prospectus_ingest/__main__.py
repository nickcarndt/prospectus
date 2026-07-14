"""CLI entrypoints for the ingest pipeline.

Usage:
  python -m prospectus_ingest fetch
  python -m prospectus_ingest extract
  python -m prospectus_ingest chunk
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Repo root .env (SEC_USER_AGENT, etc.)
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _cmd_fetch(args: argparse.Namespace) -> int:
    """Download filings for the configured ticker universe."""
    from prospectus_ingest.companies import TICKERS
    from prospectus_ingest.fetch import DEFAULT_OUT_DIR, fetch_filings

    tickers = tuple(t.upper() for t in args.tickers) if args.tickers else TICKERS
    refs = fetch_filings(
        tickers=tickers,
        out_dir=Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR,
        per_form=args.per_form,
    )
    print(f"Fetched {len(refs)} filings → {args.out_dir or DEFAULT_OUT_DIR}")
    for ref in refs:
        print(
            f"  {ref.ticker:5} {ref.form_type:4} {ref.filing_date}  "
            f"{ref.accession_number}"
        )
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    """Extract plain text + tables from downloaded filings."""
    from prospectus_ingest.extract import extract_all
    from prospectus_ingest.fetch import DEFAULT_OUT_DIR

    filings_dir = Path(args.filings_dir) if args.filings_dir else DEFAULT_OUT_DIR
    results = extract_all(filings_dir=filings_dir)
    total_tables = sum(r.table_count for r in results)
    print(f"Extracted {len(results)} filings ({total_tables} tables)")
    for r in results[:5]:
        print(
            f"  {r.ticker:5} {r.form_type:4}  chars={r.char_count:,}  "
            f"tables={r.table_count}"
        )
    if len(results) > 5:
        print(f"  ... +{len(results) - 5} more")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and run the selected ingest command."""
    parser = argparse.ArgumentParser(description="Prospectus SEC ingest")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_p = sub.add_parser("fetch", help="Download 10-K/10-Q filings from EDGAR")
    fetch_p.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: data/filings)",
    )
    fetch_p.add_argument(
        "--per-form",
        type=int,
        default=1,
        help="Newest filings to keep per form type (default: 1)",
    )
    fetch_p.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Subset of tickers (default: full 15-company universe)",
    )
    fetch_p.set_defaults(func=_cmd_fetch)

    extract_p = sub.add_parser(
        "extract", help="Extract text and tables from downloaded filings"
    )
    extract_p.add_argument(
        "--filings-dir",
        default=None,
        help="Filings root (default: data/filings)",
    )
    extract_p.set_defaults(func=_cmd_extract)

    chunk_p = sub.add_parser(
        "chunk", help="Structure-aware chunk extracted filings (256–512 tokens)"
    )
    chunk_p.add_argument(
        "--filings-dir",
        default=None,
        help="Filings root (default: data/filings)",
    )
    chunk_p.add_argument(
        "--out-dir",
        default=None,
        help="Chunk JSONL output directory (default: data/chunks)",
    )
    chunk_p.set_defaults(func=_cmd_chunk)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _cmd_chunk(args: argparse.Namespace) -> int:
    """Chunk extracted filings into citation-ready Chunk records."""
    from collections import Counter

    from prospectus_ingest.chunk import chunk_all
    from prospectus_ingest.fetch import DEFAULT_OUT_DIR, REPO_ROOT

    filings_dir = Path(args.filings_dir) if args.filings_dir else DEFAULT_OUT_DIR
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "data" / "chunks"
    chunks = chunk_all(filings_dir=filings_dir, out_dir=out_dir)
    sections = Counter(c.section_id for c in chunks)
    tokens = [c.token_count for c in chunks]
    print(f"Wrote {len(chunks)} chunks → {out_dir}")
    if tokens:
        print(
            f"  tokens: min={min(tokens)} median={sorted(tokens)[len(tokens)//2]} "
            f"max={max(tokens)}"
        )
    print(f"  top sections: {sections.most_common(8)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
