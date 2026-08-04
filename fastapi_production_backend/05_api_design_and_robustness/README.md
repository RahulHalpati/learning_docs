# Section 05 · API design & robustness

> **Prerequisites:** [04 · Auth & security](../04_auth_and_security/README.md) · **Time:** ~2 h

An API that works on the happy path isn't done. This section makes it **robust and professional**: organized **versioned routers**, consistent **error handling** (clean JSON, never a stack trace), and **middleware/CORS** for cross-cutting concerns.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [Routers & versioning](01_routers_and_versioning.md) | How do I organize routes and version the API? |
| 05-2 | [Error handling](02_error_handling.md) | How do I return consistent, safe error responses? |
| 05-3 | [Middleware & CORS](03_middleware_and_cors.md) | How do I add cross-cutting behavior and allow browser clients? |

## What you'll be able to do after this section

- Organize routes into feature routers under a versioned prefix (`/api/v1`).
- Turn domain exceptions into consistent JSON errors with correct status codes.
- Add middleware (request id, timing) and configure CORS safely.

→ Start: **[05-1 · Routers & versioning](01_routers_and_versioning.md)**
