# 02 · Variables & Types

> **Level:** Beginner · **Prerequisites:** [01 · Setup](01_setup_and_first_program.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Every program shuffles **data** around: a username, a price, whether a box is ticked. To work with data you need to *store* it (variables) and know *what kind* it is (types). Get these right and the rest of Python clicks into place.

## Concept: variables

- **What:** a **variable** is a name that refers to a value. Think of it as a labelled box holding a value.
- **Why:** it lets you store a result now and use it later by name.
- **How:** use `=` (the **assignment** operator). The name goes on the left, the value on the right.

```python
age = 30              # the name `age` now refers to the value 30
name = "Ada"          # `name` refers to the text "Ada"
age = age + 1         # read the old value (30), add 1, store 31 back into `age`
print(name, age)      # -> Ada 31
```

`=` does **not** mean "equals" like in maths. It means *"make this name refer to this value."* `age = age + 1` is perfectly normal: compute the right side first, then re-point the label.

### Naming rules and style

- Must start with a letter or `_`, then letters/digits/underscores. No spaces, no starting with a digit.
- Case-sensitive: `age` and `Age` are different.
- **Style (PEP 8):** use `lower_snake_case` for variable names — words joined by underscores: `first_name`, `total_price`. This is the universal Python convention.
- Choose **descriptive** names. `n` tells the reader nothing; `num_students` tells them everything.

## Concept: the basic types

A **type** is the *kind* of value. Python's core built-in types you'll meet first:

| Type | Name | Example | Meaning |
|------|------|---------|---------|
| `int` | integer | `30`, `-7`, `0` | whole numbers |
| `float` | floating-point | `19.99`, `3.0`, `-0.5` | numbers with a decimal point |
| `str` | string | `"Ada"`, `'hi'` | text (any characters in quotes) |
| `bool` | boolean | `True`, `False` | a yes/no, on/off value |
| `NoneType` | none | `None` | "no value / nothing here" |

Python figures out the type from the value automatically — you don't declare it. Use the built-in `type()` to ask:

```python
age = 30
price = 19.99
name = "Ada"
is_member = True
nothing = None

print(type(age), type(price), type(name), type(is_member), type(nothing))
```

Output (verified):

```text
<class 'int'> <class 'float'> <class 'str'> <class 'bool'> <class 'NoneType'>
```

- **`int` vs `float`:** `5` is an int; `5.0` is a float. Mixing them in maths gives a float (`5 + 1.0` → `6.0`). Division with `/` always gives a float (`4 / 2` → `2.0`).
- **`bool`:** only two values, `True` and `False` (capitalised). Comes from comparisons, e.g. `age > 18`.
- **`None`:** a special placeholder meaning "nothing yet" — for example a setting that hasn't been chosen. It is *not* `0` and not `""`.

> 🧠 **Mental model:** a variable doesn't *have* a type — the *value* does. The same name can refer to an int now and a string later (`x = 5` then `x = "hi"`). That's called **dynamic typing**. It's flexible, but reusing one name for different kinds of thing is usually a smell.

## Concept: converting between types

Sometimes you have the right value in the wrong type — classically, text that should be a number (everything typed by a user arrives as a string).

```python
print(int("42") + 8)      # "42" -> 42, then + 8
print(float("3.14"))      # text -> float
print(str(100) + "%")     # 100 -> "100", then glue "%" on
```

Output (verified):

```text
50
3.14
100%
```

- `int(x)`, `float(x)`, `str(x)`, `bool(x)` are **constructors** — they build a value of that type from another.
- `int("42")` works; `int("hello")` raises a `ValueError` (a runtime error — Section 05). Always convert values you actually expect to be numeric.

## Worked example: an order summary

```python
# order.py — combine variables, types, and conversion.

product = "Notebook"
unit_price = 4.50              # float: has a decimal
quantity = 3                   # int: a whole count
total = unit_price * quantity  # float * int -> float

print("Product:", product)
print("Quantity:", quantity)
print("Total:", total)
print("Total is a", type(total).__name__)   # .__name__ gives just the type's name
```

Output (verified):

```text
Product: Notebook
Quantity: 3
Total: 13.5
Total is a float
```

## Common mistakes

**Mistake: adding a string and a number**
```python
age = 30
print("Age: " + age)
```
```text
TypeError: can only concatenate str (not "int") to str
```
**Why:** `+` between text and a number is ambiguous, so Python refuses. Fix by converting (`"Age: " + str(age)`) or, better, letting `print` handle it: `print("Age:", age)`.

**Mistake: using a variable before assigning it**
```python
print(score)
```
```text
NameError: name 'score' is not defined
```
**Why:** the label `score` was never pointed at a value. Assign it first: `score = 0`.

## Practice

**Exercise:** Create variables for a person's `first_name`, `last_name`, and `birth_year` (an int). Compute their age in 2026 and print: `"<First> <Last> is <age> years old."` Use conversion only where needed.

*Hint:* you can build the sentence with commas in `print`, or with an f-string (you'll learn those in Module 04 — commas are fine for now).

<details><summary>Solution</summary>

```python
first_name = "Grace"
last_name = "Hopper"
birth_year = 1990
age = 2026 - birth_year         # int - int -> int
print(first_name, last_name, "is", age, "years old.")
```

Output:

```text
Grace Hopper is 36 years old.
```

`2026 - birth_year` is int arithmetic, so `age` is a clean integer; `print` with commas inserts spaces and converts each item to text for display.
</details>

## Recap & next

- ✅ Stored values in variables with `=` (a label pointing at a value).
- ✅ Met the core types: `int`, `float`, `str`, `bool`, `None`.
- ✅ Inspected types with `type()` and converted with `int()/float()/str()`.
- ✅ Saw `TypeError` and `NameError` for the first time.
- Self-check: why does `4 / 2` give `2.0` and not `2`?

→ Next: **[03 · Operators & expressions](03_operators_and_expressions.md)**
