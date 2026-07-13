"""Shared core for the sync and async clients.

The sync and async clients differ only in *how* they wait for I/O. Everything
else — base URL, auth headers, which statuses to retry, how long to back off —
is identical, so it lives here in one place and both clients reuse it.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger("pokesdk")

DEFAULT_BASE_URL = "https://pokeapi.co/api/v2"
# Statuses worth retrying: transient server problems and rate limits.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class BaseClient:
    """Holds configuration and the pure, transport-agnostic helpers.

    Both :class:`pokesdk.PokeClient` and :class:`pokesdk.AsyncPokeClient` inherit
    from this. None of these methods perform I/O — they only *decide* things —
    which is exactly why they can be shared.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _default_headers(self) -> dict[str, str]:
        from ._version import __version__

        headers = {
            "Accept": "application/json",
            "User-Agent": f"pokesdk/{__version__}",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _should_retry(self, *, attempt: int, status_code: Optional[int]) -> bool:
        """Retry transient failures until we run out of attempts."""
        if attempt >= self.max_retries:
            return False
        if status_code is None:  # a connection-level error, no response
            return True
        return status_code in RETRYABLE_STATUSES

    def _backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff: 0.5s, 1s, 2s, ... (attempt is 0-based)."""
        return 0.5 * (2 ** attempt)

    def _build_request(self, client: httpx.Client | httpx.AsyncClient, method: str, path: str, **kwargs) -> httpx.Request:
        """Construct an httpx.Request bound to the given client's config."""
        return client.build_request(method, path, **kwargs)
