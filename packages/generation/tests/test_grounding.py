"""Unit tests for structural grounding — the interview-critical path."""

from __future__ import annotations

from datetime import date

from prospectus_generation.grounding import (
    excerpt_in_chunk,
    ground_structured_output,
    rewrite_citation_markers,
)
from prospectus_generation.llm_schema import StructuredClaim, StructuredGeneration
from prospectus_shared import Chunk, RetrievalResult, RetrievalStrategy


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        token_count=max(1, len(text.split())),
        ticker="NVDA",
        cik="0001045810",
        company_name="NVIDIA Corp",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        accession_number="0001045810-26-000021",
        source_url="https://example.com",
        section_id="item_1_business",
        section_title="Item 1. Business",
        chunk_index=0,
    )


def test_rewrite_citation_markers_renumbers_after_gap() -> None:
    """When c1 is dropped, body [c2] must become [c1]."""
    assert (
        rewrite_citation_markers("See [c2] and [c3].", {"c2": "c1", "c3": "c2"})
        == "See [c1] and [c2]."
    )


def test_grounding_drops_bad_claim_and_rewrites_markers() -> None:
    """Hallucinated first claim must not leave a dangling [c1] in the answer."""
    good = _chunk(
        "chunk_good",
        "NVIDIA uses CoWoS packaging for advanced AI accelerators in production.",
    )
    evidence = [good]
    retrieval = RetrievalResult(
        query="What is CoWoS?",
        strategy=RetrievalStrategy.HYBRID,
        chunks=evidence,
        scores=[0.9],
    )
    structured = StructuredGeneration(
        abstain=False,
        confidence=0.9,
        answer_text="Wrong [c1]. CoWoS is advanced packaging [c2].",
        claims=[
            StructuredClaim(
                claim_text="Invented claim",
                chunk_id="does_not_exist",
                excerpt="not in any chunk at all here",
            ),
            StructuredClaim(
                claim_text="CoWoS is advanced packaging",
                chunk_id="chunk_good",
                excerpt="CoWoS packaging for advanced AI",
            ),
        ],
    )
    answer = ground_structured_output(
        structured,
        query="What is CoWoS?",
        strategy=RetrievalStrategy.HYBRID,
        evidence=evidence,
        retrieval=retrieval,
    )
    assert not answer.abstained
    assert len(answer.citations) == 1
    assert answer.citations[0].citation_id == "c1"
    assert "[c1]" in answer.answer_text
    assert "[c2]" not in answer.answer_text


def test_excerpt_in_chunk_requires_real_span() -> None:
    assert excerpt_in_chunk("CoWoS packaging", "NVIDIA uses CoWoS packaging today.")
    assert not excerpt_in_chunk("made up excerpt text", "NVIDIA uses CoWoS packaging.")
