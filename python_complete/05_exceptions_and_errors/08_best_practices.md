# 08 · Best Practices

> **Level:** Intermediate · **Prerequisites:** Modules 01–07 of this section
> **Time:** ~1 hour · **Verified:** 2026-06-04 (Python 3.12.13)

## Why this matters

Knowing the *mechanics* of exceptions isn't the same as using them *well*. This module is the judgement layer: when to check vs. just try, how to log errors so you can debug production, which patterns are robust, and which anti-patterns silently swallow bugs and cost teams days of debugging. This is the difference between code that merely "doesn't crash" and code that fails *safely and visibly*.

## Concept: EAFP vs LBYL

Two philosophies for dealing with things that might go wrong:

- **LBYL** — *Look Before You Leap*: check first, then act.
- **EAFP** — *Easier to Ask Forgiveness than Permission*: just try it, handle the failure.

```python
d = {"a": 1}

# LBYL — check, then access
if "a" in d:
    print("LBYL:", d["a"])

# EAFP — try, then handle
try:
    print("EAFP:", d["a"])
except KeyError:
    print("missing")
```

Output (verified):

```text
LBYL: 1
EAFP: 1
```

**Python leans EAFP** — it's often cleaner and avoids a subtle bug class: with LBYL, the world can change *between* the check and the action (a file exists when you check, but is deleted before you open it — a "race condition"). EAFP has no such gap.

> 🧭 **Which to use?**
> - **EAFP** when the failure is *exceptional* (rare) or checking is racy/expensive: file I/O, dict/attribute access, type coercion. `try: int(x) except ValueError:` beats elaborate "is this a number?" checks.
> - **LBYL** when the check is cheap and the "failure" is *expected/common* as normal flow: `if items:` before processing, simple bounds you control.
> Don't dogmatically pick one — but when unsure in Python, reach for EAFP.

## Concept: catch specific, narrow, and only what you can handle

The golden rules, distilled from the whole section:

```python
# ❌ BAD: catches everything, hides bugs, even silences Ctrl-C
try:
    result = process(data)
except:
    pass

# ❌ BAD: too broad, swallows unexpected errors silently
try:
    result = process(data)
except Exception:
    result = None

# ✅ GOOD: catch the specific thing you expect and can handle
try:
    result = process(data)
except ValueError as e:
    log.warning("bad data, using default: %s", e)
    result = DEFAULT
```

1. **Catch the narrowest type** that you actually know how to handle.
2. **Keep the `try` block small** — ideally one risky call (use `else` for the rest).
3. **Don't catch what you can't handle** — let it propagate to someone who can (or to the top-level handler).
4. **Never `except: pass`** — see anti-patterns below.

## Concept: logging exceptions (don't just print)

In real programs you record errors to a **log**, not the screen. The `logging` module's `log.exception(...)` logs your message *plus the full traceback* automatically — call it inside an `except`:

```python
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
log = logging.getLogger("demo")

def risky(x):
    try:
        return 10 / x
    except ZeroDivisionError:
        log.exception("division failed for x=%s", x)   # logs message + traceback
        return None

risky(0)
```

Output (verified — note the captured traceback):

```text
ERROR:division failed for x=0
Traceback (most recent call last):
  File "<stdin>", line 8, in risky
ZeroDivisionError: division by zero
```

- `log.exception(msg)` must be called *inside* an `except` block — it automatically attaches the current traceback. It logs at `ERROR` level.
- Use `log.warning(...)` (no traceback) for handled, non-fatal issues; `log.exception(...)` for unexpected errors you're recording.
- Prefer logging's lazy `%s` formatting (`log.exception("x=%s", x)`) over f-strings here — the string is only built if the message is actually emitted.

> 🧠 **Why not `print`?** Logs have levels (DEBUG/INFO/WARNING/ERROR), timestamps, and can go to files or monitoring systems. `print` to stdout vanishes in production. (FastAPI apps use logging throughout — Section 09.)

## Concept: `finally` and context managers for cleanup

If you acquire a resource (file, lock, connection), it **must** be released even if an error occurs. `finally` guarantees this, but a **context manager** (`with`) is cleaner — it's the idiomatic tool, covered fully in [Section 06](../06_pythonic_intermediate/04_context_managers.md):

```python
class Resource:
    def __enter__(self):
        print("acquire")
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("release")          # runs even if the block raises
        return False              # False = don't suppress the exception

try:
    with Resource() as r:
        print("use")
        raise ValueError("boom")
except ValueError:
    print("handled (resource still released)")
```

Output (verified):

```text
acquire
use
release
handled (resource still released)
```

The resource was released *before* the exception propagated — because `__exit__` always runs. This is why you write `with open(path) as f:` instead of manual open/close with `try/finally`: the `with` block *is* the `finally` cleanup, done right.

## Concept: don't use exceptions for ordinary control flow

Exceptions are for *exceptional* situations, not routine branching:

```python
# ❌ abusing exceptions as an if-statement
def is_even(n):
    try:
        return n % 2 == 0
    except Exception:
        return False

# ✅ just write the logic
def is_even(n):
    return n % 2 == 0
```

Raising and catching has overhead and obscures intent. Use `if`/`else` for expected branches; reserve exceptions for genuine errors. (The exception — pun intended — is EAFP for things like dict access, where "try and handle" *is* the idiomatic, readable choice.)

## Anti-patterns to avoid

| ❌ Anti-pattern | Why it's bad | ✅ Do instead |
|----------------|--------------|--------------|
| `except: pass` | silences *all* errors, including bugs and Ctrl-C; failures vanish | catch a specific type; at minimum `log.exception(...)` |
| `except Exception:` everywhere | hides unexpected errors as if handled | catch what you expect; reserve broad catches for the top level |
| Huge `try` block | mislabels which line failed | keep `try` tight; use `else` |
| Swallowing then returning `None` silently | callers get a mystery `None` and crash later | log it, and/or re-raise, or return a clear sentinel |
| `raise Exception("...")` (the base type) | callers can't catch it specifically | raise a specific or custom type |
| Losing the cause when wrapping | traceback can't explain the real failure | `raise New(...) from original` ([Module 06](06_chaining_and_context.md)) |
| Catching `BaseException` / bare `except` | traps `KeyboardInterrupt`, `SystemExit` | catch `Exception` or narrower |

## Worked example: robust vs fragile

The same task — load a number from a config file — done badly and well:

```python
import logging
log = logging.getLogger("config")

# ❌ FRAGILE: hides every failure, returns a mystery None
def load_timeout_bad(path):
    try:
        with open(path) as f:
            return int(f.read())
    except:                          # bare except!
        return None                  # WHY did it fail? Nobody knows.

# ✅ ROBUST: specific handling, logging, sensible default, clear intent
DEFAULT_TIMEOUT = 30

def load_timeout(path):
    try:
        with open(path) as f:        # `with` guarantees the file closes
            text = f.read().strip()
    except FileNotFoundError:
        log.info("no config at %s, using default %s", path, DEFAULT_TIMEOUT)
        return DEFAULT_TIMEOUT
    try:
        return int(text)
    except ValueError:
        log.warning("config at %s is not a number (%r); using default", path, text)
        return DEFAULT_TIMEOUT

from pathlib import Path
Path("/tmp/timeout.txt").write_text("oops")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
print("Result:", load_timeout("/tmp/timeout.txt"))
print("Missing:", load_timeout("/tmp/none.txt"))
```

Output (verified):

```text
WARNING:config at /tmp/timeout.txt is not a number ('oops'); using default
INFO:no config at /tmp/none.txt, using default 30
Result: 30
Missing: 30
```

> ℹ️ The `WARNING`/`INFO` lines come from `logging` (which writes to *stderr*) and the `Result:`/`Missing:` lines from `print` (*stdout*); when captured together they can appear grouped like this rather than perfectly interleaved.

The robust version: distinguishes "missing file" from "bad content", logs *what* went wrong (with the offending value), falls back to a sensible default, and never hides an unexpected error. The fragile version returns `None` for *any* reason, so a typo in your own code looks identical to a missing file.

## Common mistakes

**Mistake: logging *and* re-raising, producing duplicate logs**
```python
except ValueError:
    log.exception("failed")
    raise                  # the top-level handler logs it AGAIN
```
**Why:** if a higher level also logs, you get the same traceback twice. Decide *who owns* logging an error — usually the outermost handler — and don't log-and-reraise at every level.

**Mistake: returning a default that hides a real problem**
Silent fallbacks are great for *expected* missing config, but dangerous if they mask bugs. When in doubt, log at `WARNING`+ so the fallback is at least *visible*.

## Practice

**Exercise:** Refactor this fragile function into a robust one. It should: catch only what it expects, log a warning with the bad value on failure, return a default of `0.0`, and use a `with` block. Then show it handling a good file, a non-numeric file, and a missing file.

```python
def read_balance(path):
    try:
        return float(open(path).read())
    except:
        return 0.0
```

<details><summary>Solution</summary>

```python
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
log = logging.getLogger("balance")

DEFAULT_BALANCE = 0.0

def read_balance(path):
    try:
        with open(path) as f:                 # `with` closes the file reliably
            text = f.read().strip()
    except FileNotFoundError:
        log.info("no balance file at %s; using %.1f", path, DEFAULT_BALANCE)
        return DEFAULT_BALANCE
    try:
        return float(text)
    except ValueError:
        log.warning("balance %r is not a number; using %.1f", text, DEFAULT_BALANCE)
        return DEFAULT_BALANCE

Path("/tmp/bal_good.txt").write_text("123.45")
Path("/tmp/bal_bad.txt").write_text("lots")
print(read_balance("/tmp/bal_good.txt"))
print(read_balance("/tmp/bal_bad.txt"))
print(read_balance("/tmp/bal_missing.txt"))
```

Output (log lines on stderr, values on stdout — captured together they group like this):

```text
WARNING:balance 'lots' is not a number; using 0.0
INFO:no balance file at /tmp/bal_missing.txt; using 0.0
123.45
0.0
0.0
```

The refactor catches `FileNotFoundError` and `ValueError` *separately* (so each gets a fitting message), logs the bad value, uses `with` for safe cleanup, and never hides an unexpected error behind a bare `except`.
</details>

## Recap & next

- ✅ **EAFP** (try/handle) is often more Pythonic than **LBYL** (check first) — and avoids races.
- ✅ Catch **specific** types, keep `try` blocks **small**, don't catch what you can't handle.
- ✅ **Log** exceptions with `log.exception(...)` (traceback included) instead of printing.
- ✅ Use `with`/context managers (or `finally`) so resources are always released.
- ✅ Avoid the anti-patterns — especially `except: pass`.
- Self-check: name two reasons `except: pass` is dangerous.

🎉 **You've completed the special topic.** Errors are no longer scary — they're information. Every section from here (concurrency, async, FastAPI) leans on these habits.

→ Next: **[Section 06 · Pythonic intermediate](../06_pythonic_intermediate/README.md)**
