"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type MetricRow = {
  metric: string;
  dense: number;
  hybrid: number;
  hybrid_rerank: number;
};

type FormatKind = "ratio" | "ms" | "usd";

type ComparisonChartProps = {
  title: string;
  /** One-line plain-language gloss under the title. */
  subtitle?: string;
  data: MetricRow[];
  format?: FormatKind;
};

const SERIES = [
  { key: "dense", label: "Semantic", color: "#1F4B99" },
  { key: "hybrid", label: "Keyword + semantic", color: "#0B6E4F" },
  { key: "hybrid_rerank", label: "Best match", color: "#6B6B72" },
] as const;

function formatValue(kind: FormatKind, n: number): string {
  if (kind === "ms") return `${Math.round(n)} ms`;
  if (kind === "usd") {
    return n < 0.0001 ? n.toExponential(1) : `$${n.toFixed(5)}`;
  }
  return n.toFixed(3);
}

function axisTick(kind: FormatKind, n: number): string {
  if (kind === "ms") return `${Math.round(n)}`;
  if (kind === "usd") {
    if (n === 0) return "$0";
    if (n < 0.001) return n.toExponential(0);
    return `$${n.toFixed(3)}`;
  }
  // Avoid "0.000" eating left margin — short ticks.
  return n.toFixed(2);
}

type TipProps = {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string }>;
  label?: string | number;
  format: FormatKind;
};

function ChartTooltip({ active, payload, label, format }: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-[6px] border border-border bg-surface px-3 py-2 shadow-sm">
      <p className="mb-1.5 text-[12px] font-medium text-ink">{label}</p>
      <ul className="space-y-1">
        {payload.map((item) => (
          <li
            key={String(item.name)}
            className="flex items-center justify-between gap-6 text-[12px] tabular-nums"
          >
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span
                className="inline-block size-2 rounded-[2px]"
                style={{ background: item.color }}
              />
              {item.name}
            </span>
            <span className="font-medium text-ink">
              {formatValue(format, Number(item.value ?? 0))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Grouped bar comparison — Recharts so we own margins, colors, and tooltip.
 * Tremor was clipping the Y-axis and ignoring custom hex colors (all black).
 */
export function ComparisonChart({
  title,
  subtitle,
  data,
  format = "ratio",
}: ComparisonChartProps) {
  const yMax = Math.max(
    ...data.flatMap((row) => [row.dense, row.hybrid, row.hybrid_rerank]),
    0
  );
  // Headroom so tall bars don't kiss the legend.
  const domainMax =
    format === "ratio"
      ? Math.min(1, Math.ceil((yMax + 0.05) * 20) / 20)
      : undefined;

  return (
    <div className="rounded-[6px] border border-border bg-surface px-4 py-4 sm:px-5">
      <div className="mb-4">
        <h3 className="text-[14px] font-semibold text-ink">{title}</h3>
        {subtitle && (
          <p className="mt-1 text-[12px] leading-[1.45] text-ink-muted">
            {subtitle}
          </p>
        )}
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
            barCategoryGap="28%"
            barGap={4}
          >
            <CartesianGrid
              stroke="var(--border)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="metric"
              tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
            />
            <YAxis
              width={52}
              tick={{ fill: "var(--ink-muted)", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(n: number) => axisTick(format, n)}
              domain={domainMax != null ? [0, domainMax] : [0, "auto"]}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-subtle)" }}
              content={<ChartTooltip format={format} />}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="square"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
            />
            {SERIES.map((series) => (
              <Bar
                key={series.key}
                dataKey={series.key}
                name={series.label}
                fill={series.color}
                radius={[3, 3, 0, 0]}
                maxBarSize={36}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
