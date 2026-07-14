"use client";

import { cn } from "@/lib/utils";
import type { RetrievalStrategy } from "@/lib/types";
import { STRATEGY_LABELS } from "@/lib/api";

const OPTIONS: RetrievalStrategy[] = ["dense", "hybrid", "hybrid_rerank"];

type StrategyToggleProps = {
  value: RetrievalStrategy;
  onChange: (strategy: RetrievalStrategy) => void;
  disabled?: boolean;
};

/**
 * Live retrieval-config control — the Phase 8 demo moment.
 */
export function StrategyToggle({
  value,
  onChange,
  disabled,
}: StrategyToggleProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Retrieval strategy"
      className="inline-flex rounded-[6px] border border-border bg-surface-subtle p-0.5"
    >
      {OPTIONS.map((option) => {
        const active = option === value;
        return (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(option)}
            className={cn(
              "rounded-[4px] px-3 py-1.5 text-[12px] font-medium tracking-tight transition-colors",
              active
                ? "bg-surface text-ink shadow-[0_0_0_1px_var(--border)]"
                : "text-ink-muted hover:text-ink",
              disabled && "cursor-not-allowed opacity-50"
            )}
          >
            {STRATEGY_LABELS[option]}
          </button>
        );
      })}
    </div>
  );
}
