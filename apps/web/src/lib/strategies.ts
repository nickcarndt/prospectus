import type { RetrievalStrategy } from "@/lib/types";

/**
 * Progressive disclosure for retrieval configs:
 * plain labels for stakeholders; technical names for interview depth.
 */
export const STRATEGY_META: Record<
  RetrievalStrategy,
  { plain: string; technical: string; hint: string }
> = {
  dense: {
    plain: "Semantic",
    technical: "dense · pgvector",
    hint: "Meaning similarity: strong on paraphrase, weaker on rare exact terms.",
  },
  hybrid: {
    plain: "Keyword + semantic",
    technical: "hybrid · RRF",
    hint: "Fuses meaning search with exact keyword hits. Better for tickers and jargon.",
  },
  hybrid_rerank: {
    plain: "Best match",
    technical: "hybrid + Cohere rerank",
    hint: "Casts a wide net, then a slower model re-orders the top candidates.",
  },
};

/** Short button labels used in the live toggle. */
export const STRATEGY_LABELS: Record<RetrievalStrategy, string> = {
  dense: STRATEGY_META.dense.plain,
  hybrid: STRATEGY_META.hybrid.plain,
  hybrid_rerank: STRATEGY_META.hybrid_rerank.plain,
};
