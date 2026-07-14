"""Dense retrieval: embed query → cosine top-k over pgvector.

Independently testable: call `dense_retrieve(query, top_k=...)` with no
dependency on hybrid/rerank stages.
"""

from __future__ import annotations

import time

from pgvector import Vector
from prospectus_shared import RetrievalResult, RetrievalStrategy

from prospectus_retrieval.chunk_rows import row_to_chunk
from prospectus_retrieval.db import connect
from prospectus_retrieval.embeddings import Embedder

# pgvector cosine distance: smaller <=> is closer.
# Convert to a similarity score in [0, 1] style for display/evals: 1 - distance.
_DENSE_SQL = """
SELECT
    chunk_id,
    text,
    token_count,
    ticker,
    cik,
    company_name,
    form_type,
    filing_date,
    accession_number,
    source_url,
    section_id,
    section_title,
    chunk_index,
    embedding <=> %(query_embedding)s AS distance
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> %(query_embedding)s
LIMIT %(top_k)s
"""


def dense_retrieve(
    query: str,
    *,
    top_k: int = 10,
    embedder: Embedder | None = None,
) -> RetrievalResult:
    """Retrieve the top-k chunks by embedding cosine similarity.

    Args:
        query: Natural-language question.
        top_k: Number of neighbors to return.
        embedder: Optional shared Embedder (injectable for tests).

    Returns:
        RetrievalResult with strategy=DENSE, chunks and similarity scores.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    started = time.perf_counter()
    client = embedder or Embedder()
    query_embedding = client.embed_query(query)

    chunks = []
    scores: list[float] = []

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _DENSE_SQL,
                {
                    "query_embedding": Vector(query_embedding),
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()

    for row in rows:
        *chunk_cols, distance = row
        chunks.append(row_to_chunk(chunk_cols))
        # Cosine distance → similarity for display/evals.
        scores.append(1.0 - float(distance))

    latency_ms = (time.perf_counter() - started) * 1000.0
    return RetrievalResult(
        query=query,
        strategy=RetrievalStrategy.DENSE,
        chunks=chunks,
        scores=scores,
        latency_ms=latency_ms,
    )
