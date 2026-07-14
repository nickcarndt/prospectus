"use client";

import { STRATEGY_META } from "@/lib/strategies";
import type { RetrievalStrategy } from "@/lib/types";
import { cn } from "@/lib/utils";

const OPTIONS: RetrievalStrategy[] = ["dense", "hybrid", "hybrid_rerank"];

type StrategyToggleProps = {
  value: RetrievalStrategy;
  onChange: (strategy: RetrievalStrategy) => void;
  disabled?: boolean;
};

/**
 * Live retrieval-config control — plain labels first, technical name underneath.
 */
export function StrategyToggle({
  value,
  onChange,
  disabled,
}: StrategyToggleProps) {
  const meta = STRATEGY_META[value];

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-medium tracking-wide text-ink-subtle uppercase">
          Search mode
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
                title={STRATEGY_META[option].technical}
                className={cn(
                  "rounded-[4px] px-2.5 py-1 text-[12px] font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-ink-muted hover:text-ink",
                  disabled && "opacity-50"
                )}
              >
                {STRATEGY_META[option].plain}
              </button>
            );
          })}
        </div>
      </div>
      <p className="max-w-md text-[12px] leading-[1.45] text-ink-subtle">
        {meta.hint}{" "}
        <span className="text-ink-subtle/80">({meta.technical})</span>
      </p>
    </div>
  );
}
