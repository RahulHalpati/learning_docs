# 05 · Comprehensions

> **Level:** Beginner → Intermediate · **Prerequisites:** [01 · Lists](01_lists.md), [Section 01 loops](../01_fundamentals/07_loops.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Building a new list by looping and appending is so common that Python has a one-line shortcut: the **comprehension**. It's shorter, faster, and — once you can read it — clearer. This is one of the most recognisably "Pythonic" features, and you'll see it constantly from here on.

## Concept: the list comprehension

- **What:** a compact way to build a list from an existing iterable.
- **Why:** replaces the "create empty list → loop → append" boilerplate.

Compare the long form and the comprehension — they produce the *same* list:

```python
# the long way
squares = []
for n in range(6):
    squares.append(n * n)

# the comprehension — same result, one line
squares = [n * n for n in range(6)]
print(squares)
```

Output (verified):

```text
[0, 1, 4, 9, 16, 25]
```

Read it left to right as: **"`n * n` for each `n` in `range(6)`."** The shape is:

```text
[ EXPRESSION  for ITEM in ITERABLE ]
```

## Concept: filtering with `if`

Add an `if` at the end to keep only some items:

```python
evens = [n for n in range(10) if n % 2 == 0]
print(evens)        # [0, 2, 4, 6, 8]
```

Output (verified):

```text
[0, 2, 4, 6, 8]
```

Shape: `[ EXPRESSION for ITEM in ITERABLE if CONDITION ]`. The `if` decides whether each item is included.

A worked combination — uppercase only the long words:

```python
words = ["hi", "python", "ok", "comprehension"]
long_upper = [w.upper() for w in words if len(w) > 2]
print(long_upper)   # ['PYTHON', 'COMPREHENSION']
```

## Concept: transforming with a conditional expression

To *transform* (not filter) based on a condition, put a ternary in the **expression** part:

```python
nums = [-2, 5, -1, 8]
clamped = [n if n > 0 else 0 for n in nums]   # negatives become 0
print(clamped)      # [0, 5, 0, 8]
```

> 🧭 **Where does the `if` go?**
> - `if` **at the end** → *filter* (keep or drop the item).
> - `... if ... else ...` **in front of `for`** → *transform* (every item is kept, but changed).

## Concept: dict and set comprehensions

The same idea builds dictionaries and sets — just change the brackets:

```python
# dict comprehension: {key: value for ...}
sq_map = {n: n * n for n in range(4)}
print(sq_map)        # {0: 0, 1: 1, 2: 4, 3: 9}

# set comprehension: {value for ...}  (unique results)
lengths = {len(w) for w in ["a", "bb", "cc", "ddd"]}
print(lengths)       # {1, 2, 3}  -> "bb" and "cc" both give 2, deduped
```

Output (verified):

```text
{0: 0, 1: 1, 2: 4, 3: 9}
{1, 2, 3}
```

A practical dict comprehension — invert a lookup table:

```python
name_to_id = {"ada": 1, "grace": 2}
id_to_name = {id_: name for name, id_ in name_to_id.items()}
print(id_to_name)    # {1: 'ada', 2: 'grace'}
```

## Concept: a peek at generator expressions

Swap the brackets for parentheses and you get a **generator expression** — it produces items one at a time instead of building a whole list in memory. It's ideal when you only need to *consume* the values once, e.g. inside `sum()`:

```python
# no list is built — values stream straight into sum()
total = sum(n * n for n in range(1000))
print(total)         # 332833500
```

We cover generators properly in [Section 06](../06_pythonic_intermediate/02_generators.md). For now: **`[...]` builds a list; `(...)` streams values** and is more memory-efficient for large data you only pass through once.

## Worked example: cleaning a data set

```python
# clean.py — normalise and filter a messy list of names in one pass each.

raw = ["  Ada ", "", "GRACE", "linus ", "  ", "Margaret"]

# strip whitespace, drop blanks, title-case what remains
cleaned = [name.strip().title() for name in raw if name.strip()]
print(cleaned)

# build a quick lookup: name -> its length
name_lengths = {name: len(name) for name in cleaned}
print(name_lengths)
```

Output (verified):

```text
['Ada', 'Grace', 'Linus', 'Margaret']
{'Ada': 3, 'Grace': 5, 'Linus': 5, 'Margaret': 8}
```

The filter `if name.strip()` drops empty/whitespace entries (an empty string is falsy), while the expression `name.strip().title()` cleans the survivors.

## Common mistakes

**Mistake: cramming too much into one comprehension**
```python
# hard to read — nested loops + filter + transform
result = [f(x, y) for x in xs for y in ys if g(x) and h(y) if x != y]
```
**Why:** comprehensions are for *clear* one-liners. If you need to squint, use a regular `for` loop. Readability beats cleverness.

**Mistake: using a comprehension just for side effects**
```python
[print(x) for x in items]    # builds a throwaway list of None just to print
```
**Why:** you're creating a list you don't want. If you only need the side effect, write a plain `for` loop.

**Mistake: confusing filter vs transform placement**
```python
[n if n > 0 for n in nums]   # SyntaxError — ternary needs an else
```
**Why:** a trailing `if` filters (`[n for n in nums if n > 0]`); a leading `if/else` transforms (`[n if n > 0 else 0 for n in nums]`). Pick the right form.

## Practice

**Exercise:** Given `prices = [12.0, 5.5, 30.0, 8.0, 50.0]`, build (1) a list of prices with 20% tax added, rounded to 2 decimals, and (2) a list of only the *original* prices above \$10. Print both.

<details><summary>Solution</summary>

```python
prices = [12.0, 5.5, 30.0, 8.0, 50.0]

with_tax = [round(p * 1.20, 2) for p in prices]
expensive = [p for p in prices if p > 10]

print("With tax:", with_tax)
print("Above $10:", expensive)
```

Output:

```text
With tax: [14.4, 6.6, 36.0, 9.6, 60.0]
Above $10: [12.0, 30.0, 50.0]
```

The first comprehension *transforms* every price (multiply, round); the second *filters* to keep only those over 10.
</details>

## Recap & next

- ✅ Built lists in one line with `[expr for item in iterable]`.
- ✅ Filtered with a trailing `if`; transformed with a leading `if/else`.
- ✅ Wrote dict and set comprehensions.
- ✅ Met generator expressions `(...)` for memory-efficient streaming.
- Self-check: write a comprehension that gives the squares of the odd numbers from 1 to 10.

🎉 **Section 02 complete.** You can now store and reshape collections of data fluently.

→ Next: **[Section 03 · Functions & modules](../03_functions_and_modules/README.md)**
