# 02-3 · Durability, retries & caching

> **Level:** Intermediate · **Prerequisites:** [02-1 · Super-step model](01_super_step_model.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

Real nodes call flaky networks, cost money, and sometimes loop forever. LangGraph has *built-in* dials for all three so you don't reinvent them with hand-rolled `try/except` and counters: **`RetryPolicy`** (retry transient failures), **`CachePolicy`** (skip repeated work), **`recursion_limit`** (stop runaway loops), and **durability modes** (how often state is persisted).

---

## Retries: `RetryPolicy`

Attach a retry policy per node. LangGraph re-runs the node with exponential backoff on matching exceptions.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

class S(TypedDict):
    x: int

attempts = {"n": 0}
def flaky(state: S) -> dict:
    attempts["n"] += 1
    if attempts["n"] < 3:
        raise ConnectionError("transient network blip")
    return {"x": 99}

g = StateGraph(S)
g.add_node("flaky", flaky,
           retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.01, jitter=False))
g.add_edge(START, "flaky"); g.add_edge("flaky", END)

print("result:", g.compile().invoke({"x": 0}), "| attempts:", attempts["n"])
```

**Output (real run):**
```
result: {'x': 99} | attempts: 3
```

> ⚠️ **The default `retry_on` is selective.** It retries *transient* errors (connection errors, specific HTTP 5xx, etc.) — **not** a bare `ValueError`. To retry your own exception, pass it explicitly: `RetryPolicy(retry_on=ValueError)` or `retry_on=(ValueError, TimeoutError)`, or a predicate `retry_on=lambda e: ...`. That default is a feature: you don't want to retry a genuine bug.

`RetryPolicy` fields: `max_attempts`, `initial_interval`, `backoff_factor`, `max_interval`, `jitter`, `retry_on`.

---

## Caching: `CachePolicy`

Give a node a `CachePolicy` and a graph-level `cache`, and identical inputs skip re-execution:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import CachePolicy
from langgraph.cache.memory import InMemoryCache

class S(TypedDict):
    x: int

calls = {"n": 0}
def pricey(state: S) -> dict:
    calls["n"] += 1                 # count real executions
    return {"x": state["x"] + 100}

g = StateGraph(S)
g.add_node("pricey", pricey, cache_policy=CachePolicy(ttl=60))
g.add_edge(START, "pricey"); g.add_edge("pricey", END)
app = g.compile(cache=InMemoryCache())     # provide a cache backend

app.invoke({"x": 5})     # runs the node
app.invoke({"x": 5})     # same input → served from cache
print("real executions:", calls["n"])
```

**Output (real run):**
```
real executions: 1
```

The second call returned `{'x': 105}` without running `pricey` again. Swap `InMemoryCache` for a persistent backend in production; set `ttl` (seconds) to bound staleness.

---

## Bounding loops: `recursion_limit`

Cycles are how agents retry — but a bug can loop forever. LangGraph counts **super-steps** and raises `GraphRecursionError` past `recursion_limit` (default **25**):

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError

class S(TypedDict):
    x: int

def loop(state: S) -> dict: return {"x": state["x"] + 1}

g = StateGraph(S); g.add_node("loop", loop)
g.add_edge(START, "loop"); g.add_edge("loop", "loop")     # deliberately infinite

try:
    g.compile().invoke({"x": 0}, {"recursion_limit": 5})
except GraphRecursionError as e:
    print("stopped:", str(e)[:60])
```

**Output (real run):**
```
stopped: Recursion limit of 5 reached without hitting a stop conditio
```

> **Tip:** `recursion_limit` is a *safety net*, not your primary loop control. Still route to `END` deliberately (a quality gate, an attempt counter in state). The limit exists to turn an infinite loop into a clean error instead of a hang.

---

## Durability modes

When a checkpointer is attached (Section 05), the `durability` option controls **how often** state is persisted, trading safety for speed:

| Mode | Persists | Trade-off |
|------|----------|-----------|
| `"exit"` | once, at the end | fastest; lose progress on a mid-run crash |
| `"async"` (default) | after each step, in the background | good balance |
| `"sync"` | after each step, blocking | safest; slowest |

```python
# app.invoke(inputs, config, durability="sync")   # e.g. for high-stakes runs
```

Use `"sync"` when a crash mid-run must never lose a step (financial actions, long human-in-the-loop sessions); `"exit"` for fast, cheap, restartable batch work.

---

## Recap & next

- ✅ `RetryPolicy` retries transient errors with backoff — pass `retry_on` for your own exceptions.
- ✅ `CachePolicy` + a `cache` backend skips repeated identical work (set a `ttl`).
- ✅ `recursion_limit` (default 25) turns runaway loops into a clean `GraphRecursionError` — but route to `END` deliberately anyway.
- ✅ `durability` (`exit`/`async`/`sync`) trades crash-safety against speed.
- ✅ Self-check: why won't the default `RetryPolicy` retry a `ValueError` you raise in a node?

→ Next: **[02-4 · Runtime configuration](04_runtime_config.md)**

## Exercises

1. Give `flaky` a `RetryPolicy` with `retry_on=ValueError` and have it raise `ValueError` twice before succeeding. Confirm it retries.

<details>
<summary>Solution</summary>

```python
g.add_node("flaky", flaky, retry_policy=RetryPolicy(max_attempts=3, retry_on=ValueError,
                                                    initial_interval=0.01, jitter=False))
```
Now the previously-ignored `ValueError` is treated as retryable.
</details>
