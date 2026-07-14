"""Post-hoc grounding checks — structural, not prompt-only.

Rules enforced in code:
1. Every citation chunk_id must be in the retrieved evidence set.
2. Excerpt must appear (normalized) inside that chunk's text.
3. Non-abstained answers need ≥1 valid citation after filtering.
4. Confidence below threshold forces abstention.
5. Inline [cN] markers in answer_text are rewritten to match issued ids
   after invalid claims are dropped (so UI chips and body stay aligned).
"""

from __future__ import annotations

import re

from prospectus_shared import Answer, Citation, Chunk, RetrievalResult, RetrievalStrategy

from prospectus_generation.llm_schema import StructuredGeneration

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough evidence in these filings to answer that confidently."
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.55

_MARKER_RE = re.compile(r"\[(c\d+)\]")


def _normalize(text: str) -> str:
    """Collapse whitespace for excerpt membership checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def excerpt_in_chunk(excerpt: str, chunk_text: str) -> bool:
    """Return True if excerpt is a contiguous span of the chunk (approx)."""
    ex = _normalize(excerpt)
    body = _normalize(chunk_text)
    if not ex or len(ex) < 8:
        return False
    return ex in body


def rewrite_citation_markers(answer_text: str, marker_map: dict[str, str]) -> str:
    """Remap inline [cN] markers after claims were filtered/renumbered.

    Unknown markers are left unchanged (then UI simply won't highlight them).
    """
    if not marker_map:
        return answer_text

    def repl(match: re.Match[str]) -> str:
        old = match.group(1)
        new = marker_map.get(old)
        return f"[{new}]" if new is not None else match.group(0)

    return _MARKER_RE.sub(repl, answer_text)


def build_abstained_answer(
    *,
    query: str,
    strategy: RetrievalStrategy,
    confidence: float,
    retrieval: RetrievalResult | None,
    reason: str = INSUFFICIENT_EVIDENCE_MESSAGE,
) -> Answer:
    """Construct a valid abstaining Answer (citations may be empty)."""
    return Answer(
        query=query,
        strategy=strategy,
        answer_text=reason,
        citations=[],
        confidence=max(0.0, min(1.0, confidence)),
        abstained=True,
        retrieval=retrieval,
    )


def ground_structured_output(
    structured: StructuredGeneration,
    *,
    query: str,
    strategy: RetrievalStrategy,
    evidence: list[Chunk],
    retrieval: RetrievalResult | None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> Answer:
    """Validate Claude output against retrieved evidence; abstain if ungrounded.

    This is the structural gate: even if the model hallucinates a chunk_id or
    invents an excerpt, we drop it. If nothing valid remains (or confidence is
    low / model abstains), we return insufficient evidence.
    """
    by_id = {chunk.chunk_id: chunk for chunk in evidence}

    if structured.abstain or structured.confidence < confidence_threshold:
        return build_abstained_answer(
            query=query,
            strategy=strategy,
            confidence=structured.confidence,
            retrieval=retrieval,
        )

    if not evidence:
        return build_abstained_answer(
            query=query,
            strategy=strategy,
            confidence=min(structured.confidence, 0.2),
            retrieval=retrieval,
        )

    citations: list[Citation] = []
    seen_chunks: set[str] = set()
    # Model emits [c1]..[cN] aligned with claim order; after filtering we
    # renumber densely and rewrite the answer body to match.
    marker_map: dict[str, str] = {}
    kept_lines: list[str] = []

    for index, claim in enumerate(structured.claims, start=1):
        chunk = by_id.get(claim.chunk_id)
        if chunk is None:
            continue
        if not excerpt_in_chunk(claim.excerpt, chunk.text):
            continue
        if chunk.chunk_id in seen_chunks:
            continue
        seen_chunks.add(chunk.chunk_id)
        new_id = f"c{len(citations) + 1}"
        marker_map[f"c{index}"] = new_id
        citations.append(
            Citation(
                citation_id=new_id,
                chunk_id=chunk.chunk_id,
                ticker=chunk.ticker,
                form_type=chunk.form_type,
                filing_date=chunk.filing_date,
                section_id=chunk.section_id,
                section_title=chunk.section_title,
                excerpt=claim.excerpt.strip(),
                source_url=chunk.source_url,
            )
        )
        kept_lines.append(f"{claim.claim_text.strip()} [{new_id}]")

    if not citations:
        return build_abstained_answer(
            query=query,
            strategy=strategy,
            confidence=min(structured.confidence, 0.3),
            retrieval=retrieval,
        )

    raw = structured.answer_text.strip()
    if raw:
        answer_text = rewrite_citation_markers(raw, marker_map)
    else:
        answer_text = " ".join(kept_lines)

    return Answer(
        query=query,
        strategy=strategy,
        answer_text=answer_text,
        citations=citations,
        confidence=structured.confidence,
        abstained=False,
        retrieval=retrieval,
    )
