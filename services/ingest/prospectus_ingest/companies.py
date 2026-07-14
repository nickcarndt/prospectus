"""Universe of issuers for the Prospectus corpus.

Fifteen liquid names spanning big tech and financials — enough variety for
hybrid-retrieval evals without an unmanageable download.
"""

from __future__ import annotations

# ticker -> display hint only; CIK resolved live from SEC company_tickers.json
TICKERS: tuple[str, ...] = (
    "NVDA",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "JPM",
    "V",
    "MA",
    "NFLX",
    "AMD",
    "CRM",
    "ORCL",
    "INTC",
)

# Forms we care about for Phase 2+
TARGET_FORMS: frozenset[str] = frozenset({"10-K", "10-Q"})
