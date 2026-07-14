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
import { STRATEGY_META } from "@/lib/strategies";
import { resolveApiBaseUrl, streamCitedAnswer } from "@/lib/stream-answer";
import type { Citation, Chunk, QueryResponse, RetrievalStrategy } from "@/lib/types";

/** Cap evidence sent into the streaming generator (matches API generate cap). */
const GENERATE_TOP_K = 6;

/**
 * Research workspace — evidence-first instrument with streamed cited generation.
 */
export function ResearchWorkspace() {
  const [strategy, setStrategy] = useState<RetrievalStrategy>("hybrid_rerank");
  const [draftQuery, setDraftQuery] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [pendingGenerate, setPendingGenerate] = useState(false);
  const [streamingDraft, setStreamingDraft] = useState<string>("");
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeChunk, setActiveChunk] = useState<Chunk | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const runRetrieve = useCallback(
    (query: string, nextStrategy: RetrievalStrategy) => {
      setError(null);
      setPendingGenerate(false);
      setStreamingDraft("");
      setActiveCitation(null);
      setActiveChunk(null);
      setDraftQuery(query);
      startTransition(async () => {
        try {
          const response = await postQuery({
            query,
            strategy: nextStrategy,
            generate: false,
          });
          setResult(response);
          setLastQuery(query);
          if (response.error) {
            setError(response.error);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Request failed");
        }
      });
    },
    []
  );

  function handleSubmit(query: string) {
    runRetrieve(query, strategy);
  }

  function handleGenerate() {
    if (!lastQuery || !result?.retrieval) return;
    setError(null);
    setPendingGenerate(true);
    setStreamingDraft("");
    const retrieval = {
      ...result.retrieval,
      chunks: result.retrieval.chunks.slice(0, GENERATE_TOP_K),
      scores: result.retrieval.scores.slice(0, GENERATE_TOP_K),
    };
    startTransition(async () => {
      try {
        const grounded = await streamCitedAnswer({
          query: lastQuery,
          strategy,
          retrieval,
          apiBaseUrl: resolveApiBaseUrl(),
          handlers: {
            onPartial: (partial) => {
              if (partial.answer_text) {
                setStreamingDraft(partial.answer_text);
              }
            },
          },
        });
        setResult(grounded);
        setStreamingDraft("");
        if (grounded.error) {
          setError(grounded.error);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Generation failed");
        setStreamingDraft("");
      } finally {
        setPendingGenerate(false);
      }
    });
  }

  function handleStrategyChange(next: RetrievalStrategy) {
    setStrategy(next);
    if (lastQuery) {
      runRetrieve(lastQuery, next);
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
  const resultsVisible = hasEvidence || isPending || showAnswer || streamingDraft;
  const showOnboarding = !lastQuery;

  return (
    <div className="paper-shell flex-1">
      <div className="mx-auto w-full max-w-[1120px] px-6 py-10 md:py-14">
        <header className="mb-8 max-w-xl">
          <p className="text-[12px] font-medium tracking-wide text-primary uppercase">
            Prospectus
          </p>
          <h1 className="mt-2 text-[30px] font-semibold tracking-tight text-ink md:text-[34px]">
            Research SEC filings with receipts
          </h1>
          {showOnboarding ? (
            <p className="mt-3 text-[15px] leading-[1.65] text-ink-muted">
              Ask a question across 10-K / 10-Q filings. Compare how different
              search modes rank the same evidence, then open a source or
              generate a cited answer. If the filings don’t support a claim, we
              say so.
            </p>
          ) : (
            <p className="mt-2 text-[13px] text-ink-muted">
              Switch search mode to compare ranks · click a passage for the
              filing · generate only when you want synthesis
            </p>
          )}
        </header>

        {showOnboarding && (
          <p className="mb-7 max-w-xl text-[13px] text-ink-subtle">
            Tip: start with a demo question below. The “Exact-token win” case
            is the clearest hybrid vs semantic comparison.
          </p>
        )}

        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <StrategyToggle
            value={strategy}
            onChange={handleStrategyChange}
            disabled={isPending}
          />
          {result?.latency_ms != null && (
            <span className="text-[12px] text-ink-subtle tabular-nums">
              {Math.round(result.latency_ms)} ms
              {isPending && !pendingGenerate && " · updating…"}
            </span>
          )}
        </div>

        <div className="max-w-xl">
          <QueryInput
            value={draftQuery}
            onSubmit={handleSubmit}
            disabled={isPending}
          />
        </div>

        {showStarters && (
          <div className="max-w-xl">
            <StarterQueries onSelect={handleSubmit} disabled={isPending} />
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mt-6 max-w-xl rounded-[6px] border border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-warning-bg px-4 py-3 text-[13px] leading-[1.5] text-warning"
          >
            {error}
          </div>
        )}

        {resultsVisible && (
          <div className="mt-10 grid gap-10 lg:grid-cols-2 lg:gap-0">
            <section className="min-w-0 lg:pr-10">
              <div className="mb-1 flex items-baseline justify-between gap-3">
                <h2 className="text-[13px] font-medium tracking-wide text-ink-subtle uppercase">
                  Evidence
                </h2>
                <p className="text-[12px] text-ink-subtle">
                  Click a row to open the source
                </p>
              </div>
              <RetrievedChunks
                retrieval={result?.retrieval ?? null}
                onChunkClick={openChunk}
                activeChunkId={activeChunk?.chunk_id}
                loading={isPending && !pendingGenerate && !hasEvidence}
              />
              {!result?.generate && hasEvidence && !isPending && (
                <p className="mt-4 text-[13px] leading-[1.55] text-ink-muted">
                  Showing{" "}
                  <span className="font-medium text-ink">
                    {STRATEGY_META[strategy].plain}
                  </span>
                  . Change search mode above: same question, new order.
                </p>
              )}
            </section>

            <section className="min-w-0 border-t border-border pt-10 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-10">
              <h2 className="mb-3 text-[13px] font-medium tracking-wide text-ink-subtle uppercase">
                Cited answer
              </h2>

              {canGenerate && !hasCitedAnswer && !streamingDraft && (
                <div className="mb-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      type="button"
                      onClick={handleGenerate}
                      disabled={isPending}
                      className="rounded-[6px] bg-primary text-primary-foreground hover:bg-[var(--accent-hover)]"
                    >
                      Generate cited answer
                    </Button>
                    {result?.per_ip_remaining != null && (
                      <span className="rounded-[4px] bg-accent-subtle px-2 py-1 text-[12px] text-primary tabular-nums">
                        {result.per_ip_remaining} left today
                      </span>
                    )}
                  </div>
                  <p className="mt-2 max-w-sm text-[12px] leading-[1.5] text-ink-subtle">
                    Optional. Green chips in the answer open the filing passage.
                  </p>
                </div>
              )}

              {pendingGenerate && streamingDraft && (
                <div className="mb-6">
                  <p className="mb-2 text-[12px] text-ink-subtle">Streaming…</p>
                  <p className="whitespace-pre-wrap text-[15px] leading-[1.7] text-ink">
                    {streamingDraft}
                    <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-primary align-middle" />
                  </p>
                </div>
              )}

              {isPending && pendingGenerate && !streamingDraft && (
                <p className="mb-4 text-[13px] text-ink-subtle">
                  Writing cited answer…
                </p>
              )}

              {showAnswer && result && !pendingGenerate && (
                <AnswerView
                  answerText={result.answer_text}
                  citations={result.citations}
                  abstained={result.abstained}
                  onCitationClick={openCitation}
                  activeCitationId={activeCitation?.citation_id}
                />
              )}

              {!showAnswer &&
                !pendingGenerate &&
                !streamingDraft &&
                hasEvidence && (
                  <p className="text-[13px] leading-[1.55] text-ink-muted">
                    Open a passage on the left to read the filing, or generate a
                    cited answer when you want a short synthesis.
                  </p>
                )}
            </section>
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
