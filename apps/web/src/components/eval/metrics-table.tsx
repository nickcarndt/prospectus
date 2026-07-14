import type { ReactNode } from "react";

type Cell = number | string | null | undefined;

type MetricsTableProps = {
  rows: { label: string; dense: Cell; hybrid: Cell; hybrid_rerank: Cell }[];
};

function formatCell(value: Cell): ReactNode {
  // Primary tables should only receive measured numbers. String/null cells
  // render as n/a (never fake credit placeholders in the hero comparison).
  if (value == null) return <span className="text-ink-subtle">n/a</span>;
  if (typeof value === "string") {
    return <span className="text-ink-subtle">n/a</span>;
  }
  return (
    <span className="tabular-nums">
      {Number.isInteger(value) ? value : value.toFixed(3)}
    </span>
  );
}

/**
 * Well-typeset three-config comparison table with tabular figures.
 */
export function MetricsTable({ rows }: MetricsTableProps) {
  return (
    <div className="overflow-x-auto rounded-[6px] border border-border">
      <table className="w-full min-w-[560px] border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-border bg-surface-subtle">
            <th className="px-4 py-2.5 font-medium text-ink-muted">Metric</th>
            <th className="px-4 py-2.5 text-right font-medium text-ink-muted">
              <span className="text-ink">Semantic</span>
              <span className="mt-0.5 block text-[11px] font-normal">
                dense
              </span>
            </th>
            <th className="px-4 py-2.5 text-right font-medium text-ink-muted">
              <span className="text-ink">Keyword + semantic</span>
              <span className="mt-0.5 block text-[11px] font-normal">
                hybrid
              </span>
            </th>
            <th className="px-4 py-2.5 text-right font-medium text-ink-muted">
              <span className="text-ink">Best match</span>
              <span className="mt-0.5 block text-[11px] font-normal">
                hybrid+rerank
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.label}
              className="border-b border-border last:border-0"
            >
              <td className="px-4 py-2.5 text-ink">{row.label}</td>
              <td className="px-4 py-2.5 text-right text-ink">
                {formatCell(row.dense)}
              </td>
              <td className="px-4 py-2.5 text-right text-ink">
                {formatCell(row.hybrid)}
              </td>
              <td className="px-4 py-2.5 text-right text-ink">
                {formatCell(row.hybrid_rerank)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
