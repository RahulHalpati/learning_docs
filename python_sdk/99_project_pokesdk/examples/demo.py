"""Runnable demo of pokesdk against the live PokéAPI (no API key needed).

    python examples/demo.py
"""

import asyncio

from pokesdk import AsyncPokeClient, NotFoundError, PokeClient


def sync_demo() -> None:
    print("== sync ==")
    with PokeClient() as client:
        ditto = client.pokemon.get("ditto")
        print(f"got {ditto.name}: id={ditto.id}, weight={ditto.weight}, "
              f"types={[t.type.name for t in ditto.types]}")

        print("first 5 names:", end=" ")
        names = []
        for ref in client.pokemon.list_all(limit=20):
            names.append(ref.name)
            if len(names) == 5:
                break
        print(names)

        try:
            client.pokemon.get("not-a-real-pokemon")
        except NotFoundError as exc:
            print(f"handled NotFoundError (status {exc.status_code})")


async def async_demo() -> None:
    print("== async (concurrent) ==")
    async with AsyncPokeClient() as client:
        wanted = ["pikachu", "charizard", "snorlax"]
        results = await asyncio.gather(*(client.pokemon.get(n) for n in wanted))
        for p in results:
            print(f"  {p.name}: id={p.id}")


if __name__ == "__main__":
    sync_demo()
    asyncio.run(async_demo())
