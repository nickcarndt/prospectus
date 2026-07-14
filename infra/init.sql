-- Enable pgvector for dense embedding storage (Phase 3+).
-- Keyword/FTS uses built-in Postgres tsvector — no extension required.
CREATE EXTENSION IF NOT EXISTS vector;
