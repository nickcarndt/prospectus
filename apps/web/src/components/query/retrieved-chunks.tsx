"use client";

import { motion } from "motion/react";

import type { RetrievalResult } from "@/lib/types";
import { STRATEGY_LABELS } from "@/lib/api";

type RetrievedChunksProps = {
  retrieval: RetrievalResult | null;
};

/**
 * Ranked chunk list — updates live when strategy toggles (demo moment).
 */
export function RetrievedChunks({ retrieval }: RetrievedChunksProps) {
  if (!retrieval || retrieval.chunks.length === 0) {
    return null;
  }

  return (
    <section className="mt-10">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-[13px] font-medium tracking-wide text-ink-subtle uppercase">
          Retrieved chunks
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
          return (
            <motion.li
              key={`${retrieval.strategy}-${chunk.chunk_id}`}
              layout
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, delay: index * 0.02 }}
              className="rounded-[6px] border border-border bg-surface px-3.5 py-3"
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
            </motion.li>
          );
        })}
      </ol>
    </section>
  );
}
