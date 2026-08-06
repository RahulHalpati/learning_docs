# Section 02 · FastAPI basics

> **Prerequisites:** [Section 01 · Async Python](../01_async_python/README.md).
> **Time:** ~3–4 hours.

Now you turn async skills into a real **web server**. FastAPI is a Python framework for building HTTP APIs: you write `async def` functions, decorate them with a URL, and FastAPI handles parsing requests, validating data, serializing responses, and even generating interactive docs.

## Modules

| # | Module | You'll learn |
|---|--------|--------------|
| 01 | [Your first FastAPI app](01_first_app.md) | Install, the minimal app, running with the dev server, ASGI, auto-docs |
| 02 | [Params & Pydantic models](02_params_and_models.md) | Path/query params, request bodies, validation, response models |
| 03 | [Calling other APIs (async)](03_calling_apis_async.md) | A shared `httpx` client via lifespan; awaiting external services in a handler |

## What you'll be able to do after this section

- Create and run a FastAPI server.
- Define endpoints with typed path/query params and JSON request bodies.
- Get automatic validation and interactive API docs for free.
- Call external APIs from inside a handler the async way — the exact setup the AI project uses to reach the LLM.

→ Start: **[01 · Your first FastAPI app](01_first_app.md)**
