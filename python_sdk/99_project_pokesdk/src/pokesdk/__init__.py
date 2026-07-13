"""pokesdk — a small, typed Python client for the PokéAPI.

The public API is everything exported here. Import from ``pokesdk`` directly::

    from pokesdk import PokeClient, AsyncPokeClient, NotFoundError
"""

from ._version import __version__
from .async_client import AsyncPokeClient
from .client import PokeClient
from .exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    PokeConnectionError,
    PokeError,
    RateLimitError,
    ServerError,
)
from .models import NamedResource, Page, Pokemon

__all__ = [
    "__version__",
    "PokeClient",
    "AsyncPokeClient",
    "Pokemon",
    "NamedResource",
    "Page",
    "PokeError",
    "PokeConnectionError",
    "APIError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
]
