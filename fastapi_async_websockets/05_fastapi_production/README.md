# Section 05 · Production-grade FastAPI

> **Prerequisites:** [Section 02 · FastAPI basics](../02_fastapi_basics/README.md) (and the async ideas from [Section 01](../01_async_python/README.md)). You do **not** need the WebSocket/AI sections for this one.
> **Time:** ~6–8 hours.

Sections 02–04 taught *enough* FastAPI to build the AI app. This section is the **FastAPI deep-dive**: how professionals actually structure, secure, configure, and test a FastAPI service. These are the patterns you'll see in real codebases and that reviewers expect. It's a parallel track — take it right after Section 02 if your goal is API craftsmanship, or after the project to level up.

## Why a whole section on this?

A toy API is one `main.py` with a few routes. A *production* API has to answer harder questions: Where does code go as it grows? How do routes share a database connection? Where do secrets come from? What does an error response look like? How do you lock down an endpoint? How do you test it without a live server? Each module answers one of these with the idiomatic FastAPI tool.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Project structure & routers](01_project_structure.md) | How do I organize a growing app? (`APIRouter`, layout, app factory) |
| 02 | [Dependency injection](02_dependency_injection.md) | How do routes share resources cleanly and testably? (`Depends`, `yield`) |
| 03 | [Configuration & settings](03_config_and_settings.md) | Where do config and secrets come from? (`pydantic-settings`, env, `.env`) |
| 04 | [Errors, status codes & response design](04_errors_and_responses.md) | What should success and failure responses look like? |
| 05 | [Security & middleware](05_security_and_middleware.md) | How do I authenticate, add CORS, and run cross-cutting logic? |
| 06 | [Testing, logging & background tasks](06_testing_logging_background.md) | How do I test it properly, log well, and offload work? |

## What you'll be able to do after this section

- Lay out a FastAPI project that scales past one file, using routers and a clear layer separation.
- Use dependency injection for DB sessions, settings, and authenticated users — and override them in tests.
- Load typed, validated configuration from the environment the 12-factor way.
- Return consistent, well-typed success and error responses with correct HTTP status codes.
- Protect endpoints with API keys / bearer tokens, configure CORS, and add middleware.
- Write a real `pytest` suite, structured logging, and background tasks.

→ Start: **[01 · Project structure & routers](01_project_structure.md)**
