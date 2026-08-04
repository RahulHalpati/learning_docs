# 09-2 · Performance & hardening

> **Level:** Intermediate · **Prerequisites:** [09-1 · Pitfalls & best practices](01_pitfalls_best_practices.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

A correct graph can still be slow or fragile. Four levers make it fast (keep state small, parallelize, stream, go async) and three make it safe (validate input, handle errors, use built-in retries). None are exotic — they're the defaults you should reach for once something's real.

---

## Performance

### 1. Keep state small

State is serialized at **every** checkpoint. Storing megabytes of documents or embedding arrays there makes every step slow.

```python
class Heavy(TypedDict):
    documents: list[str]         # ❌ MBs re-serialized each step
class Light(TypedDict):
    document_ids: list[str]      # ✅ store references; fetch on demand
    index_name: str
```

### 2. Parallelize independent nodes

If two nodes don't need each other's output, fan out — they run in the **same super-step** ([02-1](../02_execution_model/01_super_step_model.md)):

```python
builder.add_edge("classify", "search_web")   # fan-out
builder.add_edge("classify", "search_db")
builder.add_edge("search_web", "synthesize") # fan-in (waits for both)
builder.add_edge("search_db", "synthesize")
```

Ensure any key both branches write has a **reducer**, or one clobbers the other.

### 3. Stream long operations

Don't make users wait for the whole graph — stream progress or tokens ([02-2](../02_execution_model/02_streaming.md)):

```python
for ev in graph.stream(inputs, stream_mode="updates"):
    print("done:", list(ev)[0])
```

### 4. Async for I/O

Blocking LLM/API calls stall the event loop under load. Use async nodes and `ainvoke`:

```python
async def node(state):
    return {"messages": [await llm.ainvoke(state["messages"])]}   # non-blocking
# await graph.ainvoke(inputs, config)
```

---

## Hardening

### 1. Validate input at the boundary

Use Pydantic to reject bad input *before* it enters the graph:

```python
from pydantic import BaseModel, field_validator

class Input(BaseModel):
    query: str
    @field_validator("query")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():          raise ValueError("query cannot be empty")
        if len(v) > 5000:          raise ValueError("query too long")
        return v.strip()
```

### 2. Handle errors — and prefer built-in retries

For *transient* failures, don't hand-roll retry loops — attach a `RetryPolicy` ([02-3](../02_execution_model/03_durability_retries_caching.md)). For failures you want to *absorb* into state, catch and record:

```python
def node(state):
    try:
        return {"result": external_call(state["query"]), "error": None}
    except Exception as e:
        return {"result": None, "error": str(e)}     # downstream can branch on error
```

Use `RetryPolicy` for "try again"; use try/except for "record and route around it".

### 3. Rate limiting

Protect API quotas. LangChain chat models accept a built-in rate limiter; or wrap a node:

```python
import time
from functools import wraps

def rate_limit(per_minute=20):
    interval, last = 60 / per_minute, [0.0]
    def deco(fn):
        @wraps(fn)
        def wrap(state):
            wait = interval - (time.time() - last[0])
            if wait > 0: time.sleep(wait)
            last[0] = time.time()
            return fn(state)
        return wrap
    return deco
```

---

## Production checklist

| Category | Check |
|----------|-------|
| State | `TypedDict`/Pydantic; reducers on accumulating fields; references not blobs |
| Safety | loop caps + `recursion_limit`; input validation; error handling / `RetryPolicy` |
| Persistence | `Postgres`/`SqliteSaver` (not in-memory); unique `thread_id` |
| HITL | `interrupt()` before destructive actions |
| Performance | parallelize independent nodes; async I/O; streaming |
| Observability | LangSmith tracing (next lesson); structured logs; scrub PII |

---

## Recap & next

- ✅ Fast: small state, parallel fan-out/fan-in, streaming, async I/O.
- ✅ Safe: validate at the boundary, `RetryPolicy` for transient errors, try/except to absorb-and-route, rate limits.
- ✅ Run the checklist before anything ships.
- ✅ Self-check: when do you use `RetryPolicy` vs a try/except in a node?

→ Next: **[09-3 · Observability (LangSmith)](03_observability_langsmith.md)**

## Exercises

1. Take the self-correcting RAG graph (08-2) and (a) add a `RetryPolicy` to `retrieve`, (b) make `generate` async.

<details>
<summary>Solution</summary>

`b.add_node("retrieve", retrieve, retry_policy=RetryPolicy(retry_on=ConnectionError))` and change `generate` to `async def` using `await gen_llm.ainvoke(...)`, invoking the graph with `await app.ainvoke(...)`.
</details>
