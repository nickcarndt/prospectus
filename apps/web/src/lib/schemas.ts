import { z } from "zod";

/** Closed set of eval strategies exposed to the UI. */
export const strategySchema = z.enum(["dense", "hybrid", "hybrid_rerank"]);

export const chunkSchema = z.object({
  chunk_id: z.string().min(1),
  text: z.string().min(1),
  token_count: z.number().int().positive(),
  ticker: z.string().min(1),
  cik: z.string().min(1),
  company_name: z.string().min(1),
  form_type: z.enum(["10-K", "10-Q"]),
  filing_date: z.string().min(1),
  accession_number: z.string().min(1),
  source_url: z.string().min(1),
  section_id: z.string().min(1),
  section_title: z.string().min(1),
  chunk_index: z.number().int().nonnegative(),
});

export const citationSchema = z.object({
  citation_id: z.string().min(1),
  chunk_id: z.string().min(1),
  ticker: z.string().min(1),
  form_type: z.enum(["10-K", "10-Q"]),
  filing_date: z.string().min(1),
  section_id: z.string().min(1),
  section_title: z.string().min(1),
  excerpt: z.string().min(1),
  source_url: z.string().min(1),
});

export const retrievalResultSchema = z.object({
  query: z.string().min(1),
  strategy: strategySchema,
  chunks: z.array(chunkSchema),
  scores: z.array(z.number()),
  latency_ms: z.number().nonnegative().nullable(),
});

export const queryResponseSchema = z.object({
  query: z.string().min(1),
  strategy: strategySchema,
  answer_text: z.string(),
  citations: z.array(citationSchema),
  confidence: z.number().min(0).max(1),
  abstained: z.boolean(),
  retrieval: retrievalResultSchema.nullable(),
  latency_ms: z.number().nonnegative().nullable(),
  generate: z.boolean(),
  error: z.string().nullable(),
  per_ip_remaining: z.number().int().nonnegative().optional(),
  global_remaining: z.number().int().nonnegative().optional(),
});

export const reserveResponseSchema = z.object({
  allowed: z.boolean(),
  reason: z.string().nullable().optional(),
  per_ip_remaining: z.number().int().nonnegative(),
  global_remaining: z.number().int().nonnegative(),
});

export const queryRequestSchema = z.object({
  query: z.string().trim().min(1).max(4000),
  strategy: strategySchema,
  top_k: z.number().int().min(1).max(20).optional(),
  candidate_depth: z.number().int().min(5).max(50).optional(),
  generate: z.boolean().optional(),
});

/**
 * Public API base URL — fail loudly if unset (no silent localhost in prod builds).
 */
export function requireApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw == null || raw.trim() === "") {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Add it to apps/web/.env.local (or Vercel env)."
    );
  }
  return raw.replace(/\/$/, "");
}
