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
 * Right-side citation drawer — filing metadata + chunk with excerpt highlight.
 * THIS IS THE PRODUCT.
 */
export function CitationDrawer({
  open,
  onOpenChange,
  citation,
  chunk,
}: CitationDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full gap-0 border-border bg-surface p-0 sm:max-w-md"
      >
        {citation && (
          <>
            <SheetHeader className="border-b border-border px-5 py-4">
              <SheetTitle className="text-[15px] font-semibold text-ink">
                {citation.ticker} · {citation.form_type}
              </SheetTitle>
              <SheetDescription className="text-[12px] text-ink-muted">
                {citation.section_title}
                <span className="mx-1.5 text-ink-subtle">·</span>
                <span className="tabular-nums">{citation.filing_date}</span>
              </SheetDescription>
              <a
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 font-mono text-[11px] text-primary hover:underline"
              >
                Open on EDGAR ↗
              </a>
            </SheetHeader>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
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

              {chunk && (
                <section>
                  <h3 className="text-[11px] font-medium tracking-wide text-ink-subtle uppercase">
                    Source chunk
                  </h3>
                  <p className="mt-1 font-mono text-[11px] text-ink-subtle">
                    {chunk.chunk_id}
                  </p>
                  <HighlightedChunk text={chunk.text} excerpt={citation.excerpt} />
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
  const idx = findExcerptIndex(text, excerpt);
  if (idx < 0) {
    return (
      <p className="mt-2 whitespace-pre-wrap text-[13px] leading-[1.6] text-ink-muted">
        {text}
      </p>
    );
  }
  const before = text.slice(0, idx);
  const mid = text.slice(idx, idx + excerpt.length);
  const after = text.slice(idx + excerpt.length);
  return (
    <p className="mt-2 whitespace-pre-wrap text-[13px] leading-[1.6] text-ink-muted">
      {before}
      <mark className="rounded-[2px] bg-citation-bg text-ink">{mid}</mark>
      {after}
    </p>
  );
}

/** Case-insensitive contiguous match for excerpt highlight. */
function findExcerptIndex(text: string, excerpt: string): number {
  const lowerText = text.toLowerCase();
  const lowerEx = excerpt.trim().toLowerCase();
  if (!lowerEx) return -1;
  const direct = lowerText.indexOf(lowerEx);
  if (direct >= 0) return direct;
  // Fallback: collapse whitespace in both
  const normText = text.replace(/\s+/g, " ");
  const normEx = excerpt.trim().replace(/\s+/g, " ");
  const n = normText.toLowerCase().indexOf(normEx.toLowerCase());
  if (n < 0) return -1;
  // Map approx back — good enough for display when whitespace differs
  return text.toLowerCase().indexOf(normEx.toLowerCase().slice(0, 24));
}
