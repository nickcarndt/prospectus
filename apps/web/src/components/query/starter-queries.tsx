"use client";

const STARTERS: { label: string; query: string; hint: string }[] = [
  {
    label: "Exact-token win",
    query: "What is CoWoS packaging and which filers discuss it?",
    hint: "Dense often misses · hybrid / rerank surface NVDA",
  },
  {
    label: "Risk factors",
    query:
      "What supply chain or manufacturing risks does NVIDIA discuss in Item 1A?",
    hint: "Compare how configs rank Item 1A vs Business",
  },
  {
    label: "Should abstain",
    query: "What was Apple’s exact Q3 2019 iPhone unit sales guidance?",
    hint: "Corpus may lack evidence — abstention is correct",
  },
];

type StarterQueriesProps = {
  onSelect: (query: string) => void;
  disabled?: boolean;
};

/**
 * Curated one-click demos — empty state is a research instrument, not a blank box.
 */
export function StarterQueries({ onSelect, disabled }: StarterQueriesProps) {
  return (
    <div className="mt-8">
      <p className="mb-3 text-[12px] font-medium tracking-wide text-ink-subtle uppercase">
        Try a research question
      </p>
      <ul className="divide-y divide-border border-y border-border">
        {STARTERS.map((item) => (
          <li key={item.query}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(item.query)}
              className="group flex w-full flex-col gap-0.5 px-0 py-3.5 text-left transition-colors hover:bg-surface-subtle/80 disabled:opacity-50"
            >
              <span className="text-[12px] font-medium text-primary">
                {item.label}
              </span>
              <span className="text-[15px] leading-[1.5] text-ink group-hover:text-ink">
                {item.query}
              </span>
              <span className="text-[12px] text-ink-subtle">{item.hint}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
