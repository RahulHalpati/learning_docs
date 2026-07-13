# 02 · Generators

> **Level:** Intermediate · **Prerequisites:** [01 · Iterators & iterables](01_iterators_and_iterables.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Writing `__iter__`/`__next__` by hand is verbose. **Generators** give you iterators almost for free, using one keyword: `yield`. They produce values **lazily** — one at a time, on demand — so you can process gigabyte files or *infinite* sequences using almost no memory. Generators are everywhere in professional Python (streaming data, pipelines) and they're the conceptual ancestor of `async`/`await` (Section 08).

## Concept: a generator function

- **What:** a function that uses `yield` instead of `return`. Calling it returns a **generator** (an iterator), without running the body yet.
- **Why:** lazy, memory-efficient sequences with tiny code.

```python
def countdown(n):
    while n > 0:
        yield n          # produce a value and PAUSE here
        n -= 1

print(list(countdown(3)))    # [3, 2, 1]
```

```text
[3, 2, 1]
```

That's the whole `Countdown` *class* from last module — in three lines. The magic is `yield`.

## Concept: how `yield` works — pause and resume

A normal function runs to completion and returns once. A generator **pauses** at each `yield`, hands back a value, and **resumes from that exact spot** the next time you ask for a value:

```python
def first_n_squares(n):
    for i in range(n):
        yield i * i      # pause, give i*i, later resume the loop

g = first_n_squares(4)   # nothing runs yet — just creates the generator
print(next(g))           # 0  -> runs until first yield, pauses
print(next(g))           # 1  -> resumes, runs to next yield
print(list(g))           # [4, 9]  -> drains the rest
```

Output (verified):

```text
0
1
[4, 9]
```

Each `next()` runs the function *until the next `yield`*, then freezes it — local variables, loop position, everything — until the next `next()`. This pause/resume is what makes generators special.

```mermaid
flowchart LR
    C["call gen()"] --> P0["paused at start"]
    P0 -->|"next()"| Y1["run to yield → value"]
    Y1 -->|"next()"| Y2["resume → next yield → value"]
    Y2 -->|"next() past end"| S["StopIteration"]
```

Like all iterators, a generator is **single-use** — once drained, it's done.

## Concept: the memory win — lazy evaluation

This is the headline benefit. A list holds *every* value at once; a generator computes each value only when asked, so it never holds them all.

```python
# A list comprehension builds ALL million numbers in memory:
big_list = [x * x for x in range(1_000_000)]      # ~ tens of MB

# A generator expression holds NONE of them — it streams:
big_gen = (x * x for x in range(1_000_000))       # a few hundred bytes

# Both give the same sum, but the generator never materialises the list:
print(sum(x * x for x in range(1000)))            # 332833500
```

Output (verified):

```text
332833500
```

`(... for ...)` with parentheses is a **generator expression** — the lazy sibling of a list comprehension (Section 02). Use it whenever you only *pass through* the values once (feeding `sum`, `max`, `any`, a `for` loop). Use a list when you need to index, reuse, or keep them.

> 🧠 **Rule of thumb:** if you'd build a list just to loop over it once and throw it away, use a generator instead — same result, a fraction of the memory.

## Concept: infinite generators

Because values are produced on demand, a generator can represent an *endless* sequence — impossible with a list. You take only what you need:

```python
def naturals():
    n = 1
    while True:          # never ends...
        yield n
        n += 1

import itertools
# ...but we only pull the first 5:
print(list(itertools.islice(naturals(), 5)))   # [1, 2, 3, 4, 5]
```

Output (verified):

```text
[1, 2, 3, 4, 5]
```

`itertools.islice(gen, n)` safely takes the first `n` from any iterator — essential for infinite generators (never call `list()` on one directly, or it loops forever!). This pattern models streams: log lines arriving, sensor readings, an endless ID sequence.

## Concept: pipelines (generators feeding generators)

Generators compose into memory-efficient **pipelines** — each stage pulls from the previous one, processing a single item at a time through the whole chain:

```python
def read_numbers(lines):
    for line in lines:
        yield int(line.strip())

def only_even(numbers):
    for n in numbers:
        if n % 2 == 0:
            yield n

def doubled(numbers):
    for n in numbers:
        yield n * 2

raw = ["1", "2", "3", "4", "5", "6"]
pipeline = doubled(only_even(read_numbers(raw)))   # nothing computed yet
print(list(pipeline))                              # now it streams through
```

Output (verified):

```text
[4, 8, 12]
```

Data flows `read → filter evens → double`, one number at a time, with no intermediate lists. The same shape scales to a 10 GB file you could never load into memory — you process it line by line.

## Worked example: reading a large file lazily

```python
# count_errors.py — scan a (potentially huge) log file without loading it all.

from pathlib import Path

# create a sample log
log = Path("/tmp/app.log")
log.write_text("INFO ok\nERROR disk full\nINFO ok\nERROR timeout\nWARN slow\n")

def error_lines(path):
    """Yield only the ERROR lines, one at a time."""
    with open(path) as f:
        for line in f:                 # iterating a file yields lines lazily
            if line.startswith("ERROR"):
                yield line.strip()

# Process the stream — only one line is ever in memory at a time
count = 0
for line in error_lines(log):
    count += 1
    print(f"{count}. {line}")

print(f"Total errors: {count}")
```

Output (verified):

```text
1. ERROR disk full
2. ERROR timeout
Total errors: 2
```

A file object is *itself* a lazy iterator of lines, so `for line in f` never loads the whole file. The generator filters it down to errors, streaming — this exact pattern handles log files far too big for memory.

## Common mistakes

**Mistake: calling `list()` on an infinite generator**
```python
list(naturals())     # runs forever (until you run out of memory / Ctrl-C)
```
**Why:** there's no end to consume. Use `itertools.islice(naturals(), n)` or `break` out of a `for` loop.

**Mistake: reusing a drained generator**
```python
g = (x for x in range(3))
print(sum(g))     # 3
print(sum(g))     # 0 — already exhausted
```
**Why:** generators are single-use (like all iterators). Recreate it if you need it again.

**Mistake: expecting the body to run when you call the function**
```python
def gen():
    print("starting")
    yield 1

g = gen()         # prints NOTHING — body hasn't run
next(g)           # NOW "starting" prints
```
**Why:** a generator function's body doesn't run until you pull the first value. If you need eager side effects, generators are the wrong tool.

## Practice

**Exercise:** Write a generator `chunks(iterable, size)` that yields lists of up to `size` items (the same paginator idea, but as a generator). Then write a generator pipeline that takes `range(1, 21)`, keeps multiples of 3, and yields their squares — print the first 4 results using `itertools.islice`.

<details><summary>Solution</summary>

```python
import itertools

def chunks(iterable, size):
    """Yield successive lists of up to `size` items."""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:                       # yield the final partial chunk
        yield batch

print(list(chunks(range(7), 3)))    # [[0, 1, 2], [3, 4, 5], [6]]

def multiples_of_3(nums):
    for n in nums:
        if n % 3 == 0:
            yield n

def squares(nums):
    for n in nums:
        yield n * n

pipeline = squares(multiples_of_3(range(1, 21)))
print(list(itertools.islice(pipeline, 4)))   # first 4 only
```

Output:

```text
[[0, 1, 2], [3, 4, 5], [6]]
[9, 36, 81, 144]
```

`chunks` accumulates a batch and yields it when full (plus any leftover at the end); the pipeline filters multiples of 3 (3, 6, 9, 12, ...) and squares them, streaming, with `islice` taking just the first four.
</details>

## Recap & next

- ✅ A generator function uses `yield`; calling it returns a lazy iterator.
- ✅ `yield` **pauses and resumes** the function, keeping its state.
- ✅ Generators (and `(... for ...)` expressions) are **memory-efficient** — they don't build the whole sequence.
- ✅ They can be **infinite**; take slices with `itertools.islice`.
- ✅ Compose them into **pipelines** that stream data one item at a time.
- Self-check: when would you prefer a generator expression `(...)` over a list comprehension `[...]`?

→ Next: **[03 · Decorators](03_decorators.md)**
