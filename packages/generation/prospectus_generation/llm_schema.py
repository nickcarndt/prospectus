"""Structured output schema for Claude.

The model does not invent filing metadata — it only returns chunk_id keys from
the retrieved set. Python fills ticker/section/date from those chunks.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StructuredClaim(BaseModel):
    """One grounded claim tied to a retrieved chunk id."""

    claim_text: str = Field(
        ...,
        description="A single factual claim supported by the cited chunk.",
    )
    chunk_id: str = Field(
        ...,
        description="Must be one of the provided evidence chunk_ids.",
    )
    excerpt: str = Field(
        ...,
        description="Short verbatim quote copied from that chunk's text.",
    )


class StructuredGeneration(BaseModel):
    """Claude's constrained JSON answer shape."""

    abstain: bool = Field(
        ...,
        description="True if evidence is insufficient to answer confidently.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in [0, 1] that the answer is grounded.",
    )
    answer_text: str = Field(
        ...,
        description="Full answer with inline markers like [c1], or abstention message.",
    )
    claims: list[StructuredClaim] = Field(
        default_factory=list,
        description="Claims with chunk_id citations; empty when abstaining.",
    )
