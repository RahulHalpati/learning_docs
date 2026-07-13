import httpx
import respx

from pokesdk import PokeClient, ServerError


@respx.mock
def test_retries_then_succeeds(ditto, monkeypatch):
    # don't actually sleep during the test
    monkeypatch.setattr(PokeClient, "_sleep", lambda self, attempt: None)

    route = respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        side_effect=[
            httpx.Response(503),          # attempt 0 -> retry
            httpx.Response(503),          # attempt 1 -> retry
            httpx.Response(200, json=ditto),  # attempt 2 -> success
        ]
    )
    with PokeClient(max_retries=2) as client:
        result = client.pokemon.get("ditto")

    assert result.name == "ditto"
    assert route.call_count == 3


@respx.mock
def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(PokeClient, "_sleep", lambda self, attempt: None)

    route = respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        return_value=httpx.Response(500)
    )
    with PokeClient(max_retries=2) as client:
        try:
            client.pokemon.get("ditto")
            assert False, "expected ServerError"
        except ServerError:
            pass

    assert route.call_count == 3  # initial + 2 retries
