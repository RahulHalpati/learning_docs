# 01 · Functions

> **Level:** Beginner · **Prerequisites:** [Section 02](../02_data_structures/README.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

A **function** is a named, reusable block of code. Instead of repeating the same ten lines in five places (and fixing the same bug in five places), you write it once, give it a name, and *call* it. Functions are how you break a big problem into small, testable pieces — the single most important organisational tool in programming.

## Concept: defining and calling

- **What:** `def` creates a function. You give it a name, optional **parameters** (inputs), and a body. Calling it with `name(args)` runs the body.
- **Why:** reuse, naming, and isolation. A well-named function is documentation.

```python
def greet(name):              # `name` is a parameter (a placeholder input)
    return f"Hello, {name}!"  # `return` hands a value back to the caller

message = greet("Ada")        # "Ada" is the argument; the result is stored
print(message)                # Hello, Ada!
print(greet("Grace"))         # call again with a different argument
```

Output (verified):

```text
Hello, Ada!
Hello, Grace!
```

- **Parameter** = the name in the definition (`name`). **Argument** = the actual value you pass (`"Ada"`).
- The function body is the indented block (same indentation rule as `if`/`for`).
- Define a function *before* you call it (the `def` must run first).

## Concept: `return` vs `print`

This trips up nearly every beginner. They are not the same:

- `print(x)` **shows** `x` on screen and gives back nothing useful.
- `return x` **sends `x` back** to whoever called the function, so the value can be stored, reused, or combined.

```python
def add_print(a, b):
    print(a + b)        # shows it, returns None

def add_return(a, b):
    return a + b        # hands the value back

x = add_print(2, 3)     # prints 5, but...
print(x)                # None  <- nothing was returned

y = add_return(2, 3)    # prints nothing, but...
print(y * 10)           # 50    <- we can USE the returned value
```

Output (verified):

```text
5
None
50
```

> 🧠 **Rule of thumb:** functions that *compute* should `return`. Reserve `print` for actually showing things to a user. A function that only prints can't be reused in a calculation.

## Concept: returning nothing, and early return

A function with no `return` (or a bare `return`) gives back `None`. You can also `return` early to stop the function:

```python
def safe_divide(a, b):
    if b == 0:
        return None          # bail out early; skip the rest
    return a / b

print(safe_divide(10, 2))    # 5.0
print(safe_divide(10, 0))    # None
```

Output (verified):

```text
5.0
None
```

Early returns (often called "guard clauses") keep code flat and readable — handle the bad cases first, then the happy path.

## Concept: returning multiple values

As you saw with tuples, a function can return several values at once:

```python
def min_max(numbers):
    return min(numbers), max(numbers)   # a tuple

low, high = min_max([5, 2, 9, 1])       # unpack the tuple
print(low, high)                        # 1 9
```

## Concept: docstrings

A **docstring** is a string literal as the first line of a function body. It documents what the function does and is the standard, tool-readable way to explain code.

```python
def add(a, b):
    """Return the sum of a and b."""    # this is the docstring
    return a + b

print(add.__doc__)        # Return the sum of a and b.
help(add)                 # shows the signature + docstring (try it in the REPL)
```

Output (verified):

```text
Return the sum of a and b.
```

For anything non-trivial, document parameters, the return value, and notable errors:

```python
def withdraw(balance, amount):
    """Subtract amount from balance.

    Args:
        balance: current funds (must be >= amount).
        amount: how much to withdraw (must be positive).
    Returns:
        The new balance.
    """
    return balance - amount
```

We'll use this docstring style throughout the course.

## Worked example: a small toolbox

```python
# toolbox.py — a few cooperating functions.

def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32

def is_freezing(celsius):
    """Return True if the temperature is at or below freezing."""
    return celsius <= 0

def describe_weather(celsius):
    """Build a human-readable weather line."""
    f = celsius_to_fahrenheit(celsius)
    state = "freezing" if is_freezing(celsius) else "above freezing"
    return f"{celsius}°C ({f:.1f}°F) — {state}"

for temp in [-5, 0, 22]:
    print(describe_weather(temp))
```

Output (verified):

```text
-5°C (23.0°F) — freezing
0°C (32.0°F) — freezing
22°C (71.6°F) — above freezing
```

Notice how `describe_weather` *reuses* the two smaller functions. Small functions that each do one thing compose into bigger behaviour — that's the whole game.

## Common mistakes

**Mistake: forgetting to `return` (function gives `None`)**
```python
def double(x):
    x * 2          # computed, but never returned!

print(double(5))   # None
```
**Why:** the result is thrown away. Add `return`: `return x * 2`.

**Mistake: calling before defining**
```python
print(square(4))
def square(n):
    return n * n
```
```text
NameError: name 'square' is not defined
```
**Why:** Python runs top to bottom; the `def` hasn't executed yet when the call happens. Define functions above the code that uses them (or inside `main()` patterns).

**Mistake: a mutable default argument** (a famous trap — covered next module)
```python
def add_item(item, basket=[]):    # DON'T: the [] is shared across calls
    basket.append(item)
    return basket
```
**Why:** the default list is created once and reused, so it accumulates across calls. Use `basket=None` and create a fresh list inside. Full explanation in [Module 02](02_arguments_and_scope.md).

## Practice

**Exercise:** Write `initials(full_name)` that returns the uppercase initials of a name. `initials("ada lovelace")` → `"AL"`. Then write `greet_formally(full_name)` that uses it to return `"Welcome, A.L."`. Give both docstrings.

<details><summary>Solution</summary>

```python
def initials(full_name):
    """Return uppercase initials, e.g. 'ada lovelace' -> 'AL'."""
    return "".join(word[0].upper() for word in full_name.split())

def greet_formally(full_name):
    """Return a formal greeting using dotted initials."""
    dotted = ".".join(initials(full_name))     # 'AL' -> 'A.L'
    return f"Welcome, {dotted}."

print(initials("ada lovelace"))     # AL
print(greet_formally("ada lovelace"))  # Welcome, A.L.
```

Output:

```text
AL
Welcome, A.L.
```

`initials` splits the name into words and takes each first letter; `greet_formally` reuses it and joins the letters with dots.
</details>

## Recap & next

- ✅ Defined and called functions with `def` and `return`.
- ✅ Learned the crucial `return` vs `print` distinction.
- ✅ Used early returns (guard clauses) and multiple return values.
- ✅ Wrote docstrings, the standard way to document.
- Self-check: why can a `return`-ing function be reused in a calculation but a `print`-ing one can't?

→ Next: **[02 · Arguments & scope](02_arguments_and_scope.md)**
