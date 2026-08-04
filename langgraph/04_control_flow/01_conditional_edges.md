# 04-1 · Conditional edges

> **Level:** Beginner → Intermediate · **Prerequisites:** [01-1 · Core concepts](../01_foundations/01_core_concepts.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

Fixed edges make a straight line. **Conditional edges** make decisions — they're what let a graph branch, loop, and end early based on what actually happened. Every router, quality gate, and agent loop in this course is a conditional edge.

---

## Anatomy

```python
builder.add_conditional_edges(source, router_fn, path_map)
```

- **`source`** — the node we're leaving.
- **`router_fn(state)`** — reads state, returns a *string* (or list of strings) naming where to go.
- **`path_map`** — maps those return values to node names. Optional if the router returns node names directly; required when the return value differs from the node name.

The router **must not** mutate state — it only *reads* and decides. (To decide *and* update, use `Command`, next lesson.)

---

## A router with a loop

```python
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END

class S(TypedDict):
    attempts: int
    log: Annotated[list, operator.add]

def work(state: S) -> dict:
    return {"attempts": state["attempts"] + 1, "log": [f"try {state['attempts'] + 1}"]}

def gate(state: S) -> Literal["work", "done"]:
    return "work" if state["attempts"] < 3 else "done"   # loop until 3 attempts

def done(state: S) -> dict:
    return {"log": ["done"]}

b = StateGraph(S)
b.add_node("work", work); b.add_node("done", done)
b.add_edge(START, "work")
b.add_conditional_edges("work", gate, {"work": "work", "done": "done"})  # cycle back to work
b.add_edge("done", END)

print(b.compile().invoke({"attempts": 0, "log": []}))
```

**Output (real run):**
```
{'attempts': 3, 'log': ['try 1', 'try 2', 'try 3', 'done']}
```

`gate` sends control back to `work` until `attempts` hits 3, then to `done`. That "loop back to the same node" is a cycle — perfectly legal, and how agents retry.

> **Tip:** The path map's *keys* are what the router returns; the *values* are node names. Using a `Literal[...]` return type on the router (as above) documents the legal branches and lets your type checker catch typos.

---

## Returning `END` directly

A router can end the graph by returning the `END` sentinel (or a key mapped to it):

```python
from langgraph.graph import END

def gate(state) -> str:
    return END if state["attempts"] >= 3 else "work"
# add_conditional_edges("work", gate)   # no path_map needed: returns node name or END
```

> ⚠️ Return the `END` **sentinel**, not the raw string `"__end__"`. They happen to be equal internally, but the sentinel is the idiomatic, future-proof choice.

---

## Recap & next

- ✅ `add_conditional_edges(source, router, path_map)` — the router reads state and names the next hop.
- ✅ Routers must be side-effect-free; loops (routing back to a node) are how agents retry.
- ✅ Return the `END` sentinel to finish; annotate routers with `Literal[...]`.
- ✅ Self-check: why should routing logic live in the edge, not inside the node?

→ Next: **[04-2 · `Command` — route + update](02_command.md)**

## Exercises

1. Build a router that classifies a `score` field into `"high"`/`"medium"`/`"low"` terminal nodes.

<details>
<summary>Solution</summary>

```python
from typing import Literal
def classify(state) -> Literal["high", "medium", "low"]:
    s = state["score"]
    return "high" if s >= 0.8 else "medium" if s >= 0.5 else "low"
b.add_conditional_edges("evaluate", classify,
                        {"high": "high", "medium": "medium", "low": "low"})
```
</details>
