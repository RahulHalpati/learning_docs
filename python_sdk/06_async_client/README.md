# Section 06 · The async client

> **Prerequisites:** Sections [03](../03_the_sync_client/README.md)–[05](../05_robustness/README.md). Some async familiarity helps but isn't required — Module 01 gives a refresher.
> **Time:** ~2–3 hours.

Many users — anyone building on FastAPI, aiohttp, or doing lots of concurrent calls — need an **async** client. The naive way would be to rewrite the whole SDK with `async`/`await`. The professional way, and what real SDKs (anthropic, openai) do, is to **share one core** between sync and async clients, so the two stay in lockstep. This section pays off the `BaseClient` design from Section 05: because every *decision* (auth headers, retry policy, backoff, error mapping) is pure and lives in the base, the async client only re-implements the part that actually differs — *how it waits for I/O*.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Why & how async](01_why_and_how_async.md) | When does async help an SDK, and what's the minimum I need to know? |
| 02 | [The async client & the shared core](02_async_client_and_shared_core.md) | How do I add `AsyncPokeClient` without duplicating logic? |

## What you'll be able to do after this section

- Explain when an async client benefits users (concurrent I/O) and when it doesn't.
- Build `AsyncPokeClient` that mirrors the sync client, awaiting its network and sleeps.
- Share auth, retry policy, backoff, and error mapping between both clients via `BaseClient` — no duplication.

→ Start: **[01 · Why & how async](01_why_and_how_async.md)**
