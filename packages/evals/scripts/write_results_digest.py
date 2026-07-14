"""Write a committed SHA-256 digest of an eval results JSON.

The full artifact under data/eval/results/ stays gitignored (large). The digest
at data/eval/RESULTS_DIGEST.json is committed so every number on the site maps
to a verifiable artifact hash + aggregate snapshot.

Usage (repo root, venv active):
  PYTHONPATH=packages/evals python packages/evals/scripts/write_results_digest.py \\
    data/eval/results/latest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "data" / "eval" / "RESULTS_DIGEST.json"
CASES_PATH = REPO_ROOT / "data" / "eval" / "cases.jsonl"


def _sha256_file(path: Path) -> str:
    """Return hex SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aggregates(summary: dict[str, Any]) -> dict[str, Any]:
    """Pull the metrics that appear on EVAL_REPORT / the eval page.

    Works for full e2e JSON and retrieval-only JSON (cite/faith may be absent).
    """
    out: dict[str, Any] = {}
    for name, payload in summary.get("strategies", {}).items():
        agg = payload["aggregate"]
        row: dict[str, Any] = {
            "n": agg["n"],
            "recall_at_5": agg["recall_at_5"],
            "recall_at_10": agg["recall_at_10"],
            "mrr": agg["mrr"],
            "latency_ms_p95": agg["latency_ms_p95"],
            "cost_usd_mean": agg["cost_usd_mean"],
        }
        if "citation_accuracy" in agg:
            row["citation_accuracy"] = agg["citation_accuracy"]
        if "faithfulness" in agg:
            row["faithfulness"] = agg["faithfulness"]
        out[name] = row
    return out


def build_digest(results_path: Path) -> dict[str, Any]:
    """Build the committed digest document for one results file."""
    summary = json.loads(results_path.read_text(encoding="utf-8"))
    try:
        rel_results = str(results_path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel_results = str(results_path)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": {
            "path": "data/eval/cases.jsonl",
            "sha256": _sha256_file(CASES_PATH),
            "n": sum(1 for _ in CASES_PATH.open(encoding="utf-8") if _.strip()),
        },
        "results": {
            "path": rel_results,
            "sha256": _sha256_file(results_path),
            "bytes": results_path.stat().st_size,
            "run_id": summary.get("run_id"),
            "case_count": summary.get("case_count"),
            "candidate_depth": summary.get("candidate_depth"),
        },
        "aggregates": _aggregates(summary),
        "verify": (
            "sha256sum <results.path> must equal results.sha256; "
            "aggregates must match EVAL_REPORT.md / phase8_report_source.json"
        ),
    }


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results",
        type=Path,
        help="Path to full eval JSON (e.g. data/eval/results/latest.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Digest output path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()
    results_path = args.results
    if not results_path.is_absolute():
        results_path = REPO_ROOT / results_path
    if not results_path.is_file():
        raise SystemExit(f"Results file not found: {results_path}")

    digest = build_digest(results_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(digest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"results.sha256={digest['results']['sha256']}")
    print(f"cases.sha256={digest['cases']['sha256']}")


if __name__ == "__main__":
    main()
