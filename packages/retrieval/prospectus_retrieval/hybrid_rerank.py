"""Hybrid + Cohere rerank: fuse wide, then cross-encode down to top 5–8.

candidate_depth is a parameter (eval will compare 20 vs 50): how many dense
and keyword hits to pull before RRF, and how many fused candidates to feed
the reranker.
"""

from __future__ import annotations

import time

from prospectus_shared import RetrievalResult, RetrievalStrategy

from prospectus_retrieval.dense import dense_retrieve
from prospectus_retrieval.embeddings import Embedder
from prospectus_retrieval.fusion import RRF_K, reciprocal_rank_fusion
from prospectus_retrieval.hybrid import DEFAULT_CANDIDATE_DEPTH
from prospectus_retrieval.keyword import keyword_retrieve
from prospectus_retrieval.rerank import Reranker, rerank_chunks

# Spec: cut reranked results to top 5–8 for generation context.
DEFAULT_RERANK_TOP_N = 8


def hybrid_rerank_retrieve(
    query: str,
    *,
    top_k: int = DEFAULT_RERANK_TOP_N,
    candidate_depth: int = DEFAULT_CANDIDATE_DEPTH,
    rrf_k: int = RRF_K,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
) -> RetrievalResult:
    """Dense + keyword → RRF (wide) → Cohere rerank (narrow).

    Args:
        query: Natural-language question.
        top_k: Final count after rerank (typically 5–8).
        candidate_depth: Per-leg retrieve depth and RRF candidate pool size
            (parameter for 20 vs 50 experiments).
        rrf_k: RRF constant (default 60).
        embedder: Optional shared Embedder.
        reranker: Optional shared Reranker.

    Returns:
        RetrievalResult with strategy=HYBRID_RERANK and Cohere relevance scores.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if candidate_depth < 1:
        raise ValueError("candidate_depth must be >= 1")

    started = time.perf_counter()

    dense = dense_retrieve(query, top_k=candidate_depth, embedder=embedder)
    keyword = keyword_retrieve(query, top_k=candidate_depth)
    fused_chunks, _fused_scores = reciprocal_rank_fusion(
        [dense.chunks, keyword.chunks],
        k=rrf_k,
        top_k=candidate_depth,
    )

    chunks, scores = rerank_chunks(
        query,
        fused_chunks,
        top_n=top_k,
        reranker=reranker,
    )

    latency_ms = (time.perf_counter() - started) * 1000.0
    return RetrievalResult(
        query=query,
        strategy=RetrievalStrategy.HYBRID_RERANK,
        chunks=chunks,
        scores=scores,
        latency_ms=latency_ms,
    )
