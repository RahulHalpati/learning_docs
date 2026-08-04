"""Pure business logic — no framework, no I/O. This is what unit tests love:
deterministic functions you can call directly and assert on.
"""

from __future__ import annotations

import re
import secrets
import string

_ALPHABET = string.ascii_lowercase + string.digits
_SLUG_RE = re.compile(r"^[a-z0-9]{3,32}$")
_ALLOWED_SCHEMES = {"http", "https"}


def is_valid_url(url: str) -> bool:
    """A deliberately strict URL check: http(s) scheme and a non-empty host."""
    if not url or len(url) > 2048:
        return False
    match = re.match(r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.\-]*)://(?P<host>[^/\s]+)", url)
    if not match:
        return False
    return match.group("scheme").lower() in _ALLOWED_SCHEMES


def generate_slug(n: int = 6) -> str:
    """A random, URL-safe short code using a cryptographically secure RNG."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))


def normalize_url(url: str) -> str:
    """Trim whitespace and a single trailing slash so equivalent URLs match."""
    url = url.strip()
    return url[:-1] if url.endswith("/") and url.count("/") > 2 else url
