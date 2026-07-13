# 05 · Dunder Methods

> **Level:** Intermediate · **Prerequisites:** [04 · Polymorphism](04_polymorphism_and_duck_typing.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

**Dunder methods** (double-underscore methods like `__init__`, `__str__`) are how your objects hook into Python's built-in syntax. Define `__add__` and your objects respond to `+`. Define `__len__` and `len(obj)` works. Define `__eq__` and `==` does something sensible. These methods are what make custom types feel like first-class citizens — printing nicely, comparing correctly, working in loops. You've already used one (`__init__`); now you'll make objects *behave* like built-ins.

## Concept: what dunders are

"Dunder" = "Double UNDERscore". These are methods Python calls *for* you when you use an operator or built-in function:

| You write | Python calls |
|-----------|--------------|
| `obj` shown in REPL / `repr(obj)` | `obj.__repr__()` |
| `print(obj)` / `str(obj)` | `obj.__str__()` |
| `a + b` | `a.__add__(b)` |
| `a == b` | `a.__eq__(b)` |
| `len(obj)` | `obj.__len__()` |
| `obj[key]` | `obj.__getitem__(key)` |
| `x in obj` | `obj.__contains__(x)` |
| `for x in obj` | `obj.__iter__()` |

You never call `__add__` directly — you write `+` and Python routes it there.

## Concept: `__repr__` and `__str__` (make objects printable)

By default, printing an object is useless:

```python
class Money:
    def __init__(self, cents):
        self.cents = cents

print(Money(500))     # <__main__.Money object at 0x7f...>  -> unhelpful
```

Define `__repr__` (an unambiguous, developer-facing representation) and `__str__` (a friendly, user-facing one):

```python
class Money:
    def __init__(self, cents):
        self.cents = cents
    def __repr__(self):
        return f"Money({self.cents})"        # ideally looks like valid code to recreate it
    def __str__(self):
        return f"${self.cents / 100:.2f}"    # human-friendly

m = Money(750)
print(repr(m))     # Money(750)   -> __repr__
print(str(m))      # $7.50        -> __str__
print(m)           # $7.50        -> print uses __str__ (falls back to __repr__)
```

Output (verified):

```text
Money(750)
$7.50
$7.50
```

> 🧠 **Which to define?** If you write only one, write `__repr__` — it's the fallback for `str()` *and* what you see in the REPL, debuggers, and lists of objects. Add `__str__` only when you want a separate prettier form for end users.

## Concept: comparison dunders (`__eq__`)

By default, `==` checks identity (are they the *same object*?), so two equal-looking objects compare unequal:

```python
class Money:
    def __init__(self, cents):
        self.cents = cents

print(Money(500) == Money(500))    # False! — different objects in memory
```

Define `__eq__` to compare by value:

```python
class Money:
    def __init__(self, cents):
        self.cents = cents
    def __eq__(self, other):
        return self.cents == other.cents

print(Money(500) == Money(500))    # True
print(Money(500) == Money(999))    # False
```

Output (verified):

```text
True
False
```

Related: `__lt__` (`<`), `__le__` (`<=`), `__gt__` (`>`), etc., let you sort objects. Defining `__lt__` alone is enough for `sorted()` to work.

## Concept: arithmetic and container dunders

Make your type respond to `+` and `len()`:

```python
class Money:
    def __init__(self, cents):
        self.cents = cents
    def __repr__(self):
        return f"Money({self.cents})"
    def __add__(self, other):
        return Money(self.cents + other.cents)   # return a NEW Money
    def __len__(self):
        return self.cents

total = Money(500) + Money(250)     # calls __add__
print(repr(total))                  # Money(750)
print(len(Money(42)))               # 42  -> __len__
```

Output (verified):

```text
Money(750)
42
```

> 💡 Arithmetic dunders should usually return a **new** object, not mutate `self` — matching how `5 + 3` gives a new number rather than changing `5`.

## Concept: making an object iterable & indexable

```python
class Playlist:
    def __init__(self, songs):
        self._songs = songs
    def __len__(self):
        return len(self._songs)
    def __getitem__(self, index):        # enables  pl[0]  AND  for s in pl
        return self._songs[index]
    def __contains__(self, song):        # enables  "x" in pl
        return song in self._songs

pl = Playlist(["Song A", "Song B", "Song C"])
print(len(pl))               # 3
print(pl[1])                 # Song B   -> __getitem__
print("Song A" in pl)        # True     -> __contains__
for song in pl:              # iteration uses __getitem__ (or __iter__)
    print("-", song)
```

Output (verified):

```text
3
Song B
True
- Song A
- Song B
- Song C
```

With just a few dunders, `Playlist` now behaves like a built-in sequence — it has a length, supports indexing, membership tests, and `for` loops. That's the power: your objects integrate seamlessly with Python's syntax.

## Worked example: a 2D vector

```python
# vector.py — a math vector that adds, scales, compares, and prints.

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __repr__(self):
        return f"Vector({self.x}, {self.y})"
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)
    def __mul__(self, scalar):              # vector * number
        return Vector(self.x * scalar, self.y * scalar)
    def __abs__(self):                      # abs(v) -> magnitude
        return (self.x ** 2 + self.y ** 2) ** 0.5

a = Vector(1, 2)
b = Vector(3, 4)
print(a + b)                # Vector(4, 6)
print(a * 3)                # Vector(3, 6)
print(a == Vector(1, 2))    # True
print(abs(b))               # 5.0  (3-4-5 triangle)
```

Output (verified):

```text
Vector(4, 6)
Vector(3, 6)
True
5.0
```

`a + b`, `a * 3`, `a == ...`, `abs(b)` all read like ordinary maths — because the dunders wired your `Vector` into Python's operators.

## Common mistakes

**Mistake: `__eq__` assuming the other object is the same type**
```python
class Money:
    def __init__(self, cents): self.cents = cents
    def __eq__(self, other):
        return self.cents == other.cents     # crashes if other has no .cents

print(Money(500) == "hello")
```
```text
AttributeError: 'str' object has no attribute 'cents'
```
**Why:** `other` might be any type. Guard it: `if not isinstance(other, Money): return NotImplemented`. Returning `NotImplemented` lets Python fall back gracefully (often to `False`).

**Mistake: confusing `__str__` and `__repr__`**
- `__str__`: friendly, for end users (`print`). 
- `__repr__`: unambiguous, for developers (REPL, debugging, logs). 
If unsure, define `__repr__` — it's the universal fallback.

## Practice

**Exercise:** Create a `Fraction` class storing `numerator` and `denominator`. Add `__repr__` (e.g. `"3/4"`), `__eq__` (compare by cross-multiplication so `1/2 == 2/4`), and `__add__` (add two fractions, no need to simplify). Test all three.

<details><summary>Solution</summary>

```python
class Fraction:
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator
    def __repr__(self):
        return f"{self.numerator}/{self.denominator}"
    def __eq__(self, other):
        # 1/2 == 2/4  ->  1*4 == 2*2
        return self.numerator * other.denominator == other.numerator * self.denominator
    def __add__(self, other):
        # a/b + c/d = (a*d + c*b) / (b*d)
        new_num = self.numerator * other.denominator + other.numerator * self.denominator
        new_den = self.denominator * other.denominator
        return Fraction(new_num, new_den)

print(Fraction(1, 2) == Fraction(2, 4))   # True
print(Fraction(1, 2) + Fraction(1, 3))    # 5/6
print(repr(Fraction(3, 4)))               # 3/4
```

Output:

```text
True
5/6
3/4
```

`__eq__` cross-multiplies so mathematically-equal fractions compare equal; `__add__` uses the common-denominator formula and returns a new `Fraction`.
</details>

## Recap & next

- ✅ Dunder methods hook your objects into Python's syntax and built-ins.
- ✅ `__repr__`/`__str__` make objects print usefully (define `__repr__` at minimum).
- ✅ `__eq__`/`__lt__` enable value comparison and sorting.
- ✅ `__add__`/`__mul__`/`__abs__` enable operators; `__len__`/`__getitem__`/`__contains__` make containers.
- Self-check: which dunder should you define first, and why?

→ Next: **[06 · dataclasses](06_dataclasses.md)**
