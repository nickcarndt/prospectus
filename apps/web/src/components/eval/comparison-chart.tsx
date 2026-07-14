"use client";

import { BarChart } from "@tremor/react";

export type MetricRow = {
  metric: string;
  dense: number;
  hybrid: number;
  hybrid_rerank: number;
};

type FormatKind = "ratio" | "ms" | "usd";

type ComparisonChartProps = {
  title: string;
  data: MetricRow[];
  format?: FormatKind;
};

function formatter(kind: FormatKind): (n: number) => string {
  if (kind === "ms") return (n) => `${Math.round(n)} ms`;
  if (kind === "usd") {
    return (n) => (n < 0.0001 ? n.toExponential(1) : `$${n.toFixed(5)}`);
  }
  return (n) => n.toFixed(3);
}

/**
 * Tremor bar comparison for the three retrieval configs.
 */
export function ComparisonChart({
  title,
  data,
  format = "ratio",
}: ComparisonChartProps) {
  return (
    <div className="rounded-[6px] border border-border bg-surface px-4 py-4">
      <h3 className="mb-3 text-[13px] font-medium text-ink">{title}</h3>
      <BarChart
        className="h-56"
        data={data}
        index="metric"
        categories={["dense", "hybrid", "hybrid_rerank"]}
        colors={["indigo", "emerald", "gray"]}
        valueFormatter={formatter(format)}
        yAxisWidth={48}
        showAnimation
      />
    </div>
  );
}
