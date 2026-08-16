import type { Metadata } from "next";
import Link from "next/link";

import { ComparisonChart } from "@/components/eval/comparison-chart";
import { MetricsTable } from "@/components/eval/metrics-table";
import report from "@/data/phase8_report_source.json";

export const metadata: Metadata = {
  title: "Eval report · Prospectus",
  description:
    "Complete retrieval and generation comparison across dense, hybrid, and hybrid+rerank.",
};

type ConfigKey = "dense" | "hybrid" | "hybrid_rerank";

export default function EvalReportPage() {
  const display = report.table_display;
  const retrieval = report.retrieval_only;
  const gen = report.generation_complete;
  const cowos = report.qualitative_demos.phase4_cowos;
  const cowosRerank = report.qualitative_demos.phase5_cowos_rerank;

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
      label: "Citation accuracy",
      dense: display.citation_accuracy.dense,
      hybrid: display.citation_accuracy.hybrid,
      hybrid_rerank: display.citation_accuracy.hybrid_rerank,
    },
    {
      label: "Faithfulness",
      dense: display.faithfulness.dense,
      hybrid: display.faithfulness.hybrid,
      hybrid_rerank: display.faithfulness.hybrid_rerank,
    },
    {
      label: "p95 latency, retrieval (ms)",
      dense: display.p95_latency_ms_retrieval.dense,
      hybrid: display.p95_latency_ms_retrieval.hybrid,
      hybrid_rerank: display.p95_latency_ms_retrieval.hybrid_rerank,
    },
    {
      label: "p95 latency, e2e (ms)",
      dense: Math.round(display.p95_latency_ms_e2e.dense),
      hybrid: Math.round(display.p95_latency_ms_e2e.hybrid),
      hybrid_rerank: Math.round(display.p95_latency_ms_e2e.hybrid_rerank),
    },
    {
      label: "Cost $/q, retrieval",
      dense: display.cost_usd_per_query_retrieval.dense,
      hybrid: display.cost_usd_per_query_retrieval.hybrid,
      hybrid_rerank: display.cost_usd_per_query_retrieval.hybrid_rerank,
    },
    {
      label: "Cost $/q, e2e (est.)",
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

  const genQualityData = [
    {
      metric: "Citation acc.",
      dense: display.citation_accuracy.dense,
      hybrid: display.citation_accuracy.hybrid,
      hybrid_rerank: display.citation_accuracy.hybrid_rerank,
    },
    {
      metric: "Faithfulness",
      dense: display.faithfulness.dense,
      hybrid: display.faithfulness.hybrid,
      hybrid_rerank: display.faithfulness.hybrid_rerank,
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

  const configs: ConfigKey[] = ["dense", "hybrid", "hybrid_rerank"];

  return (
    <main className="paper-shell mx-auto w-full max-w-[1120px] flex-1 px-6 py-12 md:py-16">
      <header className="mb-8 max-w-2xl">
        <p className="text-[12px] font-medium tracking-wide text-primary uppercase">
          Eval report
        </p>
        <h1 className="mt-1 text-[30px] font-semibold tracking-tight text-ink">
          Which search mode wins on this 35-question set?
        </h1>
        <p className="mt-3 text-[15px] leading-[1.6] text-ink-muted">
          Measured on {report.eval_set_n} labeled SEC questions. Full retrieve +
          generate + faithfulness for all three modes (n=
          {gen.dense.n} each).
        </p>
      </header>

      <section className="mb-10 rounded-[6px] border border-border bg-accent-subtle/50 px-5 py-4">
        <p className="text-[12px] font-medium tracking-wide text-primary uppercase">
          Verdict
        </p>
        <p className="mt-2 text-[16px] leading-[1.55] font-medium text-ink">
          On a single n=35 pass: Semantic search ranks the right filing section highest overall (MRR
          0.845). Keyword + semantic does not beat it on average recall (both
          R@5 0.971), but it still wins on rare exact terms (e.g. CoWoS).
          Best-match reranking is slower at retrieval; all three configs
          posted perfect citation accuracy, and reranking had the highest
          faithfulness (1.000) on this run&apos;s judge pass.
        </p>
        <p className="mt-2 text-[13px] leading-[1.5] text-ink-muted">
          That is the honest result, not a marketing chart. Details below.
        </p>
        <p className="mt-2 text-[13px] leading-[1.5] text-ink-muted">
          Caveat: generation metrics come from the pre-relabel full run;
          retrieval metrics are post-relabel. See EVAL_REPORT.md limitations.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="mb-4 text-[20px] font-semibold text-ink">
          Head-to-head metrics
        </h2>
        <MetricsTable rows={tableRows} />
        <p className="mt-3 text-[13px] text-ink-muted">
          Retrieval latency/cost come from a dedicated retrieval-only run. E2e
          rows include Claude generation + the faithfulness judge.
        </p>
      </section>

      <section className="mb-12 rounded-[6px] border border-border bg-surface px-5 py-4">
        <h2 className="text-[15px] font-semibold text-ink">
          Why Recall@5 equals Recall@10
        </h2>
        <p className="mt-2 text-[14px] leading-[1.6] text-ink-muted">
          Not a scoring bug. Recall here is{" "}
          <span className="text-ink">binary section hit-rate</span>: did any
          chunk from the gold ticker+section appear in the top-k? On this set,
          when the gold section is found it is almost always already inside the
          top-5, so widening to top-10 adds no new hits. That is why dense and
          hybrid both show R@5 = R@10 = 0.971 (34/35); hybrid+rerank is close
          (R@5 0.943, R@10 0.971). The metric that{" "}
          <span className="text-ink">does</span> separate configs is{" "}
          <span className="font-medium text-ink">MRR</span> (how high the first
          gold hit ranks).
        </p>
      </section>

      <section className="mb-12 grid gap-6 md:grid-cols-2">
        <ComparisonChart
          title="Did we find the right section?"
          subtitle="Recall@k: share of questions where the gold filing section appears in the top results."
          data={recallData}
          format="ratio"
        />
        <ComparisonChart
          title="How high was the right section ranked?"
          subtitle="MRR (mean reciprocal rank): higher means the correct section appears earlier in the list."
          data={mrrData}
          format="ratio"
        />
        <ComparisonChart
          title="Is the answer grounded?"
          subtitle="Citation accuracy and faithfulness after full generation (n=35 per config, from the prior pre-relabel full run)."
          data={genQualityData}
          format="ratio"
        />
        <ComparisonChart
          title="How long does retrieval take?"
          subtitle="p95 latency: 95% of queries finish within this many milliseconds (retrieval stage only)."
          data={latencyData}
          format="ms"
        />
      </section>

      <section className="mb-12">
        <h2 className="mb-3 text-[20px] font-semibold text-ink">
          Qualitative: where hybrid still wins
        </h2>
        <div className="space-y-3 rounded-[6px] border border-border bg-surface px-5 py-4 text-[14px] leading-[1.6] text-ink-muted">
          <p>
            <span className="font-medium text-ink">Query:</span> “{cowos.query}
            ”. {cowos.finding}
          </p>
          <p>
            <span className="font-medium text-ink">Rerank:</span>{" "}
            {cowosRerank.finding}
          </p>
          <p>
            Try it live:{" "}
            <Link href="/" className="text-primary hover:underline">
              Research → starter “Exact-token win”
            </Link>
            .
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="mb-3 text-[20px] font-semibold text-ink">
          Plain-language glossary
        </h2>
        <div className="rounded-[6px] border border-border bg-surface px-5 py-4">
          <h3 className="text-[13px] font-semibold uppercase tracking-wide text-primary">
            The three search modes
          </h3>
          <dl className="mt-2 space-y-2 text-[14px] leading-[1.6]">
            <div>
              <dt className="font-medium text-ink">Semantic (dense)</dt>
              <dd className="text-ink-muted">
                Searches by meaning. Finds passages that say the same thing even
                when they use different words.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Keyword + semantic (hybrid)</dt>
              <dd className="text-ink-muted">
                Runs meaning-based search and exact-word search, then merges the
                two lists. Catches rare exact terms — tickers, part names —
                that meaning-search can miss.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">
                Best-match reranking (hybrid_rerank)
              </dt>
              <dd className="text-ink-muted">
                Hybrid search, then a second model re-reads the shortlist and
                re-orders it by relevance. Slower, sometimes sharper.
              </dd>
            </div>
          </dl>

          <h3 className="mt-5 text-[13px] font-semibold uppercase tracking-wide text-primary">
            The metrics
          </h3>
          <dl className="mt-2 space-y-2 text-[14px] leading-[1.6]">
            <div>
              <dt className="font-medium text-ink">Recall@5 / Recall@10</dt>
              <dd className="text-ink-muted">
                &ldquo;Was the right passage in the top 5 (or 10) results?&rdquo;
                1.000 means every question had its answer somewhere in the
                shortlist.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">MRR (mean reciprocal rank)</dt>
              <dd className="text-ink-muted">
                How close to the #1 spot the right passage lands. 1.0 means it
                was always first; 0.5 means second on average. Higher is better.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Citation accuracy</dt>
              <dd className="text-ink-muted">
                Does each citation in the answer point to a real passage that
                actually contains the quoted evidence? Checked by code, not by
                opinion.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Faithfulness</dt>
              <dd className="text-ink-muted">
                Does the written answer stick to what the sources say? Scored by
                a separate AI judge comparing the answer against the passages it
                cited.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">p95 latency</dt>
              <dd className="text-ink-muted">
                95 out of 100 searches finish within this time.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">n=35</dt>
              <dd className="text-ink-muted">
                Everything here was measured on the same 35 questions with
                known-correct answers.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Abstention</dt>
              <dd className="text-ink-muted">
                When the evidence is too weak, the system says &ldquo;not
                established in these documents&rdquo; instead of guessing.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Sealed digest</dt>
              <dd className="text-ink-muted">
                A public fingerprint (checksum) of the results file, committed
                to the repo — so the numbers above can&apos;t be quietly edited
                after the fact.
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-[15px] font-semibold text-ink">
          Per-config means
        </h2>
        <ul className="space-y-1 text-[13px] text-ink-muted tabular-nums">
          {configs.map((key) => (
            <li key={key}>
              <span className="font-medium text-ink">{key}</span>: retrieval mean{" "}
              {Math.round(retrieval[key].latency_ms_mean)} ms · e2e mean{" "}
              {Math.round(gen[key].latency_ms_mean)} ms · faith{" "}
              {gen[key].faithfulness.toFixed(3)} · cite{" "}
              {gen[key].citation_accuracy.toFixed(3)}
            </li>
          ))}
        </ul>
      </section>

      <footer className="border-t border-border pt-6 text-[12px] text-ink-subtle">
        Generated {report.generated_at}. Machine source:{" "}
        <code className="font-mono">phase8_report_source.json</code>. Write-up:{" "}
        <code className="font-mono">EVAL_REPORT.md</code>.
      </footer>
    </main>
  );
}
