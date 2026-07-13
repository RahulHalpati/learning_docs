# 06 · dataclasses

> **Level:** Intermediate · **Prerequisites:** [05 · Dunder methods](05_dunder_methods.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Many classes are just "data bags" — a bundle of named values (a `Point`, a `Config`, a `User`). Writing `__init__`, `__repr__`, and `__eq__` for each by hand is tedious and error-prone. The `dataclasses` module (standard library) **generates those dunders for you** from the type-annotated fields. Less boilerplate, fewer bugs, clearer intent. This is the modern way to write data-holding classes, and it's conceptually close to the Pydantic models you'll use in FastAPI.

## Concept: the boilerplate problem

Compare a hand-written data class…

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
```

…with the `@dataclass` version that does *all of that automatically*:

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int           # a field — note the type annotation is REQUIRED here
    y: int = 0        # a field with a default

print(Point(3, 4))                 # Point(x=3, y=4)   -> free __repr__
print(Point(3, 4) == Point(3, 4))  # True             -> free __eq__
print(Point(1))                    # Point(x=1, y=0)   -> default used
```

Output (verified):

```text
Point(x=3, y=4)
True
Point(x=1, y=0)
```

The `@dataclass` decorator reads the annotated fields and writes `__init__`, `__repr__`, and `__eq__` for you. **Type annotations are mandatory** — that's how it knows what the fields are. (The types still aren't *enforced* at runtime — see [Section 03's type hints](../03_functions_and_modules/03_type_hints.md) — but Pydantic, Section 09, adds that enforcement.)

## Concept: defaults and the mutable-default fix

Fields can have defaults, with the same rule as functions: defaulted fields come after non-defaulted ones. And the mutable-default trap returns — but dataclasses give you a clean tool, `field(default_factory=...)`:

```python
from dataclasses import dataclass, field

@dataclass
class Cart:
    items: list = field(default_factory=list)   # a fresh [] for each instance
    def add(self, item):
        self.items.append(item)

a = Cart()
a.add("apple")
b = Cart()
print(a.items, b.items)        # ['apple'] []  -> independent lists
```

Output (verified):

```text
['apple'] []
```

> 📌 **Rule:** for a mutable default (`list`, `dict`, `set`), use `field(default_factory=list)`, not `items: list = []`. The latter raises an error in dataclasses precisely to stop you from sharing one list across instances.

## Concept: frozen (immutable) dataclasses

Pass `frozen=True` to make instances read-only — like a tuple with named fields. Great for values that shouldn't change after creation (configs, coordinates):

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    host: str
    port: int = 8000

c = Config("localhost")
print(c)                # Config(host='localhost', port=8000)
c.port = 9000           # attempt to mutate
```

Output (verified):

```text
Config(host='localhost', port=8000)
```
then:
```text
dataclasses.FrozenInstanceError: cannot assign to field 'port'
```

Frozen instances are also **hashable**, so they can be used in sets and as dict keys.

## Concept: ordering

Pass `order=True` and the dataclass gets `__lt__`, `__le__`, `__gt__`, `__ge__` — comparing fields in the order they're declared. That makes instances sortable for free:

```python
from dataclasses import dataclass

@dataclass(order=True)
class Version:
    major: int
    minor: int

versions = [Version(1, 2), Version(1, 0), Version(2, 0)]
print(sorted(versions))
```

Output (verified):

```text
[Version(major=1, minor=0), Version(major=1, minor=2), Version(major=2, minor=0)]
```

They sort by `major` first, then `minor` — exactly tuple-comparison semantics, generated for you.

## Concept: adding behaviour and `__post_init__`

A dataclass is a normal class — you can add methods, properties, and validation. `__post_init__` runs *after* the generated `__init__`, ideal for validation or derived fields:

```python
from dataclasses import dataclass

@dataclass
class Temperature:
    celsius: float

    def __post_init__(self):
        if self.celsius < -273.15:
            raise ValueError("below absolute zero")

    @property
    def fahrenheit(self):
        return self.celsius * 9 / 5 + 32

t = Temperature(25)
print(t.fahrenheit)        # 77.0
```

Output (verified):

```text
77.0
```

`Temperature(-500)` would raise `ValueError` from `__post_init__` — validation without writing the whole `__init__`.

## Worked example: an order line

```python
# order_line.py — a realistic data record with a computed total.

from dataclasses import dataclass, field

@dataclass
class OrderLine:
    sku: str
    quantity: int
    unit_price: float
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)

line = OrderLine("BK-1", quantity=3, unit_price=9.99)
line.notes.append("gift wrap")
print(line)
print("Total:", line.total)
print("Equal to identical line?", line == OrderLine("BK-1", 3, 9.99, ["gift wrap"]))
```

Output (verified):

```text
OrderLine(sku='BK-1', quantity=3, unit_price=9.99, notes=['gift wrap'])
Total: 29.97
Equal to identical line? True
```

You got a clean constructor, a readable `repr`, value-based `==`, a per-instance `notes` list, *and* a computed `total` — with almost no boilerplate.

## Common mistakes

**Mistake: forgetting the type annotation**
```python
@dataclass
class Point:
    x = 0           # no annotation -> NOT treated as a dataclass field!
```
**Why:** dataclasses only pick up *annotated* names (`x: int`). A bare `x = 0` becomes an ordinary class attribute and is ignored by the generated `__init__`. Always annotate: `x: int = 0`.

**Mistake: a mutable default without `default_factory`**
```python
@dataclass
class Bad:
    items: list = []
```
```text
ValueError: mutable default <class 'list'> for field items is not allowed: use default_factory
```
**Why:** dataclasses detect the shared-mutable trap and stop you. Use `field(default_factory=list)`.

## Practice

**Exercise:** Create a frozen, ordered dataclass `Student` with fields `name: str`, `grade: float`, and `subjects: tuple[str, ...] = ()`. Make a few students, sort them, and confirm two students with identical data are equal. (Use a tuple, not a list, so the frozen instance stays hashable.)

<details><summary>Solution</summary>

```python
from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class Student:
    name: str
    grade: float
    subjects: tuple[str, ...] = ()

students = [
    Student("Ada", 92.0, ("math", "cs")),
    Student("Bo", 88.5),
    Student("Cy", 92.0),
]
print(sorted(students))
print(Student("Bo", 88.5) == Student("Bo", 88.5))   # True
print({Student("Bo", 88.5)})                          # works in a set (hashable)
```

Output:

```text
[Student(name='Ada', grade=92.0, subjects=('math', 'cs')), Student(name='Bo', grade=88.5, subjects=()), Student(name='Cy', grade=92.0, subjects=())]
True
{Student(name='Bo', grade=88.5, subjects=())}
```

Sorting compares `name` first (so Ada < Bo < Cy); `frozen=True` makes instances immutable *and* hashable, so they work in a set.
</details>

## Recap & next

- ✅ `@dataclass` generates `__init__`, `__repr__`, `__eq__` from annotated fields.
- ✅ Used defaults and `field(default_factory=...)` for mutable defaults.
- ✅ Made immutable, hashable records with `frozen=True` and sortable ones with `order=True`.
- ✅ Added methods, properties, and validation via `__post_init__`.
- Self-check: why must dataclass fields be annotated, and how do you give a list field a safe default?

→ Next: **[07 · Abstract base classes](07_abstract_base_classes.md)**
