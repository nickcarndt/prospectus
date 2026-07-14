import {
  queryRequestSchema,
  queryResponseSchema,
  requireApiBaseUrl,
} from "@/lib/schemas";
import type { QueryRequest, QueryResponse } from "@/lib/types";

export { STRATEGY_LABELS, STRATEGY_META } from "@/lib/strategies";

/**
 * POST /query — full answer or retrieve-only (generate: false).
 * Validates both the outbound body and the inbound JSON payload.
 */
export async function postQuery(body: QueryRequest): Promise<QueryResponse> {
  const parsed = queryRequestSchema.parse(body);
  const res = await fetch(`${requireApiBaseUrl()}/query`, {
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
  const json: unknown = await res.json();
  return queryResponseSchema.parse(json);
}
