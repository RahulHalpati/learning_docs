# 03-1 · Pydantic schemas

> **Level:** Intermediate · **Prerequisites:** [02-1 · SQLAlchemy models](../02_data_layer/01_sqlalchemy_models.md)
> **Time:** 35 min · **Verified:** 2026-07-27 (pydantic 2.13.4)

## Why this matters

Your **models** are the database; your **schemas** are the API contract. Keeping them separate is a security and design essential: it's how you validate incoming data, and — critically — how you avoid leaking fields like `hashed_password` in responses. One model, several schemas: one for creating, one for reading, one for updating.

---

## One entity, three schemas

```python
# app/schemas/user.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import Role

class UserCreate(BaseModel):                       # what the client SENDS to register
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

class UserRead(BaseModel):                         # what the API RETURNS
    model_config = ConfigDict(from_attributes=True)   # read straight from the ORM object
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    # note: NO password / hashed_password field — it can never leak

class UserUpdate(BaseModel):                        # partial update — all optional
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
```

Three schemas, three jobs:
- **`UserCreate`** validates input — `EmailStr` checks the address, `Field(min_length=8)` enforces a password policy. Bad input → automatic **422** before your code runs.
- **`UserRead`** is the *response* shape. It has **no password field**, so a hash can never be serialized out, even by accident. This is your leak-prevention.
- **`UserUpdate`** makes every field optional for `PATCH` (partial updates).

> ⚠️ **Never return your ORM model directly.** Return a `Read` schema. If you `return user` (the SQLAlchemy object) with a response_model, FastAPI filters to the schema's fields — but the discipline of an explicit `Read` schema is what guarantees sensitive columns stay in the database.

---

## `from_attributes` — read from the ORM

`ConfigDict(from_attributes=True)` lets a `Read` schema be built from a SQLAlchemy object (reading attributes), so an endpoint can `return user` and FastAPI serializes it through `UserRead`:

```python
@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return user            # a SQLAlchemy User → serialized as UserRead (no hash)
```

---

## Validation is free and declarative

Constraints live on the schema, and FastAPI enforces them + documents them in OpenAPI:

```python
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    priority: TaskPriority = TaskPriority.medium      # enum → only valid values accepted
    assignee_id: int | None = None
```

Send `{"title": ""}` and you get a **422** with a precise error — no `if not title:` checks in your handler. Send `"priority": "urgent"` (not a valid enum) and it's rejected too. Validation you'd otherwise hand-write is declarative and self-documenting.

---

## Response models shape the docs

Because each route declares `response_model=...`, your OpenAPI/Swagger docs (`/docs`) show the *exact* response shape — the contract consumers rely on. Schemas aren't just validation; they're your API's public, typed interface.

---

## Recap & next

- ✅ Models = database; **schemas = API contract**. Keep them separate.
- ✅ Use distinct `Create` / `Read` / `Update` schemas per entity.
- ✅ The **`Read` schema has no secret fields** — that's how hashes never leak.
- ✅ `from_attributes=True` reads a schema from an ORM object; `Field(...)` gives free validation (422) + docs.
- ✅ Self-check: what stops `hashed_password` from appearing in `GET /me`'s response?

→ Next: **[03-2 · Repository & service pattern](02_repository_service_pattern.md)**

## Exercises

1. Add a `ProjectRead` that includes a computed `task_count`. (Hint: add the field and populate it in the service, or use a Pydantic computed field.)

<details>
<summary>Solution</summary>

Add `task_count: int` to `ProjectRead` and have the service set it (e.g. from a `COUNT` query) before returning, or expose it as a `@computed_field` if the ORM relationship is loaded. Either way the *schema* declares the contract; the *service* fills it.
</details>
