# 03 · Type Hints

> **Level:** Intermediate · **Prerequisites:** [01 · Functions](01_functions.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Python doesn't *require* you to declare types — but **type hints** let you *annotate* what types your functions expect and return. They're optional and don't change how your program runs, yet they pay off enormously: editors autocomplete and catch mistakes, tools like **mypy** verify correctness before you run, and the next reader (you, in six months) instantly understands the code. FastAPI (Section 09) and Pydantic use type hints as their core mechanism, so this module is essential groundwork.

## Concept: annotating functions

- **What:** add `: type` after a parameter and `-> type` for the return.
- **Why:** documentation that tools can read and check.

```python
def greet(name: str, times: int = 1) -> str:
    return f"Hi {name}! " * times

print(greet("Ada", 2))
```

Output (verified):

```text
Hi Ada! Hi Ada! 
```

- `name: str` says "`name` should be a string."
- `times: int = 1` says "an int, defaulting to 1."
- `-> str` says "this function returns a string."

> ⚠️ **Hints are NOT enforced at runtime.** Python will happily run `greet(123)` — the hint is advice, not a guard. Checking is done by *external* tools (your editor, mypy). To actually *validate* data at runtime, you use Pydantic (Section 09) or write checks yourself.

You can see the annotations Python stored:

```python
print(greet.__annotations__)
```

Output (verified):

```text
{'name': <class 'str'>, 'times': <class 'int'>, 'return': <class 'str'>}
```

## Concept: collection types (modern syntax)

Since Python 3.9 you can use the built-in containers directly as generic types — no imports needed. This is the modern style this course uses:

```python
def total(prices: list[float]) -> float:
    return sum(prices)

def lookup(table: dict[str, int], key: str) -> int:
    return table[key]

def pair() -> tuple[int, str]:
    return (1, "one")
```

- `list[float]` — a list of floats.
- `dict[str, int]` — a dict mapping strings to ints.
- `tuple[int, str]` — a 2-tuple of an int then a string.
- `set[str]`, `list[list[int]]` (nested) all work the same way.

> 📌 **Old vs new:** older code imports `from typing import List, Dict` and writes `List[float]`. Since 3.9, prefer the lowercase built-ins `list[float]`. You'll still see the capitalised forms in older tutorials.

## Concept: optional and union types

A value that might be `None`, or might be one of several types:

```python
def first(items: list[str]) -> str | None:    # returns a str OR None
    return items[0] if items else None

print(first(["a", "b"]), first([]))            # a None
```

Output (verified):

```text
a None
```

- `X | None` means "an `X` or `None`" — the modern way (Python 3.10+) to write what used to be `Optional[X]`.
- `int | str` means "an int or a string" (a *union*).
- `str | None` is so common (a value that may be missing) that you'll use it constantly.

```python
def parse(value: int | str) -> int:
    """Accept an int or a numeric string, return an int."""
    return int(value)

print(parse(5), parse("42"))     # 5 42
```

## Concept: type aliases (the `type` statement, Python 3.12+)

When a type gets long or repeated, give it a name. Python 3.12 introduced a dedicated `type` statement:

```python
type Vector = list[float]          # a named alias (Python 3.12+)

def scale(v: Vector, k: float) -> Vector:
    return [k * x for x in v]

print(scale([1.0, 2.0, 3.0], 2))   # [2.0, 4.0, 6.0]
```

Output (verified on Python 3.12.13):

```text
[2.0, 4.0, 6.0]
```

> 📌 **Version note:** the `type X = ...` statement is **Python 3.12+**. On 3.9–3.11, write a plain assignment instead: `Vector = list[float]` (no `type` keyword). Both create an alias; only the syntax differs.

## Concept: checking types with mypy (optional tooling)

Hints become *powerful* when a checker verifies them. **mypy** is the standard static type checker. You'd install and run it like this (it's a third-party tool — see the next module on pip):

```bash
pip install mypy
mypy my_script.py
```

Given this bug:

```python
def add(a: int, b: int) -> int:
    return a + b

add("hello", 3)     # passing a str where int is expected
```

mypy reports it *without running the code*:

```text
error: Argument 1 to "add" has incompatible type "str"; expected "int"
```

That's the payoff: mistakes caught at your desk, not in production. (We don't run mypy in this course's verified outputs, but the workflow is exactly the above — it's standard in professional Python.)

## Worked example: a typed mini-API helper

```python
# typed.py — types make the contract obvious.

def build_user(name: str, age: int, tags: list[str] | None = None) -> dict[str, object]:
    """Build a user record. `tags` defaults to an empty list."""
    return {
        "name": name,
        "age": age,
        "tags": tags or [],        # None -> [] (None is falsy)
        "adult": age >= 18,
    }

print(build_user("Ada", 31, ["admin"]))
print(build_user("Sam", 15))
```

Output (verified):

```text
{'name': 'Ada', 'age': 31, 'tags': ['admin'], 'adult': True}
{'name': 'Sam', 'age': 15, 'tags': [], 'adult': False}
```

Just reading the signature tells you everything: two required values, an optional list of tags, returns a dict. That clarity is the point.

## Common mistakes

**Mistake: expecting hints to validate at runtime**
```python
def square(n: int) -> int:
    return n * n

print(square("ab"))    # 'abab' — runs fine! str * int repeats text
```
**Why:** hints are not checks. `"ab"` is a string, but Python ignores the hint and runs. For real validation, check explicitly or use Pydantic.

**Mistake: using old capitalised generics unnecessarily**
```python
from typing import List
def f(xs: List[int]) -> int: ...   # works, but dated
```
**Why:** since 3.9, `list[int]` is preferred and needs no import. Reserve `typing` imports for things without a builtin (you'll meet a few in [Section 06](../06_pythonic_intermediate/05_advanced_typing.md)).

## Practice

**Exercise:** Add type hints to this function and an alias for the price list. It takes a list of floats and a discount fraction (0–1), and returns a new list with the discount applied, rounded to 2 decimals.

```python
def apply_discount(prices, fraction):
    return [round(p * (1 - fraction), 2) for p in prices]
```

<details><summary>Solution</summary>

```python
type Prices = list[float]          # 3.12+; on older Python: Prices = list[float]

def apply_discount(prices: Prices, fraction: float) -> Prices:
    """Return prices with `fraction` (0–1) taken off, rounded to 2 dp."""
    return [round(p * (1 - fraction), 2) for p in prices]

print(apply_discount([10.0, 20.0, 4.99], 0.1))
```

Output:

```text
[9.0, 18.0, 4.49]
```

The alias `Prices` documents intent and is reused for both the parameter and the return type.
</details>

## Recap & next

- ✅ Annotated parameters and returns (`: type`, `-> type`).
- ✅ Used modern generics (`list[float]`, `dict[str, int]`).
- ✅ Expressed optional/union types with `X | None` and `int | str`.
- ✅ Named types with the 3.12 `type` statement (and the older fallback).
- ✅ Understood hints are advisory; **mypy** enforces them statically.
- Self-check: what does `dict[str, list[int]]` describe?

→ Next: **[04 · Modules & packages](04_modules_and_packages.md)**
