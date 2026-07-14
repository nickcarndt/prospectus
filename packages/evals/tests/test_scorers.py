"""Unit tests for recall@k, MRR, and citation accuracy (no LLM judge)."""

from __future__ import annotations

from datetime import date

import pytest

from prospectus_evals.scorers import (
    citation_accuracy,
    first_gold_rank,
    is_gold_hit,
    mean_reciprocal_rank,
    recall_at_k,
)
from prospectus_shared import Citation

from tests.helpers import make_answer, make_chunk


def test_is_gold_hit_section_level() -> None:
    chunk = make_chunk("x", ticker="NVDA", section_id="item_1a")
    assert is_gold_hit(chunk, gold_ticker="nvda", gold_section_id="item_1a")
    assert not is_gold_hit(chunk, gold_ticker="NVDA", gold_section_id="item_7")


def test_is_gold_hit_exact_chunk_id() -> None:
    chunk = make_chunk("gold-id", section_id="other")
    assert is_gold_hit(
        chunk,
        gold_ticker="AMD",
        gold_section_id="item_1a",
        gold_chunk_id="gold-id",
    )


def test_recall_at_k_binary() -> None:
    """Gold in top-5 → R@5=1; gold only at rank 7 → R@5=0, R@10=1."""
    distractors = [
        make_chunk(f"d{i}", ticker="MSFT", section_id="item_1a") for i in range(6)
    ]
    gold = make_chunk("g", ticker="NVDA", section_id="item_1_business")
    ranked = distractors + [gold]

    assert recall_at_k(
        ranked,
        gold_ticker="NVDA",
        gold_section_id="item_1_business",
        k=5,
    ) == 0.0
    assert recall_at_k(
        ranked,
        gold_ticker="NVDA",
        gold_section_id="item_1_business",
        k=10,
    ) == 1.0


def test_recall_at_5_equals_10_when_hit_is_early() -> None:
    """Corpus artifact case: early hit → R@5 == R@10 == 1.0."""
    ranked = [
        make_chunk("g", ticker="NVDA", section_id="item_1_business"),
        make_chunk("d", ticker="MSFT", section_id="item_1a"),
    ]
    kwargs = dict(gold_ticker="NVDA", gold_section_id="item_1_business")
    assert recall_at_k(ranked, k=5, **kwargs) == recall_at_k(ranked, k=10, **kwargs)


def test_mrr_is_reciprocal_of_first_hit() -> None:
    ranked = [
        make_chunk("d0", ticker="MSFT", section_id="item_1a"),
        make_chunk("d1", ticker="MSFT", section_id="item_1a"),
        make_chunk("g", ticker="NVDA", section_id="item_1_business"),
    ]
    assert mean_reciprocal_rank(
        ranked,
        gold_ticker="NVDA",
        gold_section_id="item_1_business",
    ) == pytest.approx(1.0 / 3.0)
    assert first_gold_rank(
        ranked,
        gold_ticker="NVDA",
        gold_section_id="item_1_business",
    ) == 3


def test_mrr_zero_when_missing() -> None:
    ranked = [make_chunk("d", ticker="MSFT", section_id="item_1a")]
    assert (
        mean_reciprocal_rank(
            ranked,
            gold_ticker="NVDA",
            gold_section_id="item_1_business",
        )
        == 0.0
    )


def test_citation_accuracy_requires_excerpt_in_chunk() -> None:
    chunk = make_chunk(
        "c",
        text="NVIDIA uses CoWoS packaging for AI accelerators in production.",
    )
    good = Citation(
        citation_id="c1",
        chunk_id="c",
        ticker="NVDA",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        section_id="item_1_business",
        section_title="Item 1. Business",
        excerpt="CoWoS packaging for AI",
        source_url="https://example.com",
    )
    bad = Citation(
        citation_id="c2",
        chunk_id="c",
        ticker="NVDA",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        section_id="item_1_business",
        section_title="Item 1. Business",
        excerpt="hallucinated revenue figure xyz",
        source_url="https://example.com",
    )
    answer = make_answer(citations=[good, bad], chunks=[chunk])
    assert citation_accuracy(answer) == pytest.approx(0.5)


def test_citation_accuracy_abstain_with_no_cites() -> None:
    answer = make_answer(
        citations=[],
        chunks=[],
        abstained=True,
        answer_text="Insufficient evidence in the retrieved filings.",
    )
    assert citation_accuracy(answer) == 1.0
