# 02 · Arguments & Scope

> **Level:** Intermediate · **Prerequisites:** [01 · Functions](01_functions.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Functions become far more flexible once you control *how* arguments are passed: defaults, any number of arguments, keyword-only options. And understanding **scope** (where a variable is visible) prevents a whole category of confusing bugs. This module covers the argument features you'll see in every real codebase, including FastAPI later.

## Concept: positional vs keyword arguments

```python
def area(width, height):
    return width * height

print(area(3, 4))                    # positional: 3->width, 4->height
print(area(height=5, width=2))       # keyword: order no longer matters
```

Output (verified):

```text
12
10
```

Keyword arguments make calls self-documenting (`area(width=2, height=5)` is clearer than `area(2, 5)`), and let you skip the positional order.

## Concept: default arguments

Give a parameter a default value so callers can omit it:

```python
def power(base, exp=2):       # exp defaults to 2
    return base ** exp

print(power(5))               # 25  -> uses exp=2
print(power(5, 3))            # 125 -> overrides to 3
```

Output (verified):

```text
25
125
```

Defaults must come *after* non-default parameters (`def f(a, b=1)` is fine; `def f(a=1, b)` is a `SyntaxError`).

## Concept: the mutable-default trap ⚠️

This is one of Python's most famous gotchas — and a great early lesson in how Python evaluates things.

```python
def add_item(item, basket=[]):    # the [] is created ONCE, at definition time
    basket.append(item)
    return basket

print(add_item("apple"))    # ['apple']
print(add_item("pear"))     # ['apple', 'pear']  <- surprise! the list persisted
```

Output (verified):

```text
['apple']
['apple', 'pear']
```

**Why:** the default `[]` is evaluated a single time when the function is *defined*, not each call. Every call that omits `basket` shares that same list. The fix — use `None` as a sentinel and create a fresh object inside:

```python
def add_item(item, basket=None):
    if basket is None:
        basket = []           # a brand-new list every call
    basket.append(item)
    return basket

print(add_item("apple"))    # ['apple']
print(add_item("pear"))     # ['pear']  -> correct, independent
```

Output (verified):

```text
['apple']
['pear']
```

> 📌 **Rule:** never use a mutable value (`[]`, `{}`, `set()`) as a default argument. Use `None` and build it inside.

## Concept: `*args` and `**kwargs`

Accept any number of arguments:

- `*args` collects extra **positional** arguments into a **tuple**.
- `**kwargs` collects extra **keyword** arguments into a **dict**.

```python
def total(*numbers):              # numbers is a tuple
    return sum(numbers)

print(total(1, 2, 3, 4))          # 10

def describe(**attrs):            # attrs is a dict
    return ", ".join(f"{k}={v}" for k, v in attrs.items())

print(describe(color="red", size="L"))   # color=red, size=L
```

Output (verified):

```text
10
color=red, size=L
```

The names `args`/`kwargs` are convention; the `*` and `**` are what matter. You can combine everything in one signature:

```python
def report(title, *items, sep=", ", **meta):
    return f"{title}: {sep.join(items)} ({meta})"

print(report("Cart", "a", "b", "c", sep=" | ", currency="USD"))
```

Output (verified):

```text
Cart: a | b | c ({'currency': 'USD'})
```

### Unpacking *into* a call

The same `*`/`**` syntax can *spread* a collection into arguments:

```python
nums = [1, 2, 3, 4]
print(total(*nums))               # same as total(1, 2, 3, 4) -> 10

opts = {"color": "blue", "size": "M"}
print(describe(**opts))           # same as describe(color="blue", size="M")
```

## Concept: keyword-only arguments

A bare `*` in the signature forces everything after it to be passed by keyword — great for optional flags whose meaning isn't obvious positionally:

```python
def connect(host, *, port=5432, timeout=30):
    return f"{host}:{port} t={timeout}"

print(connect("db", port=5433))     # OK
# connect("db", 5433)               # TypeError: takes 1 positional arg
```

Output (verified):

```text
db:5433 t=30
```

This is exactly how you avoid mystery calls like `connect("db", 5433, 30, True, False)`.

## Concept: scope (local vs global)

**Scope** is *where a name is visible*. Variables created inside a function are **local** — they exist only during that call.

```python
def f():
    x = 10        # local to f
    return x

print(f())        # 10
# print(x)        # NameError: x is not defined out here
```

A function can *read* outer (global) variables, but assigning to a name makes it local unless you say otherwise:

```python
counter = 0

def bump():
    global counter      # "I mean the module-level counter, not a new local"
    counter += 1

bump(); bump()
print(counter)          # 2
```

Output (verified):

```text
2
```

> 🧠 **`global` is usually a smell.** Needing it often means you should *return* a value and let the caller reassign, rather than reaching out and mutating shared state. Use it sparingly.

Python looks up names using the **LEGB** rule: **L**ocal → **E**nclosing → **G**lobal → **B**uilt-in.

## Concept: closures

A function defined inside another function "remembers" the enclosing variables — that's a **closure**. It's the foundation of decorators (Section 06).

```python
def make_adder(n):
    def adder(x):
        return x + n        # `adder` closes over `n`
    return adder

add10 = make_adder(10)
print(add10(5))             # 15  -> n=10 was captured
```

Output (verified):

```text
15
```

## Concept: lambdas (tiny anonymous functions)

A `lambda` is a one-expression function with no name. Its main use is as a short throwaway passed to functions like `sorted`:

```python
people = [("Ada", 31), ("Grace", 45), ("Linus", 28)]
people.sort(key=lambda p: p[1])     # sort by the second item (age)
print(people)

print(sorted([3, -1, 2], key=abs))  # sort by absolute value
```

Output (verified):

```text
[('Linus', 28), ('Ada', 31), ('Grace', 45)]
[-1, 2, 3]
```

> 💡 If a lambda gets complicated, use a named `def` — it's clearer and can have a docstring. Lambdas are for the trivially short.

## Common mistakes

**Mistake: the mutable default** — covered above; use `None`.

**Mistake: assigning to a global without declaring it**
```python
total = 0
def add(n):
    total = total + n     # error: `total` is treated as local here
```
```text
UnboundLocalError: cannot access local variable 'total' where it is not associated with a value
```
**Why:** assigning to `total` makes it local, so reading it on the right side fails. Either `return` the new value (preferred) or declare `global total`.

**Mistake: passing arguments in the wrong order**
```python
def divide(a, b): return a / b
divide(2, 10)     # 0.2 — did you mean divide(10, 2)?
```
**Why:** positional order matters. Use keywords for clarity: `divide(a=10, b=2)`.

## Practice

**Exercise:** Write `make_multiplier(factor)` that returns a function multiplying its input by `factor`. Create `triple = make_multiplier(3)` and use it. Then write `summarise(*nums, label="total")` that returns `"<label>: <sum>"`.

<details><summary>Solution</summary>

```python
def make_multiplier(factor):
    """Return a function that multiplies its argument by `factor`."""
    def multiplier(x):
        return x * factor       # closure over factor
    return multiplier

triple = make_multiplier(3)
print(triple(10))               # 30

def summarise(*nums, label="total"):
    """Sum any number of values, prefixed by a keyword-only label."""
    return f"{label}: {sum(nums)}"

print(summarise(1, 2, 3))               # total: 6
print(summarise(10, 20, label="sum"))   # sum: 30
```

Output:

```text
30
total: 6
sum: 30
```

`make_multiplier` captures `factor` in a closure; `summarise` collects positional values into `nums` and takes `label` by keyword.
</details>

## Recap & next

- ✅ Used positional, keyword, default, `*args`, `**kwargs`, and keyword-only arguments.
- ✅ Internalised the **mutable-default trap** (use `None`).
- ✅ Unpacked collections into calls with `*`/`**`.
- ✅ Understood scope (LEGB), `global`, and closures.
- ✅ Wrote `lambda`s for short throwaway functions.
- Self-check: why is `def f(x, cache={})` dangerous, and what's the fix?

→ Next: **[03 · Type hints](03_type_hints.md)**
