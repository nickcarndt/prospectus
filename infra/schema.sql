-- Prospectus Phase 3: chunk storage + dense vectors
-- Apply with: ./infra/apply_schema.sh
-- (Safe to re-run for indexes; DROP/CREATE used when changing embedding dim.)

CREATE EXTENSION IF NOT EXISTS vector;

-- text-embedding-3-large supports Matryoshka dims. We store 1536 because
-- pgvector HNSW indexes reject vectors with more than 2000 dimensions.
-- Still the *large* model — just a shorter projection of the same embedding.
DROP TABLE IF EXISTS chunks;

CREATE TABLE chunks (
    chunk_id          TEXT PRIMARY KEY,
    text              TEXT NOT NULL,
    token_count       INTEGER NOT NULL CHECK (token_count >= 1),
    ticker            TEXT NOT NULL,
    cik               TEXT NOT NULL,
    company_name      TEXT NOT NULL,
    form_type         TEXT NOT NULL CHECK (form_type IN ('10-K', '10-Q')),
    filing_date       DATE NOT NULL,
    accession_number  TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    section_id        TEXT NOT NULL,
    section_title     TEXT NOT NULL,
    chunk_index       INTEGER NOT NULL CHECK (chunk_index >= 0),
    embedding         vector(1536),
    embedded_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cosine distance (<=>). HNSW is the ANN index for dense top-k.
CREATE INDEX chunks_embedding_hnsw_cosine_idx
    ON chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX chunks_ticker_idx ON chunks (ticker);
CREATE INDEX chunks_section_id_idx ON chunks (section_id);
