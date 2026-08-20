# Section 02 · FastAPI fundamentals & Pydantic v2

> **Prerequisites:** [01 · Modern Python baseline](../01_modern_python_async/README.md) · **Time:** ~5 h

This section is where FastAPI clicks: you build your first apps and learn the framework's core trade — **type hints in, validation + serialization + docs out**. You'll go deep on **Pydantic v2** (the validation engine under everything), then wire up **response models**, **pydantic-settings** config, and the **lifespan** startup/shutdown contract that every production app relies on.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 02-1 | [First app, routing & params](01_first_app_routing_params.md) | How do I build and run an app, and how do path/query/body params work? |
| 02-2 | [Pydantic v2 deep dive](02_pydantic_v2_deep_dive.md) | How do I model, validate, and serialize data — the v2 way? |
| 02-3 | [Response models, settings & lifespan](03_response_models_settings_lifespan.md) | How do I control what leaves my API, configure it, and manage startup/shutdown? |

## Mini-project

Build **linkbox** — a URL-shortener API. Storage is a plain in-memory dict (the real data layer comes in Section 05); the point is to exercise everything from this section in one small, honest app.

- [ ] `POST /links` — validated body: `url: HttpUrl`, optional `slug: str | None` constrained by `pattern=r"^[a-z0-9-]{3,30}$"`; auto-generate a slug of `settings.slug_length` characters when omitted; returns `201`, or `409` if the slug is taken. Input model uses `ConfigDict(extra="forbid")`.
- [ ] `GET /{slug}` — `307` redirect (`RedirectResponse`) to the stored URL; increments the click count; `404` for unknown slugs.
- [ ] `GET /links/{slug}/stats` — response model with `slug`, `target`, `clicks`, and a `@computed_field` `short_url` built from `settings.base_url`.
- [ ] `DELETE /links/{slug}` — `204` on success, `404` if missing.
- [ ] Config (`base_url`, `slug_length`) comes from **pydantic-settings** `BaseSettings` + a `.env` file — no hard-coded values in endpoint code.
- [ ] A startup banner (app title + base URL) printed from a **lifespan** context manager — `@app.on_event` must not appear anywhere.
- [ ] Every endpoint declares a response model (parameter or return annotation); the link store is created inside `lifespan`.

## Test task (gate)

Before Section 03, fix this seeded-bugs app. It contains **exactly three defects** — find and fix all of them:

```python
# buggy_app.py — three defects hide here
from fastapi import FastAPI
from pydantic import BaseModel
from pydantic.v1 import validator

app = FastAPI()

FAKE_DB: dict[str, dict] = {
    "abc": {"slug": "abc", "url": "https://example.com",
            "clicks": 3, "owner_email": "admin@linkbox.dev"},
}

class Link(BaseModel):
    slug: str
    url: str
    clicks: int = 0
    owner_email: str

    @validator("slug")
    def slug_is_clean(cls, v):
        if not v.isalnum():
            raise ValueError("slug must be alphanumeric")
        return v

@app.on_event("startup")
async def startup():
    print("linkbox up")

@app.post("/links", status_code=201)
async def create_link(link: Link):
    FAKE_DB[link.slug] = link.model_dump()
    return link

@app.get("/links/{slug}")
async def get_link(slug: str):
    return FAKE_DB[slug]
```

The defects (don't peek until you've hunted):

- **(a) Data leak.** `GET /links/{slug}` has no response model, so the raw dict — including the internal `owner_email` — goes over the wire. Fix with a proper output schema.
- **(b) Dead validator.** `slug_is_clean` uses the Pydantic **v1** decorator (`pydantic.v1.validator`) on a v2 model — the v2 metaclass never registers it, so it **silently never runs**. `POST /links` happily accepts `"bad slug!!"`. Rewrite it as a v2 `@field_validator`.
- **(c) Deprecated lifecycle.** `@app.on_event("startup")` is deprecated. Convert to a `lifespan` context manager.

**Passing means, verifiably:**

1. All three defects fixed — and you can explain each in one sentence.
2. `/docs` shows the **filtered** response schema for `GET /links/{slug}` (no `owner_email`), and the live response body no longer contains it.
3. `POST /links` with `{"slug": "bad slug!!", "url": "https://x.dev", "owner_email": "a@b.c"}` returns **422** — the validator provably rejects bad input.
4. The startup banner still prints, from `lifespan`, with zero deprecation warnings on boot.

## What you'll be able to do after this section

- Scaffold, run (`fastapi dev`), and explore (`/docs`) a FastAPI app managed with **uv**.
- Declare path, query, and body parameters where the type hint *is* the validation.
- Write idiomatic **Pydantic v2** models — `Field` constraints, `ConfigDict`, `@field_validator`/`@model_validator`, `computed_field`, `TypeAdapter` — and spot v1 code in outdated tutorials on sight.
- Treat `response_model` as a security boundary and keep In/Out schemas separate.
- Load config from `.env` with pydantic-settings and manage startup/shutdown with `lifespan`.

→ Start: **[02-1 · First app, routing & params](01_first_app_routing_params.md)**
