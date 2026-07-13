"""Exception hierarchy for pokesdk.

Every error a caller can catch derives from :class:`PokeError`, so users can
write ``except PokeError`` to catch anything from the SDK, or catch a specific
subclass when they want finer control.
"""

from __future__ import annotations

from typing import Optional

import httpx


class PokeError(Exception):
    """Base class for every error raised by pokesdk."""


class PokeConnectionError(PokeError):
    """The request never got a response (DNS failure, timeout, refused, ...)."""

    def __init__(self, message: str, *, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause


class APIError(PokeError):
    """The server returned a response, but it was an HTTP error status.

    Carries the status code and the originating response so callers can inspect
    headers or the raw body when they need to.
    """

    def __init__(self, message: str, *, response: httpx.Response) -> None:
        super().__init__(message)
        self.response = response
        self.status_code = response.status_code


class NotFoundError(APIError):
    """404 — the requested resource does not exist."""


class AuthenticationError(APIError):
    """401/403 — the API key is missing, wrong, or not allowed."""


class RateLimitError(APIError):
    """429 — too many requests; back off and retry later."""


class ServerError(APIError):
    """5xx — the server failed to handle a valid request."""


def error_from_response(response: httpx.Response) -> APIError:
    """Map an HTTP error response onto the most specific APIError subclass."""
    status = response.status_code
    msg = f"{status} {response.reason_phrase} for {response.request.method} {response.request.url}"
    if status in (401, 403):
        return AuthenticationError(msg, response=response)
    if status == 404:
        return NotFoundError(msg, response=response)
    if status == 429:
        return RateLimitError(msg, response=response)
    if status >= 500:
        return ServerError(msg, response=response)
    return APIError(msg, response=response)
