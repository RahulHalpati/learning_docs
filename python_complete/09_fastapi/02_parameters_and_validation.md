# 02 · Parameters & Validation

> **Level:** Advanced · **Prerequisites:** [01 · First app](01_first_app.md), [type hints](../03_functions_and_modules/03_type_hints.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (FastAPI 0.136.3)

## Why this matters

Real endpoints take input: which item (`/items/42`), how many results (`?limit=10`), what to search for (`?q=phone`). FastAPI reads these from the URL, **converts them to the types you declare**, and **validates them automatically** — returning a clear `422` error for bad input, with zero validation code from you. This is the type-hints payoff: your annotations *are* the validation rules.

## Concept: path parameters

A `{name}` in the route path becomes a function parameter. Declare its type and FastAPI converts and validates it:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/items/{item_id}")
def get_item(item_id: int):                 # {item_id} -> int parameter
    return {"item_id": item_id, "type": type(item_id).__name__}

client = TestClient(app)
print(client.get("/items/42").json())       # converted to int
print("non-int:", client.get("/items/abc").status_code)   # validation fails
```

Output (verified):

```text
{'item_id': 42, 'type': 'int'}
non-int: 422
```

The path sends text (`"42"`), but because you typed `item_id: int`, FastAPI **converts** it to the integer `42` (note `'type': 'int'`). And `/items/abc` — which can't be an int — automatically returns **`422 Unprocessable Entity`** with a helpful error body. You wrote no validation; the type hint did it.

## Concept: query parameters

Function parameters that *aren't* in the path become **query parameters** (the `?key=value` part of a URL). Give them defaults to make them optional:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/search")
def search(q: str = "", limit: int = 10, sort: str = "asc"):
    return {"q": q, "limit": limit, "sort": sort}

client = TestClient(app)
print(client.get("/search?q=phone&limit=5").json())
print(client.get("/search").json())          # all defaults
```

Output (verified):

```text
{'q': 'phone', 'limit': 5, 'sort': 'asc'}
{'q': '', 'limit': 10, 'sort': 'asc'}
```

- A parameter with a **default** is optional; without one, it's required (and a missing required query param gives `422`).
- `limit=10` is typed `int`, so `?limit=5` arrives as the integer `5` — again, auto-converted and validated.

> 🧠 **How FastAPI decides:** if the parameter name appears in the path (`{item_id}`), it's a path param; otherwise it's a query param. The type hint drives conversion and validation either way.

## Concept: optional parameters with `None`

For a query param that may be entirely absent, type it `X | None` with a `None` default ([Section 03.03](../03_functions_and_modules/03_type_hints.md)):

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/products")
def list_products(category: str | None = None):
    if category is None:
        return {"showing": "all products"}
    return {"showing": f"category: {category}"}

client = TestClient(app)
print(client.get("/products").json())                 # absent -> None
print(client.get("/products?category=books").json())  # provided
```

Output (verified):

```text
{'showing': 'all products'}
{'showing': 'category: books'}
```

## Concept: constraints with `Query` and `Path`

Beyond types, you often need *rules*: "limit between 1 and 100", "id at least 1". Use `Query(...)` / `Path(...)` with constraints, attached via `Annotated` (the modern style):

```python
from fastapi import FastAPI, Query, Path
from fastapi.testclient import TestClient
from typing import Annotated

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: Annotated[int, Path(ge=1)]):          # id must be >= 1
    return {"user_id": user_id}

@app.get("/items")
def list_items(limit: Annotated[int, Query(ge=1, le=100)] = 10):   # 1..100
    return {"limit": limit}

client = TestClient(app)
print(client.get("/users/5").json())
print("user 0:", client.get("/users/0").status_code)     # violates ge=1
print(client.get("/items?limit=50").json())
print("limit 500:", client.get("/items?limit=500").status_code)   # violates le=100
```

Output (verified):

```text
{'user_id': 5}
user 0: 422
{'limit': 50}
limit 500: 422
```

Common constraints:

| Constraint | Meaning | Applies to |
|-----------|---------|-----------|
| `ge` / `le` | greater/less than **or equal** | numbers |
| `gt` / `lt` | strictly greater/less than | numbers |
| `min_length` / `max_length` | string length bounds | strings |
| `pattern` | regular-expression match | strings |

`Annotated[int, Query(ge=1, le=100)]` reads as "an int, with these query constraints." Violations produce a `422` automatically — and the constraints also show up in the `/docs`.

> 📌 **`Annotated` is the recommended modern style** (FastAPI's docs use it throughout). You may see the older form `limit: int = Query(10, ge=1, le=100)` in tutorials; both work, but `Annotated` keeps the type and the metadata cleanly separated.

## Concept: combining path + query

A single endpoint can take both. When a query param is declared **before** a path param in the function signature, use `Path()` explicitly so FastAPI knows which is which — and to add constraints at the same time:

```python
from fastapi import FastAPI, Path
from fastapi.testclient import TestClient
from typing import Annotated

app = FastAPI()

@app.get("/user/{user_id}/post")
def user(
    user: str,                                      # query (not in path)
    user_id: Annotated[int, Path(ge=1, le=100)],   # path, constrained 1–100
):
    return {"user": user, "user_id": user_id}

test = TestClient(app)
print(test.get("/user/23/post?user=rahul").json())
```

Output (verified):

```text
{'user': 'rahul', 'user_id': 23}
```

> 📌 **Why `Path()` matters here:** FastAPI always resolves path vs query by checking whether the name appears in the URL template (`{user_id}` → path, `user` → query), so the declaration order in the function signature does **not** affect routing. However, declaring a query param first without `Path()` on the path param would look inconsistent and skip constraints. Using `Annotated[int, Path(ge=1, le=100)]` makes the intent explicit *and* enforces the range in one step.

## Concept: the 422 validation response

When validation fails, FastAPI returns `422` with a structured body explaining *exactly* what went wrong — which field, what rule, and the bad input:

```python
# requesting /items?limit=500 (limit must be <= 100) returns 422 with:
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 100",
      "input": "500",
      "ctx": {"le": 100}
    }
  ]
}
```

The `loc` tells you it was the `limit` *query* param, `msg` is human-readable, and `input` echoes the offending value. Your front-end (or the auto-docs) can show this to users directly — robust input validation, entirely for free.

## Common mistakes

**Mistake: expecting a string when you typed an int**
```python
@app.get("/items/{item_id}")
def get(item_id: int): ...
# /items/3.5 -> 422, because 3.5 is not an int
```
**Why:** the type hint is enforced. If you want to accept `"3.5"` or arbitrary text, type the parameter `str` (or `float`) instead.

**Mistake: required query param with no default**
```python
@app.get("/search")
def search(q: str): ...      # q has NO default -> it's REQUIRED
# /search (no q) -> 422
```
**Why:** a parameter without a default is required. Add `q: str = ""` (or `str | None = None`) to make it optional.

## Practice

**Exercise:** Build `GET /books/{book_id}` where `book_id` must be `>= 1`, plus query params `lang` (string, default `"en"`) and `max_pages` (int, optional, between 1 and 5000). Return all three. Verify: a valid call, a `book_id` of 0 (→422), and a `max_pages` of 9999 (→422).

<details><summary>Solution</summary>

```python
from fastapi import FastAPI, Query, Path
from fastapi.testclient import TestClient
from typing import Annotated

app = FastAPI()

@app.get("/books/{book_id}")
def get_book(
    book_id: Annotated[int, Path(ge=1)],
    lang: str = "en",
    max_pages: Annotated[int | None, Query(ge=1, le=5000)] = None,
):
    return {"book_id": book_id, "lang": lang, "max_pages": max_pages}

client = TestClient(app)
print(client.get("/books/12?lang=fr&max_pages=300").json())
print("book 0:", client.get("/books/0").status_code)
print("max_pages 9999:", client.get("/books/1?max_pages=9999").status_code)
```

Output:

```text
{'book_id': 12, 'lang': 'fr', 'max_pages': 300}
book 0: 422
max_pages 9999: 422
```

`Path(ge=1)` enforces a valid id; `lang` has a default so it's optional; `max_pages` is optional (`None` default) but *if provided* must be 1–5000 — both violations correctly return `422`.
</details>

## Recap & next

- ✅ Path params (`{id}`) and query params (`?key=value`) are just typed function parameters.
- ✅ FastAPI **converts** them to your declared types and **validates** automatically (`422` on failure).
- ✅ Optional params use a default (or `X | None = None`).
- ✅ Added constraints with `Annotated[int, Query(ge=..., le=...)]` / `Path(...)`.
- ✅ The `422` response pinpoints the field, rule, and bad input.
- Self-check: how does FastAPI decide whether a parameter is a path or query param?

→ Next: **[03 · Request bodies & Pydantic](03_request_bodies_pydantic.md)**
