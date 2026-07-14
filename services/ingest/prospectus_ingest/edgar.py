"""Thin SEC EDGAR HTTP client.

SEC fair-access rules: identify via User-Agent (app + contact email) and stay
under 10 requests/second. See https://www.sec.gov/os/accessing-edgar-data
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


class EdgarClient:
    """Rate-limited EDGAR client with required User-Agent identification."""

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        min_interval_s: float = 0.12,
        timeout_s: float = 60.0,
    ) -> None:
        """Create a client.

        Args:
            user_agent: Value for the User-Agent header. Defaults to SEC_USER_AGENT.
            min_interval_s: Minimum seconds between requests (< 10 req/s).
            timeout_s: Per-request timeout.
        """
        resolved = user_agent or os.getenv("SEC_USER_AGENT")
        if not resolved:
            raise ValueError(
                "SEC_USER_AGENT is required "
                '(e.g. "Prospectus Research you@example.com"). '
                "Set it in the environment or .env."
            )
        self._min_interval_s = min_interval_s
        self._last_request_at = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": resolved,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=timeout_s,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> EdgarClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _throttle(self) -> None:
        """Sleep if needed to respect the SEC rate limit."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_at = time.monotonic()

    def get_json(self, url: str) -> Any:
        """GET JSON from EDGAR."""
        self._throttle()
        response = self._client.get(url)
        response.raise_for_status()
        return response.json()

    def get_bytes(self, url: str) -> bytes:
        """GET raw bytes (filing HTML/text)."""
        self._throttle()
        response = self._client.get(url)
        response.raise_for_status()
        return response.content

    def load_ticker_to_cik(self) -> dict[str, str]:
        """Return uppercase ticker -> zero-padded 10-digit CIK."""
        payload = self.get_json(TICKERS_URL)
        mapping: dict[str, str] = {}
        for row in payload.values():
            ticker = str(row["ticker"]).upper()
            cik = str(row["cik_str"]).zfill(10)
            mapping[ticker] = cik
        return mapping

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        """Fetch the submissions JSON for a CIK."""
        return self.get_json(SUBMISSIONS_URL.format(cik=cik.zfill(10)))

    @staticmethod
    def document_url(cik: str, accession_number: str, primary_document: str) -> str:
        """Build the Archives URL for a filing's primary document."""
        cik_numeric = str(int(cik))  # strip leading zeros for path
        accession_nodash = accession_number.replace("-", "")
        return (
            f"{ARCHIVES_BASE}/{cik_numeric}/{accession_nodash}/{primary_document}"
        )
