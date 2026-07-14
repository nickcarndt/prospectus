-- Phase 4: Postgres full-text search for keyword retrieval.
-- Safe to re-run. Does NOT drop chunks (preserves embeddings).

-- Weighted document: ticker boosted (A) so exact issuer matches rank high;
-- section title (B); body text (C).
ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS tsv tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(ticker, '')), 'A')
        || setweight(to_tsvector('english', coalesce(section_title, '')), 'B')
        || setweight(to_tsvector('english', coalesce(text, '')), 'C')
    ) STORED;

CREATE INDEX IF NOT EXISTS chunks_tsv_gin_idx ON chunks USING gin (tsv);
