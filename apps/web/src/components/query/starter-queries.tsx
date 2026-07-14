"use client";

const STARTERS: { label: string; query: string; hint: string }[] = [
  {
    label: "Exact-token win",
    query: "What is CoWoS packaging and which filers discuss it?",
    hint: "Semantic often misses · keyword modes surface NVDA",
  },
  {
    label: "Should abstain",
    query: "What was Apple’s exact Q3 2019 iPhone unit sales guidance?",
    hint: "Corpus may lack evidence; abstention is correct",
  },
  {
    label: "Multi-ticker",
    query:
      "How do NVIDIA, TSMC, and AMD describe advanced packaging or foundry capacity risk?",
    hint: "Compare ranking across issuers when you toggle strategies",
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
        Start with a demo question
      </p>
      <ul className="flex flex-col gap-2">
        {STARTERS.map((item) => (
          <li key={item.query}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(item.query)}
              className="group w-full rounded-[6px] border border-border bg-surface px-3.5 py-3 text-left transition-colors hover:border-[color-mix(in_srgb,var(--primary)_30%,var(--border))] hover:bg-accent-subtle/40 disabled:opacity-50"
            >
              <span className="text-[12px] font-medium text-primary">
                {item.label}
              </span>
              <span className="mt-0.5 block text-[14px] leading-[1.45] text-ink">
                {item.query}
              </span>
              <span className="mt-1 block text-[12px] text-ink-subtle">
                {item.hint}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
