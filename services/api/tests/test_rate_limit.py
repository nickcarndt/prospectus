"""Unit tests for generation and retrieval budget counters."""

from __future__ import annotations

from app.rate_limit import GenerateBudget, RetrievalBudget


def test_per_ip_budget_exhausts() -> None:
    budget = GenerateBudget(per_ip_per_day=2, global_per_day=100)
    first = budget.check_and_consume("1.1.1.1")
    second = budget.check_and_consume("1.1.1.1")
    third = budget.check_and_consume("1.1.1.1")

    assert first.allowed is True
    assert first.per_ip_remaining == 1
    assert second.allowed is True
    assert second.per_ip_remaining == 0
    assert third.allowed is False
    assert third.per_ip_remaining == 0
    assert "limit" in (third.reason or "").lower()


def test_global_budget_blocks_other_ips() -> None:
    budget = GenerateBudget(per_ip_per_day=10, global_per_day=1)
    assert budget.check_and_consume("a").allowed is True
    denied = budget.check_and_consume("b")
    assert denied.allowed is False
    assert denied.global_remaining == 0


def test_remaining_counts_decrement() -> None:
    budget = GenerateBudget(per_ip_per_day=3, global_per_day=5)
    decision = budget.check_and_consume("ip")
    assert decision.per_ip_remaining == 2
    assert decision.global_remaining == 4


def test_peek_does_not_consume() -> None:
    budget = GenerateBudget(per_ip_per_day=2, global_per_day=10)
    first = budget.peek("ip")
    second = budget.peek("ip")
    assert first.per_ip_remaining == 2
    assert second.per_ip_remaining == 2
    budget.check_and_consume("ip")
    assert budget.peek("ip").per_ip_remaining == 1


def test_retrieval_budget_exhausts_per_ip() -> None:
    budget = RetrievalBudget(per_ip_per_day=1, global_per_day=100)
    assert budget.check_and_consume("ip").allowed is True
    denied = budget.check_and_consume("ip")
    assert denied.allowed is False
    assert "retrieval" in (denied.reason or "").lower()
