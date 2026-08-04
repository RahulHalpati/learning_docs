# 04-4 · Subgraphs

> **Level:** Intermediate · **Prerequisites:** [04-1 · Conditional edges](01_conditional_edges.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

As graphs grow, you want to *compose* them — build a self-contained "research" graph once and drop it into three different parent graphs. A compiled graph is itself a `Runnable`, so it can be a **node** in another graph. Subgraphs are how you get reuse, encapsulation, and (in Section 07) whole agents-as-components.

There are two ways to embed one, depending on whether the parent and child share a state schema.

---

## Case 1 — shared state: a compiled graph *is* a node

If the subgraph's state schema overlaps the parent's, add the compiled graph directly as a node. Shared keys flow in and out automatically.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class Sub(TypedDict):
    x: int

def inc(state: Sub): return {"x": state["x"] + 1}

sg = StateGraph(Sub); sg.add_node("inc", inc)
sg.add_edge(START, "inc"); sg.add_edge("inc", END)
subgraph = sg.compile()

class Par(TypedDict):
    x: int

pg = StateGraph(Par)
pg.add_node("sub", subgraph)          # ← a compiled graph used as a node
pg.add_edge(START, "sub"); pg.add_edge("sub", END)

print(pg.compile().invoke({"x": 100}))
```

**Output (real run):**
```
{'x': 101}
```

The parent handed its state to the subgraph, which ran its own `START → inc → END` and returned the updated `x`. The parent doesn't know or care what's inside.

---

## Case 2 — different state: wrap it in a function

When the schemas differ, you can't share keys directly. Instead, a normal node **invokes** the subgraph, translating state in and out:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class SubState(TypedDict):
    text: str
    word_count: int

def counter(s: SubState): return {"word_count": len(s["text"].split())}
sg = StateGraph(SubState); sg.add_node("counter", counter)
sg.add_edge(START, "counter"); sg.add_edge("counter", END)
subgraph = sg.compile()

class ParentState(TypedDict):
    document: str
    stats: dict

def analyze(state: ParentState) -> dict:
    result = subgraph.invoke({"text": state["document"], "word_count": 0})   # translate in
    return {"stats": {"words": result["word_count"]}}                        # translate out

pg = StateGraph(ParentState); pg.add_node("analyze", analyze)
pg.add_edge(START, "analyze"); pg.add_edge("analyze", END)

print(pg.compile().invoke({"document": "the quick brown fox jumps", "stats": {}}))
```

**Output (real run):**
```
{'document': 'the quick brown fox jumps', 'stats': {'words': 5}}
```

The wrapper node is the adapter: it maps `document → text`, invokes the subgraph, and maps `word_count → stats`. Use this whenever the child speaks a different "state language" than the parent.

| | Shared schema | Different schema |
|---|---|---|
| How | add compiled graph as a node | invoke it inside a wrapper node |
| State | keys flow automatically | you translate in/out |
| Use when | child is a natural continuation | child is a reusable, differently-shaped component |

> **Tip:** Streaming from a parent will *not* include subgraph-internal steps unless you pass `subgraphs=True` to `.stream(...)`. Handy when debugging why a nested graph "did nothing" from the parent's view.

---

## Recap & next

- ✅ A compiled graph is a `Runnable`, so it can be a **node** — the basis of composition and agents-as-components.
- ✅ Shared schema → drop it in as a node; different schema → invoke it inside a wrapper that translates state.
- ✅ Use `.stream(..., subgraphs=True)` to see inside nested graphs.
- ✅ Self-check: which embedding style would you use to reuse a generic "summarize any text" graph across projects?

→ Next: **[05 · Persistence & memory](../05_persistence_and_memory/README.md)**

## Exercises

1. Build a subgraph that lowercases and strips text (`SubState{text}`) and embed it via a wrapper into a parent that stores the cleaned text under a `clean` key.

<details>
<summary>Solution</summary>

```python
def clean_node(state):
    out = subgraph.invoke({"text": state["raw"]})
    return {"clean": out["text"]}
```
The wrapper adapts `raw → text` and `text → clean`, exactly as in Case 2.
</details>
