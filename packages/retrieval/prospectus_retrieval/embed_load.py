"""Load chunk JSONL from disk, embed with OpenAI, upsert into Postgres."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from prospectus_shared import Chunk

from prospectus_retrieval.db import connect
from prospectus_retrieval.embeddings import Embedder

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHUNKS_DIR = REPO_ROOT / "data" / "chunks"

_UPSERT_SQL = """
INSERT INTO chunks (
    chunk_id, text, token_count, ticker, cik, company_name, form_type,
    filing_date, accession_number, source_url, section_id, section_title,
    chunk_index, embedding, embedded_at
) VALUES (
    %(chunk_id)s, %(text)s, %(token_count)s, %(ticker)s, %(cik)s,
    %(company_name)s, %(form_type)s, %(filing_date)s, %(accession_number)s,
    %(source_url)s, %(section_id)s, %(section_title)s, %(chunk_index)s,
    %(embedding)s, %(embedded_at)s
)
ON CONFLICT (chunk_id) DO UPDATE SET
    text = EXCLUDED.text,
    token_count = EXCLUDED.token_count,
    ticker = EXCLUDED.ticker,
    cik = EXCLUDED.cik,
    company_name = EXCLUDED.company_name,
    form_type = EXCLUDED.form_type,
    filing_date = EXCLUDED.filing_date,
    accession_number = EXCLUDED.accession_number,
    source_url = EXCLUDED.source_url,
    section_id = EXCLUDED.section_id,
    section_title = EXCLUDED.section_title,
    chunk_index = EXCLUDED.chunk_index,
    embedding = EXCLUDED.embedding,
    embedded_at = EXCLUDED.embedded_at
"""


def load_chunks_from_jsonl(chunks_dir: Path = DEFAULT_CHUNKS_DIR) -> list[Chunk]:
    """Read all chunk JSONL files under data/chunks."""
    chunks: list[Chunk] = []
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chunks.append(Chunk.model_validate_json(line))
    return chunks


def embed_and_upsert(
    chunks: list[Chunk],
    *,
    embedder: Embedder | None = None,
    batch_size: int = 64,
) -> int:
    """Embed chunks in batches and upsert rows into Postgres.

    Args:
        chunks: Chunk models from Phase 2.
        embedder: Optional shared Embedder.
        batch_size: Texts per OpenAI embeddings request.

    Returns:
        Number of chunks upserted.
    """
    if not chunks:
        return 0

    client = embedder or Embedder()
    now = datetime.now(timezone.utc)

    with connect() as conn:
        with conn.cursor() as cur:
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                vectors = client.embed_texts([c.text for c in batch])
                for chunk, vector in zip(batch, vectors, strict=True):
                    cur.execute(
                        _UPSERT_SQL,
                        {
                            "chunk_id": chunk.chunk_id,
                            "text": chunk.text,
                            "token_count": chunk.token_count,
                            "ticker": chunk.ticker,
                            "cik": chunk.cik,
                            "company_name": chunk.company_name,
                            "form_type": chunk.form_type,
                            "filing_date": chunk.filing_date,
                            "accession_number": chunk.accession_number,
                            "source_url": chunk.source_url,
                            "section_id": chunk.section_id,
                            "section_title": chunk.section_title,
                            "chunk_index": chunk.chunk_index,
                            "embedding": vector,
                            "embedded_at": now,
                        },
                    )
    return len(chunks)


def embed_corpus(
    *,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    batch_size: int = 64,
    limit: int | None = None,
) -> int:
    """Load JSONL chunks from disk, embed, and store in pgvector.

    Args:
        chunks_dir: Directory of `*.jsonl` chunk files.
        batch_size: OpenAI batch size.
        limit: Optional max chunks (smoke tests).

    Returns:
        Number of chunks upserted.
    """
    chunks = load_chunks_from_jsonl(chunks_dir)
    if limit is not None:
        chunks = chunks[:limit]
    return embed_and_upsert(chunks, batch_size=batch_size)
