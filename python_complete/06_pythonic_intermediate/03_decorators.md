# 03 · Decorators

> **Level:** Intermediate → Advanced · **Prerequisites:** [Functions & closures](../03_functions_and_modules/02_arguments_and_scope.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

A **decorator** wraps a function to add behaviour — logging, timing, caching, access checks, retries — *without changing the function's own code*. You've already seen the `@` syntax (`@property`, `@dataclass`, `@abstractmethod`). Now you'll understand how it works and write your own. Decorators are everywhere in real Python, and FastAPI uses them for *every* route (`@app.get(...)`), so this module is direct preparation for Section 09.

## Concept: functions are objects (the prerequisite)

Recall from [Section 03](../03_functions_and_modules/02_arguments_and_scope.md): functions can be passed around, returned, and nested. A decorator relies on all three.

```python
def greet():
    return "hi"

f = greet            # assign the function to another name (no parentheses!)
print(f())           # hi  -> call it through f
print(callable(f))   # True
```

A function is just a value you can hand around. A decorator is a function that *takes a function and returns a (usually wrapped) function*.

## Concept: a decorator by hand

Before the `@` sugar, here's the raw mechanism — wrap a function in another function:

```python
def shout(func):                     # takes a function...
    def wrapper(*args, **kwargs):    # ...defines a replacement...
        result = func(*args, **kwargs)
        return result.upper() + "!"
    return wrapper                   # ...and returns the replacement

def greet(name):
    return f"hello {name}"

greet = shout(greet)                 # manually wrap it
print(greet("ada"))                  # HELLO ADA!
```

```text
HELLO ADA!
```

`shout` returns `wrapper`, which calls the original `greet` and then modifies its result. Reassigning `greet = shout(greet)` replaces the name with the wrapped version. The `*args, **kwargs` ([Section 03](../03_functions_and_modules/02_arguments_and_scope.md)) let the wrapper accept *any* arguments and pass them straight through.

## Concept: the `@` syntax

`@shout` above a definition is **exactly** `greet = shout(greet)` — just cleaner:

```python
import functools

def shout(func):
    @functools.wraps(func)           # see below — preserves func's identity
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).upper() + "!"
    return wrapper

@shout                               # <-- same as greet = shout(greet)
def greet(name):
    """Greets a person."""
    return f"hello {name}"

print(greet("ada"))                  # HELLO ADA!
print(greet.__name__, "-", greet.__doc__)
```

Output (verified):

```text
HELLO ADA!
greet - Greets a person.
```

```mermaid
flowchart LR
    A["@shout above greet"] --> B["greet = shout(greet)"]
    B --> C["greet now refers to wrapper"]
    C --> D["call greet() → wrapper runs original + extra"]
```

### Always use `functools.wraps`

Without `@functools.wraps(func)`, the wrapper would *replace* the original's name and docstring — `greet.__name__` would say `"wrapper"` and `greet.__doc__` would be lost, confusing debuggers and docs tools. `@functools.wraps(func)` copies that metadata across. **Always add it** to your wrappers (notice above: the name and docstring are correctly preserved).

## Concept: a practical decorator — timing

```python
import functools, time

def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  {func.__name__} took {elapsed*1000:.1f} ms")
        return result
    return wrapper

@timed
def slow_sum(n):
    return sum(range(n))

print(slow_sum(1_000_000))
```

Output (timing varies, but the shape is fixed):

```text
  slow_sum took 7.4 ms
slow_sum 499999500000
```

The function's logic is untouched — timing is "bolted on" by the decorator. Swap `print` for logging and you have production-grade instrumentation you can add to any function with one line.

## Concept: decorators that take arguments

To configure a decorator (e.g. "repeat 3 times"), you add *another* layer: a function that takes the argument and *returns a decorator*.

```python
import functools

def repeat(times):                       # takes the config...
    def decorator(func):                 # ...returns a normal decorator...
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return [func(*args, **kwargs) for _ in range(times)]
        return wrapper
    return decorator

@repeat(times=3)                         # repeat(3) returns the decorator
def roll():
    return 4

print(roll())                            # [4, 4, 4]
```

Output (verified):

```text
[4, 4, 4]
```

Three layers: `repeat(3)` returns `decorator`, which wraps `roll` into `wrapper`. It looks like a lot, but the pattern is fixed — outer takes the argument, middle takes the function, inner does the work. (`@app.get("/path")` in FastAPI works exactly this way.)

## Concept: a built-in decorator you'll love — `lru_cache`

`functools.lru_cache` memoises a function: it caches results so repeated calls with the same arguments are instant. It turns the exponential, naive Fibonacci into a fast one:

```python
import functools

@functools.lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(50))              # instant, thanks to caching
print(fib.cache_info())     # stats about hits/misses
```

Output (verified):

```text
12586269025
CacheInfo(hits=48, misses=51, maxsize=None, currsize=51)
```

Without the cache, `fib(50)` would make billions of calls; with it, each `n` is computed once (51 misses) and reused (48 hits). One line, enormous speedup — a perfect illustration of "add behaviour without touching the function."

## Worked example: a retry decorator

```python
# retry.py — re-run a flaky function a few times before giving up.

import functools

def retry(attempts):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:          # catch, log, try again
                    last_error = e
                    print(f"  attempt {attempt} failed: {e}")
            raise last_error                    # all attempts used up — re-raise
        return wrapper
    return decorator

# A function that fails the first two times, then succeeds.
calls = {"n": 0}

@retry(attempts=3)
def flaky():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError(f"network down (call {calls['n']})")
    return "success!"

print(flaky())
```

Output (verified):

```text
  attempt 1 failed: network down (call 1)
  attempt 2 failed: network down (call 2)
success!
```

The retry logic — a real-world need for flaky network calls — lives entirely in the decorator. Any function can gain retries by adding `@retry(attempts=3)`, with no changes to its own body. This combines everything: closures, `*args/**kwargs`, and the exception handling from [Section 05](../05_exceptions_and_errors/README.md).

## Common mistakes

**Mistake: forgetting `functools.wraps`**
```python
def deco(func):
    def wrapper(*a, **k):
        return func(*a, **k)
    return wrapper           # no @wraps

@deco
def hello(): "says hi"
print(hello.__name__)        # 'wrapper'  -> identity lost!
```
**Why:** the wrapped function reports the wrapper's name/docstring, breaking introspection and docs. Always `@functools.wraps(func)`.

**Mistake: wrapper that doesn't accept `*args/**kwargs`**
```python
def deco(func):
    def wrapper():           # accepts no arguments!
        return func()
    return wrapper

@deco
def add(a, b): return a + b
add(1, 2)                    # TypeError: wrapper() takes 0 positional arguments
```
**Why:** the wrapper must forward whatever the original accepts. Use `def wrapper(*args, **kwargs):` and pass them through.

## Practice

**Exercise:** Write a decorator `logged` that prints `"calling <name> with <args>"` before the call and `"<name> returned <result>"` after, then returns the result. Use `functools.wraps`. Decorate an `add(a, b)` function and call `add(2, 3)`.

<details><summary>Solution</summary>

```python
import functools

def logged(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__} with {args}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@logged
def add(a, b):
    return a + b

print("final:", add(2, 3))
```

Output:

```text
calling add with (2, 3)
add returned 5
final: 5
```

The wrapper logs around the original call, forwards `*args`/`**kwargs`, returns the real result, and `@functools.wraps` keeps `add`'s identity intact.
</details>

## Recap & next

- ✅ A decorator takes a function and returns a wrapped function; `@deco` ≡ `f = deco(f)`.
- ✅ Wrappers use `*args, **kwargs` to forward any arguments.
- ✅ Always add `@functools.wraps(func)` to preserve identity.
- ✅ Decorators with arguments add one more layer (config → decorator → wrapper).
- ✅ Built-ins like `functools.lru_cache` give caching for free; you wrote `timed` and `retry`.
- Self-check: what does `@deco` literally translate to?

→ Next: **[04 · Context managers](04_context_managers.md)**
