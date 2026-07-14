"""Cohere cross-encoder reranking stage.

Independently testable: pass any (query, chunks) list — no dense/keyword/DB
required.

Bi-encoder (embeddings): encode query and doc separately, compare vectors —
fast, approximate.
Cross-encoder (reranker): score (query, doc) jointly — slower, more accurate.
That is why we retrieve wide (cheap) then rerank narrow (expensive).
"""

from __future__ import annotations

import os
from typing import Sequence

import cohere

from prospectus_shared import Chunk

# Stable English rerank model; override via Reranker(model=...).
DEFAULT_RERANK_MODEL = "rerank-english-v3.0"


class Reranker:
    """Thin wrapper around Cohere Rerank (cross-encoder)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_RERANK_MODEL,
    ) -> None:
        """Create a reranker.

        Args:
            api_key: Cohere API key; defaults to COHERE_API_KEY.
            model: Cohere rerank model id.
        """
        key = api_key or os.getenv("COHERE_API_KEY")
        if not key:
            raise ValueError(
                "COHERE_API_KEY is required. Set it in the environment or .env."
            )
        self._client = cohere.ClientV2(api_key=key)
        self.model = model

    def rerank(
        self,
        query: str,
        chunks: Sequence[Chunk],
        *,
        top_n: int,
    ) -> tuple[list[Chunk], list[float]]:
        """Rerank chunks for a query; return top_n with relevance scores.

        Args:
            query: Natural-language question.
            chunks: Candidate chunks (typically fused top-`candidate_depth`).
            top_n: How many to keep after reranking (spec: 5–8).

        Returns:
            (chunks, relevance_scores) best-first.
        """
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        if not chunks:
            return [], []

        top_n = min(top_n, len(chunks))
        documents = [chunk.text for chunk in chunks]

        response = self._client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=top_n,
        )

        out_chunks: list[Chunk] = []
        scores: list[float] = []
        for result in response.results:
            out_chunks.append(chunks[result.index])
            scores.append(float(result.relevance_score))
        return out_chunks, scores


def rerank_chunks(
    query: str,
    chunks: Sequence[Chunk],
    *,
    top_n: int = 8,
    reranker: Reranker | None = None,
) -> tuple[list[Chunk], list[float]]:
    """Functional entrypoint for the rerank stage (independently testable)."""
    client = reranker or Reranker()
    return client.rerank(query, chunks, top_n=top_n)
