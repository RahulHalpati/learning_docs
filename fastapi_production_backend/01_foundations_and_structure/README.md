# Section 01 · Foundations & structure

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~2 h

Before a single endpoint, get the skeleton right: a **layered layout** that scales, **settings** loaded from the environment, and an **app factory** that wires it all together. Get this foundation right and every later section drops neatly into place.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 01-1 | [Project layout](01_project_layout.md) | How do I structure a FastAPI project so it scales and tests cleanly? |
| 01-2 | [Config & settings](02_config_and_settings.md) | How do I load configuration from the environment (12-factor)? |
| 01-3 | [The app factory](03_app_factory.md) | How do I assemble the app — middleware, routers, handlers — in one place? |

## What you'll be able to do after this section

- Explain the API → service → repository → model layering and where each concern lives.
- Load typed settings from env/.env with `pydantic-settings`.
- Write a `create_app()` factory with lifespan, middleware, routers, and exception handlers.

→ Start: **[01-1 · Project layout](01_project_layout.md)**
