"""FastAPI application — health + grounded /query over SEC filings."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prospectus_generation.answer import answer_query
from prospectus_generation.grounding import (
    build_abstained_answer,
    ground_structured_output,
)
from prospectus_generation.llm_schema import StructuredGeneration
from prospectus_retrieval.hybrid import DEFAULT_CANDIDATE_DEPTH
from prospectus_retrieval.retrieve import retrieve
from prospectus_shared import Answer, Citation, RetrievalResult, RetrievalStrategy
from pydantic import BaseModel, Field, field_validator

from app.rate_limit import generate_budget, retrieval_budget

# Load repo-root .env when running locally (Railway injects env directly).
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()

EvalStrategy = Literal["dense", "hybrid", "hybrid_rerank"]

# Keep generation prompts smaller on the public demo (input tokens dominate cost).
_GENERATE_TOP_K_CAP = 6
# Cap retrieval too — otherwise hybrid_rerank + wide candidate_depth amplifies
# OpenAI/Cohere spend on an unauthenticated public API.
_RETRIEVAL_TOP_K_CAP = 20
_RETRIEVAL_CANDIDATE_DEPTH_CAP = 50

# Production browser origins only (no *.vercel.app wildcard).
_DEFAULT_PRODUCTION_ORIGINS = (
    "https://prospectus-nickarndt.vercel.app",
    "https://web-drab-phi-91.vercel.app",
)


class HealthResponse(BaseModel):
    """Liveness payload for load balancers and local smoke checks."""

    status: str


class QueryRequest(BaseModel):
    """UI/API request for retrieve (+ optional generate)."""

    query: str = Field(..., min_length=1, max_length=4000)
    strategy: EvalStrategy = "hybrid_rerank"
    top_k: int | None = Field(default=None, ge=1, le=_RETRIEVAL_TOP_K_CAP)
    candidate_depth: int = Field(
        default=DEFAULT_CANDIDATE_DEPTH,
        ge=5,
        le=_RETRIEVAL_CANDIDATE_DEPTH_CAP,
    )
    generate: bool = Field(
        default=False,
        description=(
            "If true, call Claude for a cited answer (budgeted). "
            "Default false — retrieval only (free for the public demo)."
        ),
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
        default=False,
        description="Echo of request.generate — false means retrieval-only.",
    )
    error: str | None = Field(
        default=None,
        description="Set when generation failed; retrieval may still be present.",
    )
    per_ip_remaining: int = Field(
        default=0,
        ge=0,
        description="Cited answers left today for this visitor IP.",
    )
    global_remaining: int = Field(
        default=0,
        ge=0,
        description="Cited answers left today on the shared demo budget.",
    )


def _cors_origins() -> list[str]:
    """Explicit browser origins only — no wildcard regex.

    Defaults: local Next.js + known production aliases. Extra origins via
    comma-separated CORS_ORIGINS (e.g. a new custom domain).
    """
    defaults = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *_DEFAULT_PRODUCTION_ORIGINS,
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    parsed = [origin.strip() for origin in extra.split(",") if origin.strip()]
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    origins: list[str] = []
    for origin in defaults + parsed:
        if origin not in seen:
            seen.add(origin)
            origins.append(origin)
    return origins


def _client_key(request: Request) -> str:
    """Trusted client IP for rate limits (not spoofable XFF prefix).

    Prefer platform-set ``X-Real-IP`` (Railway overwrites this at the edge).
    If only ``X-Forwarded-For`` is present, use the *rightmost* hop — the
    value appended by the trusted proxy. Never use the leftmost XFF entry;
    clients can prepend arbitrary addresses.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        # Starlette may join duplicate headers with commas; take the last.
        part = real_ip.split(",")[-1].strip()
        if part:
            return part

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _generation_top_k(requested: int | None) -> int:
    """Cap evidence depth for Claude to control input-token spend."""
    if requested is None:
        return _GENERATE_TOP_K_CAP
    return max(1, min(requested, _GENERATE_TOP_K_CAP))


def _retrieval_top_k(requested: int | None) -> int | None:
    """Clamp client top_k on the retrieval path (None → strategy default)."""
    if requested is None:
        return None
    return max(1, min(requested, _RETRIEVAL_TOP_K_CAP))


def _retrieval_candidate_depth(requested: int) -> int:
    """Clamp hybrid/rerank wide-retrieve depth."""
    return max(5, min(requested, _RETRIEVAL_CANDIDATE_DEPTH_CAP))


class ReserveResponse(BaseModel):
    """Result of consuming one generation budget slot."""

    allowed: bool
    reason: str | None = None
    per_ip_remaining: int = 0
    global_remaining: int = 0


class GroundRequest(BaseModel):
    """Structured model output + retrieval for server-side grounding."""

    query: str = Field(..., min_length=1, max_length=4000)
    strategy: EvalStrategy
    structured: StructuredGeneration
    retrieval: RetrievalResult


app = FastAPI(
    title="Prospectus API",
    description="Hybrid-retrieval research API over SEC filings.",
    version="0.8.4",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
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
    client_key: str = "unknown",
) -> QueryResponse:
    """Map shared Answer → API QueryResponse (includes live budget remaining)."""
    budget = generate_budget.peek(client_key)
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
        per_ip_remaining=budget.per_ip_remaining,
        global_remaining=budget.global_remaining,
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


def _retrieve_only(
    *,
    query: str,
    strategy: RetrievalStrategy,
    top_k: int | None,
    candidate_depth: int,
    started: float,
    client_key: str,
    error: str | None = None,
) -> QueryResponse:
    """Run retrieval without Claude (always allowed for the public demo)."""
    top_k = _retrieval_top_k(top_k)
    candidate_depth = _retrieval_candidate_depth(candidate_depth)
    try:
        retrieval = retrieve(
            query,
            strategy=strategy,
            top_k=top_k,
            candidate_depth=candidate_depth,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Retrieval failed: {exc}",
        ) from exc
    answer = build_abstained_answer(
        query=query,
        strategy=strategy,
        confidence=0.0,
        retrieval=retrieval,
        reason="",
    )
    latency_ms = (time.perf_counter() - started) * 1000
    return _answer_to_response(
        answer,
        latency_ms=latency_ms,
        generate=False,
        error=error,
        client_key=client_key,
    )


@app.post("/generate/reserve", response_model=ReserveResponse)
def reserve_generation(request: Request) -> ReserveResponse:
    """Consume one Claude generation slot for this client IP.

    The Next.js AI SDK route streams Anthropic from Vercel; the browser calls
    this first so per-IP / global daily budgets still key off the visitor, not
    the Vercel edge IP.
    """
    decision = generate_budget.check_and_consume(_client_key(request))
    return ReserveResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        per_ip_remaining=decision.per_ip_remaining,
        global_remaining=decision.global_remaining,
    )


@app.post("/ground", response_model=QueryResponse)
def ground_endpoint(body: GroundRequest, request: Request) -> QueryResponse:
    """Apply structural grounding to a streamed StructuredGeneration.

    Excerpt membership + closed chunk_id set stay in Python so the AI SDK
    path cannot bypass the product invariants.
    """
    started = time.perf_counter()
    strategy = RetrievalStrategy(body.strategy)
    answer = ground_structured_output(
        body.structured,
        query=body.query,
        strategy=strategy,
        evidence=body.retrieval.chunks,
        retrieval=body.retrieval,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    return _answer_to_response(
        answer,
        latency_ms=latency_ms,
        generate=True,
        client_key=_client_key(request),
    )


@app.post("/query", response_model=QueryResponse)
def query_endpoint(body: QueryRequest, request: Request) -> QueryResponse:
    """Retrieve (and optionally generate) a grounded answer.

    Strategy is a parameter (dense | hybrid | hybrid_rerank). When generate
    is false, returns retrieval chunks only so the UI can demo rank changes
    without calling Claude. Generation is budgeted per IP and globally per day;
    if the budget is exhausted we still return retrieval + a clear error.
    """
    strategy = RetrievalStrategy(body.strategy)
    started = time.perf_counter()
    top_k = _retrieval_top_k(body.top_k)
    candidate_depth = _retrieval_candidate_depth(body.candidate_depth)
    client_key = _client_key(request)

    # Every /query path embeds (and may Cohere-rerank). Cap before spend.
    retrieval_decision = retrieval_budget.check_and_consume(client_key)
    if not retrieval_decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=retrieval_decision.reason
            or "Retrieval rate limit exceeded.",
        )

    if not body.generate:
        return _retrieve_only(
            query=body.query,
            strategy=strategy,
            top_k=top_k,
            candidate_depth=candidate_depth,
            started=started,
            client_key=client_key,
        )

    decision = generate_budget.check_and_consume(client_key)
    if not decision.allowed:
        # Soft deny: keep the research demo useful without spending credits.
        return _retrieve_only(
            query=body.query,
            strategy=strategy,
            top_k=top_k,
            candidate_depth=candidate_depth,
            started=started,
            client_key=client_key,
            error=decision.reason,
        )

    gen_top_k = _generation_top_k(top_k)
    try:
        answer = answer_query(
            body.query,
            strategy=strategy,
            top_k=gen_top_k,
            candidate_depth=candidate_depth,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return _answer_to_response(
            answer,
            latency_ms=latency_ms,
            generate=True,
            client_key=client_key,
        )
    except Exception as exc:  # noqa: BLE001 — surface provider/DB errors cleanly
        message = str(exc)
        try:
            retrieval = retrieve(
                body.query,
                strategy=strategy,
                top_k=top_k if top_k is not None else _RETRIEVAL_TOP_K_CAP,
                candidate_depth=candidate_depth,
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
            client_key=client_key,
        )
