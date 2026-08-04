# 03-2 · Repository & service pattern

> **Level:** Intermediate · **Prerequisites:** [03-1 · Pydantic schemas](01_pydantic_schemas.md)
> **Time:** 45 min · **Verified:** 2026-07-27 (SQLAlchemy 2.0.51)

## Why this matters

The most valuable structural decision in the app: **don't put SQL or business rules in your route functions.** Routes get fat, untestable, and duplicated. Instead, **repositories** own data access and **services** own business rules. Routes become thin translators of HTTP. This is what makes the app testable and changeable.

---

## Repository — data access only

A repository wraps queries for one aggregate. A generic base gives every repo `get`/`create`/`delete`/pagination:

```python
# app/repositories/base.py (essentials)
class BaseRepository(Generic[ModelT]):
    model: type[ModelT]
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()          # assign PK, but DON'T commit (02-2)
        await self.session.refresh(obj)
        return obj
```

Specific repos add their queries — and encode rules like tenant isolation:

```python
# app/repositories/project.py
class ProjectRepository(BaseRepository[Project]):
    model = Project
    async def list_for_owner(self, owner_id: int, page: int, size: int):
        stmt = select(Project).where(Project.owner_id == owner_id).order_by(Project.id.desc())
        return await self._paginate(stmt, page, size)
```

The repository knows **SQL**. It does not know about HTTP, or *why* it's only returning one owner's rows — it just does the query it's asked for.

---

## Service — business rules only

A service enforces the rules and orchestrates repositories. Here, ownership:

```python
# app/services/project.py (essentials)
class ProjectService:
    def __init__(self, session: AsyncSession):
        self.repo = ProjectRepository(session)

    async def _owned(self, project_id: int, user: User) -> Project:
        project = await self.repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        if project.owner_id != user.id and user.role != Role.admin:
            raise PermissionDeniedError("You do not have access to this project.")
        return project

    async def update(self, project_id, data: ProjectUpdate, user: User) -> Project:
        project = await self._owned(project_id, user)         # rule enforced here
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)                    # partial update
        await self.repo.session.flush()
        return project
```

The service raises **domain exceptions** (`NotFoundError`, `PermissionDeniedError`), not HTTP errors — it doesn't know about status codes. The API layer turns those into responses ([05-2](../05_api_design_and_robustness/02_error_handling.md)). And `exclude_unset=True` is what makes `PATCH` a true *partial* update: only the fields the client actually sent are applied.

> **Tip — services compose.** `TaskService` reuses `ProjectService._owned` to check that you own the project before touching its tasks. Business rules live in one place and get reused, instead of being copy-pasted into three route handlers.

---

## Why this seam pays off

| Benefit | How the split delivers it |
|---------|---------------------------|
| **Testable** | Test a service with a session and no HTTP; test a repo with no business rules |
| **No duplication** | Ownership check written once (`_owned`), reused by update/delete/tasks |
| **Swappable** | Change the query (add caching, switch DB) without touching services or routes |
| **Readable routes** | The endpoint is 2 lines that say *what*, not *how* |

The cost is a little more indirection. For anything beyond a toy, it pays for itself the first time you need to change data access or write a test.

---

## Recap & next

- ✅ **Repositories** own data access (queries); **services** own business rules; neither knows HTTP.
- ✅ Services raise **domain exceptions**, not HTTP errors; repos `flush()` (not `commit()`).
- ✅ `model_dump(exclude_unset=True)` powers true partial `PATCH` updates.
- ✅ Services compose, so rules like ownership are written once and reused.
- ✅ Self-check: a task endpoint must check "do you own the parent project?" — which layer does that, and how does it avoid duplicating the check?

→ Next: **[03-3 · CRUD endpoints & pagination](03_crud_endpoints_pagination.md)**

## Exercises

1. Add a `count_by_status(project_id)` method to `TaskRepository` and a service method that returns `{status: count}`. Note how the SQL stays in the repo and the shaping stays in the service.

<details>
<summary>Solution</summary>

Repo: `select(Task.status, func.count()).where(Task.project_id==pid).group_by(Task.status)`. Service: call it (after an ownership check) and build the dict. SQL in the repository, rule + shaping in the service, nothing in the route.
</details>
