# 06 · Standard Library Tour

> **Level:** Intermediate · **Prerequisites:** [04 · Modules & packages](04_modules_and_packages.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Python is "batteries included": a huge **standard library** ships with the interpreter, so you don't have to install (or write) common tools. Knowing what's there saves you from reinventing wheels. This is a *tour* — a working familiarity with the modules you'll reach for most. The full reference is at <https://docs.python.org/3/library/>.

## `math` — numeric helpers

```python
import math

print(math.sqrt(144))     # 12.0   square root
print(math.floor(3.7))    # 3      round down
print(math.ceil(3.2))     # 4      round up
print(math.gcd(12, 18))   # 6      greatest common divisor
print(round(math.pi, 3))  # 3.142  (round() is a builtin, not from math)
```

Output (verified):

```text
12.0 3 4 6 3.142
```

## `random` — randomness

```python
import random

random.seed(42)                     # seed makes results reproducible (for demos/tests)
print(random.randint(1, 6))         # 6   random int in [1, 6] inclusive
print(random.choice(["a", "b", "c"]))  # a   pick one item
print(round(random.random(), 4))    # 0.025  random float in [0.0, 1.0)
```

Output (verified, because we seeded with 42):

```text
6
a
0.025
```

> 🧠 `random.seed(n)` fixes the sequence so you get the same "random" values every run — invaluable for reproducible tests. Without a seed, you'd get different values each time. (For security-sensitive randomness like tokens, use the `secrets` module instead.)

## `json` — read & write JSON

JSON is *the* data format of the web. Python objects ↔ JSON text in two functions:

```python
import json

data = {"name": "Ada", "tags": ["a", "b"], "age": 31}

text = json.dumps(data)             # Python dict -> JSON string ("dump-s"tring)
print(text)

back = json.loads(text)             # JSON string -> Python dict ("load-s"tring)
print(back["tags"], type(back).__name__)
```

Output (verified):

```text
{"name": "Ada", "tags": ["a", "b"], "age": 31}
['a', 'b'] dict
```

- `json.dumps(obj)` / `json.loads(text)` work with **strings**.
- `json.dump(obj, file)` / `json.load(file)` work with **files** (no `s`).
- `json.dumps(data, indent=2)` pretty-prints with indentation.

This is the same dict ↔ JSON conversion FastAPI does for you automatically in Section 09.

## `datetime` — dates and times

```python
from datetime import datetime, date, timedelta

d = date(2026, 6, 4)
print(d.isoformat(), d.year)        # 2026-06-04 2026

later = d + timedelta(days=30)      # date arithmetic
print("30 days later:", later.isoformat())

dt = datetime(2026, 6, 4, 14, 30)
print(dt.strftime("%Y-%m-%d %H:%M"))  # format to a custom string
```

Output (verified):

```text
2026-06-04 2026
30 days later: 2026-07-04
2026-06-04 14:30
```

- `date` is just the day; `datetime` includes the time.
- `timedelta` represents a *duration* you can add/subtract.
- `strftime` formats a datetime into text; `strptime` parses text back into a datetime.
- `datetime.now()` gives the current moment (we don't show it here because its output changes every run).

## `collections` — specialised containers

Three gems you'll use constantly:

**`Counter` — tally things in one line:**
```python
from collections import Counter

c = Counter("banana")
print(c)                  # Counter({'a': 3, 'n': 2, 'b': 1})
print(c.most_common(1))   # [('a', 3)]
```
Output:
```text
Counter({'a': 3, 'n': 2, 'b': 1})
[('a', 3)]
```
This replaces the manual `counts.get(ch, 0) + 1` loop from [Section 02](../02_data_structures/03_dicts.md).

**`defaultdict` — a dict with automatic default values:**
```python
from collections import defaultdict

groups = defaultdict(list)            # missing keys auto-create an empty list
for word in ["apple", "ant", "bee", "bat"]:
    groups[word[0]].append(word)      # no need to check if the key exists first
print(dict(groups))
```
Output:
```text
{'a': ['apple', 'ant'], 'b': ['bee', 'bat']}
```

**`namedtuple` — a lightweight record with named fields:**
```python
from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
print(p, p.x, p.y)        # Point(x=3, y=4) 3 4
```
Output:
```text
Point(x=3, y=4) 3 4
```
(For richer records, `dataclasses` — coming in [Section 04](../04_oop/06_dataclasses.md) — are usually the better choice.)

## `itertools` — efficient iteration tools

```python
import itertools

print(list(itertools.chain([1, 2], [3, 4])))          # join iterables
print(["".join(c) for c in itertools.combinations("abc", 2)])  # all 2-letter combos
```
Output (verified):
```text
[1, 2, 3, 4]
['ab', 'ac', 'bc']
```
Other staples: `itertools.count()`, `cycle()`, `groupby()`, `product()`. These produce values lazily (one at a time), which ties into generators in Section 06.

## `pathlib` — modern file paths

`pathlib.Path` is the modern, object-oriented way to handle file paths — cleaner and cross-platform compared to string juggling:

```python
from pathlib import Path

p = Path("/tmp/demo_dir/file.txt")
print(p.name)     # file.txt   the final component
print(p.suffix)   # .txt       the extension
print(p.stem)     # file       name without extension
print(p.parent)   # /tmp/demo_dir   the containing folder
```
Output (verified):
```text
file.txt
.txt
file
/tmp/demo_dir
```

Real file work with `Path` (combine paths with `/`, and read/write directly):

```python
from pathlib import Path

folder = Path("/tmp/demo_dir")
folder.mkdir(parents=True, exist_ok=True)   # create the folder if needed
file = folder / "notes.txt"                 # `/` joins path parts
file.write_text("hello\nworld\n")           # write a whole string
print(file.read_text())                     # read it all back
print(file.exists())                        # True
```
Output (verified):
```text
hello
world

True
```

> 💡 `pathlib` is preferred over the older `os.path` string functions for new code: `folder / "notes.txt"` reads better than `os.path.join(folder, "notes.txt")`, and `Path` objects carry handy methods.

## Other modules worth knowing exist

| Module | For |
|--------|-----|
| `os` / `sys` | operating system, environment variables, command-line args |
| `re` | regular expressions (pattern matching in text) |
| `csv` | reading/writing CSV spreadsheets |
| `decimal` | exact decimal arithmetic (money!) — fixes float rounding |
| `statistics` | mean, median, stdev |
| `logging` | proper logging (you'll use it in [Section 05](../05_exceptions_and_errors/08_best_practices.md)) |
| `secrets` | cryptographically secure random (tokens, passwords) |
| `urllib` / `http` | low-level HTTP (though `requests`/`httpx` are friendlier) |

When you have a common need, **check the standard library first** — it's probably already solved.

## Common mistakes

**Mistake: floats for money (use `decimal`)**
```python
print(0.1 + 0.2)      # 0.30000000000000004
```
**Why:** binary floats can't represent `0.1` exactly. For money, use `from decimal import Decimal; Decimal("0.1") + Decimal("0.2")` → `Decimal('0.3')`, or work in integer cents.

**Mistake: shadowing a stdlib module name** — naming your file `json.py` or `random.py` breaks `import json`. (Covered last module.)

## Practice

**Exercise:** Use `Counter` to find the three most common words in this text, and `json.dumps` to print the result as pretty JSON:
```python
text = "the quick brown fox the lazy dog the fox"
```

<details><summary>Solution</summary>

```python
from collections import Counter
import json

text = "the quick brown fox the lazy dog the fox"
words = text.split()
top3 = Counter(words).most_common(3)        # [('the', 3), ('fox', 2), ...]

print(json.dumps(dict(top3), indent=2))
```

Output:

```text
{
  "the": 3,
  "fox": 2,
  "quick": 1
}
```

`Counter(words).most_common(3)` returns the three highest counts as `(word, count)` tuples; `dict(...)` turns them into a dict and `json.dumps(..., indent=2)` pretty-prints it.
</details>

## Recap & next

- ✅ Toured `math`, `random`, `json`, `datetime`, `collections`, `itertools`, `pathlib`.
- ✅ Converted Python ↔ JSON with `json.dumps`/`loads`.
- ✅ Tallied with `Counter`, grouped with `defaultdict`, made records with `namedtuple`.
- ✅ Handled files and paths the modern way with `pathlib`.
- ✅ Learned to reach for the standard library before writing your own.
- Self-check: which module would you use to count occurrences, and which to handle file paths?

🎉 **Section 03 complete.** Your code is now organised, typed, installable, and powered by the standard library.

→ Next: **[Section 04 · Object-oriented programming](../04_oop/README.md)**
