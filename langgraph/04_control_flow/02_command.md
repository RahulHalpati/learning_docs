# 04-2 · `Command` — route and update in one move

> **Level:** Intermediate · **Prerequisites:** [04-1 · Conditional edges](01_conditional_edges.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

A conditional edge *decides* where to go but can't change state; a node *changes* state but (with plain edges) can't decide where to go. **`Command`** does both at once: a node returns `Command(update=..., goto=...)` to update state **and** name the next node. That single idea powers dynamic routing, and — via `Command.PARENT` — **agent handoffs** between graphs (Section 07).

---

## `update` + `goto` in one return

Instead of a node plus a separate router, one node can do both:

```python
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

class S(TypedDict):
    x: int
    path: Annotated[list, operator.add]

def router(state: S) -> Command[Literal["big", "small"]]:
    goto = "big" if state["x"] > 10 else "small"
    return Command(update={"path": ["router"]}, goto=goto)   # update AND route

def big(state: S):   return {"path": ["big"]}
def small(state: S): return {"path": ["small"]}

b = StateGraph(S)
b.add_node("router", router); b.add_node("big", big); b.add_node("small", small)
b.add_edge(START, "router")
b.add_edge("big", END); b.add_edge("small", END)

print(b.compile().invoke({"x": 42, "path": []}))
```

**Output (real run):**
```
{'x': 42, 'path': ['router', 'big']}
```

Note there's **no `add_conditional_edges`** for `router` — the `goto` *is* the routing. The `Command[Literal["big", "small"]]` return annotation tells LangGraph (and your type checker) the possible destinations so it can validate and draw the graph.

> **Tip:** `Command` vs conditional edge — use a **conditional edge** when routing is a pure decision with no state change; use **`Command`** when the same step naturally does both (e.g. "record the decision *and* jump there"). Both are idiomatic.

---

## `Command.PARENT` — handing off across graphs

A node inside a **subgraph** can route to a node in its **parent** graph by setting `graph=Command.PARENT`. This is the mechanism behind multi-agent *handoffs*: an agent (a subgraph) finishes and passes control — plus state — to a sibling agent in the parent.

```python
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

class State(TypedDict):
    path: Annotated[list, operator.add]

def node_a(state: State):
    # hand off to node_b, which lives in the PARENT graph
    return Command(update={"path": ["sub:a"]}, goto="node_b", graph=Command.PARENT)

sub = StateGraph(State); sub.add_node("node_a", node_a)
sub.add_edge(START, "node_a")
subgraph = sub.compile()

def node_b(state: State): return {"path": ["parent:b"]}

parent = StateGraph(State)
parent.add_node("subgraph", subgraph, destinations=("node_b",))   # declare the handoff target
parent.add_node("node_b", node_b)
parent.add_edge(START, "subgraph")
parent.add_edge("node_b", END)

print(parent.compile().invoke({"path": []}))
```

**Output (real run):**
```
{'path': ['sub:a', 'parent:b']}
```

Control started in the subgraph (`sub:a`), then jumped *out* to the parent's `node_b` — carrying the state update along. `destinations=("node_b",)` on the subgraph node tells the parent this handoff can happen (needed because the target isn't reachable via a normal edge).

---

## Recap & next

- ✅ `Command(update=..., goto=...)` lets a node change state **and** pick the next node — no separate router.
- ✅ Annotate the node's return as `Command[Literal[...]]` so destinations are validated and drawable.
- ✅ `graph=Command.PARENT` routes from a subgraph to a parent node — the basis of agent handoffs.
- ✅ Self-check: when would you prefer a conditional edge over returning a `Command`?

→ Next: **[04-3 · `Send` & map-reduce](03_send_map_reduce.md)**

## Exercises

1. Rewrite the loop from [04-1](01_conditional_edges.md) so `work` returns a `Command` that both increments `attempts` and `goto`s either itself or `done` — eliminating the separate `gate` router.

<details>
<summary>Solution</summary>

```python
from langgraph.types import Command
from typing import Literal

def work(state) -> Command[Literal["work", "done"]]:
    n = state["attempts"] + 1
    goto = "work" if n < 3 else "done"
    return Command(update={"attempts": n, "log": [f"try {n}"]}, goto=goto)
```
The routing decision now lives in the node via `goto`; no `add_conditional_edges` needed.
</details>
