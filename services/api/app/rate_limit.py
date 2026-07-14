"""In-memory budgets for public-demo spend (Claude + retrieval providers).

Generation burns Anthropic. Retrieval burns OpenAI embeddings and (on
hybrid_rerank) Cohere — so /query is capped per IP as well. Counters are
process-local and reset on redeploy (acceptable for a single-replica demo).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import date


def _env_int(name: str, default: int) -> int:
    """Parse a non-negative int env var, falling back to default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


@dataclass(frozen=True)
class BudgetDecision:
    """Result of checking (and optionally consuming) a daily quota."""

    allowed: bool
    reason: str | None = None
    per_ip_remaining: int = 0
    global_remaining: int = 0


# Back-compat alias for existing imports/tests.
GenerateBudgetDecision = BudgetDecision


class DailyBudget:
    """UTC-day counters: per client IP + global."""

    def __init__(
        self,
        *,
        per_ip_per_day: int,
        global_per_day: int,
        exhausted_ip_reason: str,
        exhausted_global_reason: str,
    ) -> None:
        """Configure caps and human-readable denial messages."""
        self.per_ip_per_day = per_ip_per_day
        self.global_per_day = global_per_day
        self.exhausted_ip_reason = exhausted_ip_reason
        self.exhausted_global_reason = exhausted_global_reason
        self._lock = threading.Lock()
        self._day: date = date.today()
        self._per_ip: dict[str, int] = {}
        self._global: int = 0

    def _roll_day_locked(self) -> None:
        """Reset counters when the UTC calendar day changes."""
        today = date.today()
        if today != self._day:
            self._day = today
            self._per_ip.clear()
            self._global = 0

    def peek(self, client_key: str) -> BudgetDecision:
        """Return remaining quota without consuming a slot."""
        key = (client_key or "unknown").strip() or "unknown"
        with self._lock:
            self._roll_day_locked()
            used_ip = self._per_ip.get(key, 0)
            return BudgetDecision(
                allowed=used_ip < self.per_ip_per_day
                and self._global < self.global_per_day,
                per_ip_remaining=max(0, self.per_ip_per_day - used_ip),
                global_remaining=max(0, self.global_per_day - self._global),
            )

    def check_and_consume(self, client_key: str) -> BudgetDecision:
        """Atomically allow one call or return a denial reason.

        Args:
            client_key: Trusted client id (IP, or "unknown").
        """
        key = (client_key or "unknown").strip() or "unknown"
        with self._lock:
            self._roll_day_locked()
            used_ip = self._per_ip.get(key, 0)
            ip_remaining = max(0, self.per_ip_per_day - used_ip)
            global_remaining = max(0, self.global_per_day - self._global)

            if used_ip >= self.per_ip_per_day:
                return BudgetDecision(
                    allowed=False,
                    reason=self.exhausted_ip_reason.format(
                        per_ip=self.per_ip_per_day
                    ),
                    per_ip_remaining=0,
                    global_remaining=global_remaining,
                )
            if self._global >= self.global_per_day:
                return BudgetDecision(
                    allowed=False,
                    reason=self.exhausted_global_reason.format(
                        global_cap=self.global_per_day
                    ),
                    per_ip_remaining=ip_remaining,
                    global_remaining=0,
                )

            self._per_ip[key] = used_ip + 1
            self._global += 1
            return BudgetDecision(
                allowed=True,
                per_ip_remaining=max(0, self.per_ip_per_day - (used_ip + 1)),
                global_remaining=max(0, self.global_per_day - self._global),
            )


class GenerateBudget(DailyBudget):
    """Daily Claude generation budget (per IP + global)."""

    def __init__(
        self,
        *,
        per_ip_per_day: int | None = None,
        global_per_day: int | None = None,
    ) -> None:
        """Load caps from args or GENERATE_* env vars."""
        super().__init__(
            per_ip_per_day=(
                per_ip_per_day
                if per_ip_per_day is not None
                else _env_int("GENERATE_PER_IP_PER_DAY", 3)
            ),
            global_per_day=(
                global_per_day
                if global_per_day is not None
                else _env_int("GENERATE_GLOBAL_PER_DAY", 12)
            ),
            exhausted_ip_reason=(
                "Daily generation limit for this visitor reached "
                "({per_ip}/day). Retrieval still works — "
                "try again tomorrow, or explore the strategy toggle."
            ),
            exhausted_global_reason=(
                "Public demo hit today's shared generation budget "
                "({global_cap}/day) so credits last longer. "
                "Retrieval and the config toggle still work."
            ),
        )


class RetrievalBudget(DailyBudget):
    """Daily retrieval budget (OpenAI embeddings + optional Cohere)."""

    def __init__(
        self,
        *,
        per_ip_per_day: int | None = None,
        global_per_day: int | None = None,
    ) -> None:
        """Load caps from args or RETRIEVAL_* env vars."""
        super().__init__(
            per_ip_per_day=(
                per_ip_per_day
                if per_ip_per_day is not None
                else _env_int("RETRIEVAL_PER_IP_PER_DAY", 100)
            ),
            global_per_day=(
                global_per_day
                if global_per_day is not None
                else _env_int("RETRIEVAL_GLOBAL_PER_DAY", 2000)
            ),
            exhausted_ip_reason=(
                "Daily retrieval limit for this visitor reached "
                "({per_ip}/day). Try again tomorrow."
            ),
            exhausted_global_reason=(
                "Public demo hit today's shared retrieval budget "
                "({global_cap}/day). Try again tomorrow."
            ),
        )


# Process-wide singletons used by the API.
generate_budget = GenerateBudget()
retrieval_budget = RetrievalBudget()
