"""Trusted client IP extraction for rate limits."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.main import _client_key


def _request(
    *,
    headers: dict[str, str] | None = None,
    host: str | None = "10.0.0.1",
) -> MagicMock:
    """Build a minimal Starlette-like Request mock."""
    req = MagicMock()
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    req.headers.get.side_effect = lambda key, default=None: hdrs.get(
        key.lower(), default
    )
    if host is None:
        req.client = None
    else:
        req.client = MagicMock()
        req.client.host = host
    return req


def test_prefers_x_real_ip_over_xff() -> None:
    req = _request(
        headers={
            "x-real-ip": "203.0.113.9",
            "x-forwarded-for": "1.1.1.1, 203.0.113.9",
        }
    )
    assert _client_key(req) == "203.0.113.9"


def test_xff_uses_rightmost_not_spoofed_prefix() -> None:
    """Attacker-prepended leftmost IPs must not become the budget key."""
    req = _request(headers={"x-forwarded-for": "8.8.8.8, 9.9.9.9, 198.51.100.4"})
    assert _client_key(req) == "198.51.100.4"


def test_falls_back_to_direct_client_host() -> None:
    req = _request(headers={}, host="127.0.0.1")
    assert _client_key(req) == "127.0.0.1"
