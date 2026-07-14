"""Shared schema invariants — citation rule is architectural, not optional."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from prospectus_shared import Answer, Citation, RetrievalStrategy


def test_non_abstained_answer_requires_citations() -> None:
    with pytest.raises(ValidationError, match="Citation"):
        Answer(
            query="q",
            strategy=RetrievalStrategy.DENSE,
            answer_text="Something without cites.",
            citations=[],
            confidence=0.9,
            abstained=False,
        )


def test_abstained_answer_may_omit_citations() -> None:
    answer = Answer(
        query="q",
        strategy=RetrievalStrategy.DENSE,
        answer_text="Insufficient evidence.",
        citations=[],
        confidence=0.0,
        abstained=True,
    )
    assert answer.abstained is True


def test_citation_round_trip() -> None:
    cite = Citation(
        citation_id="c1",
        chunk_id="chunk-1",
        ticker="NVDA",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        section_id="item_1a",
        section_title="Item 1A",
        excerpt="Risk factors include supply constraints.",
        source_url="https://example.com",
    )
    assert cite.model_dump()["ticker"] == "NVDA"
