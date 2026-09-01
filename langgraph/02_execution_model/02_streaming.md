# 02-2 · Streaming

> **Level:** Intermediate · **Prerequisites:** [02-1 · Super-step model](01_super_step_model.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0)

## Why this matters

`invoke()` gives you the final state and nothing until then — fine for a script, painful for a UI where a user stares at a spinner for 10 seconds. Streaming lets you show progress: state as it changes, node outputs as they finish, LLM tokens as they're generated, and your *own* progress events. Picking the right mode is the whole game.

---

## The five stream modes

| `stream_mode` | Emits | Use for |
|---------------|-------|---------|
| `"values"` | the **full state** after each super-step | "show me the latest everything" |
| `"updates"` | only each node's **delta** | logging which node did what |
| `"messages"` | LLM **tokens** `(chunk, metadata)` | token-by-token chat UIs |
| `"custom"` | data **you** emit via `get_stream_writer()` | progress bars, tool status |
| `"debug"` | maximum detail (tasks, checkpoints, timing) | deep debugging |

You can also pass a **list** to get several at once — each item comes back tagged with its mode.

---

## `values` vs `updates`

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class S(TypedDict):
    x: int

def a(s): return {"x": s["x"] + 1}
def b(s): return {"x": s["x"] * 2}

g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile()

print("values:", list(app.stream({"x": 1}, stream_mode="values")))
print("updates:", list(app.stream({"x": 1}, stream_mode="updates")))
```

**Output (real run):**
```
values: [{'x': 1}, {'x': 2}, {'x': 4}]
updates: [{'a': {'x': 2}}, {'b': {'x': 4}}]
```

`values` includes the initial state and shows the whole thing each step; `updates` shows *who changed what*.

---

## `messages` — token-by-token

Stream the LLM's output as it's produced. Each item is `(message_chunk, metadata)`:

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
def chat(s: MessagesState): return {"messages": [llm.invoke(s["messages"])]}

g = StateGraph(MessagesState); g.add_node("chat", chat)
g.add_edge(START, "chat"); g.add_edge("chat", END)

for chunk, meta in g.compile().stream(
    {"messages": [HumanMessage(content="hi")]}, stream_mode="messages"
):
    print(chunk.content, end="", flush=True)
print()
```

**Output (representative — your wording will differ):**
```
Hello! How can I assist you today?
```

(Under the hood that arrived token by token, with `meta["langgraph_node"] == "chat"` on each chunk so you know which node produced it.)

---

## `custom` — your own progress events

When a node does slow non-LLM work (a web call, a file crunch), emit your own updates with `get_stream_writer()`:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

class S(TypedDict):
    x: int

def crunch(s):
    writer = get_stream_writer()
    writer({"progress": "loading data"})
    writer({"progress": "computing"})
    return {"x": s["x"] + 1}

g = StateGraph(S); g.add_node("crunch", crunch)
g.add_edge(START, "crunch"); g.add_edge("crunch", END)

for ev in g.compile().stream({"x": 0}, stream_mode="custom"):
    print(ev)
```

**Output (real run):**
```
{'progress': 'loading data'}
{'progress': 'computing'}
```

---

## Multiple modes at once

Pass a list; each yielded item is a `(mode, payload)` tuple:

```python
for mode, payload in app.stream({"x": 1}, stream_mode=["updates", "custom"]):
    print(mode, "→", payload)
```

**Output (real run, from the fan-out graph in 02-1 with a custom writer in `a`):**
```
custom → {'custom': 'hello from a'}
updates → {'a': {'x': 2, 'log': ['a']}}
updates → {'b': {'x': 4, 'log': ['b']}}
```

> **Tip:** For fine-grained framework events (LLM start/end, tool start/end, retriever events) there's also `async for ev in app.astream_events(input, version="v2")`. Prefer the `stream_mode`s above unless you specifically need that event taxonomy.

---

## Recap & next

- ✅ `values` = full state per step; `updates` = per-node deltas; `messages` = LLM tokens; `custom` = your events; `debug` = everything.
- ✅ Pass a **list** of modes to multiplex; items arrive tagged `(mode, payload)`.
- ✅ `get_stream_writer()` inside a node emits `custom` events for progress UIs.
- ✅ Self-check: which mode powers a "typing…" chat effect, and which powers a "step 2 of 5" progress bar?

→ Next: **[02-3 · Durability, retries & caching](03_durability_retries_caching.md)**

## Exercises

1. Take any two-node graph and stream it with `stream_mode=["values", "updates"]`. Print each item's mode tag.

<details>
<summary>Solution</summary>

```python
for mode, payload in app.stream({"x": 1}, stream_mode=["values", "updates"]):
    print(f"[{mode}] {payload}")
```
You'll see interleaved `values` snapshots and `updates` deltas, each labeled.
</details>
