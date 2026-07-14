"""Load the labeled eval set from data/eval/cases.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES_PATH = REPO_ROOT / "data" / "eval" / "cases.jsonl"


class EvalCase(BaseModel):
    """One labeled question with a gold source section."""

    id: str
    query: str
    gold_ticker: str
    gold_form_type: str
    gold_section_id: str
    gold_section_title: str
    gold_chunk_id: str
    gold_filing_date: str
    gold_accession_number: str
    gold_phrase: str = Field(
        ...,
        description="Phrase known to appear in the gold chunk (for debugging).",
    )


def load_eval_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    """Load eval cases from JSONL."""
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(EvalCase.model_validate_json(line))
    return cases


def cases_as_braintrust_rows(cases: list[EvalCase]) -> list[dict[str, Any]]:
    """Shape cases for Braintrust Eval(data=...)."""
    rows: list[dict[str, Any]] = []
    for case in cases:
        rows.append(
            {
                "input": case.query,
                "expected": {
                    "gold_ticker": case.gold_ticker,
                    "gold_section_id": case.gold_section_id,
                    "gold_chunk_id": case.gold_chunk_id,
                    "gold_section_title": case.gold_section_title,
                },
                "metadata": {"case_id": case.id, "form_type": case.gold_form_type},
            }
        )
    return rows
