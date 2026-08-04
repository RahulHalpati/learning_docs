# Section 06 · Testing

> **Prerequisites:** [03 · Schemas & CRUD](../03_schemas_and_crud/README.md), [04 · Auth & security](../04_auth_and_security/README.md) · **Time:** ~2 h

Untested code isn't production-ready. This section sets up a fast, isolated test suite — **pytest + httpx + a throwaway database** — and writes tests that exercise the real API, auth included. This is where the layered architecture pays off: everything is easy to test.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Test setup & fixtures](01_test_setup_fixtures.md) | How do I get an isolated app + database + client for tests? |
| 06-2 | [Writing API tests](02_writing_api_tests.md) | How do I test endpoints, auth, and error cases? |

## What you'll be able to do after this section

- Configure pytest-asyncio and an in-memory test database with dependency overrides.
- Provide `client` and `auth_client` fixtures via httpx `ASGITransport`.
- Test happy paths, validation, auth (401/403), and ownership isolation.

→ Start: **[06-1 · Test setup & fixtures](01_test_setup_fixtures.md)**
