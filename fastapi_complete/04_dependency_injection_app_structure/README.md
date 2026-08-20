# Section 04 · Dependency injection & app structure

> **Prerequisites:** [03 · Request handling: forms, files & parsing](../03_request_handling_files_parsing/README.md) · **Time:** ~4 h

Dependency injection is what separates a script with routes from a service you can test, grow, and hand to a team. This section restructures the Section-02 linkbox around **Depends** with **Annotated** type aliases, **yield dependencies** for per-request resources, **dependency_overrides** for test-time swaps, and an **app factory** composed from **APIRouter**s — settings via **pydantic-settings**, never module-level globals. Everything runs with **uv** on Python 3.12+.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Depends fundamentals](01_depends_fundamentals.md) | How do endpoints declare what they need — and why not just import a global? |
| 04-2 | [Yield dependencies & overrides](02_yield_dependencies_and_overrides.md) | How do I manage per-request resources, and swap them out without touching app code? |
| 04-3 | [App factory & routers](03_app_factory_and_routers.md) | How do I structure an app that can be built twice with different configs — and keep growing? |

## Mini-project

**Refactor linkbox into a factory-built app.** Same URL-shortener endpoints as Section 02, new skeleton:

- [ ] `create_app() -> FastAPI` lives in `app/main.py`; no routes, storage, or settings are constructed at import time
- [ ] Routers split by resource: `app/api/links.py` (`prefix="/links"`, `tags=["links"]`) and `app/api/health.py` (`tags=["ops"]`), composed with `include_router` — links under `/api/v1`, health unversioned at `/health`
- [ ] Storage behind a **`LinkStore` dependency**: `get_store` + `Store = Annotated[LinkStore, Depends(get_store)]` in `app/api/deps.py`; handlers never touch a module-level dict
- [ ] In-memory `LinkStore` implementation in `app/stores/memory.py`
- [ ] Settings injected via `pydantic-settings` + a `get_settings` dependency (`Settings` alias) — no module-level `settings` global imported anywhere
- [ ] **Swap-ability proof:** a ~10-line `swap_demo.py` that replaces the store with a pre-seeded fake via `app.dependency_overrides` and hits the API with `httpx.ASGITransport` — the seeded short code resolves without a single POST

## Test task (gate)

**Extension challenge — API-key protection.** Build on the mini-project:

- A `require_api_key` dependency reads the `X-API-Key` header and compares it against `settings.api_key` with `secrets.compare_digest` (never `==` — timing attacks).
- Applied at **router level** (`dependencies=[Depends(require_api_key)]`) to all mutating endpoints (POST/DELETE); GET redirects stay public. Hint: two routers, or `include_router(..., dependencies=[...])`.
- Wrong or missing key → **401** with a `WWW-Authenticate: ApiKey` response header.

**Passing looks like exactly this:**

- [ ] Manual curl checks, documented as a transcript in your project: `curl -i -X POST .../api/v1/links -d ...` with no key → `401` + `WWW-Authenticate` header; the same request with `-H 'X-API-Key: <key>'` → `201`; `curl -i .../api/v1/links/<code>` with no key → `307`
- [ ] An httpx script whose assertions all pass: POST without key → 401; POST with the correct key → 201; then `app.dependency_overrides[require_api_key] = lambda: None` and POST without key → 201 (auth bypassed for testing)

All assertions green + curl transcript matching → continue to [Section 05](../05_async_database_sqlalchemy_alembic/README.md).

## What you'll be able to do after this section

- Declare shared logic as dependencies with `Annotated` type aliases — including sub-dependencies and per-request caching.
- Manage per-request resources with yield dependencies that clean up on success, failure, and mid-stream.
- Swap any dependency (storage, settings, auth) with `app.dependency_overrides` — the backbone of testing.
- Structure a growing service: `create_app()` factory, one `APIRouter` per resource, versioned `/api/v1` layout, router-level auth.

→ Start: **[04-1 · Depends fundamentals](01_depends_fundamentals.md)**
