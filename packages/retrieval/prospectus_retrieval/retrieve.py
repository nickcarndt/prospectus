"""Retrieval entrypoint — strategy is a parameter, not a code path fork in callers.

Callers always use `retrieve(query, strategy=..., candidate_depth=...)`.
"""

from __future__ import annotations

from prospectus_shared import RetrievalResult, RetrievalStrategy

from prospectus_retrieval.dense import dense_retrieve
from prospectus_retrieval.embeddings import Embedder
from prospectus_retrieval.hybrid import DEFAULT_CANDIDATE_DEPTH, hybrid_retrieve
from prospectus_retrieval.hybrid_rerank import (
    DEFAULT_RERANK_TOP_N,
    hybrid_rerank_retrieve,
)
from prospectus_retrieval.keyword import keyword_retrieve
from prospectus_retrieval.rerank import Reranker


def retrieve(
    query: str,
    *,
    strategy: RetrievalStrategy = RetrievalStrategy.DENSE,
    top_k: int | None = None,
    candidate_depth: int = DEFAULT_CANDIDATE_DEPTH,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
) -> RetrievalResult:
    """Run retrieval for the given strategy.

    Args:
        query: Natural-language question.
        strategy: Which config/stage to use.
        top_k: Number of chunks to return. Defaults: 10 for dense/keyword/hybrid,
            8 for hybrid_rerank (spec top 5–8).
        candidate_depth: How wide to retrieve before fusion/rerank (test 20 vs 50).
            Used by hybrid and hybrid_rerank; ignored by dense/keyword stages.
        embedder: Optional shared Embedder for tests / batch runners.
        reranker: Optional shared Reranker for hybrid_rerank.

    Returns:
        Ranked RetrievalResult for the chosen strategy.
    """
    if strategy is RetrievalStrategy.DENSE:
        return dense_retrieve(
            query, top_k=top_k if top_k is not None else 10, embedder=embedder
        )

    if strategy is RetrievalStrategy.KEYWORD:
        return keyword_retrieve(query, top_k=top_k if top_k is not None else 10)

    if strategy is RetrievalStrategy.HYBRID:
        return hybrid_retrieve(
            query,
            top_k=top_k if top_k is not None else 10,
            candidate_depth=candidate_depth,
            embedder=embedder,
        )

    if strategy is RetrievalStrategy.HYBRID_RERANK:
        return hybrid_rerank_retrieve(
            query,
            top_k=top_k if top_k is not None else DEFAULT_RERANK_TOP_N,
            candidate_depth=candidate_depth,
            embedder=embedder,
            reranker=reranker,
        )

    raise ValueError(f"Unknown retrieval strategy: {strategy!r}")
