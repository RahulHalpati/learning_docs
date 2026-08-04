# 05-1 · Routers & versioning

> **Level:** Intermediate · **Prerequisites:** [01-3 · The app factory](../01_foundations_and_structure/03_app_factory.md)
> **Time:** 25 min · **Verified:** 2026-07-27 (fastapi 0.140.8)

## Why this matters

One file with 40 routes is unnavigable. **`APIRouter`** lets you split routes by feature (auth, projects, tasks) into their own modules, then compose them. And a **version prefix** (`/api/v1`) means you can ship breaking changes as `/api/v2` later *without* breaking existing clients. Both are cheap now and expensive to retrofit.

---

## One router per feature

Each feature module owns an `APIRouter` with its prefix and tag:

```python
# app/api/v1/projects.py
router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(...): ...
```

- **`prefix="/projects"`** — every route here starts with `/projects`, written once.
- **`tags=["projects"]`** — groups these endpoints in the `/docs` UI.

---

## Compose them under a version

A single aggregator mounts every feature router under `/api/v1`:

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, health, projects, tasks

api_router = APIRouter(prefix="/api/v1")
for module in (health, auth, projects, tasks):
    api_router.include_router(module.router)
```

And the app factory includes just that one router ([01-3](../01_foundations_and_structure/03_app_factory.md)):

```python
app.include_router(api_router)      # mounts everything under /api/v1
```

So the full path composes from three prefixes: `/api/v1` + `/projects` + `/{project_id}` = `/api/v1/projects/7`. Adding a feature is: create `api/v1/thing.py` with a `router`, add it to the loop. `main.py` never changes.

---

## Why version from day one

`/api/v1` costs nothing today and saves you later. When you must make a **breaking** change (rename a field, change auth), you add `/api/v2` and run both while clients migrate — instead of breaking every existing integration overnight.

```
app/api/
├── v1/   # current, stable
└── v2/   # new breaking changes live here; v1 keeps working
```

> **Tip — what counts as "breaking"?** Removing/renaming a field, changing a type, tightening validation, or altering status codes. *Additive* changes (a new optional field, a new endpoint) are backward-compatible and don't need a new version. Version for breaks, not for every change.

---

## Nested & tagged routes

Sub-resources nest naturally with prefixes — tasks live under a project:

```python
# app/api/v1/tasks.py
router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])
```

The `{project_id}` path param flows into every task route. Tags keep `/docs` organized by feature, so consumers find endpoints fast.

---

## Recap & next

- ✅ Split routes into **feature routers** (`APIRouter` with prefix + tags); compose them in one aggregator.
- ✅ Mount everything under a **version prefix** (`/api/v1`) so future breaking changes can live in `/api/v2`.
- ✅ Adding a feature touches its module + the aggregator, never `main.py`.
- ✅ Version for **breaking** changes; additive changes don't need a new version.
- ✅ Self-check: which of these needs a new API version — adding an optional `due_date` field, or renaming `name` to `title`?

→ Next: **[05-2 · Error handling](02_error_handling.md)**

## Exercises

1. Add a `GET /api/v1/version` endpoint (in a small `meta` router) returning `{"api": "v1", "app": settings.app_name}`. Wire it into the aggregator.

<details>
<summary>Solution</summary>

Create `api/v1/meta.py` with a router and route, then add `meta` to the aggregator's loop. It appears at `/api/v1/version` and in `/docs` under a `meta` tag — no change to `main.py`.
</details>
