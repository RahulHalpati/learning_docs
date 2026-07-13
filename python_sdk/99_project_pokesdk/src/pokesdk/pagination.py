"""Pagination helpers.

List endpoints return one page at a time with a ``next`` URL. Callers almost
never want to manage that by hand, so the SDK exposes iterators that walk the
pages transparently — ``for p in client.pokemon.list_all(): ...`` just works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Iterator

from .models import NamedResource, Page

if TYPE_CHECKING:  # avoid an import cycle at runtime
    from .client import PokeClient
    from .async_client import AsyncPokeClient


def iterate_pages(client: "PokeClient", path: str, *, limit: int = 20) -> Iterator[NamedResource]:
    """Yield every NamedResource across all pages, fetching lazily as you go."""
    params: dict[str, object] | None = {"limit": limit, "offset": 0}
    next_url: str | None = path
    while next_url is not None:
        data = client._request("GET", next_url, params=params)
        page = Page[NamedResource].model_validate(data)
        yield from page.results
        next_url = page.next  # already a full URL, or None on the last page
        params = None         # the `next` URL carries its own query string


async def aiterate_pages(client: "AsyncPokeClient", path: str, *, limit: int = 20) -> AsyncIterator[NamedResource]:
    """Async twin of :func:`iterate_pages`."""
    params: dict[str, object] | None = {"limit": limit, "offset": 0}
    next_url: str | None = path
    while next_url is not None:
        data = await client._request("GET", next_url, params=params)
        page = Page[NamedResource].model_validate(data)
        for item in page.results:
            yield item
        next_url = page.next
        params = None
