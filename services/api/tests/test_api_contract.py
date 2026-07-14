"""API contract tests — request validation, health, caps (no live DB)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import (
    QueryRequest,
    _cors_origins,
    _retrieval_candidate_depth,
    _retrieval_top_k,
    app,
)
from prospectus_shared import Chunk, RetrievalResult, RetrievalStrategy


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="   ")


def test_query_request_rejects_top_k_over_cap() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="CoWoS", top_k=999)


def test_query_request_rejects_candidate_depth_over_cap() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="CoWoS", candidate_depth=500)


def test_retrieval_helpers_clamp() -> None:
    assert _retrieval_top_k(None) is None
    assert _retrieval_top_k(3) == 3
    assert _retrieval_top_k(999) == 20
    assert _retrieval_candidate_depth(50) == 50
    assert _retrieval_candidate_depth(999) == 50
    assert _retrieval_candidate_depth(1) == 5


def test_cors_defaults_include_production_not_wildcard() -> None:
    origins = _cors_origins()
    assert "https://prospectus-nickarndt.vercel.app" in origins
    assert "http://localhost:3000" in origins
    assert not any("*" in o for o in origins)


def test_query_retrieval_only_mocked(client: TestClient) -> None:
    """POST /query with generate=false must not require Claude/DB when mocked."""
    chunk = Chunk(
        chunk_id="c1",
        text="NVIDIA discusses CoWoS packaging for AI GPUs.",
        token_count=8,
        ticker="NVDA",
        cik="0001045810",
        company_name="NVIDIA Corp",
        form_type="10-K",
        filing_date=date(2026, 2, 25),
        accession_number="0001045810-26-000021",
        source_url="https://example.com",
        section_id="item_1_business",
        section_title="Item 1. Business",
        chunk_index=0,
    )
    fake = RetrievalResult(
        query="What is CoWoS?",
        strategy=RetrievalStrategy.HYBRID,
        chunks=[chunk],
        scores=[0.91],
        latency_ms=12.0,
    )

    with patch("app.main.retrieve", return_value=fake):
        response = client.post(
            "/query",
            json={
                "query": "What is CoWoS?",
                "strategy": "hybrid",
                "generate": False,
                "top_k": 3,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["generate"] is False
    assert body["abstained"] is True or body["retrieval"] is not None
    assert body["retrieval"]["chunks"][0]["ticker"] == "NVDA"
    assert "per_ip_remaining" in body
    assert "global_remaining" in body
    assert isinstance(body["per_ip_remaining"], int)


def test_query_rejects_oversized_top_k_at_http(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={"query": "x", "top_k": 999, "generate": False},
    )
    assert response.status_code == 422


def test_query_retrieval_rate_limit_returns_429(client: TestClient) -> None:
    """Exhausted retrieval budget must 429 before calling providers."""
    from app.rate_limit import BudgetDecision

    denied = BudgetDecision(
        allowed=False,
        reason="Daily retrieval limit for this visitor reached (1/day).",
        per_ip_remaining=0,
        global_remaining=10,
    )
    with (
        patch("app.main.retrieval_budget.check_and_consume", return_value=denied),
        patch("app.main.retrieve") as retrieve_mock,
    ):
        response = client.post(
            "/query",
            json={"query": "CoWoS", "strategy": "dense", "generate": False},
        )
    assert response.status_code == 429
    assert "retrieval" in response.json()["detail"].lower()
    retrieve_mock.assert_not_called()
