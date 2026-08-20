# 10-3 · OpenAPI, pagination & CORS

> **Level:** Intermediate→Advanced · **Prerequisites:** [10-2 · Middleware & logging](02_middleware_logging.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · structlog)

## Why this matters

The last two lessons made failures debuggable. This one makes success *consumable*: collection endpoints that paginate consistently, CORS that lets your frontend in without opening the door to everyone, and an OpenAPI schema accurate enough that a client team generates their SDK from it instead of emailing you questions. Your `/docs` page is the first thing an integrator sees — it's a product surface, and auto-generated doesn't have to mean auto-neglected.

---

## `Page[T]`: an envelope, not a bare list

A bare `list[LinkOut]` response answers "what did I get?" but not "how much is there?" or "how do I get the rest?" — so clients can't render page controls or know when to stop. And you can't fix it later without breaking them: turning a JSON array into an object is a breaking change, while *adding a key to an object* is not. Start with an envelope and the response can evolve additively forever:

```python
# app/schemas/common.py
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard envelope for every collection response in the API."""
    items: list[T]
    total: int      # total matching rows, ignoring limit/offset
    limit: int      # echo the paging back — responses are self-describing
    offset: int
```

Being generic, `Page[LinkOut]` and `Page[UserOut]` are distinct, fully-typed models — Pydantic v2 generates a proper JSON schema for each, so the envelope shows up correctly in OpenAPI too.

---

## The pagination dependency

Paging, sorting, and filtering params are the same on every collection endpoint — which is precisely what dependencies are for. Declare them once, validated:

```python
# app/api/deps.py
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Query


@dataclass
class PageParams:
    limit: int
    offset: int
    sort: str


def page_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,       # cap it — no ?limit=1000000
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[Literal["created_at", "-created_at", "slug"], Query()] = "-created_at",
) -> PageParams:
    return PageParams(limit=limit, offset=offset, sort=sort)


Pagination = Annotated[PageParams, Depends(page_params)]
```

The `Literal` on `sort` matters more than it looks: it's an allowlist. Sorting by a client-supplied raw column name is a classic injection-adjacent bug; here anything outside the three allowed values is a 422 before your code runs. Using it:

```python
@router.get("", response_model=Page[LinkOut], summary="List links")
async def list_links(db: DbSession, page: Pagination) -> Page[LinkOut]:
    total = await db.scalar(select(func.count()).select_from(Link))
    order = SORT_MAP[page.sort]                    # dict of Literal value → column clause
    rows = await db.scalars(
        select(Link).order_by(order).limit(page.limit).offset(page.offset)
    )
    return Page(items=list(rows.all()), total=total, limit=page.limit, offset=page.offset)
```

Every collection endpoint in linkbox now takes `page: Pagination` and returns `Page[...]` — one convention, learned once, by you and by every client.

> **Tip — offset has a ceiling.** `OFFSET 500000` makes Postgres walk half a million rows to throw them away. Fine for admin UIs and modest data; for infinite-scroll feeds over big tables, keyset pagination (Section 05) is the upgrade. The `Page` envelope doesn't care — swap `offset` for a `next_cursor` extension when you get there.

---

## CORS done right

Browsers enforce the same-origin policy: JavaScript on `https://app.linkbox.dev` may not read responses from `https://api.linkbox.dev` unless the API *opts in* via CORS headers. That's `CORSMiddleware` — with the origins list coming from settings, like every other environment-dependent value:

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,        # e.g. ["https://app.linkbox.dev"] — explicit
    allow_credentials=True,                      # cookies / Authorization cross-origin
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],             # let browser JS read our tracing header
)
```

**Never `allow_origins=["*"]` together with credentials.** The fetch spec forbids the wildcard on credentialed responses, so a spec-following server that sends `Access-Control-Allow-Origin: *` gets its response *discarded by the browser* — your frontend just breaks. And the "workaround" (echoing whatever `Origin` arrives, which is what wildcard-plus-credentials effectively degrades to) is worse than breakage: it means *any website on the internet* can script authenticated requests against your API with the visitor's cookies and read the responses. The browser's rule is protecting your users; the fix is an explicit origin list per environment — `["http://localhost:5173"]` in dev, your real frontend origins in prod, driven by `settings.cors_origins`.

**Preflight, in one paragraph.** For anything beyond simple GETs/POSTs — a `PATCH`, or any request carrying `Authorization` — the browser first sends an `OPTIONS` request ("preflight") asking `Access-Control-Request-Method: PATCH`, may I? `CORSMiddleware` answers it directly from the middleware layer with the allow-lists above; the request never reaches your routes, which is why you never write an `OPTIONS` handler and why CORS bugs are invisible in curl (curl doesn't preflight — only browsers do).

---

## OpenAPI as a product

FastAPI generates the schema from your code — your job is to feed it the parts it can't infer. Start with the app itself:

```python
app = FastAPI(
    title="Linkbox API",
    version="1.4.0",                     # clients pin against this
    description="Shorten links, track clicks, get reports.",
    servers=[{"url": "https://api.linkbox.dev", "description": "Production"}],
    openapi_tags=[
        {"name": "links", "description": "Create, resolve, and manage short links."},
        {"name": "auth", "description": "Signup, login, and token refresh."},
    ],
    lifespan=lifespan,
)
```

Tag descriptions become section intros in `/docs`; routers opt in with `APIRouter(tags=["links"])`. Then per endpoint: a `summary` (the one-liner in the sidebar), a `description` (the docstring works), and **documented error responses** — because without them, the schema claims your endpoints can only succeed. Reuse the `Problem` model from 10-1 via a small helper:

```python
# app/api/problems.py (continued)
from pydantic import BaseModel


class Problem(BaseModel):
    """RFC 9457 problem details — the shape every linkbox error uses."""
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str


def problem_doc(status: int, description: str, example: dict) -> dict:
    """responses={...} entry documenting one problem+json failure."""
    return {status: {
        "model": Problem,                # the schema clients generate types from
        "description": description,
        "content": {"application/problem+json": {"example": example}},  # honest media type
    }}
```

```python
@router.get(
    "/{slug}",
    response_model=LinkOut,
    summary="Resolve a short link",
    responses={
        **problem_doc(404, "No link with this slug.", {
            "type": "https://api.linkbox.dev/problems/not_found",
            "title": "Not Found", "status": 404,
            "detail": "link 'abc123' does not exist",
            "instance": "/links/abc123", "code": "not_found",
        }),
    },
)
async def resolve_link(slug: str, db: DbSession) -> LinkOut:
    """Return the link for `slug`, or a problem+json 404 if it doesn't exist."""
    return await links_service.get_link(db, slug)
```

Now the docs show the 404, its schema, and a realistic example — an integrator writes their error handling without ever hitting the failure live.

**Auth documents itself.** Your `OAuth2PasswordBearer(tokenUrl="/auth/token")` dependency registers an OAuth2 security scheme in the schema automatically: Swagger UI grows an **Authorize** button, protected endpoints get a padlock, and generated clients know to send `Authorization: Bearer ...`. You wrote it in Section 07 for auth — the documentation is free.

**Hide what isn't for clients.** Health checks, metrics, debug hooks — real endpoints, not API surface:

```python
@router.get("/internal/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
```

If it's in the schema, someone will build on it and you'll own it forever. `include_in_schema=False` keeps the contract honest: the schema *is* the API.

**The payoff: generated SDKs.** `/openapi.json` is machine-readable, and tools like `openapi-generator`, `openapi-typescript`, or Fern turn it into typed client libraries — TypeScript for the frontend, Python for a partner — in one command. Every field you documented becomes a type; every `Problem` response becomes a typed error the client can `catch` on `code`. This is why schema accuracy compounds: an undocumented 409 is a runtime surprise in *every* generated client, while a documented one is a compile-time branch. Teams that treat the schema as the contract stop writing API clients by hand entirely.

---

## Recap & next

- ✅ Collections return a generic **`Page[T]` envelope** (`items`, `total`, `limit`, `offset`) — evolvable additively, never a bare list.
- ✅ Paging/sorting params live in **one dependency**, validated with bounds and a `Literal` sort allowlist.
- ✅ CORS: explicit `allow_origins` from settings; **never wildcard with credentials** — the browser blocks it, and the echo-workaround hands your users' sessions to any website.
- ✅ OpenAPI is a product: app metadata + tag descriptions, per-endpoint summaries and examples, **error responses documented with the `Problem` model**, auth scheme picked up from `OAuth2PasswordBearer`, internals hidden with `include_in_schema=False`.
- ✅ An accurate schema generates typed client SDKs — documentation that compiles.
- ✅ Self-check: why is adding `next_cursor` to `Page` a safe change for existing clients, while switching a bare-list response to `Page` is a breaking one?

→ Next: **[11 · Production, Docker & CI/CD](../11_production_docker_cicd/README.md)**

## Exercises

1. Add a `q: str | None` search filter to `page_params` (matches against slug), and cap its length at 100 characters. What does OpenAPI show for it without you writing any docs?

<details>
<summary>Solution</summary>

```python
def page_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[Literal["created_at", "-created_at", "slug"], Query()] = "-created_at",
    q: Annotated[str | None, Query(max_length=100, description="Filter by slug substring")] = None,
) -> PageParams:
    ...
```

(and `if page.q: stmt = stmt.where(Link.slug.contains(page.q))` in the query). OpenAPI picks up everything from the type and `Query` metadata: an optional string parameter, `maxLength: 100`, the description, and — because it lives in the shared dependency — it appears on *every* endpoint using `Pagination` automatically. One definition, documented everywhere.
</details>

2. Prove the preflight flow with curl: send the `OPTIONS` request a browser would send before a `PATCH` from `https://app.linkbox.dev`, and identify the three response headers that tell the browser "allowed."

<details>
<summary>Solution</summary>

```bash
curl -is -X OPTIONS http://localhost:8000/links/abc123 \
  -H "Origin: https://app.linkbox.dev" \
  -H "Access-Control-Request-Method: PATCH" \
  -H "Access-Control-Request-Headers: authorization,content-type"
```

Look for `Access-Control-Allow-Origin: https://app.linkbox.dev` (this specific origin may call), `Access-Control-Allow-Methods: ... PATCH ...` (this verb is permitted), and `Access-Control-Allow-Headers: authorization, content-type` (these request headers may be sent). Note the response comes back `200 OK` with no body and your route never ran — `CORSMiddleware` answered from the middleware layer. Repeat with `Origin: https://evil.example` and the allow-origin header is absent: the browser would block the real request.
</details>

3. Add a CI check that snapshots the schema: a script that writes `app.openapi()` to `openapi.json`, and a test that fails when the committed file is stale. Why is this worth a CI job?

<details>
<summary>Solution</summary>

```python
# scripts/export_openapi.py
import json
from app.main import app

with open("openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2, sort_keys=True)
```

```python
# tests/test_openapi_snapshot.py
import json
from app.main import app

def test_openapi_snapshot_is_current():
    committed = json.loads(open("openapi.json").read())
    assert app.openapi() == committed, "schema changed — rerun scripts/export_openapi.py"
```

Worth it because the schema is your public contract, and this makes contract changes **visible in code review**: renaming a field or dropping a response now shows up as a diff on `openapi.json` that a reviewer can flag as breaking, instead of shipping silently. It's also the artifact client teams generate SDKs from — pinning it in the repo means they build against exactly what's deployed.
</details>
