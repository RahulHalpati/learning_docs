# 02 · Threading

> **Level:** Advanced · **Prerequisites:** [01 · Concurrency & the GIL](01_concurrency_vs_parallelism_and_the_gil.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Threads let multiple parts of your program make progress concurrently. For **I/O-bound** work — downloading URLs, reading files, calling APIs — threads can give dramatic speedups because the GIL is released during the waiting. This module shows the low-level `threading` API and the high-level `ThreadPoolExecutor` you'll actually use most.

## Concept: creating and running threads

- **What:** a `Thread` runs a function concurrently with the rest of your program.
- **Why:** overlap independent waiting (I/O) so total time drops.

```python
import threading

def worker(name, n):
    total = sum(range(n))
    print(f"  {name} computed {total}")

# create three threads, each running worker with different args
threads = [threading.Thread(target=worker, args=(f"T{i}", 100_000)) for i in range(3)]

for t in threads:
    t.start()        # start each thread running
for t in threads:
    t.join()         # wait for each to finish before continuing

print("all done")
```

Output (verified — print *order* between threads may vary run to run):

```text
  T0 computed 4999950000
  T1 computed 4999950000
  T2 computed 4999950000
all done
```

- `Thread(target=func, args=(...))` defines a thread; `.start()` launches it; `.join()` blocks until it finishes.
- **`start()` vs `join()`:** `start` *begins* concurrent execution; `join` *waits* for completion. Start all threads first, *then* join them all — that's what lets them overlap. (Calling `join` right after each `start` would run them one at a time.)

> ⚠️ The order of the `T0/T1/T2` lines isn't guaranteed — the OS schedules threads as it sees fit. Never rely on thread output order; rely on results after `join()`.

## Concept: the I/O-bound payoff

Here's where threads shine. Simulate 8 slow I/O operations (each waits 0.1s):

```python
import time
from concurrent.futures import ThreadPoolExecutor

def slow_io(x):
    time.sleep(0.1)        # simulate waiting on network/disk
    return x

# Sequential: each wait happens one after another
start = time.perf_counter()
for x in range(8):
    slow_io(x)
print(f"sequential: {time.perf_counter() - start:.2f}s")

# Threaded: the waits overlap
start = time.perf_counter()
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(slow_io, range(8)))
print(f"threaded:   {time.perf_counter() - start:.2f}s")
```

Output (verified):

```text
sequential: 0.80s
threaded:   0.10s
```

**8× faster.** Sequentially, the eight 0.1s waits add up to 0.8s. With threads, all eight wait *at the same time* (the GIL is released during `sleep`/I/O), so the total is ~0.1s. This is the real-world win: fetching 8 URLs concurrently instead of one at a time.

## Concept: `ThreadPoolExecutor` (the tool you'll actually use)

Manually creating and joining `Thread` objects is fine for a few, but for many tasks use a **pool**. `ThreadPoolExecutor` manages a fixed set of reusable threads and a clean API:

```python
from concurrent.futures import ThreadPoolExecutor

def square(x):
    return x * x

with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(square, range(6)))   # like map(), but concurrent

print(results)        # [0, 1, 4, 9, 16, 25]
```

Output (verified):

```text
[0, 1, 4, 9, 16, 25]
```

- `ex.map(func, iterable)` runs `func` on each item across the pool and returns results **in input order** (even though they finish out of order).
- The `with` block ([context managers](../06_pythonic_intermediate/04_context_managers.md)) cleanly shuts the pool down when done.
- `max_workers` caps how many threads run at once — sensible for I/O (you might use dozens), pointless to set high for CPU work (the GIL).

## Concept: `submit` and `Future` (for individual tasks)

`map` is great for "same function over many inputs." For finer control — different functions, handling results as they complete, capturing exceptions — use `submit`, which returns a **`Future`** (a handle to a result that isn't ready yet):

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(url):
    if "bad" in url:
        raise ValueError(f"cannot fetch {url}")
    return f"data from {url}"

urls = ["site/a", "site/bad", "site/c"]

with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(fetch, u): u for u in urls}   # Future -> url
    for fut in as_completed(futures):                  # yields as each finishes
        url = futures[fut]
        try:
            print(f"  {url}: {fut.result()}")          # .result() re-raises errors
        except ValueError as e:
            print(f"  {url}: FAILED ({e})")
```

Output (verified — order depends on completion timing; here `site/bad` finished first as it does no work):

```text
  site/bad: FAILED (cannot fetch site/bad)
  site/a: data from site/a
  site/c: data from site/c
```

- `ex.submit(func, *args)` schedules one call and returns a `Future` immediately.
- `future.result()` blocks until that task is done and returns its value — **or re-raises any exception** the task raised. This is how you handle errors from threads (covered in [Section 05](../05_exceptions_and_errors/README.md)): wrap `.result()` in `try/except`.
- `as_completed(futures)` yields futures **as they finish**, so you can process fast results without waiting for slow ones.

> 🧠 **Exceptions in threads** don't crash your main program — they're stored in the `Future` and re-raised when you call `.result()`. If you never check the result, the error is silently lost — a common bug. Always retrieve results.

## Worked example: concurrent "downloads"

```python
# downloader.py — fetch several resources concurrently, handling failures.

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def download(name):
    time.sleep(0.1)                      # simulate network latency
    if name == "broken":
        raise ConnectionError(f"{name} unreachable")
    return f"{name}.html ({len(name)} bytes)"

pages = ["home", "about", "broken", "contact"]

start = time.perf_counter()
results = {}
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(download, p): p for p in pages}
    for fut in as_completed(futures):
        page = futures[fut]
        try:
            results[page] = fut.result()
        except ConnectionError as e:
            results[page] = f"ERROR: {e}"
elapsed = time.perf_counter() - start

for page in pages:                       # print in stable order
    print(f"  {page}: {results[page]}")
print(f"fetched {len(pages)} pages in {elapsed:.2f}s")
```

Output (verified):

```text
  home: home.html (4 bytes)
  about: about.html (5 bytes)
  broken: ERROR: broken unreachable
  contact: contact.html (7 bytes)
  fetched 4 pages in 0.10s
```
*(The pages print in stable order because we loop `pages` at the end; the timing line varies slightly by run.)*

Four "downloads" (one failing) completed in ~0.1s instead of ~0.4s sequential, with the failure cleanly captured per-page via `fut.result()` in a `try/except`. This is the bread-and-butter pattern for concurrent I/O.

## Common mistakes

**Mistake: joining immediately after starting (no concurrency)**
```python
for t in threads:
    t.start()
    t.join()        # waits for THIS one before starting the next — serial!
```
**Why:** you've serialised them. Start *all* threads, then join *all* threads in separate loops.

**Mistake: ignoring a Future's result (swallowing errors)**
```python
futures = [ex.submit(task, x) for x in items]
# never call .result() -> exceptions vanish silently
```
**Why:** exceptions raised in tasks live in the `Future`. If you never call `.result()`, you won't know a task failed. Always collect results.

**Mistake: using threads for CPU-bound work** — see [Module 01](01_concurrency_vs_parallelism_and_the_gil.md). The GIL means no speedup; use processes ([Module 04](04_multiprocessing_and_pools.md)).

## Practice

**Exercise:** You have a list of "user IDs" `[1, 2, 3, 4, 5]`. Write `fetch_user(uid)` that sleeps 0.1s and returns `f"user-{uid}"`, but raises `ValueError` for `uid == 3`. Use a `ThreadPoolExecutor` to fetch all concurrently, collecting successes into a dict and printing which failed. Confirm it's much faster than sequential.

<details><summary>Solution</summary>

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_user(uid):
    time.sleep(0.1)
    if uid == 3:
        raise ValueError(f"user {uid} not found")
    return f"user-{uid}"

ids = [1, 2, 3, 4, 5]
users = {}

start = time.perf_counter()
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(fetch_user, uid): uid for uid in ids}
    for fut in as_completed(futures):
        uid = futures[fut]
        try:
            users[uid] = fut.result()
        except ValueError as e:
            print(f"  failed: {e}")
elapsed = time.perf_counter() - start

print("fetched:", {k: users[k] for k in sorted(users)})
print(f"took {elapsed:.2f}s (vs ~0.50s sequential)")
```

Output:

```text
  failed: user 3 not found
fetched: {1: 'user-1', 2: 'user-2', 4: 'user-4', 5: 'user-5'}
took 0.10s (vs ~0.50s sequential)
```

Five concurrent fetches finish in ~0.1s instead of ~0.5s; the failing one is caught via `fut.result()` in a `try/except`, and the rest succeed.
</details>

## Recap & next

- ✅ Created threads with `Thread(target=...)`, `.start()`, `.join()`.
- ✅ Saw the **I/O-bound speedup** (8 waits overlap → ~8× faster).
- ✅ Used `ThreadPoolExecutor` + `ex.map` for "same function, many inputs."
- ✅ Used `submit` + `Future` + `as_completed` for control and error handling.
- ✅ Learned exceptions surface via `future.result()` — always collect results.
- Self-check: why must you `start()` all threads before `join()`-ing them?

→ Next: **[03 · Synchronization](03_synchronization.md)**
