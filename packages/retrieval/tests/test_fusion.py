"""Unit tests for Reciprocal Rank Fusion — pure logic, no DB/API."""

from __future__ import annotations

import pytest

from prospectus_retrieval.fusion import RRF_K, reciprocal_rank_fusion

from tests.helpers import make_chunk


def test_rrf_k_is_spec_locked() -> None:
    """Spec / architectural principle: RRF uses k=60."""
    assert RRF_K == 60


def test_rrf_prefers_chunks_appearing_in_both_lists() -> None:
    """A mid-rank hit in both lists beats a #1 that only appears once."""
    a = make_chunk("a")
    b = make_chunk("b")
    c = make_chunk("c")

    # Dense: a > b > c. Keyword: b > c > a. b gets two contributions.
    fused, scores = reciprocal_rank_fusion([[a, b, c], [b, c, a]], k=60)

    assert fused[0].chunk_id == "b"
    assert scores[0] == pytest.approx(1.0 / (60 + 2) + 1.0 / (60 + 1))
    assert len(fused) == 3
    assert len(scores) == 3


def test_rrf_single_list_preserves_order() -> None:
    """One list degenerates to the original ranking (same relative order)."""
    chunks = [make_chunk("x"), make_chunk("y"), make_chunk("z")]
    fused, scores = reciprocal_rank_fusion([chunks], k=60)
    assert [c.chunk_id for c in fused] == ["x", "y", "z"]
    assert scores[0] > scores[1] > scores[2]


def test_rrf_top_k_truncates() -> None:
    fused, scores = reciprocal_rank_fusion(
        [[make_chunk("a"), make_chunk("b"), make_chunk("c")]],
        top_k=2,
    )
    assert [c.chunk_id for c in fused] == ["a", "b"]
    assert len(scores) == 2


def test_rrf_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="k must be"):
        reciprocal_rank_fusion([[make_chunk("a")]], k=0)


def test_rrf_empty_lists() -> None:
    fused, scores = reciprocal_rank_fusion([])
    assert fused == []
    assert scores == []
