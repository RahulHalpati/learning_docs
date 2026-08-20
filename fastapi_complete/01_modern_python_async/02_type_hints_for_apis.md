# 01-2 · Type hints for APIs

> **Level:** Beginner · **Prerequisites:** [01-1 · Tooling: uv & project setup](01_tooling_uv_project_setup.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (Python 3.12 · mypy · pyright)

## Why this matters

In most languages, type annotations are for the compiler and disappear at runtime. In FastAPI they are **load-bearing**: the framework reads your function's type hints *at runtime* and derives request validation, response serialization, and the OpenAPI docs from them. Declare a parameter `user_id: int` and FastAPI converts the path string, rejects `"abc"` with a proper 422, and documents the field — all from that one hint. Hints you'd write as decoration elsewhere are your API contract here, so writing them fluently is a prerequisite, not a nicety.

---

## Function annotations — the basics

```python
def greet(name: str, excited: bool = False) -> str:
    suffix = "!" if excited else "."
    return f"Hello, {name}{suffix}"

# Built-in generics — no imports needed on 3.12:
def summarize(scores: list[int]) -> dict[str, float]:
    return {"mean": sum(scores) / len(scores), "max": float(max(scores))}
```

- **Parameters and return types, always.** In this course an unannotated signature is a defect — ruff and your type checker are configured to agree.
- **`list[int]`, `dict[str, float]`, `tuple[int, str]`** — lowercase built-ins, parameterized directly. The old `from typing import List, Dict` is dead; don't import what the language gives you.
- A bare `list` or `dict` hint is a smell: it tells FastAPI (and readers) nothing about what's *inside*, which is usually the part that matters.

---

## `X | None`, not Optional

"Might be absent" is the single most common shape in API code — an optional query param, a nullable DB column, a lookup that can miss:

```python
def find_user(user_id: int) -> User | None:
    """Return the user, or None if no such id."""
    ...

# The classic trap — a default of None must be reflected in the hint:
def search(q: str, limit: int | None = None) -> list[User]:
    effective_limit = limit if limit is not None else 50
    ...
```

- **`X | None` is the 2026 standard.** `Optional[X]` means the same thing but is legacy spelling; ruff's `UP` rules rewrite it on sight.
- Read it literally: "a `User`, or `None`." The type checker then *forces* every caller to handle the `None` branch — the whole class of `AttributeError: 'NoneType' object has no attribute ...` production crashes becomes a red squiggle at dev time instead.
- In FastAPI, `limit: int | None = None` on an endpoint means *optional query parameter* — the hint drives the API behavior directly.

---

## Annotated — attaching metadata to a type

`Annotated[T, ...]` is a type plus extra metadata bolted on. Type checkers see only `T`; frameworks can read the metadata at runtime:

```python
from typing import Annotated

# Plain type: "q is a string"
q: str

# Annotated: "q is a string, AND here's extra info for whoever inspects it"
q: Annotated[str, "must be lowercase"]        # metadata can be anything
```

This is exactly the hook FastAPI and Pydantic build on — the metadata slot carries validation rules and dependency wiring:

```python
from typing import Annotated
from fastapi import Depends, Query

# Validation metadata: still a str to the type checker,
# but FastAPI enforces the length rules and documents them.
q: Annotated[str, Query(min_length=1, max_length=50)]

# Dependency metadata: inject the result of get_db here.
db: Annotated[AsyncSession, Depends(get_db)]
```

Why not just `q: str = Query(min_length=1)`? That older style lies to the type checker — it claims the *default value* of a `str` parameter is a `Query` object. `Annotated` keeps the two channels separate: the type is the type, the metadata rides alongside. One more payoff: an `Annotated[...]` alias is reusable — define `DbSession = Annotated[AsyncSession, Depends(get_db)]` once and every endpoint just says `db: DbSession`.

---

## TypedDict vs dataclass vs Pydantic model

Three ways to say "an object with these fields" — the difference is **what happens at runtime**:

```python
from dataclasses import dataclass
from typing import TypedDict
from pydantic import BaseModel

class UserRow(TypedDict):        # still a plain dict at runtime
    id: int
    email: str

@dataclass
class RetryPolicy:               # a real class; NO validation
    attempts: int
    backoff_s: float

class UserCreate(BaseModel):     # validates & converts at runtime
    email: str
    age: int | None = None
```

| | Runtime object | Validates input? | Use it for |
|---|---|---|---|
| `TypedDict` | plain `dict` | No — checker-only | Typing dicts you don't control: JSON blobs, rows from a driver, `**kwargs` |
| `dataclass` | class instance | No | *Internal* structures built from data you already trust: config, in-process value objects |
| Pydantic `BaseModel` | class instance | **Yes** — parses, converts, rejects | Every **trust boundary**: request bodies, responses, external API payloads, env config |

The decision rule is about trust: **data crossing a trust boundary gets a Pydantic model** — a client can send `{"age": "forty"}` and only Pydantic turns that into a clean 422 instead of a deep, confusing `TypeError`. Data that never leaves your process doesn't need to pay validation cost twice — a dataclass (or TypedDict, if it really is just a dict) is lighter and honest about that. Validating already-validated data everywhere is a performance tax; validating *nothing* at the boundary is a security hole. Pick per boundary, not per habit.

---

## mypy / pyright — the checker that runs before runtime

Hints only pay off if something checks them. Two mainstream checkers, same job:

```bash
uv add --dev mypy
uv run mypy src/
```

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true                # new project? start strict — loosening later is easy,
                             # tightening a lax codebase is a slog
```

```python
def find_user(user_id: int) -> User | None: ...

user = find_user(42)
print(user.email)
# mypy: error: Item "None" of "User | None" has no attribute "email"
```

That error is a production `NoneType` crash caught at zero cost, before the code ever ran. **pyright** is the same idea (it powers Pylance, so VS Code users already run it live in-editor); either is fine — pick one, wire it into CI next to ruff, and treat its errors like test failures. The layering: **ruff** catches style and bug patterns, the **type checker** proves the hints are consistent, and **FastAPI/Pydantic** enforce those same hints at runtime against real input. Three layers, one set of annotations.

---

## The punchline: hints are the API contract

Everything above converges in a single FastAPI endpoint — this is the code Section 02 starts from:

```python
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,                                      # path param: str → int, 422 if not numeric
    db: Annotated[AsyncSession, Depends(get_db)],      # dependency injected via metadata
    verbose: bool = False,                             # optional query param, "true"/"1" parsed
) -> UserOut:                                          # response validated & documented
    ...
```

No parsing code, no validation code, no docs written by hand — FastAPI introspected the hints and generated all of it. Delete the hints and the endpoint doesn't merely lose documentation; it loses its behavior. That's what "load-bearing" means.

---

## Recap & next

- ✅ Annotate every signature; use built-in generics (`list[int]`), never bare `list`/`dict`.
- ✅ `X | None` for "maybe absent" — and the checker forces callers to handle the `None` branch.
- ✅ `Annotated[T, metadata]` keeps the type honest while carrying validation/DI info — the mechanism FastAPI and Pydantic are built on.
- ✅ Trust decides the shape: Pydantic at trust boundaries, dataclass/TypedDict for internal, already-trusted data.
- ✅ mypy or pyright in CI turns hints into enforced contracts instead of comments.
- ✅ Self-check: why does FastAPI need `Annotated` rather than reading a plain `q: str` hint for validation rules — what can't a plain type express?

→ Next: **[01-3 · async/await mechanics](03_async_await_mechanics.md)**

## Exercises

1. Fully annotate this function, including the tricky return type, then explain what the hint tells a caller that the code alone doesn't guarantee loudly:

```python
def parse_port(raw):
    if raw.isdigit() and 0 < int(raw) < 65536:
        return int(raw)
    return None
```

<details>
<summary>Solution</summary>

```python
def parse_port(raw: str) -> int | None:
    if raw.isdigit() and 0 < int(raw) < 65536:
        return int(raw)
    return None
```

The `int | None` return makes the failure path part of the signature: every caller is forced (by mypy/pyright) to handle `None` before using the value as an int. Without the hint, the `None` return is invisible until it explodes somewhere far from this function.
</details>

2. You're building an endpoint that accepts a JSON body `{"email": ..., "age": ...}` from clients, an internal `CacheEntry(value, expires_at)` object passed between your own functions, and you're typing the raw dict rows a legacy DB driver returns. Which of TypedDict / dataclass / Pydantic model fits each, and why?

<details>
<summary>Solution</summary>

- JSON body → **Pydantic model**: it crosses a trust boundary; clients send garbage, and only Pydantic validates/converts and produces a 422.
- `CacheEntry` → **dataclass**: internal, constructed from data you already trust — validation would be redundant cost, and you want a real object with attribute access.
- Driver rows → **TypedDict**: they *are* plain dicts at runtime and you don't control their construction; TypedDict types them for the checker without changing anything at runtime.
</details>

3. Write `Annotated`-based aliases `Limit` (an `int` query param constrained to 1–100 via `Query(ge=1, le=100)`) and use it in two endpoint signatures. What did the alias buy you over repeating the constraint inline?

<details>
<summary>Solution</summary>

```python
from typing import Annotated
from fastapi import Query

Limit = Annotated[int, Query(ge=1, le=100)]

@app.get("/users")
async def list_users(limit: Limit = 20) -> list[UserOut]: ...

@app.get("/posts")
async def list_posts(limit: Limit = 50) -> list[PostOut]: ...
```

One definition, one place to change the policy (say, cap at 200), and the two endpoints can't drift apart. Note the defaults still differ per endpoint — `Annotated` carries the type + constraint, the default value stays local. This only works because `Annotated` is a first-class type; the old `limit: int = Query(...)` style couldn't be aliased.
</details>
