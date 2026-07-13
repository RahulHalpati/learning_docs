import httpx
import respx

from pokesdk import PokeClient

BASE = "https://pokeapi.co/api/v2"


@respx.mock
def test_list_all_walks_pages():
    page1 = {
        "count": 3,
        "next": f"{BASE}/pokemon?offset=2&limit=2",
        "previous": None,
        "results": [
            {"name": "bulbasaur", "url": f"{BASE}/pokemon/1/"},
            {"name": "ivysaur", "url": f"{BASE}/pokemon/2/"},
        ],
    }
    page2 = {
        "count": 3,
        "next": None,
        "previous": f"{BASE}/pokemon?offset=0&limit=2",
        "results": [{"name": "venusaur", "url": f"{BASE}/pokemon/3/"}],
    }
    respx.get(f"{BASE}/pokemon").mock(
        side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    )

    with PokeClient() as client:
        names = [p.name for p in client.pokemon.list_all(limit=2)]

    assert names == ["bulbasaur", "ivysaur", "venusaur"]
