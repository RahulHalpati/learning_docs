"""The synchronous client — the main entry point most users touch."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional

import httpx

from ._base import BaseClient, logger
from .exceptions import PokeConnectionError, error_from_response
from .models import Pokemon
from .pagination import iterate_pages


class PokemonResource:
    """The ``client.pokemon`` namespace — methods that act on Pokémon."""

    def __init__(self, client: "PokeClient") -> None:
        self._client = client

    def get(self, name_or_id: str | int) -> Pokemon:
        """Fetch a single Pokémon by name or numeric id."""
        data = self._client._request("GET", f"/pokemon/{name_or_id}")
        return Pokemon.model_validate(data)

    def list_all(self, *, limit: int = 20) -> Iterator:
        """Iterate over every Pokémon reference, paging automatically."""
        return iterate_pages(self._client, "/pokemon", limit=limit)


class PokeClient(BaseClient):
    """Synchronous PokéAPI client.

    Use as a context manager so the underlying connection pool is closed::

        with PokeClient() as client:
            ditto = client.pokemon.get("ditto")
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.Client(
            base_url=self.base_url,
            headers=self._default_headers(),
            timeout=self.timeout,
        )
        # resource namespaces
        self.pokemon = PokemonResource(self)

    # --- lifecycle -----------------------------------------------------
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PokeClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- the one place that talks to the network -----------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send a request with retries and turn errors into typed exceptions."""
        attempt = 0
        while True:
            try:
                request = self._http.build_request(method, path, **kwargs)
                logger.debug("request %s %s (attempt %d)", method, request.url, attempt)
                response = self._http.send(request)
            except httpx.HTTPError as exc:
                if self._should_retry(attempt=attempt, status_code=None):
                    self._sleep(attempt)
                    attempt += 1
                    continue
                raise PokeConnectionError(str(exc), cause=exc) from exc

            if response.is_success:
                return response.json()

            if self._should_retry(attempt=attempt, status_code=response.status_code):
                logger.debug("retrying after status %d", response.status_code)
                self._sleep(attempt)
                attempt += 1
                continue

            raise error_from_response(response)

    def _sleep(self, attempt: int) -> None:
        time.sleep(self._backoff_seconds(attempt))
