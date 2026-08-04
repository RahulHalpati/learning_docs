# 03-4 · The functional API (`@entrypoint` / `@task`)

> **Level:** Intermediate · **Prerequisites:** [03-1 · Your first chatbot](01_first_chatbot.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

The graph API (`StateGraph`, nodes, edges) is explicit and visual — great when the control flow *is* the point. But sometimes your logic is naturally imperative ("do A, then B, then loop") and drawing a graph feels like overhead. The **functional API** lets you write that as ordinary Python functions and still get LangGraph's superpowers: checkpointing, memory, streaming, human-in-the-loop, and retries.

---

## Two decorators

- **`@task`** — wraps a unit of work. Calling it returns a *future*; call `.result()` to get the value. Tasks are the checkpoint/retry boundary (the functional-API equivalent of a node).
- **`@entrypoint`** — wraps the workflow. You `invoke`/`stream` it like a compiled graph. Add `checkpointer=` for persistence.

```python
from langgraph.func import entrypoint, task

@task
def double(x: int) -> int:
    return x * 2

@task
def add_ten(x: int) -> int:
    return x + 10

@entrypoint()
def pipeline(n: int) -> int:
    d = double(n).result()        # run task, await its result
    return add_ten(d).result()

print(pipeline.invoke(5))
```

**Output (real run):**
```
20
```

No `StateGraph`, no edges — just functions. `double` and `add_ten` are still checkpointed tasks, so they get retries and show up in traces.

---

## Short-term memory with `previous`

An entrypoint with a checkpointer can see its **own previous return value** via a `previous` keyword arg — that's persistent state without a state schema:

```python
from langgraph.func import entrypoint
from langgraph.checkpoint.memory import InMemorySaver

@entrypoint(checkpointer=InMemorySaver())
def accumulator(x: int, *, previous: int | None = None) -> int:
    return (previous or 0) + x

cfg = {"configurable": {"thread_id": "acc-1"}}
print(accumulator.invoke(3, cfg), accumulator.invoke(4, cfg), accumulator.invoke(5, cfg))
```

**Output (real run):**
```
3 7 12
```

Each call remembers the running total on thread `acc-1` — the same `thread_id` memory model as the graph API, expressed as a return value.

---

## When to use which

| | Graph API (`StateGraph`) | Functional API (`@entrypoint`) |
|---|---|---|
| Mental model | explicit nodes + edges | ordinary control flow |
| Best for | branching, cycles, HITL mid-flow, visualization | linear/imperative pipelines, quick agents |
| Visualization | `draw_mermaid()` | not a graph to draw |
| State | typed schema + reducers | function args + `previous` |
| Interop | — | tasks/entrypoints can call each other |

They share the same runtime — checkpointers, streaming, `interrupt`, and retries work in both. Pick the graph API when the *structure* is the interesting part; pick the functional API when the *procedure* is.

> **Tip:** You can mix them: call a compiled graph from inside a `@task`, or wrap a functional workflow as a step in a larger graph. It's one engine underneath.

---

## Recap & next

- ✅ `@task` = a checkpointed unit (returns a future; `.result()` to await); `@entrypoint` = the invokable workflow.
- ✅ `previous` gives an entrypoint short-term memory when a checkpointer is attached.
- ✅ Same runtime as the graph API — choose by whether structure or procedure dominates.
- ✅ Self-check: what does `double(n)` return *before* you call `.result()` on it?

→ Next: **[04 · Control flow](../04_control_flow/README.md)**

## Exercises

1. Rewrite the accumulator to keep a **list** of all inputs seen so far (using `previous`), returning the list each call.

<details>
<summary>Solution</summary>

```python
@entrypoint(checkpointer=InMemorySaver())
def history(x, *, previous=None):
    seen = (previous or []) + [x]
    return seen

cfg = {"configurable": {"thread_id": "h1"}}
print(history.invoke("a", cfg))   # ['a']
print(history.invoke("b", cfg))   # ['a', 'b']
```
</details>
