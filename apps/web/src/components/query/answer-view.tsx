"use client";

import { Fragment, useMemo, type ReactNode } from "react";

import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

type AnswerViewProps = {
  answerText: string;
  citations: Citation[];
  abstained: boolean;
  onCitationClick: (citation: Citation) => void;
  activeCitationId?: string | null;
};

const MARKER = /\[(c\d+)\]/g;

/**
 * Answer body with prominent clickable citation chips ([c1], [c2], …).
 */
export function AnswerView({
  answerText,
  citations,
  abstained,
  onCitationClick,
  activeCitationId,
}: AnswerViewProps) {
  const byId = useMemo(() => {
    const map = new Map<string, Citation>();
    for (const c of citations) map.set(c.citation_id, c);
    return map;
  }, [citations]);

  if (abstained) {
    return (
      <div className="rounded-[6px] border border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-warning-bg px-5 py-4">
        <p className="text-[12px] font-medium tracking-wide text-warning uppercase">
          Insufficient evidence
        </p>
        <p className="mt-2 text-[15px] leading-[1.6] text-ink">
          {answerText ||
            "I don't have enough evidence in these filings to answer that confidently."}
        </p>
      </div>
    );
  }

  const parts: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(MARKER);
  while ((match = re.exec(answerText)) !== null) {
    if (match.index > last) {
      parts.push(
        <Fragment key={`t-${last}`}>{answerText.slice(last, match.index)}</Fragment>
      );
    }
    const citationId = match[1];
    const citation = byId.get(citationId);
    if (citation) {
      parts.push(
        <button
          key={`c-${match.index}-${citationId}`}
          type="button"
          onClick={() => onCitationClick(citation)}
          className={cn(
            "mx-0.5 inline-flex translate-y-[-1px] items-center rounded-[4px] px-1.5 py-0.5 text-[11px] font-medium tabular-nums transition-colors",
            "bg-citation-bg text-citation hover:bg-[color-mix(in_srgb,var(--citation)_18%,white)]",
            activeCitationId === citationId && "ring-1 ring-citation"
          )}
        >
          {citation.ticker} · {citationId}
        </button>
      );
    } else {
      parts.push(
        <span key={`u-${match.index}`} className="text-ink-subtle">
          [{citationId}]
        </span>
      );
    }
    last = match.index + match[0].length;
  }
  if (last < answerText.length) {
    parts.push(<Fragment key={`t-end`}>{answerText.slice(last)}</Fragment>);
  }

  return (
    <div className="text-[15px] leading-[1.7] text-ink">
      <p className="whitespace-pre-wrap">{parts.length > 0 ? parts : answerText}</p>
    </div>
  );
}
