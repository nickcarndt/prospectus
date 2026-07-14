/**
 * Shared API types mirroring services/api QueryResponse / Prospectus schemas.
 */

export type RetrievalStrategy = "dense" | "hybrid" | "hybrid_rerank";

export type Chunk = {
  chunk_id: string;
  text: string;
  token_count: number;
  ticker: string;
  cik: string;
  company_name: string;
  form_type: "10-K" | "10-Q";
  filing_date: string;
  accession_number: string;
  source_url: string;
  section_id: string;
  section_title: string;
  chunk_index: number;
};

export type Citation = {
  citation_id: string;
  chunk_id: string;
  ticker: string;
  form_type: "10-K" | "10-Q";
  filing_date: string;
  section_id: string;
  section_title: string;
  excerpt: string;
  source_url: string;
};

export type RetrievalResult = {
  query: string;
  strategy: RetrievalStrategy;
  chunks: Chunk[];
  scores: number[];
  latency_ms: number | null;
};

export type QueryResponse = {
  query: string;
  strategy: RetrievalStrategy;
  answer_text: string;
  citations: Citation[];
  confidence: number;
  abstained: boolean;
  retrieval: RetrievalResult | null;
  latency_ms: number | null;
  generate: boolean;
  error: string | null;
  /** Remaining Claude generations for this visitor today (from API). */
  per_ip_remaining?: number;
  /** Remaining shared demo generations today (from API). */
  global_remaining?: number;
};

export type QueryRequest = {
  query: string;
  strategy: RetrievalStrategy;
  top_k?: number;
  candidate_depth?: number;
  generate?: boolean;
};
