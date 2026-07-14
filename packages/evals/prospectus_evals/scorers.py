"""Eval scorers — what each measures (interview-ready).

Recall@k
  Did we retrieve *any* chunk from the gold ticker+section in the top-k?
  Measures coverage of the retrieval stage. Binary per query; average over set.

MRR (Mean Reciprocal Rank)
  1/rank of the first gold hit (0 if missing). Measures how *high* the right
  section is ranked, not just whether it appears somewhere in top-k.

Faithfulness (LLM-as-judge)
  Given the answer and the retrieved context, does the answer invent facts
  outside that context? Measures generation grounding — separate from whether
  retrieval found the gold section.

Citation accuracy
  For each citation, does the cited chunk/section actually contain the excerpt
  (and match the cited section metadata)? Measures whether citation pointers
  are real, not decorative.
"""

from __future__ import annotations

import os
import re
from typing import Any, Sequence

import anthropic
from prospectus_shared import Answer, Chunk, Citation

ScoreDict = dict[str, Any]


def _normalize(text: str) -> str:
    """Collapse whitespace for membership checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def is_gold_hit(
    chunk: Chunk,
    *,
    gold_ticker: str,
    gold_section_id: str,
    gold_chunk_id: str | None = None,
) -> bool:
    """Return True if chunk matches the gold section (ticker + section_id).

    Prefer section-level match (spec: gold *source section*). Exact chunk_id
    is also accepted when present.
    """
    if gold_chunk_id and chunk.chunk_id == gold_chunk_id:
        return True
    return (
        chunk.ticker.upper() == gold_ticker.upper()
        and chunk.section_id == gold_section_id
    )


def first_gold_rank(
    chunks: Sequence[Chunk],
    *,
    gold_ticker: str,
    gold_section_id: str,
    gold_chunk_id: str | None = None,
) -> int | None:
    """1-based rank of the first gold hit, or None."""
    for index, chunk in enumerate(chunks, start=1):
        if is_gold_hit(
            chunk,
            gold_ticker=gold_ticker,
            gold_section_id=gold_section_id,
            gold_chunk_id=gold_chunk_id,
        ):
            return index
    return None


def recall_at_k(
    chunks: Sequence[Chunk],
    *,
    gold_ticker: str,
    gold_section_id: str,
    gold_chunk_id: str | None = None,
    k: int,
) -> float:
    """1.0 if a gold section chunk appears in top-k, else 0.0."""
    rank = first_gold_rank(
        chunks[:k],
        gold_ticker=gold_ticker,
        gold_section_id=gold_section_id,
        gold_chunk_id=gold_chunk_id,
    )
    return 1.0 if rank is not None else 0.0


def mean_reciprocal_rank(
    chunks: Sequence[Chunk],
    *,
    gold_ticker: str,
    gold_section_id: str,
    gold_chunk_id: str | None = None,
) -> float:
    """Reciprocal rank of the first gold hit (0 if absent)."""
    rank = first_gold_rank(
        chunks,
        gold_ticker=gold_ticker,
        gold_section_id=gold_section_id,
        gold_chunk_id=gold_chunk_id,
    )
    return 0.0 if rank is None else 1.0 / float(rank)


def citation_accuracy(answer: Answer) -> float:
    """Fraction of citations whose excerpt appears in the cited retrieved chunk.

    Uses retrieval trace on the Answer when available. Citations that reference
    unknown chunk_ids score as incorrect.
    """
    if answer.abstained:
        # Abstention with no citations is vacuously correct for this metric.
        return 1.0 if not answer.citations else 0.0
    if not answer.citations:
        return 0.0

    by_id: dict[str, Chunk] = {}
    if answer.retrieval is not None:
        by_id = {c.chunk_id: c for c in answer.retrieval.chunks}

    correct = 0
    for cite in answer.citations:
        if _citation_is_accurate(cite, by_id):
            correct += 1
    return correct / len(answer.citations)


def _citation_is_accurate(cite: Citation, by_id: dict[str, Chunk]) -> bool:
    """Check excerpt grounding + section metadata consistency."""
    chunk = by_id.get(cite.chunk_id)
    if chunk is None:
        return False
    if cite.ticker.upper() != chunk.ticker.upper():
        return False
    if cite.section_id != chunk.section_id:
        return False
    excerpt = _normalize(cite.excerpt)
    body = _normalize(chunk.text)
    return bool(excerpt) and len(excerpt) >= 8 and excerpt in body


def faithfulness(
    answer: Answer,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-sonnet-4-5",
) -> float:
    """LLM-as-judge: is the answer supported by retrieved context only?

    Returns 1.0 (faithful), 0.5 (partial), or 0.0 (unfaithful/abstain mishap).
    Abstentions with the insufficient-evidence message score 1.0 (correct behavior).
    """
    if answer.abstained:
        return 1.0

    context_chunks = answer.retrieval.chunks if answer.retrieval else []
    if not context_chunks:
        return 0.0

    context = "\n\n".join(
        f"[{c.ticker} {c.section_title}]\n{c.text}" for c in context_chunks[:8]
    )
    prompt = (
        "You are evaluating faithfulness of an answer to retrieved SEC filing context.\n"
        "Score ONLY whether the answer's claims are supported by the context.\n"
        "Do NOT reward or penalize for missing information that isn't in context.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"ANSWER:\n{answer.answer_text}\n\n"
        "Reply with exactly one token: FAITHFUL, PARTIAL, or UNFAITHFUL."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_client = client or anthropic.Anthropic(api_key=api_key)
    try:
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=16,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        # Don't abort a full experiment if the judge is rate-limited / out of credit.
        raise RuntimeError(f"faithfulness judge failed: {exc}") from exc

    text = ""
    for block in message.content:
        if hasattr(block, "text"):
            text += block.text
    token = text.strip().upper().split()[0] if text.strip() else "UNFAITHFUL"
    if token.startswith("FAITHFUL"):
        return 1.0
    if token.startswith("PARTIAL"):
        return 0.5
    return 0.0


# --- Braintrust-compatible scorer wrappers (output = task result dict) ---


def bt_recall_at_5(output: dict[str, Any], expected: dict[str, Any]) -> ScoreDict:
    """Braintrust scorer: Recall@5."""
    chunks = _chunks_from_output(output)
    value = recall_at_k(
        chunks,
        gold_ticker=expected["gold_ticker"],
        gold_section_id=expected["gold_section_id"],
        gold_chunk_id=expected.get("gold_chunk_id"),
        k=5,
    )
    return {"name": "recall_at_5", "score": value}


def bt_recall_at_10(output: dict[str, Any], expected: dict[str, Any]) -> ScoreDict:
    """Braintrust scorer: Recall@10."""
    chunks = _chunks_from_output(output)
    value = recall_at_k(
        chunks,
        gold_ticker=expected["gold_ticker"],
        gold_section_id=expected["gold_section_id"],
        gold_chunk_id=expected.get("gold_chunk_id"),
        k=10,
    )
    return {"name": "recall_at_10", "score": value}


def bt_mrr(output: dict[str, Any], expected: dict[str, Any]) -> ScoreDict:
    """Braintrust scorer: MRR."""
    chunks = _chunks_from_output(output)
    value = mean_reciprocal_rank(
        chunks,
        gold_ticker=expected["gold_ticker"],
        gold_section_id=expected["gold_section_id"],
        gold_chunk_id=expected.get("gold_chunk_id"),
    )
    return {"name": "mrr", "score": value}


def bt_citation_accuracy(output: dict[str, Any], expected: dict[str, Any]) -> ScoreDict:
    """Braintrust scorer: citation accuracy."""
    del expected  # gold section not required; uses answer citations vs retrieval
    answer = Answer.model_validate(output["answer"])
    return {"name": "citation_accuracy", "score": citation_accuracy(answer)}


def bt_faithfulness(output: dict[str, Any], expected: dict[str, Any]) -> ScoreDict:
    """Braintrust scorer: faithfulness (LLM-as-judge)."""
    del expected
    answer = Answer.model_validate(output["answer"])
    return {"name": "faithfulness", "score": faithfulness(answer)}


def _chunks_from_output(output: dict[str, Any]) -> list[Chunk]:
    """Extract retrieved chunks from a task output payload."""
    answer = Answer.model_validate(output["answer"])
    if answer.retrieval is None:
        return []
    return list(answer.retrieval.chunks)
