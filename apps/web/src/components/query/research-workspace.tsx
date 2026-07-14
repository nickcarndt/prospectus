"use client";

import { useCallback, useState, useTransition } from "react";

import { AnswerView } from "@/components/query/answer-view";
import { CitationDrawer } from "@/components/query/citation-drawer";
import { QueryInput } from "@/components/query/query-input";
import { RetrievedChunks } from "@/components/query/retrieved-chunks";
import { StarterQueries } from "@/components/query/starter-queries";
import { StrategyToggle } from "@/components/query/strategy-toggle";
import { Button } from "@/components/ui/button";
import { postQuery } from "@/lib/api";
import type { Citation, Chunk, QueryResponse, RetrievalStrategy } from "@/lib/types";

/**
 * Research workspace — evidence-first instrument with opt-in cited generation.
 */
export function ResearchWorkspace() {
  const [strategy, setStrategy] = useState<RetrievalStrategy>("hybrid_rerank");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [pendingGenerate, setPendingGenerate] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeChunk, setActiveChunk] = useState<Chunk | null>(null);
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
    runQuery(query, strategy, false);
  }

  function handleGenerate() {
    if (!lastQuery) return;
    runQuery(lastQuery, strategy, true);
  }

  function handleStrategyChange(next: RetrievalStrategy) {
    setStrategy(next);
    if (lastQuery) {
      runQuery(lastQuery, next, false);
    }
  }

  function openCitation(citation: Citation) {
    setActiveCitation(citation);
    const chunk =
      result?.retrieval?.chunks.find((c) => c.chunk_id === citation.chunk_id) ??
      null;
    setActiveChunk(chunk);
    setDrawerOpen(true);
  }

  function openChunk(chunk: Chunk) {
    setActiveCitation(null);
    setActiveChunk(chunk);
    setDrawerOpen(true);
  }

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
  const hasEvidence = !!result?.retrieval?.chunks.length;
  const showStarters = !lastQuery && !isPending;

  return (
    <div className="paper-shell flex-1">
      <div className="mx-auto w-full max-w-[1200px] px-6 py-10 md:py-14">
        <header className="mb-8 max-w-2xl">
          <p className="text-[12px] font-medium tracking-wide text-primary uppercase">
            SEC research instrument
          </p>
          <h1 className="mt-2 text-[30px] font-semibold tracking-tight text-ink md:text-[34px]">
            Ask filings. Compare retrieval. Cite everything.
          </h1>
          <p className="mt-3 text-[15px] leading-[1.6] text-ink-muted">
            Search and toggle dense · hybrid · hybrid+rerank for free. Cited
            answers are opt-in and budgeted so the public demo lasts.
          </p>
        </header>

        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
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

        <div className="max-w-2xl">
          <QueryInput onSubmit={handleSubmit} disabled={isPending} />
        </div>

        {showStarters && (
          <div className="max-w-2xl">
            <StarterQueries onSelect={handleSubmit} disabled={isPending} />
          </div>
        )}

        {error && (
          <div className="mt-6 max-w-2xl rounded-[6px] border border-border bg-warning-bg px-4 py-3 text-[13px] text-warning">
            {error}
          </div>
        )}

        {(hasEvidence || isPending || showAnswer) && (
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12">
            <div className="min-w-0">
              <RetrievedChunks
                retrieval={result?.retrieval ?? null}
                onChunkClick={openChunk}
                activeChunkId={activeChunk?.chunk_id}
                loading={isPending && !pendingGenerate && !hasEvidence}
              />
              {!result?.generate && hasEvidence && !isPending && (
                <p className="mt-4 text-[13px] text-ink-muted">
                  Showing retrieval for{" "}
                  <span className="font-medium text-ink">{strategy}</span>.
                  Toggle configs to compare ranking, or generate a cited answer.
                </p>
              )}
            </div>

            <div className="min-w-0 lg:border-l lg:border-border lg:pl-12">
              {canGenerate && !hasCitedAnswer && (
                <div className="mb-6 flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    onClick={handleGenerate}
                    disabled={isPending}
                    className="rounded-[6px] bg-primary text-primary-foreground hover:bg-[var(--accent-hover)]"
                  >
                    Generate cited answer
                  </Button>
                  <p className="text-[12px] text-ink-subtle">
                    Uses Claude · limited per visitor / day
                  </p>
                </div>
              )}

              {isPending && pendingGenerate && (
                <p className="mb-4 text-[13px] text-ink-subtle">
                  Writing cited answer…
                </p>
              )}

              {showAnswer && result && (
                <section>
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
                </section>
              )}

              {!showAnswer && !pendingGenerate && hasEvidence && (
                <div className="rounded-[6px] border border-dashed border-border bg-surface-subtle/50 px-4 py-5">
                  <p className="text-[13px] leading-[1.55] text-ink-muted">
                    Evidence is ranked on the left. Open any chunk for the full
                    filing passage, or generate a cited answer when you want
                    synthesis.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        <CitationDrawer
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          citation={activeCitation}
          chunk={activeChunk}
        />
      </div>
    </div>
  );
}
