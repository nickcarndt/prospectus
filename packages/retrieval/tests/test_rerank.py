"""Unit tests for Cohere rerank stage with a fake client (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from prospectus_retrieval.rerank import Reranker

from tests.helpers import make_chunk


class _FakeRerankResponse:
    """Minimal Cohere-shaped rerank response."""

    def __init__(self, results: list[Any]) -> None:
        self.results = results


class _FakeCohereClient:
    """Records calls and returns a fixed permutation of document indices."""

    def __init__(self, order: list[int]) -> None:
        self.order = order
        self.last_call: dict[str, Any] | None = None

    def rerank(self, **kwargs: Any) -> _FakeRerankResponse:
        self.last_call = kwargs
        top_n = kwargs["top_n"]
        results = [
            SimpleNamespace(index=i, relevance_score=1.0 - 0.1 * rank)
            for rank, i in enumerate(self.order[:top_n])
        ]
        return _FakeRerankResponse(results)


def test_rerank_reorders_by_client_indices() -> None:
    """Reranker must map Cohere indices back onto the original Chunk objects."""
    chunks = [make_chunk("c0"), make_chunk("c1"), make_chunk("c2")]
    reranker = Reranker.__new__(Reranker)
    fake = _FakeCohereClient(order=[2, 0, 1])
    reranker._client = fake  # noqa: SLF001 — intentional inject for unit test
    reranker.model = "rerank-english-v3.0"

    out, scores = reranker.rerank("CoWoS", chunks, top_n=2)

    assert [c.chunk_id for c in out] == ["c2", "c0"]
    assert scores[0] > scores[1]
    assert fake.last_call is not None
    assert fake.last_call["top_n"] == 2
    assert fake.last_call["documents"] == [c.text for c in chunks]


def test_rerank_empty_candidates() -> None:
    reranker = Reranker.__new__(Reranker)
    reranker._client = _FakeCohereClient(order=[])  # noqa: SLF001
    reranker.model = "rerank-english-v3.0"
    out, scores = reranker.rerank("q", [], top_n=5)
    assert out == []
    assert scores == []


def test_rerank_rejects_invalid_top_n() -> None:
    reranker = Reranker.__new__(Reranker)
    reranker._client = _FakeCohereClient(order=[0])  # noqa: SLF001
    reranker.model = "rerank-english-v3.0"
    with pytest.raises(ValueError, match="top_n"):
        reranker.rerank("q", [make_chunk("a")], top_n=0)


def test_reranker_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="COHERE_API_KEY"):
        Reranker(api_key=None)
