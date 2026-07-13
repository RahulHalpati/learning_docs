# 03 · Dictionaries

> **Level:** Beginner · **Prerequisites:** [02 · Tuples](02_tuples.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

A **dictionary** (`dict`) maps **keys** to **values** — look something up by name instead of by position. It's arguably the most important data structure in Python: JSON, configuration, database rows, counting, caching — all dictionaries underneath. Master this one.

## Concept: creating and reading

- **What:** a collection of `key: value` pairs, written in braces. Keys are unique; you look up a value by its key.
- **Why:** when "by position" (a list) is the wrong model and "by name" is the right one.

```python
user = {
    "name": "Ada",
    "age": 31,
}

print(user["name"])    # Ada   -> look up by key
print(user["age"])     # 31
print(len(user))       # 2     -> number of pairs
```

- Keys are usually strings, but can be any immutable value (numbers, tuples — recall the grid example).
- As of Python 3.7+, dictionaries **preserve insertion order**.

## Concept: adding, updating, and safe access

```python
user = {"name": "Ada", "age": 31}

user["email"] = "ada@x.io"   # add a new pair
user["age"] = 32             # update an existing key

print(user["name"])          # Ada
print(user.get("phone", "n/a"))   # n/a  -> safe lookup with a default
```

Output (verified):

```text
Ada
n/a
```

> ⚠️ **`[]` vs `.get()`:** `user["phone"]` raises `KeyError` if the key is missing. `user.get("phone")` returns `None` instead, and `user.get("phone", "n/a")` returns a default you choose. Use `.get()` when a key might be absent.

## Concept: checking membership and removing

```python
user = {"name": "Ada", "age": 32, "email": "ada@x.io"}

print("email" in user)        # True   -> `in` checks KEYS
print("Ada" in user)          # False  -> values are not checked by `in`

del user["email"]             # remove a pair (KeyError if absent)
age = user.pop("age")         # remove AND return the value
print(age, user)              # 32 {'name': 'Ada'}
```

## Concept: iterating over a dict

```python
user = {"name": "Ada", "age": 32, "email": "ada@x.io"}

print(list(user.keys()))      # ['name', 'age', 'email']
print(list(user.values()))    # ['Ada', 32, 'ada@x.io']

for key, value in user.items():       # .items() yields (key, value) tuples
    print(f"  {key} = {value}")
```

Output (verified):

```text
['name', 'age', 'email']
  name = Ada
  age = 32
  email = ada@x.io
```

`.items()` + tuple unpacking (`for key, value in ...`) is *the* idiom for walking a dictionary.

## Concept: counting with `.get()` (a classic pattern)

Dictionaries are perfect for tallying things:

```python
counts = {}
for ch in "banana":
    counts[ch] = counts.get(ch, 0) + 1   # default 0 the first time we see a char
print(counts)
```

Output (verified):

```text
{'b': 1, 'a': 3, 'n': 2}
```

This "get-with-default, then add one" pattern is so common that the standard library has a shortcut, `collections.Counter`, which you'll meet in [Section 03's stdlib tour](../03_functions_and_modules/06_standard_library_tour.md).

## Concept: nested dictionaries (modelling real data)

Dictionaries hold any values — including other dictionaries and lists. This is exactly the shape of **JSON**, the format web APIs speak (you'll see it again in FastAPI).

```python
order = {
    "id": 1001,
    "customer": {"name": "Ada", "vip": True},
    "items": [
        {"sku": "BK-1", "qty": 2, "price": 9.99},
        {"sku": "PN-7", "qty": 5, "price": 1.50},
    ],
}

print(order["customer"]["name"])             # Ada  -> drill in with chained keys
total = sum(i["qty"] * i["price"] for i in order["items"])
print(f"Order total: ${total:.2f}")
```

Output (verified):

```text
Ada
Order total: $27.48
```

## Worked example: a tiny phone book

```python
# phonebook.py — add, look up, and list contacts.

book = {}
book["Ada"] = "555-0100"
book["Grace"] = "555-0199"

# safe lookup
who = "Linus"
print(f"{who}: {book.get(who, 'not found')}")

# update and list
book["Ada"] = "555-0101"     # changed number
for name, number in book.items():
    print(f"{name}: {number}")
```

Output (verified):

```text
Linus: not found
Ada: 555-0101
Grace: 555-0199
```

## Common mistakes

**Mistake: `KeyError` on a missing key**
```python
user = {"name": "Ada"}
print(user["age"])
```
```text
KeyError: 'age'
```
**Why:** the key doesn't exist. Use `user.get("age")` (returns `None`) or check `"age" in user` first.

**Mistake: thinking `in` checks values**
```python
prices = {"apple": 1.0, "pear": 1.5}
print(1.0 in prices)     # False! -> `in` checks KEYS, not values
```
**Why:** `in` tests keys. To test values use `1.0 in prices.values()`.

**Mistake: using a mutable value (a list) as a key**
```python
d = {[1, 2]: "x"}
```
```text
TypeError: unhashable type: 'list'
```
**Why:** keys must be immutable/hashable. Use a tuple `(1, 2)` instead.

## Practice

**Exercise:** Given a list of words `["apple", "banana", "apple", "cherry", "banana", "apple"]`, build a dictionary of word → count, then print the most common word and its count.

*Hint:* count with `.get(word, 0) + 1`, then find the max by value with `max(counts, key=counts.get)`.

<details><summary>Solution</summary>

```python
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]

counts = {}
for word in words:
    counts[word] = counts.get(word, 0) + 1

most = max(counts, key=counts.get)    # the key with the largest value
print(f"Counts: {counts}")
print(f"Most common: {most} ({counts[most]})")
```

Output:

```text
Counts: {'apple': 3, 'banana': 2, 'cherry': 1}
Most common: apple (3)
```

`max(counts, key=counts.get)` looks at each key but compares them by `counts.get(key)` — i.e. by their counts — so it returns the key with the highest count.
</details>

## Recap & next

- ✅ Created dicts and looked values up by key.
- ✅ Used `.get()` for safe access and `in` for key membership.
- ✅ Iterated with `.items()` + unpacking.
- ✅ Counted with the `.get(k, 0) + 1` pattern.
- ✅ Modelled nested, JSON-shaped data.
- Self-check: what's the difference between `d["x"]` and `d.get("x")` when `"x"` is missing?

→ Next: **[04 · Sets](04_sets.md)**
