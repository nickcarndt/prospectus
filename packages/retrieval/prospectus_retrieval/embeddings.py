"""OpenAI embedding client for Prospectus.

Model: text-embedding-3-large at 1536 dimensions (Matryoshka truncation so
vectors fit pgvector's HNSW limit of 2000 dims while keeping the large model).
"""

from __future__ import annotations

import os
from typing import Sequence

from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 1536


class Embedder:
    """Thin wrapper around OpenAI embeddings.create."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = EMBEDDING_MODEL,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        """Create an embedder.

        Args:
            api_key: OpenAI key; defaults to OPENAI_API_KEY.
            model: Embedding model id.
            dimensions: Output dimensionality (Matryoshka for -3-large).
        """
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY is required. Set it in the environment or .env."
            )
        self._client = OpenAI(api_key=key)
        self.model = model
        self.dimensions = dimensions

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed one or more texts; returns vectors aligned with inputs.

        Args:
            texts: Non-empty strings to embed.

        Returns:
            List of embedding vectors (each length `dimensions`).
        """
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self.model,
            input=list(texts),
            dimensions=self.dimensions,
        )
        # API may not preserve order in theory; sort by index to be safe.
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def embed_query(self, query: str) -> list[float]:
        """Embed a single retrieval query."""
        vectors = self.embed_texts([query])
        return vectors[0]
