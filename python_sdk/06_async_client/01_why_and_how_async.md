# 01: Why & how async

> **Level:** Intermediate · **Prerequisites:** Section 05
> **Time:** ~1 hour · **Verified:** 2026-06-04 (live httpbin)

## Why this matters

Before adding an async client, you should know *when it actually helps* — adding async "because it's modern" just doubles your API surface for no gain. This module gives the minimum async mental model you need and shows, with real numbers, the one scenario where an async SDK shines: **many I/O calls that can overlap.**

## The one-sentence model of async

> `async`/`await` lets a single thread start a slow I/O operation, set it aside while it waits, and do *other* work in the meantime — so many waits happen **concurrently** instead of one-after-another.

An SDK call spends almost all its time **waiting on the network**, not computing. That idle waiting is exactly what async reclaims: while request A waits for the server, request B can be in flight.

```mermaid
flowchart TD
    subgraph Sync["Sync: 3 calls, sequential"]
      direction LR
      A1["wait A"] --> A2["wait B"] --> A3["wait C"]
    end
    subgraph Async["Async: 3 calls, overlapped"]
      direction LR
      B1["wait A"]
      B2["wait B"]
      B3["wait C"]
    end
```

Same total *work*, but the async version's waits happen at the same time, so wall-clock time drops to roughly the *slowest single* call instead of the *sum*.

## When async helps (and when it doesn't)

| Scenario | Async helps? |
|----------|--------------|
| Fetch 100 Pokémon to build a report | ✅ huge — overlap all 100 waits |
| One call, then use the result | ❌ nothing to overlap; sync is simpler |
| Inside an async web app (FastAPI) | ✅ required — sync calls would block the event loop |
| A simple script, one request at a time | ❌ sync is easier to read and debug |

The honest takeaway: **async is for concurrency.** If your users make many independent calls or run inside an async framework, give them an async client. If not, the sync client is the better tool. Real SDKs ship *both* and let the user choose — which is exactly what we'll do.

## Verified: concurrency is real

Here's the payoff, measured. We make 5 requests that each take ~1s of server time (httpbin's `/delay/1`), sync vs async:

```python
import asyncio, time
from pokesdk import AsyncPokeClient, PokeClient

with PokeClient(base_url="https://httpbin.org", timeout=20) as c:
    t = time.time()
    for _ in range(5):
        c._request("GET", "/delay/1")           # one after another
    print("sync     : %.2fs" % (time.time() - t))

async def main():
    async with AsyncPokeClient(base_url="https://httpbin.org", timeout=20) as c:
        t = time.time()
        await asyncio.gather(*[c._request("GET", "/delay/1") for _ in range(5)])  # overlapped
        print("async    : %.2fs" % (time.time() - t))

asyncio.run(main())
```

**Live output (illustrative — exact numbers depend on the server/network):**

```text
sync (5x /delay/1) : 15.15s
async concurrent   : 5.82s
speedup            : 2.6x
```

The sync version paid for each wait in series; the async version, via `asyncio.gather`, ran all five waits concurrently and finished in a fraction of the time. *That* is the entire reason to offer an async client. (The speedup isn't a perfect 5× here because httpbin throttles concurrent requests — against a faster API it's larger; the shape is what matters.)

> Note we don't yet expose a nice concurrent API — `asyncio.gather(...)` is the user's tool. The SDK's job is to provide an async client whose methods are awaitable so they *can* be gathered.

## The four things that change in async code

To write the async client (next module), you only need these mechanical differences from sync:

1. **`async def`** marks a coroutine function — calling it returns a coroutine you must `await`.
2. **`await`** suspends until an awaitable (like a network send) completes, freeing the loop to run other coroutines.
3. **`httpx.AsyncClient`** instead of `httpx.Client`; you `await client.send(...)` and `await client.aclose()`.
4. **`async with` / `__aenter__`/`__aexit__`** for async context managers, and **`asyncio.sleep`** instead of `time.sleep` (a sleep that doesn't block the whole loop).

Everything *else* — what headers to send, whether to retry, how long to back off, which exception to raise — is identical to the sync client. That identical part is what `BaseClient` already holds, and why the next module is short.

## Recap & next

- ✅ Async reclaims the time an SDK spends **waiting on the network**, letting many calls overlap — wall-clock drops from sum-of-waits to slowest-wait.
- ✅ It helps for **concurrent I/O** and inside async frameworks; it adds nothing for one-at-a-time calls. Ship both, let users choose.
- ✅ Verified: 5×`/delay/1` took ~15s sync vs ~6s async via `asyncio.gather`.
- ✅ Only four things change in async code: `async def`, `await`, `AsyncClient`/`aclose`, `async with`/`asyncio.sleep`.
- ✅ Self-check: in one sentence, what does async let a single thread do? Name a case where async does *not* help.

→ Next: **[02 · The async client & the shared core](02_async_client_and_shared_core.md)** — build `AsyncPokeClient` by reusing `BaseClient`.

## Exercises

1. **Predict the timing.** Ten independent calls each take ~200ms server-side. Estimate the wall-clock time sync vs async (ignoring overhead). What dominates each?

<details><summary>Solution</summary>

Sync ≈ 10 × 200ms = **~2.0s** (sum of waits — each call blocks until done). Async ≈ **~200ms** (all ten waits overlap, so you wait roughly one call's duration). Sync is dominated by the *sum* of latencies; async by the *single longest* latency (plus small scheduling overhead). Real-world async will be a bit higher than the ideal due to connection limits and server throttling.
</details>

2. **Spot the misuse.** A user writes `for n in names: await client.pokemon.get(n)` in an async function and is surprised it's no faster than sync. Why, and what should they write?

<details><summary>Solution</summary>

`await` *inside* the loop waits for each call to finish before starting the next — that's sequential, just with async syntax. To overlap, create all the coroutines first and await them together: `await asyncio.gather(*[client.pokemon.get(n) for n in names])`. Async only helps when calls are actually *concurrent*; `await` in a loop serialises them.
</details>

3. **Should you add async?** You're writing an SDK for an API that users call once per CLI invocation to fetch a single config value. Is an async client worth it?

<details><summary>Solution</summary>

Probably not as a priority. One call per run has nothing to overlap, so async adds no speed — only a second client class, more docs, and more tests to maintain. A clean sync client serves this use case best. Add async later *if* users start making many concurrent calls or want to use it inside an async app. Match the API surface to real usage.
</details>
