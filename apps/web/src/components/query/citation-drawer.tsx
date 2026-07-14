"use client";

import { motion } from "motion/react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Citation, Chunk } from "@/lib/types";

type CitationDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  citation: Citation | null;
  chunk: Chunk | null;
};

/**
 * Right-side source drawer — filing metadata + chunk with excerpt highlight.
 * THIS IS THE PRODUCT. Openable from citations or ranked evidence rows.
 */
export function CitationDrawer({
  open,
  onOpenChange,
  citation,
  chunk,
}: CitationDrawerProps) {
  const ticker = citation?.ticker ?? chunk?.ticker;
  const formType = citation?.form_type ?? chunk?.form_type;
  const sectionTitle = citation?.section_title ?? chunk?.section_title;
  const filingDate = citation?.filing_date ?? chunk?.filing_date;
  const sourceUrl = citation?.source_url ?? chunk?.source_url;
  const body = chunk?.text ?? citation?.excerpt ?? "";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full gap-0 border-border bg-surface p-0 sm:max-w-md"
      >
        {(citation || chunk) && (
          <>
            <SheetHeader className="border-b border-border px-5 py-4">
              <SheetTitle className="text-[15px] font-semibold text-ink">
                {ticker} · {formType}
              </SheetTitle>
              <SheetDescription className="text-[12px] text-ink-muted">
                {sectionTitle}
                <span className="mx-1.5 text-ink-subtle">·</span>
                <span className="tabular-nums">{filingDate}</span>
              </SheetDescription>
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 font-mono text-[11px] text-primary hover:underline"
                >
                  Open on EDGAR ↗
                </a>
              )}
            </SheetHeader>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
              {citation && (
                <section>
                  <h3 className="text-[11px] font-medium tracking-wide text-ink-subtle uppercase">
                    Cited excerpt
                  </h3>
                  <motion.blockquote
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="mt-2 rounded-[6px] border-l-2 border-citation bg-citation-bg px-3 py-2.5 text-[13px] leading-[1.55] text-ink"
                  >
                    {citation.excerpt}
                  </motion.blockquote>
                </section>
              )}

              {chunk && (
                <section>
                  <h3 className="text-[11px] font-medium tracking-wide text-ink-subtle uppercase">
                    Source chunk
                  </h3>
                  <p className="mt-1 font-mono text-[11px] text-ink-subtle">
                    {chunk.chunk_id}
                  </p>
                  {citation ? (
                    <HighlightedChunk
                      text={chunk.text}
                      excerpt={citation.excerpt}
                    />
                  ) : (
                    <p className="mt-2 whitespace-pre-wrap text-[13px] leading-[1.6] text-ink-muted">
                      {body}
                    </p>
                  )}
                </section>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function HighlightedChunk({ text, excerpt }: { text: string; excerpt: string }) {
  const match = findExcerptSpan(text, excerpt);
  if (!match) {
    return (
      <div className="mt-2">
        <p className="mb-2 text-[12px] text-warning">
          Excerpt is not a contiguous span in this chunk (whitespace or
          grounding mismatch).
        </p>
        <p className="whitespace-pre-wrap text-[13px] leading-[1.6] text-ink-muted">
          {text}
        </p>
      </div>
    );
  }
  const { start, end } = match;
  return (
    <p className="mt-2 whitespace-pre-wrap text-[13px] leading-[1.6] text-ink-muted">
      {text.slice(0, start)}
      <mark className="rounded-[2px] bg-citation-bg text-ink">
        {text.slice(start, end)}
      </mark>
      {text.slice(end)}
    </p>
  );
}

/** Case-insensitive contiguous match; no fuzzy guess if whitespace differs. */
function findExcerptSpan(
  text: string,
  excerpt: string
): { start: number; end: number } | null {
  const lowerText = text.toLowerCase();
  const lowerEx = excerpt.trim().toLowerCase();
  if (!lowerEx) return null;
  const direct = lowerText.indexOf(lowerEx);
  if (direct >= 0) {
    return { start: direct, end: direct + excerpt.trim().length };
  }
  const normText = text.replace(/\s+/g, " ");
  const normEx = excerpt.trim().replace(/\s+/g, " ");
  const n = normText.toLowerCase().indexOf(normEx.toLowerCase());
  if (n < 0) return null;
  // Map normalized index back by walking original whitespace collapses.
  let ni = 0;
  let start = -1;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const isSpace = /\s/.test(ch);
    if (isSpace) {
      if (ni < normText.length && normText[ni] === " ") {
        if (ni === n) start = i;
        ni += 1;
        while (i + 1 < text.length && /\s/.test(text[i + 1])) i += 1;
      }
      continue;
    }
    if (ni === n) start = i;
    ni += 1;
  }
  if (start < 0) return null;
  return { start, end: Math.min(text.length, start + excerpt.trim().length) };
}
