import httpx
import respx

from pokesdk import AsyncPokeClient


@respx.mock
async def test_async_get(ditto):
    respx.get("https://pokeapi.co/api/v2/pokemon/ditto").mock(
        return_value=httpx.Response(200, json=ditto)
    )
    async with AsyncPokeClient() as client:
        result = await client.pokemon.get("ditto")
    assert result.name == "ditto"


@respx.mock
async def test_async_list_all():
    base = "https://pokeapi.co/api/v2"
    page = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [{"name": "ditto", "url": f"{base}/pokemon/132/"}],
    }
    respx.get(f"{base}/pokemon").mock(return_value=httpx.Response(200, json=page))
    async with AsyncPokeClient() as client:
        names = [p.name async for p in client.pokemon.list_all()]
    assert names == ["ditto"]
