import { anthropic } from "@ai-sdk/anthropic";
import { streamObject, zodSchema } from "ai";

import { structuredGenerationSchema } from "@/lib/structured-generation";
import type { RetrievalResult, RetrievalStrategy } from "@/lib/types";

export const maxDuration = 60;

type AnswerBody = {
  query: string;
  strategy: RetrievalStrategy;
  retrieval: RetrievalResult;
};

function formatEvidence(retrieval: RetrievalResult): string {
  return retrieval.chunks
    .map((chunk) => {
      const header =
        `chunk_id=${chunk.chunk_id}\n` +
        `ticker=${chunk.ticker} form=${chunk.form_type} ` +
        `filed=${chunk.filing_date} section=${chunk.section_title}`;
      return `---\n${header}\nTEXT:\n${chunk.text}\n`;
    })
    .join("\n");
}

function ndjsonLine(payload: unknown): Uint8Array {
  return new TextEncoder().encode(`${JSON.stringify(payload)}\n`);
}

/**
 * Stream StructuredGeneration with Vercel AI SDK `streamObject`, then ground
 * via FastAPI `/ground`. Emits NDJSON lines:
 *   { type: "partial", data } | { type: "answer", data } | { type: "error", data }
 *
 * Budget reserve is done by the browser against FastAPI first (visitor IP).
 */
export async function POST(req: Request) {
  const body = (await req.json()) as AnswerBody;
  const query = body.query?.trim();
  if (!query) {
    return Response.json({ error: "query is required" }, { status: 400 });
  }
  if (!body.retrieval?.chunks?.length) {
    return Response.json(
      { error: "retrieval with chunks is required" },
      { status: 400 }
    );
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json(
      {
        error:
          "ANTHROPIC_API_KEY is not set on the web server (Vercel/local Next).",
      },
      { status: 503 }
    );
  }

  const apiBase = (
    process.env.PROSPECTUS_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    ""
  ).replace(/\/$/, "");
  if (!apiBase) {
    return Response.json(
      { error: "PROSPECTUS_API_URL or NEXT_PUBLIC_API_URL must be set" },
      { status: 500 }
    );
  }

  const allowedIds = body.retrieval.chunks.map((c) => c.chunk_id);
  const modelId = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-5";
  const maxTokens = Number(process.env.ANTHROPIC_MAX_TOKENS ?? "1024");

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        const result = streamObject({
          model: anthropic(modelId),
          schema: zodSchema(structuredGenerationSchema),
          maxOutputTokens: maxTokens,
          system:
            "You are Prospectus, a research assistant over SEC 10-K/10-Q filings. " +
            "Answer ONLY from the evidence chunks. Every factual claim must cite a " +
            "chunk_id from the allowed list. Copy excerpts verbatim from the chunk " +
            "text. If evidence is weak or missing, set abstain=true and do not guess. " +
            "Never invent tickers, sections, numbers, or chunk_ids.",
          prompt:
            `Question:\n${query}\n\n` +
            `Allowed chunk_ids (cite ONLY these):\n${JSON.stringify(allowedIds)}\n\n` +
            `Evidence:\n${formatEvidence(body.retrieval)}\n\n` +
            "Return structured JSON. Put inline markers like [c1], [c2] in answer_text " +
            "aligned with the order of claims. Prefer abstain over speculation.",
        });

        for await (const partial of result.partialObjectStream) {
          controller.enqueue(
            ndjsonLine({ type: "partial", data: partial })
          );
        }

        const structured = await result.object;
        const groundRes = await fetch(`${apiBase}/ground`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            strategy: body.strategy,
            structured,
            retrieval: body.retrieval,
          }),
        });
        if (!groundRes.ok) {
          const detail = await groundRes.text();
          controller.enqueue(
            ndjsonLine({
              type: "error",
              data: {
                message: detail || `Grounding failed (${groundRes.status})`,
              },
            })
          );
          controller.close();
          return;
        }
        const grounded = await groundRes.json();
        controller.enqueue(ndjsonLine({ type: "answer", data: grounded }));
        controller.close();
      } catch (error) {
        controller.enqueue(
          ndjsonLine({
            type: "error",
            data: {
              message:
                error instanceof Error ? error.message : "Generation failed",
            },
          })
        );
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}
