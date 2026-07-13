# 01-4 · LangGraph refresher

> **Level:** Beginner · **Time:** 25 min · **Verified:** langgraph 1.1.10, Python 3.10

You only need five LangGraph concepts to build the whole pipeline. If you've done
the [LangGraph core guide](../../langgraph/) or the
[Proposal Agent](../../langgraph_proposal_agent/), skim this; otherwise, type it out.

| Concept | What it is |
|---|---|
| **State** | A `TypedDict` — the shared memory every node reads and writes |
| **Nodes** | Functions that read state and return **only what changed** |
| **Edges** | Fixed connections: "after A, run B" |
| **Conditional edges** | A router function picks the next node at runtime |
| **Checkpointer** | Saves state so you can **pause, resume, and gate** |

---

## A mini-graph in 30 lines

```python
# mini_graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class MyState(TypedDict):
    count: int
    message: str

def increment(state: MyState) -> dict:
    return {"count": state["count"] + 1}        # return ONLY what changed

def greet(state: MyState) -> dict:
    return {"message": f"Count reached {state['count']}"}

builder = StateGraph(MyState)
builder.add_node("increment", increment)
builder.add_node("greet", greet)
builder.add_edge(START, "increment")
builder.add_edge("increment", "greet")
builder.add_edge("greet", END)
graph = builder.compile()

print(graph.invoke({"count": 0, "message": ""}))
```

```bash
python3 mini_graph.py
# {'count': 1, 'message': 'Count reached 1'}
```

That's the pattern our pipeline scales up: six nodes instead of two.

---

## Nodes return partial updates

A node returns a dict of **only the keys it changed**. LangGraph merges it into
the running state.

```python
# ✅ correct
def researcher(state): return {"research": "...", "hook": "..."}
# ❌ wasteful and bug-prone — don't re-return unchanged keys
def researcher(state): return {"research": "...", "hook": "...", "topic": state["topic"]}
```

In our pipeline the scriptwriter returns `{"segments": [...]}`, the voiceover
returns `{"audio_path": ..., "segments": [...]}` (it enriches segments with
durations), and so on.

---

## Reducers: when several nodes write the same key

If more than one node writes a key, you need a **reducer** to say how values
combine. The common one is `operator.add`, which **appends** to a list:

```python
from typing import Annotated
import operator

class VideoState(TypedDict, total=False):
    log: Annotated[list[str], operator.add]   # every node appends its name
```

Every node in the capstone returns `{"log": ["<node name>"]}`. Because of the
reducer, the final `log` is the full ordered path — that's how the CLI prints
`researcher → scriptwriter → voiceover → ...`. Without the reducer, each node
would *overwrite* the log and you'd see only the last name.

---

## Conditional edges (the review loop)

A conditional edge calls a **router** that returns a string key mapping to the
next node (or `END`):

```python
from typing import Literal

def route_after_review(state) -> Literal["scriptwriter", "__end__"]:
    if state.get("approved"):
        return END
    return "scriptwriter"          # loop back and rewrite

builder.add_conditional_edges(
    "reviewer", route_after_review,
    {"scriptwriter": "scriptwriter", END: END},
)
```

Our capstone keeps the main path linear and uses an **interrupt** (below) for the
human gate, but you'll add a review-loop variant as an exercise.

---

## Checkpointers: pause, resume, gate

Compile with a **checkpointer** and the graph can persist state across calls,
keyed by a `thread_id`:

```python
from langgraph.checkpoint.memory import MemorySaver

graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["voiceover"],       # ← pause before rendering media
)
config = {"configurable": {"thread_id": "video-1"}}

graph.invoke({"topic": "Big-O"}, config)  # runs research + script, then PAUSES
state = graph.get_state(config)
print(state.next)                          # ('voiceover',)  ← waiting here
# ... a human reviews state.values["segments"] ...
graph.invoke(None, config)                 # resume: invoke(None) continues
```

`invoke(None, config)` means "continue from where this thread paused." This exact
mechanism is the human approval gate in
[03-2](../03_assembling_the_graph/02_human_in_the_loop.md), and it's verified by a
test in the capstone.

---

## Recap

| Concept | In Faceless Studio |
|---|---|
| `TypedDict` state | `VideoState` — topic in, video + metadata out |
| Nodes | `researcher`, `scriptwriter`, `voiceover`, `visuals`, `assembler`, `metadata` |
| `add_edge` | The linear pipeline, START → … → END |
| `add_conditional_edges` | A review→rewrite loop (exercise) |
| `Annotated[list, operator.add]` | The `log` field that records the path |
| `MemorySaver` + `interrupt_before` | The human approval gate |

## Self-check

1. A node returns `{"audio_path": "x.wav"}`. What happens to `topic` and `segments`?
2. Why does `log` need `Annotated[list[str], operator.add]`?
3. What does `graph.invoke(None, config)` do after an interrupt?

<details>
<summary>Answers</summary>

1. Unchanged — LangGraph merges the partial update; it never drops keys you didn't
   return.
2. Every node appends to `log`. Without the reducer each write would overwrite the
   list, so you'd lose the ordered path and only see the last node.
3. It **resumes** the paused thread, continuing from the interrupted node with the
   (possibly human-edited) saved state.

</details>

---

**Next → [02-1 · Shared state](../02_building_the_nodes/01_shared_state.md)**
