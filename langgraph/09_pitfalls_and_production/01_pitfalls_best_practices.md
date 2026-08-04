# 09-1 · Pitfalls & best practices

> **Level:** Intermediate · **Prerequisites:** Sections 01–08
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

Almost every LangGraph bug a beginner hits is one of six mistakes. Learn to spot them and you'll debug in minutes instead of hours.

---

## Mistake 1 — untyped state (raw `dict`)

```python
graph = StateGraph(dict)                     # ❌ no type safety
def node(state): return {"resutls": ...}     # typo silently creates a new key
```

**Fix:** always use a `TypedDict` (or Pydantic). A typo like `resutls` then gets flagged by your editor/linter, and autocomplete works.

```python
class MyState(TypedDict):
    query: str
    results: list[str]
graph = StateGraph(MyState)                  # ✅
```

---

## Mistake 2 — missing reducer on accumulating fields

```python
class BadState(TypedDict):
    results: list[str]                       # ❌ each node's return REPLACES the list
```

**Fix:** add `operator.add` (or `add_messages`) so updates *accumulate* ([01-1](../01_foundations/01_core_concepts.md)):

```python
results: Annotated[list[str], operator.add]  # ✅
```

This is the single most common "where did my data go?" bug.

---

## Mistake 3 — unbounded loops

```python
def gate(state):
    return "retry" if state["quality"] < 0.8 else "done"   # ❌ may loop forever
```

**Fix:** cap it with a counter **and** rely on `recursion_limit` as a backstop ([02-3](../02_execution_model/03_durability_retries_caching.md)):

```python
def gate(state) -> Literal["retry", "done"]:
    if state["quality"] < 0.8 and state.get("attempt", 0) < 3:   # ✅ hard cap
        return "retry"
    return "done"
```

**Rule:** every edge that can loop back needs a counter or a timeout.

---

## Mistake 4 — `InMemorySaver` in production

```python
builder.compile(checkpointer=InMemorySaver())   # ❌ state lost on restart
```

**Fix:** use `SqliteSaver` (single node) or `PostgresSaver` (production) ([05-1](../05_persistence_and_memory/01_checkpointers.md)). `InMemorySaver` is for dev and tests only.

---

## Mistake 5 — routing logic inside nodes

```python
def node(state):
    return {"next": "node_a" if cond else "node_b", "data": ...}   # ❌ mixes work + routing
```

**Fix:** nodes do *work*; edges (or `Command`) decide *flow*. Put the decision in a conditional edge ([04-1](../04_control_flow/01_conditional_edges.md)) or return a `Command(goto=...)` ([04-2](../04_control_flow/02_command.md)) — don't invent a `next` field and branch on it manually.

---

## Mistake 6 — forgetting `thread_id`

```python
graph.invoke({"messages": [...]})            # ❌ with a checkpointer, this errors / mixes users
```

**Fix:** pass a unique thread per conversation ([03-1](../03_building_graphs/01_first_chatbot.md)):

```python
config = {"configurable": {"thread_id": f"user-{user_id}-{session_id}"}}   # ✅
graph.invoke({"messages": [...]}, config)
```

---

## Quick reference

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Untyped state | silent typo bugs | `TypedDict`/Pydantic |
| Missing reducer | data disappears | `operator.add` / `add_messages` |
| Unbounded loop | hangs / `GraphRecursionError` | counter + `recursion_limit` |
| `InMemorySaver` in prod | memory lost on restart | `Sqlite`/`PostgresSaver` |
| Routing in nodes | tangled, untestable | conditional edge / `Command` |
| No `thread_id` | users share state | unique `thread_id` per convo |

---

## Recap & next

- ✅ The six mistakes: untyped state, missing reducer, unbounded loop, dev checkpointer in prod, routing-in-nodes, missing `thread_id`.
- ✅ Each has a one-line fix you've already seen in earlier sections.
- ✅ Self-check: which two mistakes cause *silent* data loss rather than a crash?

→ Next: **[09-2 · Performance & hardening](02_performance_and_hardening.md)**

## Exercises

1. Audit any graph you built earlier in the course against the quick-reference table. Fix at least one issue.

<details>
<summary>Solution</summary>

Most beginner graphs miss a reducer on an accumulating list or lack a loop cap. Add `Annotated[list, operator.add]` and an attempt counter, and confirm behavior is unchanged for the happy path but safe for the edge cases.
</details>
