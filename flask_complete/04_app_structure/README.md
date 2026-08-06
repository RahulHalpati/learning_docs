# Section 04 · App structure

> **Prerequisites:** [03 · Request handling](../03_request_handling/README.md) · **Time:** ~2.5 h

The most important section in the course. Flask won't stop you writing a 2,000-line `app.py` — these three conventions are what the industry uses to stop that happening: the **application factory**, **blueprints**, and **config classes**.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 04-1 | [The application factory](01_app_factory.md) | Why build the app in a function, and how do extensions fit? |
| 04-2 | [Blueprints](02_blueprints.md) | How do I split routes into feature modules? |
| 04-3 | [Config & environments](03_config_and_env.md) | How do I manage settings and secrets per environment? |

## What you'll be able to do after this section

- Write `create_app()` and understand `init_app()`, `current_app`, and the app context.
- Split an app into blueprints with URL prefixes and per-blueprint concerns.
- Configure dev/test/prod with config classes, env vars, and a safe `SECRET_KEY`.

→ Start: **[04-1 · The application factory](01_app_factory.md)**
