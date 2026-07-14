"""Shared builders for Prospectus unit tests (no DB / provider calls)."""

from __future__ import annotations

from datetime import date

from prospectus_shared import (
    Answer,
    Citation,
    Chunk,
    RetrievalResult,
    RetrievalStrategy,
)


def make_chunk(
    chunk_id: str,
    *,
    ticker: str = "NVDA",
    section_id: str = "item_1_business",
    text: str | None = None,
) -> Chunk:
    """Build a minimal valid Chunk."""
    body = text or f"Body for {chunk_id}"
    return Chunk(
        chunk_id=chunk_id,
        text=body,
        token_count=max(1, len(body.split())),
        ticker=ticker,
        cik="0001045810",
        company_name="NVIDIA Corp",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        accession_number="0001045810-26-000021",
        source_url="https://example.com/filing",
        section_id=section_id,
        section_title="Item 1. Business",
        chunk_index=0,
    )


def make_answer(
    *,
    citations: list[Citation],
    chunks: list[Chunk],
    abstained: bool = False,
    answer_text: str = "CoWoS is advanced packaging [c1].",
) -> Answer:
    """Answer with an optional retrieval trace for citation_accuracy."""
    retrieval = RetrievalResult(
        query="What is CoWoS?",
        strategy=RetrievalStrategy.HYBRID,
        chunks=chunks,
        scores=[0.9] * len(chunks) if chunks else [],
    )
    return Answer(
        query="What is CoWoS?",
        strategy=RetrievalStrategy.HYBRID,
        answer_text=answer_text,
        citations=citations,
        confidence=0.0 if abstained else 0.8,
        abstained=abstained,
        retrieval=retrieval,
    )
