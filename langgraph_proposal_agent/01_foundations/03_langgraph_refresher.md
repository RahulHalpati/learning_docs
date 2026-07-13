# 01-3 · LangGraph Refresher

> **Level:** Beginner · **Prerequisites:** [02 Environment & providers](02_environment_and_providers.md)
> **Time:** 25 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## The four concepts you need

LangGraph is a library for building **stateful agent graphs**. You only need four
concepts for this course:

| Concept | What it is |
|---|---|
| **State** | A `TypedDict` — the shared memory that flows through every node |
| **Nodes** | Python functions that read the state and return updates |
| **Edges** | Connections that decide which node runs next |
| **Conditional edges** | Edges where a function decides the next node at runtime |

> Already comfortable with LangGraph? → [skip to Section 02](../02_building_the_agents/01_shared_state.md)
>
> Want the deep-dive? → [LangGraph core concepts guide](../../langgraph/01_core_concepts.md)

---

## A mini-graph in 30 lines

Run this to confirm your install is working:

```python
# mini_graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class MyState(TypedDict):
    count: int
    message: str

def increment(state: MyState) -> dict:
    return {"count": state["count"] + 1}

def greet(state: MyState) -> dict:
    return {"message": f"Count reached {state['count']}"}

builder = StateGraph(MyState)
builder.add_node("increment", increment)
builder.add_node("greet", greet)

builder.add_edge(START, "increment")
builder.add_edge("increment", "greet")
builder.add_edge("greet", END)

graph = builder.compile()

result = graph.invoke({"count": 0, "message": ""})
print(result)
```

```bash
python3 mini_graph.py
```

Output:

```
{'count': 1, 'message': 'Count reached 1'}
```

---

## State: only return what changed

Nodes return a **partial update** — only the keys they changed. LangGraph merges
this with the existing state:

```python
# ✅ correct: return only what this node writes
def my_node(state: MyState) -> dict:
    return {"count": state["count"] + 1}

# ❌ wrong: re-returning unchanged keys wastes work and can cause bugs
def my_node(state: MyState) -> dict:
    return {"count": state["count"] + 1, "message": state["message"]}
```

---

## Conditional edges

A conditional edge calls a **router function** to decide which node runs next.
The router returns a string key that maps to a node name (or `END`).

```python
from typing import Literal

def route(state: MyState) -> Literal["increment", "__end__"]:
    if state["count"] < 3:
        return "increment"   # loop back
    return END               # "__end__" also works

builder.add_conditional_edges(
    "increment",             # FROM this node
    route,                   # call this function
    {"increment": "increment", END: END},  # map return values to nodes
)
```

This is exactly how the **reviewer → writer revision loop** works in the proposal
agent — the router checks `approved` and `revisions` and returns either `"writer"`
or `END`.

---

## The `Annotated` reducer

When a key can be written by multiple nodes (or the same node multiple times), you
need a **reducer** that controls how new values are merged.

The most common reducer is `operator.add` — it **appends** new values to a list:

```python
from typing import Annotated
import operator

class MyState(TypedDict):
    log: Annotated[list[str], operator.add]  # each node appends; never overwrites
```

```python
# Node A returns {"log": ["node_a"]}
# Node B returns {"log": ["node_b"]}
# Final state: {"log": ["node_a", "node_b"]}
```

Without `Annotated`, each node would overwrite the list — you'd only see the last
node's entry.

The proposal agent uses this for the `log` field to track which agents ran and in
what order.

---

## Memory with `MemorySaver`

By default a graph is stateless — each `invoke()` starts fresh. Add a
**checkpointer** to persist state across calls:

```python
from langgraph.checkpoint.memory import MemorySaver

graph = builder.compile(checkpointer=MemorySaver())

# First call — thread "user-123" starts
result1 = graph.invoke({"count": 0}, config={"configurable": {"thread_id": "user-123"}})

# Second call — same thread_id resumes from saved state
result2 = graph.invoke({"count": 0}, config={"configurable": {"thread_id": "user-123"}})
```

`thread_id` is the key: same ID = same conversation. Different ID = fresh start.

---

## Recap

| LangGraph concept | In the proposal agent |
|---|---|
| `TypedDict` state | `ProposalState` — 9 keys shared by all 4 agents |
| Nodes | `analyzer`, `matcher`, `writer`, `reviewer` functions |
| `add_edge` | Sequential: START→analyzer→matcher→writer→reviewer |
| `add_conditional_edges` | `reviewer → route_after_review → writer or END` |
| `Annotated[list, operator.add]` | `log` field — accumulates every node name |
| `MemorySaver` + `thread_id` | Per-job conversation persistence |

---

## Self-check

1. A node returns `{"count": 5}`. What happens to other keys in the state?
2. What is the difference between `add_edge` and `add_conditional_edges`?
3. Why does the `log` field use `Annotated[list[str], operator.add]`?

<details>
<summary>Answers</summary>

1. They are unchanged — LangGraph merges the partial update into the existing state.
2. `add_edge` always goes to the same next node. `add_conditional_edges` calls a
   router function at runtime to decide the next node.
3. Multiple nodes (and the writer node running multiple times) all append to `log`.
   Without the reducer, each write would overwrite the previous list.

</details>

---

**Next → [02-1 Shared state](../02_building_the_agents/01_shared_state.md)**
