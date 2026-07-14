import { z } from "zod";

import type { QueryRequest, QueryResponse, RetrievalStrategy } from "@/lib/types";

const strategySchema = z.enum(["dense", "hybrid", "hybrid_rerank"]);

export const queryRequestSchema = z.object({
  query: z.string().trim().min(1).max(4000),
  strategy: strategySchema,
  top_k: z.number().int().min(1).max(50).optional(),
  candidate_depth: z.number().int().min(5).max(100).optional(),
  generate: z.boolean().optional(),
});

function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (!base) {
    return "http://localhost:8000";
  }
  return base;
}

/**
 * POST /query — full answer or retrieve-only (generate: false).
 */
export async function postQuery(body: QueryRequest): Promise<QueryResponse> {
  const parsed = queryRequestSchema.parse(body);
  const res = await fetch(`${apiBaseUrl()}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = (await res.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return (await res.json()) as QueryResponse;
}

export const STRATEGY_LABELS: Record<RetrievalStrategy, string> = {
  dense: "Dense",
  hybrid: "Hybrid",
  hybrid_rerank: "Hybrid + rerank",
};
