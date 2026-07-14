"""Claude structured-output generation over retrieved evidence."""

from __future__ import annotations

import os
from typing import Sequence

import anthropic
from prospectus_shared import Chunk, RetrievalResult

from prospectus_generation.llm_schema import StructuredGeneration

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 2048


def resolve_model(model: str | None = None) -> str:
    """Resolve Claude model id: explicit arg > ANTHROPIC_MODEL > default."""
    if model is not None:
        return model
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)


def resolve_max_tokens(max_tokens: int | None = None) -> int:
    """Resolve max_tokens: explicit arg > ANTHROPIC_MAX_TOKENS > default."""
    if max_tokens is not None:
        return max_tokens
    raw = os.getenv("ANTHROPIC_MAX_TOKENS")
    if raw is None or raw.strip() == "":
        return DEFAULT_MAX_TOKENS
    return int(raw)


def _format_evidence(chunks: Sequence[Chunk]) -> str:
    """Render evidence blocks with closed-set chunk_ids for the model."""
    blocks: list[str] = []
    for chunk in chunks:
        header = (
            f"chunk_id={chunk.chunk_id}\n"
            f"ticker={chunk.ticker} form={chunk.form_type} "
            f"filed={chunk.filing_date} section={chunk.section_title}"
        )
        blocks.append(f"---\n{header}\nTEXT:\n{chunk.text}\n")
    return "\n".join(blocks)


def generate_structured(
    query: str,
    chunks: Sequence[Chunk],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    client: anthropic.Anthropic | None = None,
) -> StructuredGeneration:
    """Ask Claude for a StructuredGeneration constrained by output_format.

    Structural constraint #1: `output_format=StructuredGeneration` forces a
    typed JSON shape (claims with chunk_id + excerpt), not free-form prose.
    Structural constraint #2: the prompt enumerates allowed chunk_ids; post-
    validation in grounding.py rejects anything outside that set.

    Model / max_tokens: keyword args override env
    (`ANTHROPIC_MODEL`, `ANTHROPIC_MAX_TOKENS`), which override defaults.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if client is None and not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required. Set it in the environment or .env."
        )
    anthropic_client = client or anthropic.Anthropic(api_key=api_key)
    resolved_model = resolve_model(model)
    resolved_max_tokens = resolve_max_tokens(max_tokens)

    allowed_ids = [chunk.chunk_id for chunk in chunks]
    if not allowed_ids:
        # No evidence → deterministic abstain without calling the model.
        return StructuredGeneration(
            abstain=True,
            confidence=0.0,
            answer_text=(
                "I don't have enough evidence in these filings to answer "
                "that confidently."
            ),
            claims=[],
        )

    system = (
        "You are Prospectus, a research assistant over SEC 10-K/10-Q filings. "
        "Answer ONLY from the evidence chunks. Every factual claim must cite a "
        "chunk_id from the allowed list. Copy excerpts verbatim from the chunk "
        "text. If evidence is weak or missing, set abstain=true and do not guess. "
        "Never invent tickers, sections, numbers, or chunk_ids."
    )
    user = (
        f"Question:\n{query}\n\n"
        f"Allowed chunk_ids (cite ONLY these):\n"
        f"{allowed_ids}\n\n"
        f"Evidence:\n{_format_evidence(chunks)}\n\n"
        "Return structured JSON. Put inline markers like [c1], [c2] in answer_text "
        "aligned with the order of claims. Prefer abstain over speculation."
    )

    parsed = anthropic_client.messages.parse(
        model=resolved_model,
        max_tokens=resolved_max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=StructuredGeneration,
    )
    structured = parsed.parsed_output
    if structured is None:
        return StructuredGeneration(
            abstain=True,
            confidence=0.0,
            answer_text=(
                "I don't have enough evidence in these filings to answer "
                "that confidently."
            ),
            claims=[],
        )
    return structured


def generate_from_retrieval(
    retrieval: RetrievalResult,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    client: anthropic.Anthropic | None = None,
) -> StructuredGeneration:
    """Generate structured output from a RetrievalResult."""
    return generate_structured(
        retrieval.query,
        retrieval.chunks,
        model=model,
        max_tokens=max_tokens,
        client=client,
    )
