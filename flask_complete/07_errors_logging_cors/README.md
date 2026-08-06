# Section 07 · Errors, logging & CORS

> **Prerequisites:** [04 · App structure](../04_app_structure/README.md) · **Time:** ~2 h

Robustness: never show a user a stack trace, always leave yourself a trail, and let the right browsers call your API.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 07-1 | [Error handling](01_error_handling.md) | How do I return clean errors — HTML *or* JSON — from one app? |
| 07-2 | [Logging](02_logging.md) | How do I record what happened without leaking secrets? |
| 07-3 | [CORS & middleware](03_cors_and_middleware.md) | How do I let a frontend call the API, and hook every request? |

## What you'll be able to do after this section

- Register central error handlers with content negotiation (JSON for `/api/*`, pages elsewhere).
- Log with levels and context; never log secrets; know what to log in production.
- Configure CORS for real origins and use `before_request`/`after_request` hooks.

→ Start: **[07-1 · Error handling](01_error_handling.md)**
