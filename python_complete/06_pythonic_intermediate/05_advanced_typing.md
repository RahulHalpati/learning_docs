# 05 · Advanced Typing

> **Level:** Advanced · **Prerequisites:** [Type hints](../03_functions_and_modules/03_type_hints.md), [Protocols](../04_oop/07_abstract_base_classes.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)
> **📌 Version:** the generic syntax `def f[T](...)` and `class Box[T]` is **new in Python 3.12**. Pre-3.12 alternatives are noted inline.

## Why this matters

Basic hints (`int`, `list[str]`) cover most code. But large codebases — and libraries like Pydantic and FastAPI — use richer typing tools to express precise contracts: "a function that works for any type but consistently", "a dict with exactly these keys", "anything with a `draw()` method". These types are checked by tools like **mypy** and power editor autocomplete. You won't need all of them daily, but recognising them makes professional code readable.

## Concept: generics — code that works for any type, consistently

A **generic** uses a type *variable* (here `T`) so the type checker knows the input and output types match. Python 3.12 gives this a clean syntax:

```python
def first[T](items: list[T]) -> T | None:    # 3.12 generic syntax
    return items[0] if items else None

print(first([1, 2, 3]))     # 1   — checker knows this is int | None
print(first(["a", "b"]))    # a   — checker knows this is str | None
print(first([]))            # None
```

Output (verified):

```text
1
a
None
```

`T` ties the input element type to the return type: pass a `list[int]`, get back `int | None`; pass a `list[str]`, get `str | None`. Without a generic, you'd have to type the return as `object | None` and lose that precision.

> 📌 **Pre-3.12:** you wrote `from typing import TypeVar; T = TypeVar("T")`, then `def first(items: list[T]) -> T | None:`. The 3.12 `[T]` syntax is sugar for the same thing.

## Concept: generic classes

Classes can be generic too — a `Box` that holds *some* type and remembers which:

```python
class Box[T]:                            # 3.12 generic class
    def __init__(self, value: T):
        self.value = value
    def get(self) -> T:
        return self.value

b = Box(42)            # a Box[int]
print(b.get())         # 42  — checker knows get() returns int
```

Output (verified):

```text
42
```

`Box[int]` and `Box[str]` are distinct to the type checker, so it catches `Box(42).get() + "oops"` before you run. (Pre-3.12: `class Box(Generic[T]):` with `T = TypeVar("T")`.)

## Concept: `Protocol` — structural typing recap

From [Section 04.07](../04_oop/07_abstract_base_classes.md): a `Protocol` describes an interface by its *methods*, not by inheritance. Anything with the right shape matches — duck typing the checker understands.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> str: ...

class Circle:                  # does NOT inherit Drawable
    def draw(self):
        return "O"

def render(shape: Drawable) -> str:   # accepts anything with draw()
    return shape.draw()

print(render(Circle()))                # O
print(isinstance(Circle(), Drawable))  # True (thanks to @runtime_checkable)
```

Output (verified):

```text
O
True
```

Use `Protocol` to type "anything that *can* do X" without forcing a base class — more flexible than an ABC, and the modern way to type duck-typed code.

## Concept: `TypedDict` — a dict with a known shape

When you have a dict that always has the same keys (a JSON record, a config), `TypedDict` documents and checks its structure — while it stays a plain dict at runtime:

```python
from typing import TypedDict

class Movie(TypedDict):
    title: str
    year: int

m: Movie = {"title": "Arrival", "year": 2016}    # checker verifies keys & types
print(m["title"], m["year"])                     # still an ordinary dict
```

Output (verified):

```text
Arrival 2016
```

A type checker now flags `m["yera"]` (typo) or `m["year"] = "soon"` (wrong type). This is great for the dicts you get from `json.loads` — you describe their shape once. (Pydantic, Section 09, takes this further with *runtime* validation.)

## Concept: typed `NamedTuple`

A class-based `NamedTuple` ([recall `collections.namedtuple`](../03_functions_and_modules/06_standard_library_tour.md)) with type annotations — an immutable record with named, typed fields:

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: int
    y: int

p = Point(1, 2)
print(p.x, p.y, p)        # 1 2 Point(x=1, y=2)
```

Output (verified):

```text
1 2 Point(x=1, y=2)
```

It's a tuple (immutable, unpackable, hashable) with named fields *and* type info — handy for small fixed records. (For mutable records or behaviour, prefer a `@dataclass`.)

## Concept: `Literal` and `Final`

Two precise, lightweight tools:

```python
from typing import Literal, Final

MAX_RETRIES: Final = 3                # Final = "don't reassign this constant"

def set_align(side: Literal["left", "right", "center"]) -> str:
    return side                       # only these three strings are allowed

print(set_align("left"), MAX_RETRIES)
```

Output (verified):

```text
left 3
```

- `Literal["left", "right"]` restricts a value to *specific* constants — a checker rejects `set_align("up")`. Great for modes, flags, and enum-like strings.
- `Final` marks a constant — the checker warns if you reassign `MAX_RETRIES` later.

## Concept: type aliases recap

From [Section 03.03](../03_functions_and_modules/03_type_hints.md), name complex types with the 3.12 `type` statement:

```python
type Json = dict[str, "Json"] | list["Json"] | str | int | float | bool | None
type UserId = int

def get_name(user_id: UserId) -> str:
    return f"user-{user_id}"

print(get_name(42))      # user-42
```

Output (verified):

```text
user-42
```

`UserId = int` documents *intent* (this int is an ID, not a count), and the recursive `Json` alias describes any JSON-shaped value. (Pre-3.12: plain `UserId = int` assignment, or `TypeAlias` from typing.)

## When to use what (quick guide)

| Need | Reach for |
|------|-----------|
| Function/class that works for any type *consistently* | **generics** `def f[T]` / `class C[T]` |
| "Anything with method X" without a base class | **`Protocol`** |
| A dict with fixed, known keys | **`TypedDict`** |
| Small immutable record with named fields | **`NamedTuple`** (or `@dataclass`) |
| Value limited to specific constants | **`Literal`** |
| A constant that shouldn't be reassigned | **`Final`** |
| A readable name for a complex type | **`type` alias** |

> 🧠 **Reality check:** none of these change runtime behaviour — they're for *humans and tools* (mypy, your editor). Run `mypy your_file.py` to actually enforce them. For *runtime* validation of incoming data, you need Pydantic (Section 09).

## Common mistakes

**Mistake: expecting `Literal`/`TypedDict` to enforce at runtime**
```python
def set_align(side: Literal["left", "right"]) -> str:
    return side

print(set_align("up"))    # runs fine! prints 'up' — hints aren't enforced
```
**Why:** like all hints, these are checked by mypy/your editor, not at runtime. `set_align("up")` runs. For runtime guarantees, validate explicitly or use Pydantic.

**Mistake: over-typing simple code**
```python
def add[T: (int, float)](a: T, b: T) -> T:    # overkill for a tiny helper
    return a + b
```
**Why:** generics shine in libraries and reusable components. For a one-off internal function, `def add(a, b):` (or simple `int` hints) is clearer. Match the typing effort to the code's reach.

## Practice

**Exercise:** (1) Write a generic function `last[T](items: list[T]) -> T | None` returning the last item or `None`. (2) Define a `TypedDict` `Config` with `host: str` and `port: int`, make one, and print a formatted URL. (3) Write `set_mode(mode: Literal["dev", "prod"])` that returns the mode.

<details><summary>Solution</summary>

```python
from typing import TypedDict, Literal

def last[T](items: list[T]) -> T | None:
    return items[-1] if items else None

print(last([1, 2, 3]))      # 3
print(last([]))             # None

class Config(TypedDict):
    host: str
    port: int

cfg: Config = {"host": "localhost", "port": 8000}
print(f"http://{cfg['host']}:{cfg['port']}")

def set_mode(mode: Literal["dev", "prod"]) -> str:
    return f"running in {mode}"

print(set_mode("prod"))
```

Output:

```text
3
None
http://localhost:8000
running in prod
```

`last[T]` ties the return type to the list's element type; `Config` documents the dict's shape; `set_mode`'s `Literal` would make a checker reject any mode other than `"dev"`/`"prod"`.
</details>

## Recap & next

- ✅ **Generics** (`def f[T]`, `class Box[T]`, 3.12 syntax) keep input/output types linked.
- ✅ **`Protocol`** types "anything with these methods" — structural, no inheritance.
- ✅ **`TypedDict`** describes a dict's fixed shape; **`NamedTuple`** a typed immutable record.
- ✅ **`Literal`** restricts to specific constants; **`Final`** marks constants.
- ✅ All are checked by tools (mypy/editor), not at runtime.
- Self-check: which tool types "a dict that always has keys `host` and `port`"?

🎉 **Section 06 complete.** Your Python is now idiomatic and efficient. Next: doing many things at once.

→ Next: **[Section 07 · Concurrency](../07_concurrency/README.md)**
