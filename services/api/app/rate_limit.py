"""In-memory budgets for Claude generation (protects a public demo's credits).

Retrieval is unlimited. Only `generate=true` consumes Anthropic spend, so we
gate that path with per-IP and global daily caps. Single-process Railway
deploy is enough — counters reset on redeploy (acceptable for a demo).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import date


def _env_int(name: str, default: int) -> int:
    """Parse a positive int env var, falling back to default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


@dataclass(frozen=True)
class GenerateBudgetDecision:
    """Result of checking (and optionally consuming) generation quota."""

    allowed: bool
    reason: str | None = None
    per_ip_remaining: int = 0
    global_remaining: int = 0


class GenerateBudget:
    """UTC-day counters for Claude calls: per client IP + global."""

    def __init__(
        self,
        *,
        per_ip_per_day: int | None = None,
        global_per_day: int | None = None,
    ) -> None:
        """Load caps from args or env (GENERATE_PER_IP_PER_DAY / GLOBAL)."""
        self.per_ip_per_day = (
            per_ip_per_day
            if per_ip_per_day is not None
            else _env_int("GENERATE_PER_IP_PER_DAY", 3)
        )
        self.global_per_day = (
            global_per_day
            if global_per_day is not None
            else _env_int("GENERATE_GLOBAL_PER_DAY", 12)
        )
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

    def peek(self, client_key: str) -> GenerateBudgetDecision:
        """Return remaining quota without consuming a slot."""
        key = (client_key or "unknown").strip() or "unknown"
        with self._lock:
            self._roll_day_locked()
            used_ip = self._per_ip.get(key, 0)
            return GenerateBudgetDecision(
                allowed=used_ip < self.per_ip_per_day
                and self._global < self.global_per_day,
                per_ip_remaining=max(0, self.per_ip_per_day - used_ip),
                global_remaining=max(0, self.global_per_day - self._global),
            )

    def check_and_consume(self, client_key: str) -> GenerateBudgetDecision:
        """Atomically allow one generate call or return a denial reason.

        Args:
            client_key: Stable client id (IP, or "unknown").
        """
        key = (client_key or "unknown").strip() or "unknown"
        with self._lock:
            self._roll_day_locked()
            used_ip = self._per_ip.get(key, 0)
            ip_remaining = max(0, self.per_ip_per_day - used_ip)
            global_remaining = max(0, self.global_per_day - self._global)

            if used_ip >= self.per_ip_per_day:
                return GenerateBudgetDecision(
                    allowed=False,
                    reason=(
                        "Daily generation limit for this visitor reached "
                        f"({self.per_ip_per_day}/day). Retrieval still works — "
                        "try again tomorrow, or explore the strategy toggle."
                    ),
                    per_ip_remaining=0,
                    global_remaining=global_remaining,
                )
            if self._global >= self.global_per_day:
                return GenerateBudgetDecision(
                    allowed=False,
                    reason=(
                        "Public demo hit today's shared generation budget "
                        f"({self.global_per_day}/day) so credits last longer. "
                        "Retrieval and the config toggle still work."
                    ),
                    per_ip_remaining=ip_remaining,
                    global_remaining=0,
                )

            self._per_ip[key] = used_ip + 1
            self._global += 1
            return GenerateBudgetDecision(
                allowed=True,
                per_ip_remaining=max(0, self.per_ip_per_day - (used_ip + 1)),
                global_remaining=max(0, self.global_per_day - self._global),
            )


# Process-wide singleton used by the API.
generate_budget = GenerateBudget()
