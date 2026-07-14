"use client";

import { useCallback, useState, useTransition } from "react";

import { AnswerView } from "@/components/query/answer-view";
import { CitationDrawer } from "@/components/query/citation-drawer";
import { QueryInput } from "@/components/query/query-input";
import { RetrievedChunks } from "@/components/query/retrieved-chunks";
import { StrategyToggle } from "@/components/query/strategy-toggle";
import { Button } from "@/components/ui/button";
import { postQuery } from "@/lib/api";
import type { Citation, Chunk, QueryResponse, RetrievalStrategy } from "@/lib/types";

/**
 * Research workspace — search retrieves for free; cited answers are opt-in.
 *
 * Claude spend is budgeted on the API for the public LinkedIn demo. Strategy
 * toggles always re-retrieve only (no generation).
 */
export function ResearchWorkspace() {
  const [strategy, setStrategy] = useState<RetrievalStrategy>("hybrid_rerank");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [pendingGenerate, setPendingGenerate] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const runQuery = useCallback(
    (query: string, nextStrategy: RetrievalStrategy, generate: boolean) => {
      setError(null);
      setPendingGenerate(generate);
      startTransition(async () => {
        try {
          const response = await postQuery({
            query,
            strategy: nextStrategy,
            generate,
          });
          setResult(response);
          setLastQuery(query);
          if (response.error) {
            setError(response.error);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Request failed");
        } finally {
          setPendingGenerate(false);
        }
      });
    },
    []
  );

  function handleSubmit(query: string) {
    // Retrieve only — LinkedIn visitors can explore without burning Claude.
    runQuery(query, strategy, false);
  }

  function handleGenerate() {
    if (!lastQuery) return;
    runQuery(lastQuery, strategy, true);
  }

  function handleStrategyChange(next: RetrievalStrategy) {
    setStrategy(next);
    if (lastQuery) {
      // Demo moment: re-retrieve so ranked chunks update; skip Claude.
      runQuery(lastQuery, next, false);
    }
  }

  function openCitation(citation: Citation) {
    setActiveCitation(citation);
    setDrawerOpen(true);
  }

  const activeChunk: Chunk | null =
    activeCitation && result?.retrieval
      ? (result.retrieval.chunks.find(
          (c) => c.chunk_id === activeCitation.chunk_id
        ) ?? null)
      : null;

  const showAnswer =
    !!result &&
    result.generate &&
    !result.error &&
    (result.answer_text.length > 0 || result.abstained);

  const canGenerate =
    !!lastQuery &&
    !!result?.retrieval &&
    result.retrieval.chunks.length > 0 &&
    !isPending;

  const hasCitedAnswer = showAnswer && !result?.abstained;

  return (
    <div className="mx-auto w-full max-w-[720px] px-6 py-12 md:py-16">
      <header className="mb-10">
        <h1 className="text-[30px] font-semibold tracking-tight text-ink">
          Prospectus
        </h1>
        <p className="mt-2 max-w-xl text-[15px] leading-[1.6] text-ink-muted">
          Grounded research over SEC filings. Search and compare retrieval
          configs freely — cited answers use a shared daily budget so the
          public demo lasts.
        </p>
      </header>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <StrategyToggle
          value={strategy}
          onChange={handleStrategyChange}
          disabled={isPending}
        />
        {result?.latency_ms != null && (
          <span className="text-[12px] text-ink-subtle tabular-nums">
            {Math.round(result.latency_ms)} ms e2e
            {result.generate && result.confidence > 0 && (
              <> · confidence {result.confidence.toFixed(2)}</>
            )}
          </span>
        )}
      </div>

      <QueryInput onSubmit={handleSubmit} disabled={isPending} />

      {isPending && (
        <p className="mt-6 text-[13px] text-ink-subtle">
          {pendingGenerate ? "Writing cited answer…" : "Searching filings…"}
        </p>
      )}

      {error && (
        <div className="mt-6 rounded-[6px] border border-border bg-warning-bg px-4 py-3 text-[13px] text-warning">
          {error}
        </div>
      )}

      {canGenerate && !hasCitedAnswer && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={handleGenerate}
            disabled={isPending}
            className="rounded-[6px] bg-primary text-primary-foreground hover:bg-[var(--accent-hover)]"
          >
            Generate cited answer
          </Button>
          <p className="text-[12px] text-ink-subtle">
            Uses Claude (limited per visitor / day). Retrieval above is free.
          </p>
        </div>
      )}

      {showAnswer && (
        <section className="mt-10">
          <h2 className="mb-3 text-[13px] font-medium tracking-wide text-ink-subtle uppercase">
            Answer
          </h2>
          <AnswerView
            answerText={result.answer_text}
            citations={result.citations}
            abstained={result.abstained}
            onCitationClick={openCitation}
            activeCitationId={activeCitation?.citation_id}
          />
          {!result.abstained && result.citations.length > 0 && (
            <ul className="mt-6 flex flex-wrap gap-2">
              {result.citations.map((c) => (
                <li key={c.citation_id}>
                  <button
                    type="button"
                    onClick={() => openCitation(c)}
                    className="rounded-[4px] border border-border bg-surface px-2 py-1 text-[12px] text-citation hover:bg-citation-bg"
                  >
                    [{c.citation_id}] {c.ticker} · {c.section_title}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {!result?.generate && lastQuery && result?.retrieval && (
        <p className="mt-8 text-[13px] text-ink-muted">
          Showing retrieval for{" "}
          <span className="font-medium text-ink">{strategy}</span> — toggle
          configs to compare ranking, or generate a cited answer.
        </p>
      )}

      <RetrievedChunks retrieval={result?.retrieval ?? null} />

      <CitationDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        citation={activeCitation}
        chunk={activeChunk}
      />
    </div>
  );
}
