"""Keyword retrieval via Postgres full-text search (BM25-style ranking).

Independently testable: call `keyword_retrieve(query, top_k=...)` with no
dependency on dense or fusion.
"""

from __future__ import annotations

import time

from prospectus_shared import RetrievalResult, RetrievalStrategy

from prospectus_retrieval.chunk_rows import row_to_chunk
from prospectus_retrieval.db import connect

_KEYWORD_SQL = """
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
    ts_rank_cd(tsv, query) AS rank
FROM chunks,
     websearch_to_tsquery('english', %(query)s) AS query
WHERE tsv @@ query
ORDER BY rank DESC
LIMIT %(top_k)s
"""


def keyword_retrieve(
    query: str,
    *,
    top_k: int = 10,
) -> RetrievalResult:
    """Retrieve top-k chunks by Postgres full-text relevance.

    Uses `websearch_to_tsquery` so queries can include quoted phrases.
    Ranking is `ts_rank_cd` over a weighted tsvector
    (ticker > section title > body).

    Args:
        query: Natural-language or keyword query.
        top_k: Number of hits to return.

    Returns:
        RetrievalResult with strategy=KEYWORD.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    started = time.perf_counter()
    chunks = []
    scores: list[float] = []

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_KEYWORD_SQL, {"query": query, "top_k": top_k})
            rows = cur.fetchall()

    for row in rows:
        *chunk_cols, rank = row
        chunks.append(row_to_chunk(chunk_cols))
        scores.append(float(rank))

    latency_ms = (time.perf_counter() - started) * 1000.0
    return RetrievalResult(
        query=query,
        strategy=RetrievalStrategy.KEYWORD,
        chunks=chunks,
        scores=scores,
        latency_ms=latency_ms,
    )
