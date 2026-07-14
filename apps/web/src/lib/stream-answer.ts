import {
  queryResponseSchema,
  requireApiBaseUrl,
  reserveResponseSchema,
} from "@/lib/schemas";
import type { QueryResponse, RetrievalResult, RetrievalStrategy } from "@/lib/types";
import type { StructuredGenerationPayload } from "@/lib/structured-generation";

export type StreamAnswerHandlers = {
  onPartial?: (partial: Partial<StructuredGenerationPayload>) => void;
  onBudget?: (remaining: {
    per_ip_remaining: number;
    global_remaining: number;
  }) => void;
};

/**
 * Reserve budget on FastAPI (visitor IP), then stream StructuredGeneration
 * through the Next.js AI SDK route and return the grounded QueryResponse.
 */
export async function streamCitedAnswer(args: {
  query: string;
  strategy: RetrievalStrategy;
  retrieval: RetrievalResult;
  apiBaseUrl: string;
  handlers?: StreamAnswerHandlers;
}): Promise<QueryResponse> {
  const reserveRes = await fetch(`${args.apiBaseUrl}/generate/reserve`, {
    method: "POST",
  });
  if (!reserveRes.ok) {
    throw new Error(`Budget reserve failed (${reserveRes.status})`);
  }
  const reserve = reserveResponseSchema.parse(await reserveRes.json());
  args.handlers?.onBudget?.({
    per_ip_remaining: reserve.per_ip_remaining,
    global_remaining: reserve.global_remaining,
  });
  if (!reserve.allowed) {
    throw new Error(
      reserve.reason ??
        "Daily generation budget reached. Retrieval still works."
    );
  }

  const res = await fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: args.query,
      strategy: args.strategy,
      retrieval: args.retrieval,
    }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = (await res.json()) as { error?: string };
      if (payload.error) detail = payload.error;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Stream failed (${res.status})`);
  }
  if (!res.body) {
    throw new Error("Stream response had no body");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalAnswer: QueryResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const event = JSON.parse(trimmed) as {
        type: string;
        data: unknown;
      };
      if (event.type === "partial") {
        args.handlers?.onPartial?.(
          event.data as Partial<StructuredGenerationPayload>
        );
      } else if (event.type === "answer") {
        finalAnswer = queryResponseSchema.parse(event.data);
      } else if (event.type === "error") {
        const data = event.data as { message?: string };
        throw new Error(data.message ?? "Generation failed");
      }
    }
  }

  if (!finalAnswer) {
    throw new Error("Stream ended without a grounded answer");
  }
  return finalAnswer;
}

/** Alias for schemas.requireApiBaseUrl — no silent localhost fallback. */
export function resolveApiBaseUrl(): string {
  return requireApiBaseUrl();
}
