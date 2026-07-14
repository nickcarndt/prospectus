import type { Metadata } from "next";

import { ComparisonChart } from "@/components/eval/comparison-chart";
import { MetricsTable } from "@/components/eval/metrics-table";
import report from "@/data/phase8_report_source.json";

export const metadata: Metadata = {
  title: "Eval report · Prospectus",
  description: "Head-to-head retrieval configs on the SEC labeled eval set.",
};

type ConfigKey = "dense" | "hybrid" | "hybrid_rerank";

function num(v: number | string | null | undefined): number | null {
  return typeof v === "number" ? v : null;
}

export default function EvalReportPage() {
  const display = report.table_display;
  const retrieval = report.retrieval_only;
  const gen = report.generation_partial;

  const tableRows = [
    {
      label: "Recall@5",
      dense: display.recall_at_5.dense,
      hybrid: display.recall_at_5.hybrid,
      hybrid_rerank: display.recall_at_5.hybrid_rerank,
    },
    {
      label: "Recall@10",
      dense: display.recall_at_10.dense,
      hybrid: display.recall_at_10.hybrid,
      hybrid_rerank: display.recall_at_10.hybrid_rerank,
    },
    {
      label: "MRR",
      dense: display.mrr.dense,
      hybrid: display.mrr.hybrid,
      hybrid_rerank: display.mrr.hybrid_rerank,
    },
    {
      label: "Faithfulness",
      dense: display.faithfulness.dense,
      hybrid: display.faithfulness.hybrid,
      hybrid_rerank: display.faithfulness.hybrid_rerank,
    },
    {
      label: "Citation accuracy",
      dense: display.citation_accuracy.dense,
      hybrid: display.citation_accuracy.hybrid,
      hybrid_rerank: display.citation_accuracy.hybrid_rerank,
    },
    {
      label: "p95 latency — retrieval (ms)",
      dense: display.p95_latency_ms_retrieval.dense,
      hybrid: display.p95_latency_ms_retrieval.hybrid,
      hybrid_rerank: display.p95_latency_ms_retrieval.hybrid_rerank,
    },
    {
      label: "p95 latency — e2e (ms)",
      dense: display.p95_latency_ms_e2e.dense,
      hybrid: display.p95_latency_ms_e2e.hybrid,
      hybrid_rerank: display.p95_latency_ms_e2e.hybrid_rerank,
    },
    {
      label: "Cost $/q — retrieval",
      dense: display.cost_usd_per_query_retrieval.dense,
      hybrid: display.cost_usd_per_query_retrieval.hybrid,
      hybrid_rerank: display.cost_usd_per_query_retrieval.hybrid_rerank,
    },
    {
      label: "Cost $/q — e2e",
      dense: display.cost_usd_per_query_e2e.dense,
      hybrid: display.cost_usd_per_query_e2e.hybrid,
      hybrid_rerank: display.cost_usd_per_query_e2e.hybrid_rerank,
    },
  ];

  const recallData = [
    {
      metric: "Recall@5",
      dense: display.recall_at_5.dense,
      hybrid: display.recall_at_5.hybrid,
      hybrid_rerank: display.recall_at_5.hybrid_rerank,
    },
    {
      metric: "Recall@10",
      dense: display.recall_at_10.dense,
      hybrid: display.recall_at_10.hybrid,
      hybrid_rerank: display.recall_at_10.hybrid_rerank,
    },
  ];

  const mrrData = [
    {
      metric: "MRR",
      dense: display.mrr.dense,
      hybrid: display.mrr.hybrid,
      hybrid_rerank: display.mrr.hybrid_rerank,
    },
  ];

  const latencyData = [
    {
      metric: "p95 retrieval (ms)",
      dense: display.p95_latency_ms_retrieval.dense,
      hybrid: display.p95_latency_ms_retrieval.hybrid,
      hybrid_rerank: display.p95_latency_ms_retrieval.hybrid_rerank,
    },
  ];

  const costData = [
    {
      metric: "Retrieval $/q",
      dense: display.cost_usd_per_query_retrieval.dense,
      hybrid: display.cost_usd_per_query_retrieval.hybrid,
      hybrid_rerank: display.cost_usd_per_query_retrieval.hybrid_rerank,
    },
  ];

  const configs: ConfigKey[] = ["dense", "hybrid", "hybrid_rerank"];

  return (
    <main className="mx-auto w-full max-w-[960px] px-6 py-12 md:py-16">
      <header className="mb-10 max-w-2xl">
        <p className="text-[12px] font-medium tracking-wide text-ink-subtle uppercase">
          Eval report
        </p>
        <h1 className="mt-1 text-[30px] font-semibold tracking-tight text-ink">
          Three-config comparison
        </h1>
        <p className="mt-3 text-[15px] leading-[1.6] text-ink-muted">
          Head-to-head on the labeled SEC set (n={report.eval_set_n},
          candidate_depth={report.candidate_depth}). Numbers from{" "}
          <code className="font-mono text-[12px] text-ink">
            phase8_report_source.json
          </code>
          . Generation incomplete for hybrid configs — shown as n/a, not zero.
        </p>
      </header>

      <section className="mb-12">
        <h2 className="mb-4 text-[20px] font-semibold text-ink">Metrics</h2>
        <MetricsTable rows={tableRows} />
      </section>

      <section className="mb-12 grid gap-6 md:grid-cols-2">
        <ComparisonChart title="Recall" data={recallData} format="ratio" />
        <ComparisonChart title="MRR" data={mrrData} format="ratio" />
        <ComparisonChart
          title="p95 retrieval latency"
          data={latencyData}
          format="ms"
        />
        <ComparisonChart
          title="Retrieval cost per query"
          data={costData}
          format="usd"
        />
      </section>

      <section className="mb-12">
        <h2 className="mb-3 text-[20px] font-semibold text-ink">
          Generation (partial)
        </h2>
        <p className="mb-4 max-w-2xl text-[15px] leading-[1.6] text-ink-muted">
          Dense e2e ran through n={gen.dense?.n ?? "—"} before Anthropic credits
          exhausted. Hybrid / hybrid_rerank generation:{" "}
          <span className="text-ink">n/a (API credits)</span>.
        </p>
        <dl className="grid gap-3 sm:grid-cols-3">
          {configs.map((key) => {
            const block = gen[key];
            return (
              <div
                key={key}
                className="rounded-[6px] border border-border bg-surface px-4 py-3"
              >
                <dt className="text-[12px] font-medium text-ink-subtle">
                  {key}
                </dt>
                <dd className="mt-2 text-[13px] text-ink">
                  {block == null ? (
                    <span className="text-ink-subtle">n/a (API credits)</span>
                  ) : (
                    <ul className="space-y-1 tabular-nums">
                      <li>cite {num(block.citation_accuracy)?.toFixed(3)}</li>
                      <li>faith {num(block.faithfulness)?.toFixed(3)}</li>
                      <li>
                        p95 e2e{" "}
                        {num(block.latency_ms_p95) != null
                          ? `${Math.round(block.latency_ms_p95)} ms`
                          : "n/a"}
                      </li>
                    </ul>
                  )}
                </dd>
              </div>
            );
          })}
        </dl>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-[20px] font-semibold text-ink">
          Retrieval means
        </h2>
        <ul className="space-y-1 text-[13px] text-ink-muted tabular-nums">
          {configs.map((key) => (
            <li key={key}>
              <span className="font-medium text-ink">{key}</span>: mean{" "}
              {Math.round(retrieval[key].latency_ms_mean)} ms · R@5{" "}
              {retrieval[key].recall_at_5.toFixed(3)} · MRR{" "}
              {retrieval[key].mrr.toFixed(3)}
            </li>
          ))}
        </ul>
      </section>

      <footer className="border-t border-border pt-6 text-[12px] text-ink-subtle">
        Generated {report.generated_at}. Full write-up:{" "}
        <code className="font-mono">EVAL_REPORT.md</code> at repo root.
      </footer>
    </main>
  );
}
