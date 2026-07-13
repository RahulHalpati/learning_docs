"""The asynchronous client — mirrors PokeClient but awaits its I/O.

Notice how little is different from the sync client: the network calls become
``await``, sleeps become ``await asyncio.sleep``, and the retry *policy* comes
straight from the shared :class:`BaseClient`. That's the payoff of putting the
decisions in the base class.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

import httpx

from ._base import BaseClient, logger
from .exceptions import PokeConnectionError, error_from_response
from .models import Pokemon
from .pagination import aiterate_pages


class AsyncPokemonResource:
    def __init__(self, client: "AsyncPokeClient") -> None:
        self._client = client

    async def get(self, name_or_id: str | int) -> Pokemon:
        data = await self._client._request("GET", f"/pokemon/{name_or_id}")
        return Pokemon.model_validate(data)

    def list_all(self, *, limit: int = 20) -> AsyncIterator:
        return aiterate_pages(self._client, "/pokemon", limit=limit)


class AsyncPokeClient(BaseClient):
    """Asynchronous PokéAPI client.

    ::

        async with AsyncPokeClient() as client:
            ditto = await client.pokemon.get("ditto")
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._default_headers(),
            timeout=self.timeout,
        )
        self.pokemon = AsyncPokemonResource(self)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncPokeClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        attempt = 0
        while True:
            try:
                request = self._http.build_request(method, path, **kwargs)
                logger.debug("request %s %s (attempt %d)", method, request.url, attempt)
                response = await self._http.send(request)
            except httpx.HTTPError as exc:
                if self._should_retry(attempt=attempt, status_code=None):
                    await asyncio.sleep(self._backoff_seconds(attempt))
                    attempt += 1
                    continue
                raise PokeConnectionError(str(exc), cause=exc) from exc

            if response.is_success:
                return response.json()

            if self._should_retry(attempt=attempt, status_code=response.status_code):
                await asyncio.sleep(self._backoff_seconds(attempt))
                attempt += 1
                continue

            raise error_from_response(response)
