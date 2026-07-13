import httpx
import pytest
import respx

from pokesdk import AuthenticationError, NotFoundError, PokeClient


@respx.mock
def test_get_pokemon_parses_model(ditto):
    respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        return_value=httpx.Response(200, json=ditto)
    )
    with PokeClient() as client:
        result = client.pokemon.get("ditto")

    assert result.name == "ditto"
    assert result.id == 132
    assert result.types[0].type.name == "normal"


@respx.mock
def test_404_raises_not_found():
    respx.get("https://pokeapi.co/api/v2/pokemon/nope").mock(
        return_value=httpx.Response(404)
    )
    with PokeClient() as client:
        with pytest.raises(NotFoundError) as exc:
            client.pokemon.get("nope")
    assert exc.value.status_code == 404


@respx.mock
def test_api_key_sent_as_bearer(ditto):
    route = respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        return_value=httpx.Response(200, json=ditto)
    )
    with PokeClient(api_key="secret-123") as client:
        client.pokemon.get("ditto")

    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer secret-123"


@respx.mock
def test_401_raises_authentication_error():
    respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        return_value=httpx.Response(401)
    )
    with PokeClient(api_key="bad") as client:
        with pytest.raises(AuthenticationError):
            client.pokemon.get("ditto")
