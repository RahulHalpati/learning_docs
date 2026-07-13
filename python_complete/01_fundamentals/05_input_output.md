# 05 · Input & Output

> **Level:** Beginner · **Prerequisites:** [04 · Strings](04_strings.md)
> **Time:** ~45 min · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

A program that can't communicate is useless. **Output** shows results; **input** lets a user steer the program. With both, you can write your first *interactive* programs.

## Concept: `print()` in depth

You've used `print`. It has a few options worth knowing:

```python
print("a", "b", "c")              # a b c   -> items joined by a space by default
print("a", "b", "c", sep="-")     # a-b-c   -> change the separator
print("no newline", end="")       # don't move to a new line after
print(" ...continued")            # this lands on the same line
```

Output (verified):

```text
a b c
a-b-c
no newline ...continued
```

- `sep=` sets what goes *between* items (default: a space).
- `end=` sets what goes *after* the line (default: `"\n"`, a newline). `end=""` keeps the next print on the same line.

## Concept: reading input with `input()`

- **What:** `input(prompt)` shows the prompt, waits for the user to type a line and press Enter, and returns what they typed.
- **Why:** it makes programs interactive.
- **Critical detail:** `input()` **always returns a `str`** — even if the user types `42`.

```python
name = input("What's your name? ")
print(f"Hello, {name}!")
```

A session looks like:

```text
What's your name? Ada
Hello, Ada!
```

### Converting input to numbers

Because input is always text, convert before doing maths:

```python
age_text = input("Your age? ")     # e.g. user types 30 -> "30"
age = int(age_text)                # "30" -> 30
print(f"In 10 years you'll be {age + 10}.")
```

Session:

```text
Your age? 30
In 10 years you'll be 40.
```

> ⚠️ If you forget to convert, `age + 10` becomes `"30" + 10` → `TypeError`. And if the user types `"thirty"`, `int("thirty")` raises `ValueError`. We'll handle that gracefully in [Section 05](../05_exceptions_and_errors/README.md); for now, assume cooperative input.

## Worked example: a tip calculator

Because `input()` pauses for a human, the file below is written so you can run it interactively. We show a sample session.

```python
# tip.py — interactive tip calculator.

bill_text = input("Bill amount: $")
tip_text = input("Tip percent: ")

bill = float(bill_text)            # "48.50" -> 48.5
tip_percent = float(tip_text)      # "18" -> 18.0

tip = bill * tip_percent / 100
total = bill + tip

print(f"Tip:   ${tip:.2f}")
print(f"Total: ${total:.2f}")
```

Sample session:

```text
Bill amount: $48.50
Tip percent: 18
Tip:   $8.73
Total: $57.23
```

> 🧪 **Testing input-driven scripts without typing:** you can pipe text in from the terminal:
> ```bash
> printf "48.50\n18\n" | python3 tip.py
> ```
> Each line feeds one `input()` call. This is how the output above was produced and verified.

## Concept: a peek at file output (optional)

Screen output is great, but you'll often want to *save* results. The modern, safe way uses a `with` block (fully explained in [Section 06](../06_pythonic_intermediate/04_context_managers.md)):

```python
with open("greeting.txt", "w") as f:    # "w" = write mode; creates/overwrites
    f.write("Hello from Python!\n")
# the file is automatically closed when the block ends
```

This creates `greeting.txt` containing one line. Reading it back:

```python
with open("greeting.txt") as f:          # default mode "r" = read
    content = f.read()
print(content)                           # Hello from Python!
```

Don't dwell on this yet — just know files use `open()` and a `with` block. We return to it properly later.

## Common mistakes

**Mistake: doing maths on raw input**
```python
n = input("A number: ")    # n is a STRING, e.g. "5"
print(n * 3)               # '555'  -> string repetition, not 15!
```
**Why:** `str * int` repeats the text. Convert first: `n = int(input("A number: "))`.

**Mistake: prompt with no trailing space**
```python
name = input("Name:")      # "Name:Ada"  cramped
```
**Why:** purely cosmetic, but add a trailing space (`"Name: "`) so the cursor isn't glued to your prompt.

## Practice

**Exercise:** Write `rectangle.py` that asks for a width and a height (whole numbers), then prints the area and perimeter. Convert the inputs properly.

<details><summary>Solution</summary>

```python
width = int(input("Width: "))
height = int(input("Height: "))
area = width * height
perimeter = 2 * (width + height)
print(f"Area: {area}")
print(f"Perimeter: {perimeter}")
```

Sample session (input piped as `5` then `3`):

```text
Width: Height: Area: 15
Perimeter: 16
```

(When piping, the prompts share a line because there's no interactive pause — run it by hand and they appear one at a time.) `int(...)` turns each typed line into a number so the arithmetic is numeric, not text.
</details>

## Recap & next

- ✅ Controlled `print` with `sep=` and `end=`.
- ✅ Read user input with `input()` — remembering it's **always a string**.
- ✅ Converted input with `int()`/`float()` before doing maths.
- ✅ Saw a preview of writing/reading files with `with open(...)`.
- Self-check: why does `input("Age: ") + 1` fail, and how do you fix it?

→ Next: **[06 · Control flow](06_control_flow.md)**
