"""End-to-end: retrieve → generate (structured) → ground → Answer."""

from __future__ import annotations

import anthropic
from prospectus_retrieval.embeddings import Embedder
from prospectus_retrieval.hybrid import DEFAULT_CANDIDATE_DEPTH
from prospectus_retrieval.rerank import Reranker
from prospectus_retrieval.retrieve import retrieve
from prospectus_shared import Answer, RetrievalStrategy

from prospectus_generation.generate import generate_from_retrieval
from prospectus_generation.grounding import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    ground_structured_output,
)


def answer_query(
    query: str,
    *,
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID_RERANK,
    top_k: int | None = None,
    candidate_depth: int = DEFAULT_CANDIDATE_DEPTH,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    model: str | None = None,
    max_tokens: int | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    client: anthropic.Anthropic | None = None,
) -> Answer:
    """Answer a question with cited, grounded generation (or abstain).

    Args:
        query: User research question.
        strategy: Retrieval strategy parameter.
        top_k: Retrieval depth into the generator (defaults per strategy).
        candidate_depth: Wide retrieve depth for hybrid / hybrid_rerank.
        confidence_threshold: Below this → abstain.
        model: Claude model id (else ANTHROPIC_MODEL / default).
        max_tokens: Generation cap (else ANTHROPIC_MAX_TOKENS / default).
        embedder / reranker / client: Optional injected clients for tests.

    Returns:
        Answer with citations, or abstained insufficient-evidence Answer.
    """
    retrieval = retrieve(
        query,
        strategy=strategy,
        top_k=top_k,
        candidate_depth=candidate_depth,
        embedder=embedder,
        reranker=reranker,
    )
    structured = generate_from_retrieval(
        retrieval, model=model, max_tokens=max_tokens, client=client
    )
    return ground_structured_output(
        structured,
        query=query,
        strategy=strategy,
        evidence=retrieval.chunks,
        retrieval=retrieval,
        confidence_threshold=confidence_threshold,
    )
