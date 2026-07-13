# 03 · Operators & Expressions

> **Level:** Beginner · **Prerequisites:** [02 · Variables & types](02_variables_and_types.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Programs constantly compute and compare: a total, a discount, "is the user old enough?". **Operators** are the symbols that do this work, and an **expression** is any piece of code that produces a value. This module gives you the arithmetic, comparison, and logic you'll use in every program from here on.

## Concept: arithmetic operators

```python
print(7 + 3)    # 10   addition
print(7 - 3)    # 4    subtraction
print(7 * 3)    # 21   multiplication
print(7 / 2)    # 3.5  true division -> ALWAYS a float
print(7 // 2)   # 3    floor division -> drops the remainder, rounds down
print(7 % 2)    # 1    modulo -> the remainder after division
print(2 ** 10)  # 1024 exponentiation (2 to the power 10)
```

Output (verified):

```text
10 4 21 3.5 3 1 1024
```

Two are non-obvious and very useful:

- **`//` floor division** gives the whole-number part: `17 // 5 == 3`. Great for "how many full groups?".
- **`%` modulo** gives the leftover: `17 % 5 == 2`. The classic use is *"is this number even?"* → `n % 2 == 0`.

## Concept: operator precedence

Like maths, Python does `*`, `/`, `//`, `%` before `+` and `-`, and `**` before all of those. Use parentheses `()` to be explicit and readable.

```python
print(3 + 4 * 2)      # 11, not 14 -> the * happens first
print((3 + 4) * 2)    # 14 -> parentheses force the addition first
```

> 💡 When in doubt, **add parentheses**. They cost nothing and make intent obvious to the next reader (often future-you).

## Concept: comparison operators

These compare two values and produce a **bool** (`True`/`False`).

```python
print(5 > 3)     # True   greater than
print(5 == 5)    # True   equal? (note: TWO equals signs)
print(5 != 4)    # True   not equal
print("a" < "b") # True   strings compare alphabetically (by character code)
```

Output (verified):

```text
True True True True
```

> ⚠️ **`=` vs `==`** is the #1 beginner trap. `=` *assigns* (`x = 5`). `==` *compares* (`x == 5` asks "are they equal?"). Using `=` where you meant `==` is a `SyntaxError` in an `if`, which actually helps you catch it.

The full set: `<`, `<=`, `>`, `>=`, `==`, `!=`. You can even chain them like maths: `0 <= age <= 120` means "age is between 0 and 120 inclusive".

## Concept: boolean logic

Combine or invert booleans with `and`, `or`, `not`:

```python
print(True and False)   # False -> True only if BOTH are true
print(True or False)    # True  -> True if AT LEAST ONE is true
print(not True)         # False -> flips it
```

Output (verified):

```text
False False
True
```

Real use — guarding a decision:

```python
age = 20
has_ticket = True
can_enter = age >= 18 and has_ticket
print(can_enter)        # True
```

**Short-circuiting:** `and`/`or` stop early. `False and anything` is `False` without checking the right side; `True or anything` is `True`. This is handy and occasionally a subtle bug source — keep it in mind.

## Concept: augmented assignment

A shorthand for "update a variable using its current value":

```python
score = 10
score += 5     # same as: score = score + 5  -> 15
score -= 2     # -> 13
score *= 2     # -> 26
print(score)   # 26
```

`+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=` all exist. You'll use `+=` constantly (e.g. running totals in loops).

## Worked example: splitting a bill

```python
# bill.py — use //, %, and arithmetic together.

total_cents = 4625      # $46.25, stored as whole cents to avoid float rounding
people = 3

each = total_cents // people        # whole cents per person
remainder = total_cents % people    # leftover cents that don't divide evenly

print(f"Each pays {each} cents (${each/100:.2f})")
print(f"{remainder} cent(s) left over")
```

Output (verified):

```text
Each pays 1541 cents ($15.41)
2 cent(s) left over
```

> 💰 **Why cents, not dollars?** Floats can't represent `0.1` exactly, so money maths in floats drifts (`0.1 + 0.2 == 0.30000000000000004`). Working in integer cents sidesteps this. (For serious money code, the `decimal` module — Section 03's stdlib tour — is the professional tool.)

## Common mistakes

**Mistake: integer vs float division surprise**
```python
print(10 / 2)    # 5.0  (a float! note the .0)
```
**Why:** `/` is *always* float division in Python 3. If you want the integer `5`, use `//`: `10 // 2 == 5`.

**Mistake: comparing with `is` instead of `==`**
```python
print(1000 == 1000)   # True  -> compares VALUES
print(1000 is 1000)   # may be True OR False, and Python warns you
```
**Why:** `is` asks "are these the *same object in memory*?", not "are they equal?". For values, use `==`. Reserve `is` for `x is None`. (Modern Python even raises a `SyntaxWarning` for `is` with a literal.)

## Practice

**Exercise:** A shop gives 10% off orders over \$50. Given `price = 64.0`, compute the final price (apply the discount only if it qualifies — for now, just compute both and pick with a comparison printed as a bool; you'll do the real `if` next module). Print whether it qualifies and the discounted price rounded to 2 decimals.

<details><summary>Solution</summary>

```python
price = 64.0
qualifies = price > 50          # bool from a comparison
discounted = price * 0.9        # 10% off
print("Qualifies for discount:", qualifies)
print(f"Discounted price: ${discounted:.2f}")
```

Output:

```text
Qualifies for discount: True
Discounted price: $57.60
```

`price > 50` yields `True`; `price * 0.9` removes 10%; `:.2f` formats to two decimal places.
</details>

## Recap & next

- ✅ Arithmetic, including the special `//` (floor) and `%` (modulo).
- ✅ Precedence — and that parentheses make intent clear.
- ✅ Comparisons (`==` vs `=`!) producing booleans.
- ✅ Boolean logic with `and`/`or`/`not` and short-circuiting.
- ✅ Augmented assignment (`+=` and friends).
- Self-check: what does `17 % 4` give, and what does `17 // 4` give?

→ Next: **[04 · Strings](04_strings.md)**
