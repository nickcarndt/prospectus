"""FastAPI application — health + grounded /query over SEC filings."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prospectus_generation.answer import answer_query
from prospectus_generation.grounding import build_abstained_answer
from prospectus_retrieval.hybrid import DEFAULT_CANDIDATE_DEPTH
from prospectus_retrieval.retrieve import retrieve
from prospectus_shared import Answer, Citation, RetrievalResult, RetrievalStrategy
from pydantic import BaseModel, Field, field_validator

# Load repo-root .env when running locally (Railway injects env directly).
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()

EvalStrategy = Literal["dense", "hybrid", "hybrid_rerank"]


class HealthResponse(BaseModel):
    """Liveness payload for load balancers and local smoke checks."""

    status: str


class QueryRequest(BaseModel):
    """UI/API request for retrieve (+ optional generate)."""

    query: str = Field(..., min_length=1, max_length=4000)
    strategy: EvalStrategy = "hybrid_rerank"
    top_k: int | None = Field(default=None, ge=1, le=50)
    candidate_depth: int = Field(default=DEFAULT_CANDIDATE_DEPTH, ge=5, le=100)
    generate: bool = Field(
        default=True,
        description="If false, return retrieval only (demo toggle / no Claude).",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        """Reject whitespace-only queries."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned


class QueryResponse(BaseModel):
    """Answer schema plus e2e latency and optional generation error."""

    query: str
    strategy: RetrievalStrategy
    answer_text: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    abstained: bool
    retrieval: RetrievalResult | None = None
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="End-to-end request latency in milliseconds.",
    )
    generate: bool = Field(
        default=True,
        description="Echo of request.generate — false means retrieval-only.",
    )
    error: str | None = Field(
        default=None,
        description="Set when generation failed; retrieval may still be present.",
    )


def _cors_origins() -> list[str]:
    """Local Next.js + optional Vercel origins from CORS_ORIGINS env."""
    defaults = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    parsed = [origin.strip() for origin in extra.split(",") if origin.strip()]
    return defaults + parsed


app = FastAPI(
    title="Prospectus API",
    description="Hybrid-retrieval research API over SEC filings.",
    version="0.8.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service liveness (does not verify DB or provider keys)."""
    return HealthResponse(status="ok")


def _answer_to_response(
    answer: Answer,
    *,
    latency_ms: float,
    generate: bool,
    error: str | None = None,
) -> QueryResponse:
    """Map shared Answer → API QueryResponse."""
    return QueryResponse(
        query=answer.query,
        strategy=answer.strategy,
        answer_text=answer.answer_text,
        citations=answer.citations,
        confidence=answer.confidence,
        abstained=answer.abstained,
        retrieval=answer.retrieval,
        latency_ms=latency_ms,
        generate=generate,
        error=error,
    )


def _friendly_generation_error(raw: str) -> str:
    """Map provider errors to short UI-safe messages."""
    lower = raw.lower()
    if "credit" in lower or "too low" in lower or "billing" in lower:
        return (
            "Generation unavailable: Anthropic API credits exhausted. "
            "Retrieved chunks are still shown below."
        )
    if "api_key" in lower or "anthropic" in lower:
        return f"Generation failed: {raw}"
    return f"Query error: {raw}"


@app.post("/query", response_model=QueryResponse)
def query_endpoint(body: QueryRequest) -> QueryResponse:
    """Retrieve (and optionally generate) a grounded answer.

    Strategy is a parameter (dense | hybrid | hybrid_rerank). When generate
    is false, returns retrieval chunks only so the UI can demo rank changes
    without calling Claude. Generation failures return retrieval + error.
    """
    strategy = RetrievalStrategy(body.strategy)
    started = time.perf_counter()

    if not body.generate:
        try:
            retrieval = retrieve(
                body.query,
                strategy=strategy,
                top_k=body.top_k,
                candidate_depth=body.candidate_depth,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=503,
                detail=f"Retrieval failed: {exc}",
            ) from exc
        answer = build_abstained_answer(
            query=body.query,
            strategy=strategy,
            confidence=0.0,
            retrieval=retrieval,
            reason="",
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return _answer_to_response(
            answer, latency_ms=latency_ms, generate=False
        )

    try:
        answer = answer_query(
            body.query,
            strategy=strategy,
            top_k=body.top_k,
            candidate_depth=body.candidate_depth,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return _answer_to_response(
            answer, latency_ms=latency_ms, generate=True
        )
    except Exception as exc:  # noqa: BLE001 — surface provider/DB errors cleanly
        message = str(exc)
        try:
            retrieval = retrieve(
                body.query,
                strategy=strategy,
                top_k=body.top_k,
                candidate_depth=body.candidate_depth,
            )
        except Exception as retrieve_exc:  # noqa: BLE001
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Query failed: {message}; "
                    f"retrieve also failed: {retrieve_exc}"
                ),
            ) from retrieve_exc

        # Keep retrieval visible; do not pretend we abstained for lack of evidence.
        answer = build_abstained_answer(
            query=body.query,
            strategy=strategy,
            confidence=0.0,
            retrieval=retrieval,
            reason="",
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return _answer_to_response(
            answer,
            latency_ms=latency_ms,
            generate=True,
            error=_friendly_generation_error(message),
        )
