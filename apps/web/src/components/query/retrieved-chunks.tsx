"use client";

import { motion } from "motion/react";

import type { Chunk, RetrievalResult } from "@/lib/types";
import { STRATEGY_LABELS } from "@/lib/api";
import { cn } from "@/lib/utils";

type RetrievedChunksProps = {
  retrieval: RetrievalResult | null;
  onChunkClick?: (chunk: Chunk) => void;
  activeChunkId?: string | null;
  loading?: boolean;
};

/**
 * Ranked evidence pane — clickable rows open the citation drawer.
 * This is the product surface for the strategy-toggle demo.
 */
export function RetrievedChunks({
  retrieval,
  onChunkClick,
  activeChunkId,
  loading,
}: RetrievedChunksProps) {
  if (loading) {
    return (
      <section className="mt-2">
        <div className="mb-3 h-3 w-28 animate-pulse rounded-[4px] bg-surface-subtle" />
        <ol className="flex flex-col gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <li
              key={i}
              className="h-[72px] animate-pulse rounded-[6px] border border-border bg-surface-subtle/80"
            />
          ))}
        </ol>
      </section>
    );
  }

  if (!retrieval || retrieval.chunks.length === 0) {
    return null;
  }

  return (
    <section className="mt-2">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-[13px] font-medium tracking-wide text-ink-subtle uppercase">
          Evidence
        </h2>
        <p className="text-[12px] text-ink-subtle tabular-nums">
          {STRATEGY_LABELS[retrieval.strategy]}
          {retrieval.latency_ms != null && (
            <> · {Math.round(retrieval.latency_ms)} ms</>
          )}
        </p>
      </div>
      <ol className="flex flex-col gap-2">
        {retrieval.chunks.map((chunk, index) => {
          const score = retrieval.scores[index];
          const active = activeChunkId === chunk.chunk_id;
          return (
            <motion.li
              key={`${retrieval.strategy}-${chunk.chunk_id}`}
              layout
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, delay: index * 0.02 }}
            >
              <button
                type="button"
                onClick={() => onChunkClick?.(chunk)}
                className={cn(
                  "w-full rounded-[6px] border px-3.5 py-3 text-left transition-colors",
                  active
                    ? "border-citation bg-citation-bg"
                    : "border-border bg-surface hover:border-[color-mix(in_srgb,var(--primary)_35%,var(--border))] hover:bg-surface-subtle"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-medium text-ink">
                    <span className="mr-2 tabular-nums text-ink-subtle">
                      #{index + 1}
                    </span>
                    {chunk.ticker} · {chunk.form_type} · {chunk.section_title}
                  </span>
                  {score != null && (
                    <span className="shrink-0 font-mono text-[11px] text-ink-subtle tabular-nums">
                      {score.toFixed(4)}
                    </span>
                  )}
                </div>
                <p className="mt-1.5 line-clamp-2 text-[13px] leading-[1.5] text-ink-muted">
                  {chunk.text}
                </p>
              </button>
            </motion.li>
          );
        })}
      </ol>
    </section>
  );
}
