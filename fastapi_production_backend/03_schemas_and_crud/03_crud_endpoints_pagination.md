# 03-3 · CRUD endpoints & pagination

> **Level:** Intermediate · **Prerequisites:** [03-2 · Repository & service pattern](02_repository_service_pattern.md)
> **Time:** 40 min · **Verified:** 2026-07-27 (fastapi 0.140.8; from the TaskFlow test suite)

## Why this matters

With schemas and services in place, the endpoints are the easy, thin part — which is the whole point. This lesson wires CRUD routes, adds **pagination** (never return an unbounded list) and **filtering**, and shows the consistent response envelope real APIs use.

---

## Thin CRUD routes

Each route validates input (schema), calls a service, and returns a `Read` schema. That's it:

```python
# app/api/v1/projects.py
router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession):
    return await ProjectService(db).create(data, user)

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, user: CurrentUser, db: DbSession):
    return await ProjectService(db).get(project_id, user)   # service raises 404/403

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, data: ProjectUpdate, user: CurrentUser, db: DbSession):
    return await ProjectService(db).update(project_id, data, user)

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, user: CurrentUser, db: DbSession) -> None:
    await ProjectService(db).delete(project_id, user)
```

Note the **correct status codes**: `201 Created` for POST, `204 No Content` for DELETE. The route says *what*; the service does *how*; errors are raised as domain exceptions and become clean JSON.

---

## Pagination — always bound your lists

An unpaginated "list everything" endpoint is a production outage waiting for the table to grow. Use `page`/`size` query params (with sane caps) and a consistent envelope:

```python
# app/schemas/common.py
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

# app/api/deps.py — page/size as a reusable dependency, bounded
class Pagination:
    def __init__(self, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
        self.page, self.size = page, size
```

`size` is capped at 100 (`le=100`) so a client can't request a million rows. The list route returns the envelope:

```python
@router.get("", response_model=Page[ProjectRead])
async def list_projects(user: CurrentUser, db: DbSession, page: PageParams):
    items, total = await ProjectService(db).list(user, page.page, page.size)
    return Page.create(items, total, page.page, page.size)
```

**Output (real run, 3 projects, `?page=1&size=2`):**
```json
{"items": [ ... 2 projects ... ], "total": 3, "page": 1, "size": 2, "pages": 2}
```

The `total`/`pages` metadata lets clients build "page 1 of 2" UIs. Every list endpoint returns this same shape — consistency consumers love.

---

## Filtering

Optional query params filter the list. Declare them and pass them down:

```python
@router.get("", response_model=Page[TaskRead])
async def list_tasks(project_id: int, user: CurrentUser, db: DbSession, page: PageParams,
                     status: TaskStatus | None = None):        # ?status=done
    items, total = await TaskService(db).list(project_id, user, page.page, page.size, status)
    return Page.create(items, total, page.page, page.size)
```

**Output (real run, 2 tasks, one `done`, `?status=done`):**
```
total: 1   (only the done task)
```

The `status: TaskStatus | None` param is validated (only real enum values accepted) and self-documented in `/docs`. The filter itself is applied in the repository's `WHERE` — HTTP declares it, SQL applies it.

> **Tip — offset pagination is simple but slow for deep pages.** `LIMIT/OFFSET` (what we use) is perfect up to thousands of rows. For very large tables or infinite scroll, **keyset (cursor) pagination** (`WHERE id < last_seen`) scales better. Start with offset; reach for keyset when profiling says so.

---

## Nested resources

Tasks live under a project, so the route is nested: `/projects/{project_id}/tasks`. The `project_id` in the path flows to the service, which checks ownership of the parent before touching tasks — the composition from [03-2](02_repository_service_pattern.md) in action.

---

## Recap & next

- ✅ Thin routes: validate (schema) → call service → return `Read` schema, with correct status codes (201/204).
- ✅ **Always paginate** lists; cap `size`; return a consistent `Page` envelope with `total`/`pages`.
- ✅ Filters are optional, validated query params applied in the repository's `WHERE`.
- ✅ Nest sub-resources under their parent (`/projects/{id}/tasks`); check parent ownership in the service.
- ✅ Self-check: why cap `size` at 100 instead of trusting the client's requested page size?

→ Next: **[04 · Auth & security](../04_auth_and_security/README.md)**

## Exercises

1. Add a `priority` filter to the task list (`?priority=high`) alongside `status`, both optional.

<details>
<summary>Solution</summary>

Add `priority: TaskPriority | None = None` to the route and thread it to `TaskRepository.list_for_project`, adding `if priority: stmt = stmt.where(Task.priority == priority)`. Two independent, validated, self-documented filters — combinable.
</details>
