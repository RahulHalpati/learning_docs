# Section 03 · The sync client

> **Prerequisites:** [Section 02 · Packaging basics](../02_packaging_basics/README.md).
> **Time:** ~4–5 hours.

This is where the SDK starts to feel real. You'll build `PokeClient`: the object users create once and call methods on. By the end of the section it sets auth once, reuses a connection pool, routes every call through a single request helper, and groups methods into resource namespaces (`client.pokemon.get(...)`). This fixes the naive client's repeated-auth and smeared-base-URL problems and lays the spine — *one request core* — that Sections 04–06 build on.

We keep responses as plain dicts for now; typed models arrive in Section 04, and errors/retries in Section 05. Building incrementally is deliberate — you'll see each layer added to the same skeleton.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [The client class & the session](01_client_class_and_session.md) | Why a class? Why reuse one `httpx.Client`? How do I clean it up? |
| 02 | [Auth & headers](02_auth_and_headers.md) | How do I set the API key once and send it on every request? |
| 03 | [The request helper & base URL](03_request_helper_and_base_url.md) | How does every method funnel through one place? |
| 04 | [Resource namespaces](04_resource_namespaces.md) | How do I get `client.pokemon.get(...)` instead of a giant flat client? |

## What you'll be able to do after this section

- Build a `Client` class that owns a pooled `httpx.Client` and cleans it up via a context manager.
- Attach auth and default headers once, centrally, and verify they're sent.
- Route every API call through a single `_request` method (the seam for retries/errors later).
- Organise methods into resource namespaces that mirror the API and autocomplete well.

→ Start: **[01 · The client class & the session](01_client_class_and_session.md)**
