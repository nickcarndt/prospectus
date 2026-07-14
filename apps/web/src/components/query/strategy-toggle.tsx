"use client";

import type { RetrievalStrategy } from "@/lib/types";
import { STRATEGY_LABELS } from "@/lib/api";
import { cn } from "@/lib/utils";

const OPTIONS: RetrievalStrategy[] = ["dense", "hybrid", "hybrid_rerank"];

const HINTS: Record<RetrievalStrategy, string> = {
  dense: "Semantic similarity only (pgvector)",
  hybrid: "Dense + keyword fused with RRF",
  hybrid_rerank: "Hybrid pool, then Cohere rerank",
};

type StrategyToggleProps = {
  value: RetrievalStrategy;
  onChange: (strategy: RetrievalStrategy) => void;
  disabled?: boolean;
};

/**
 * Live retrieval-config control — the demo moment.
 */
export function StrategyToggle({
  value,
  onChange,
  disabled,
}: StrategyToggleProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-medium tracking-wide text-ink-subtle uppercase">
          Live config
        </span>
        <div
          className="inline-flex rounded-[6px] border border-border bg-surface p-0.5"
          role="group"
          aria-label="Retrieval strategy"
        >
          {OPTIONS.map((option) => {
            const active = option === value;
            return (
              <button
                key={option}
                type="button"
                disabled={disabled}
                onClick={() => onChange(option)}
                className={cn(
                  "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-ink-muted hover:text-ink",
                  disabled && "opacity-50"
                )}
              >
                {STRATEGY_LABELS[option]}
              </button>
            );
          })}
        </div>
      </div>
      <p className="text-[12px] text-ink-subtle">{HINTS[value]}</p>
    </div>
  );
}
