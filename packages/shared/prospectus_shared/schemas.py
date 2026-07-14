"""Core domain schemas.

Every retrieved/generated answer must be citeable back to a filing section.
An Answer without citations is a bug (unless it abstains).
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RetrievalStrategy(str, Enum):
    """Retrieval config / stage as a parameter — not a hardcoded code path.

    Eval configs (the three we compare in EVAL_REPORT): dense | hybrid | hybrid_rerank.
    KEYWORD is a stage module (Phase 4), callable independently but not an eval config.
    """

    DENSE = "dense"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"


class Chunk(BaseModel):
    """A structure-aware text unit from a filing, carrying citation metadata.

    Section fields are required so generation can cite Item/section without
    guessing from the raw text alone.
    """

    chunk_id: str = Field(..., description="Stable unique id for this chunk.")
    text: str = Field(..., min_length=1, description="Chunk body text.")
    token_count: int = Field(..., ge=1, description="Approximate token count.")

    # Filing identity
    ticker: str = Field(..., min_length=1, description="Issuer ticker symbol.")
    cik: str = Field(..., min_length=1, description="SEC CIK, zero-padded.")
    company_name: str = Field(..., min_length=1)
    form_type: Literal["10-K", "10-Q"] = Field(..., description="SEC form type.")
    filing_date: date = Field(..., description="SEC filing date.")
    accession_number: str = Field(
        ...,
        description="EDGAR accession number (e.g. 0001045810-25-000001).",
    )
    source_url: str = Field(..., description="EDGAR URL for the primary document.")

    # Structure / citation anchors
    section_id: str = Field(
        ...,
        description="Normalized section key, e.g. 'item_1a' or 'unknown'.",
    )
    section_title: str = Field(
        ...,
        description="Human-readable section title, e.g. 'Item 1A — Risk Factors'.",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="0-based index of this chunk within the filing.",
    )


class Citation(BaseModel):
    """Pointer from a claim in an Answer back to a filing section (and chunk)."""

    citation_id: str = Field(..., description="Id used for inline markers, e.g. 'c1'.")
    chunk_id: str = Field(..., description="Retrieved chunk that supports the claim.")
    ticker: str
    form_type: Literal["10-K", "10-Q"]
    filing_date: date
    section_id: str
    section_title: str
    excerpt: str = Field(
        ...,
        min_length=1,
        description="Short supporting passage shown in the citation drawer.",
    )
    source_url: str


class RetrievalResult(BaseModel):
    """Ranked chunks returned by a retrieval strategy."""

    query: str = Field(..., min_length=1)
    strategy: RetrievalStrategy
    chunks: list[Chunk] = Field(default_factory=list)
    scores: list[float] = Field(
        default_factory=list,
        description="Relevance scores aligned 1:1 with chunks (higher is better).",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="End-to-end retrieval latency in milliseconds, if measured.",
    )

    @model_validator(mode="after")
    def scores_match_chunks(self) -> RetrievalResult:
        """Ensure scores and chunks stay aligned for evals."""
        if self.scores and len(self.scores) != len(self.chunks):
            raise ValueError("scores must be the same length as chunks")
        return self


class Answer(BaseModel):
    """Grounded answer, or an explicit abstention when evidence is insufficient."""

    query: str = Field(..., min_length=1)
    strategy: RetrievalStrategy
    answer_text: str = Field(
        ...,
        description="Natural-language answer, or the insufficient-evidence message.",
    )
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model/system confidence in [0, 1].",
    )
    abstained: bool = Field(
        ...,
        description="True when the system refused to answer for lack of evidence.",
    )
    retrieval: RetrievalResult | None = Field(
        default=None,
        description="Optional retrieval trace for UI/debug/evals.",
    )

    @model_validator(mode="after")
    def citations_required_unless_abstained(self) -> Answer:
        """Architectural rule: answers without citations are bugs unless abstained."""
        if not self.abstained and not self.citations:
            raise ValueError("non-abstained Answer must include at least one Citation")
        return self
