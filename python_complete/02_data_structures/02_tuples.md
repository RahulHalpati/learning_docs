# 02 · Tuples

> **Level:** Beginner · **Prerequisites:** [01 · Lists](01_lists.md)
> **Time:** ~45 min · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

A **tuple** is like a list, but **immutable** — once created, it can't be changed. That sounds like a limitation, but immutability is a feature: it signals "these values belong together and won't change," and it lets tuples be used as dictionary keys. Tuples also power one of Python's most-loved features: **unpacking**.

## Concept: creating tuples

- **What:** an ordered, **immutable** sequence, usually written with parentheses.
- **Why:** fixed records (a coordinate, an RGB colour, a row from a database) where changing items would be a bug.

```python
point = (3, 4)             # a 2-tuple
rgb = (255, 128, 0)        # a 3-tuple
single = (5,)              # a ONE-item tuple needs a trailing comma!
empty = ()
also_tuple = 1, 2, 3       # parentheses are often optional
```

Reading them is just like lists:

```python
point = (3, 4)
print(point[0])      # 3
print(len(point))    # 2
print(point[0] + point[1])  # 7
```

> ⚠️ **The one-element gotcha:** `(5)` is just the number 5 in parentheses. `(5,)` — with the comma — is a tuple of one item. The comma, not the parentheses, makes the tuple.

## Concept: immutability

```python
point = (3, 4)
point[0] = 9
```
```text
TypeError: 'tuple' object does not support item assignment
```

You can't change a tuple in place. To "change" one, build a new tuple. This guarantee is exactly why tuples are safe as dictionary keys (next module) and as constants.

## Concept: unpacking (the killer feature)

You can assign a tuple's items to several variables at once:

```python
point = (3, 4)
x, y = point          # x=3, y=4
print(x, y)           # 3 4
```

Output (verified):

```text
3 4
```

Unpacking shows up everywhere:

```python
# swap two variables with no temp variable
a, b = 1, 2
a, b = b, a
print(a, b)           # 2 1

# multiple return values (functions return tuples naturally)
def min_max(nums):
    return min(nums), max(nums)   # returns a tuple

lo, hi = min_max([5, 2, 9, 1])
print(lo, hi)         # 1 9

# the "rest" with *
first, *middle, last = [1, 2, 3, 4, 5]
print(first, middle, last)   # 1 [2, 3, 4] 5
```

Output:

```text
2 1
1 9
1 [2, 3, 4] 5
```

The `*name` soaks up "everything in the middle" as a list. This is the same unpacking you saw with `username, domain = email.split("@")` back in Section 01.

## Concept: tuples as dictionary keys

Because they're immutable (and therefore *hashable*), tuples can be dictionary keys — great for grids and lookups by a pair:

```python
grid = {(0, 0): "origin", (1, 2): "treasure"}
print(grid[(0, 0)])      # origin
```

Output (verified):

```text
origin
```

A list *can't* be a key (`TypeError: unhashable type: 'list'`) precisely because it could change underneath the dictionary.

## Worked example: returning structured data

```python
# stats.py — a function that returns several related values as a tuple.

def summarise(numbers):
    """Return (count, total, average) for a list of numbers."""
    count = len(numbers)
    total = sum(numbers)
    average = total / count
    return count, total, average        # a 3-tuple

count, total, avg = summarise([10, 20, 30, 40])
print(f"count={count}, total={total}, avg={avg}")
```

Output (verified):

```text
count=4, total=100, avg=25.0
```

Returning a tuple and unpacking it at the call site is the idiomatic Python way to return more than one value.

## Common mistakes

**Mistake: forgetting the trailing comma for a single-item tuple**
```python
t = (5)
print(type(t))    # <class 'int'>  -> NOT a tuple!
```
**Why:** parentheses alone group; the comma makes the tuple. Use `(5,)`.

**Mistake: trying to mutate a tuple**
```python
colours = ("red", "green")
colours.append("blue")
```
```text
AttributeError: 'tuple' object has no attribute 'append'
```
**Why:** tuples are immutable, so they have no `append`. If you need to add items, you wanted a list.

**Mistake: wrong number of values when unpacking**
```python
a, b = (1, 2, 3)
```
```text
ValueError: too many values to unpack (expected 2)
```
**Why:** the left side must match the number of items (or use `*rest` to absorb extras).

## Practice

**Exercise:** Write a function `divmod_pair(a, b)` that returns both the quotient (`a // b`) and remainder (`a % b`) as a tuple. Call it with `17, 5`, unpack into `q, r`, and print `"17 = 5*q + r"` with real values.

<details><summary>Solution</summary>

```python
def divmod_pair(a, b):
    return a // b, a % b

q, r = divmod_pair(17, 5)
print(f"17 = 5*{q} + {r}")    # 17 = 5*3 + 2
```

Output:

```text
17 = 5*3 + 2
```

The function returns a 2-tuple; unpacking pulls the quotient and remainder into `q` and `r`. (Python even has this built in: `divmod(17, 5)` returns `(3, 2)`.)
</details>

## Recap & next

- ✅ Created tuples (and the `(5,)` single-item gotcha).
- ✅ Understood immutability and why it's useful.
- ✅ Used **unpacking** for swaps, multiple return values, and `*rest`.
- ✅ Used tuples as dictionary keys.
- Self-check: when would you choose a tuple over a list?

→ Next: **[03 · Dictionaries](03_dicts.md)**
