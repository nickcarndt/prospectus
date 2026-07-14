"""Strategy dispatch tests — strategy is a parameter, not a caller fork."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prospectus_retrieval.retrieve import retrieve
from prospectus_shared import RetrievalResult, RetrievalStrategy

from tests.helpers import make_chunk


def _fake_result(strategy: RetrievalStrategy) -> RetrievalResult:
    return RetrievalResult(
        query="q",
        strategy=strategy,
        chunks=[make_chunk("a")],
        scores=[0.9],
        latency_ms=1.0,
    )


@patch("prospectus_retrieval.retrieve.dense_retrieve")
def test_retrieve_dispatches_dense(mock_dense: MagicMock) -> None:
    mock_dense.return_value = _fake_result(RetrievalStrategy.DENSE)
    result = retrieve("q", strategy=RetrievalStrategy.DENSE, top_k=3)
    mock_dense.assert_called_once()
    assert result.strategy is RetrievalStrategy.DENSE
    assert mock_dense.call_args.kwargs["top_k"] == 3


@patch("prospectus_retrieval.retrieve.keyword_retrieve")
def test_retrieve_dispatches_keyword(mock_kw: MagicMock) -> None:
    mock_kw.return_value = _fake_result(RetrievalStrategy.KEYWORD)
    result = retrieve("q", strategy=RetrievalStrategy.KEYWORD, top_k=5)
    mock_kw.assert_called_once_with("q", top_k=5)
    assert result.strategy is RetrievalStrategy.KEYWORD


@patch("prospectus_retrieval.retrieve.hybrid_retrieve")
def test_retrieve_dispatches_hybrid_with_candidate_depth(
    mock_hybrid: MagicMock,
) -> None:
    mock_hybrid.return_value = _fake_result(RetrievalStrategy.HYBRID)
    retrieve(
        "q",
        strategy=RetrievalStrategy.HYBRID,
        top_k=7,
        candidate_depth=20,
    )
    assert mock_hybrid.call_args.kwargs["candidate_depth"] == 20
    assert mock_hybrid.call_args.kwargs["top_k"] == 7


@patch("prospectus_retrieval.retrieve.hybrid_rerank_retrieve")
def test_retrieve_dispatches_hybrid_rerank(mock_hr: MagicMock) -> None:
    mock_hr.return_value = _fake_result(RetrievalStrategy.HYBRID_RERANK)
    retrieve("q", strategy=RetrievalStrategy.HYBRID_RERANK, candidate_depth=50)
    mock_hr.assert_called_once()
    assert mock_hr.call_args.kwargs["candidate_depth"] == 50


def test_dense_rejects_invalid_top_k() -> None:
    from prospectus_retrieval.dense import dense_retrieve

    with pytest.raises(ValueError, match="top_k"):
        dense_retrieve("q", top_k=0)


def test_keyword_rejects_invalid_top_k() -> None:
    from prospectus_retrieval.keyword import keyword_retrieve

    with pytest.raises(ValueError, match="top_k"):
        keyword_retrieve("q", top_k=0)
