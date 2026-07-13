import pytest

DITTO = {
    "id": 132,
    "name": "ditto",
    "height": 3,
    "weight": 40,
    "base_experience": 101,
    "types": [{"slot": 1, "type": {"name": "normal", "url": "https://pokeapi.co/api/v2/type/1/"}}],
    "stats": [{"base_stat": 48, "stat": {"name": "hp", "url": "https://pokeapi.co/api/v2/stat/1/"}}],
}


@pytest.fixture
def ditto():
    return DITTO
