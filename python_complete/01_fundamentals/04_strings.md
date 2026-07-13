# 04 · Strings

> **Level:** Beginner · **Prerequisites:** [03 · Operators](03_operators_and_expressions.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Text is everywhere: names, messages, file contents, web responses. A **string** (`str`) is Python's text type. Knowing how to slice, search, and build strings is a daily skill — and f-strings (string formatting) will appear in almost every program you write.

## Concept: making strings

A string is characters inside quotes. Single and double quotes are equivalent; pick one and be consistent.

```python
a = "hello"
b = 'world'
both = "she said \"hi\""     # \" is an escaped quote inside double quotes
path = 'C:\\Users\\Sam'      # \\ is a literal backslash
multi = """line one
line two"""                  # triple quotes span multiple lines
```

- **Escape sequences** start with `\`: `\n` newline, `\t` tab, `\"` quote, `\\` backslash.
- A **raw string** `r"C:\Users"` turns escapes off — handy for Windows paths and regular expressions.

## Concept: strings are sequences (indexing & slicing)

A string is an ordered sequence of characters, numbered from `0`.

```python
s = "Python"
#    P y t h o n
#    0 1 2 3 4 5      (and -1 -2 -3... from the right)

print(len(s))    # 6   number of characters
print(s[0])      # P   first character (index 0!)
print(s[-1])     # n   last character
print(s[0:3])    # Pyt slice: indices 0,1,2 (the end index is EXCLUDED)
print(s[::-1])   # nohtyP   step of -1 reverses it
```

Output (verified):

```text
6
P
n
Pyt
nohtyP
```

- **Indexing starts at 0.** The first item is `s[0]`, not `s[1]`.
- **Slicing** `s[start:stop]` includes `start`, excludes `stop`. `s[:3]` = first three; `s[2:]` = from index 2 to the end.
- The third number is a **step**: `s[::2]` takes every second char; `s[::-1]` walks backwards (a neat reverse).
- Strings are **immutable**: you can't change a character in place (`s[0] = "J"` raises `TypeError`). You build a *new* string instead.

## Concept: useful string methods

A **method** is a function attached to a value, called with a dot: `value.method()`. Strings have dozens; here are the workhorses.

```python
print("Python".upper())        # PYTHON
print("Python".lower())        # python
print("  hi  ".strip())        # 'hi'  -> removes leading/trailing whitespace
print("a,b,c".split(","))      # ['a', 'b', 'c'] -> splits into a list
print("ja".join(["a", "b"]))   # 'ajab' -> glue list items with "ja" between
print("banana".replace("a", "o"))  # bonono
print("Python".startswith("Py"))   # True
print("file.txt".endswith(".txt")) # True
print("Python".find("th"))     # 2  -> index where "th" starts (-1 if absent)
```

Verified samples:

```text
PYTHON
python
hi
['a', 'b', 'c']
ajab
```

> 🧠 Methods **return new strings** (strings are immutable); they never modify the original. `name.upper()` gives you an uppercase copy — `name` itself is unchanged unless you reassign: `name = name.upper()`.

`split`/`join` are a pair you'll lean on constantly: `split` breaks text apart, `join` stitches pieces together.

## Concept: f-strings (the modern way to build text)

- **What:** an **f-string** is a string prefixed with `f` where `{...}` holds a Python expression that gets inserted.
- **Why:** it's the clearest, fastest way to build text from values. Prefer it over `+` concatenation.

```python
name = "Ada"
age = 31
print(f"{name} is {age} years old.")     # Ada is 31 years old.
print(f"Next year: {age + 1}")           # expressions work: Next year: 32
```

**Format specifiers** after a colon control how a value is shown:

```python
import math
print(f"{math.pi:.2f}")     # 3.14   -> 2 decimal places
print(f"{255:#x}")          # 0xff   -> hexadecimal
print(f"{42:>6}")           # '    42' -> right-align in a width of 6
print(f"{0.25:.0%}")        # 25%    -> as a percentage
print(f"{name=}")           # name='Ada' -> debug form, shows name AND value
```

Verified samples:

```text
3.14
0xff
    42
```

The `{var=}` form is a debugging gift: it prints both the expression and its value.

## Worked example: a name formatter

```python
# format_name.py — clean up messy user-entered names.

raw = "   ada LOVELACE  "

cleaned = raw.strip()              # remove surrounding spaces
parts = cleaned.split()            # split on whitespace -> ['ada', 'LOVELACE']
first = parts[0].capitalize()      # 'Ada'  -> first letter up, rest down
last = parts[1].capitalize()       # 'Lovelace'
display = f"{first} {last}"
initials = f"{first[0]}.{last[0]}."

print(f"Display name: {display}")
print(f"Initials:     {initials}")
```

Output (verified):

```text
Display name: Ada Lovelace
Initials:     A.L.
```

## Common mistakes

**Mistake: off-by-one in slicing**
```python
s = "Python"
print(s[0:6])   # 'Python' — you need stop=6 to include index 5
print(s[0:5])   # 'Pytho' — stop is EXCLUSIVE, so index 5 ('n') is left out
```
**Why:** the stop index is *not* included. To get the whole string, the stop must be `len(s)` (or just omit it: `s[:]`).

**Mistake: trying to mutate a string**
```python
s = "cat"
s[0] = "b"
```
```text
TypeError: 'str' object does not support item assignment
```
**Why:** strings are immutable. Build a new one: `s = "b" + s[1:]` → `"bat"`.

**Mistake: forgetting the `f`**
```python
name = "Ada"
print("Hello {name}")    # Hello {name}  -> printed literally!
```
**Why:** without the `f` prefix, `{name}` is just text. Add it: `f"Hello {name}"`.

## Practice

**Exercise:** Given `email = "Ada.Lovelace@Example.COM"`, produce a normalised version: lowercase, and print the username (before `@`) and domain (after `@`) separately. Then print how many characters the whole email has.

*Hint:* `.lower()`, then `.split("@")`.

<details><summary>Solution</summary>

```python
email = "Ada.Lovelace@Example.COM"
normal = email.lower()                 # ada.lovelace@example.com
username, domain = normal.split("@")   # split into two parts, unpack into two names
print(f"Username: {username}")
print(f"Domain:   {domain}")
print(f"Length:   {len(email)} characters")
```

Output:

```text
Username: ada.lovelace
Domain:   example.com
Length:   24 characters
```

`split("@")` returns a 2-item list which we unpack directly into `username` and `domain`. (Multiple assignment like this is covered more in Section 02.)
</details>

## Recap & next

- ✅ Created strings, including escapes and triple-quoted text.
- ✅ Indexed and sliced (0-based; stop is exclusive; `[::-1]` reverses).
- ✅ Used core methods: `upper`, `lower`, `strip`, `split`, `join`, `replace`, `find`.
- ✅ Built text with **f-strings** and format specifiers — your go-to from now on.
- Self-check: how do you get the last 3 characters of a string `s`?

→ Next: **[05 · Input & output](05_input_output.md)**
