"""Hybrid retrieval: dense + keyword fused with Reciprocal Rank Fusion.

Independently callable via `hybrid_retrieve`. Candidate depth defaults to 50
per leg (spec: dense top-50 + keyword top-50), then RRF, then truncate to top_k.
"""

from __future__ import annotations

import time

from prospectus_shared import RetrievalResult, RetrievalStrategy

from prospectus_retrieval.dense import dense_retrieve
from prospectus_retrieval.embeddings import Embedder
from prospectus_retrieval.fusion import RRF_K, reciprocal_rank_fusion
from prospectus_retrieval.keyword import keyword_retrieve

# Spec: retrieve wide, then fuse (rerank in Phase 5 cuts further).
DEFAULT_CANDIDATE_DEPTH = 50


def hybrid_retrieve(
    query: str,
    *,
    top_k: int = 10,
    candidate_depth: int = DEFAULT_CANDIDATE_DEPTH,
    rrf_k: int = RRF_K,
    embedder: Embedder | None = None,
) -> RetrievalResult:
    """Run dense and keyword in parallel depth, fuse with RRF, return top_k.

    Args:
        query: Natural-language question.
        top_k: Final number of chunks to return after fusion.
        candidate_depth: How many hits to pull from each leg before RRF.
        rrf_k: RRF constant (default 60).
        embedder: Optional shared Embedder.

    Returns:
        RetrievalResult with strategy=HYBRID and RRF scores.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if candidate_depth < 1:
        raise ValueError("candidate_depth must be >= 1")

    started = time.perf_counter()

    dense = dense_retrieve(query, top_k=candidate_depth, embedder=embedder)
    keyword = keyword_retrieve(query, top_k=candidate_depth)

    chunks, scores = reciprocal_rank_fusion(
        [dense.chunks, keyword.chunks],
        k=rrf_k,
        top_k=top_k,
    )

    latency_ms = (time.perf_counter() - started) * 1000.0
    return RetrievalResult(
        query=query,
        strategy=RetrievalStrategy.HYBRID,
        chunks=chunks,
        scores=scores,
        latency_ms=latency_ms,
    )
