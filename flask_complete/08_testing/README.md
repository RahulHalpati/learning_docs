# Section 08 · Testing

> **Prerequisites:** [04-1 · The application factory](../04_app_structure/01_app_factory.md) · **Time:** ~2 h

The app factory's payoff: every test gets a fresh app and an in-memory database. FlaskNotes' suite is **20 tests in ~3 seconds**, covering the web UI, the JSON API, uploads, and ownership isolation.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 08-1 | [pytest setup & fixtures](01_pytest_setup.md) | How do I get an isolated app, DB, and client per test? |
| 08-2 | [Testing views, API & DB](02_testing_endpoints_db.md) | How do I test pages, JSON endpoints, auth, and uploads? |

## What you'll be able to do after this section

- Write `app`/`client`/`auth_client` fixtures on top of `create_app("testing")`.
- Test HTML pages, JSON endpoints, login flows, file uploads, and error paths.
- Prove ownership isolation — the test that matters most in a multi-user app.

→ Start: **[08-1 · pytest setup & fixtures](01_pytest_setup.md)**
