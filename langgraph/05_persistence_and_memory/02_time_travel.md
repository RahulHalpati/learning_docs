# 05-2 · Time-travel

> **Level:** Intermediate · **Prerequisites:** [05-1 · Checkpointers](01_checkpointers.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

Because every step is checkpointed, you can treat a run like a git history: **list** past states, **replay** from any of them, and **fork** by editing a past state and continuing down a new branch. This is gold for debugging ("what did state look like right before it went wrong?") and for human-in-the-loop ("let me fix that value and re-run from here").

Three APIs: `get_state` (current), `get_state_history` (all), `update_state` (edit/fork).

---

## Listing history

With a checkpointer attached, `get_state_history(config)` yields every checkpoint, newest first. Each snapshot has `.values` (the state) and `.next` (the nodes that were about to run):

```python
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

class S(TypedDict):
    x: int
    log: Annotated[list, operator.add]

def step1(s):    return {"x": 1, "log": ["step1"]}
def step2(s):    return {"x": 2, "log": ["step2"]}
def finalize(s): return {"x": s["x"] + 100, "log": ["finalize"]}   # depends on x

g = StateGraph(S)
for n, f in [("step1", step1), ("step2", step2), ("finalize", finalize)]:
    g.add_node(n, f)
g.add_edge(START, "step1"); g.add_edge("step1", "step2")
g.add_edge("step2", "finalize"); g.add_edge("finalize", END)
app = g.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "tt"}}
print("original:", app.invoke({"x": 0, "log": []}, cfg))

for h in app.get_state_history(cfg):
    print(f"  next={h.next} x={h.values.get('x')}")
```

**Output (real run):**
```
original: {'x': 102, 'log': ['step1', 'step2', 'finalize']}
  next=() x=102
  next=('finalize',) x=2
  next=('step2',) x=1
  next=('step1',) x=0
  next=('__start__',) x=None
```

Read bottom-to-top for chronological order. The snapshot with `next=('finalize',)` is the moment *just before* `finalize` ran, when `x` was 2.

---

## Forking: edit a past state and continue

`update_state(config, values)` writes a new checkpoint on top of a chosen one and returns a config pointing at it. Invoke with `None` as input to **resume** from there — down a new branch:

```python
# grab the checkpoint where `finalize` was about to run
target = next(h for h in app.get_state_history(cfg) if h.next == ("finalize",))

forked = app.update_state(target.config, {"x": 5})   # edit x: 2 → 5
print("forked:", app.invoke(None, forked))
```

**Output (real run):**
```
forked: {'x': 105, 'log': ['step1', 'step2', 'finalize']}
```

The original run produced `102` (2 + 100). By rewinding to just before `finalize`, editing `x` to `5`, and resuming, we get `105` — a *different* branch of history, without re-running `step1`/`step2`. That's time-travel.

> **Tip:** `update_state` applies your edit **through the reducers**, just like a node return. Editing a plain field replaces it; editing an `operator.add` list *appends*. To fully rewrite a reduced field you may need a custom reducer or `RemoveMessage` (next lesson).

---

## When you'll use it

- **Debugging:** print `get_state_history` to see exactly where state diverged from expectations.
- **Human-in-the-loop:** pause, let a human correct a value with `update_state`, then resume (Section 06 builds on this).
- **A/B a decision:** fork the same checkpoint two ways and compare outcomes.

---

## Recap & next

- ✅ `get_state_history(config)` lists every checkpoint (`.values`, `.next`), newest first.
- ✅ `update_state(config, values)` forks: it writes an edited checkpoint; `invoke(None, forked_cfg)` resumes from it.
- ✅ Edits go through reducers — replacing scalars, appending reduced lists.
- ✅ Self-check: why does resuming a fork skip `step1`/`step2` but still run `finalize`?

→ Next: **[05-3 · Long-term memory (the store)](03_long_term_memory_store.md)**

## Exercises

1. Fork the run at the checkpoint where `step2` was next and set `x` to `50`; predict and verify the final `x`.

<details>
<summary>Solution</summary>

Rewinding to before `step2` means `step2` still runs and *replaces* `x` with `2` (it ignores the incoming value), so `finalize` yields `102` again — editing `x` there has no effect. Edit a field a downstream node *reads* rather than *overwrites* to see a change. (This is why understanding which nodes overwrite which keys matters.)
</details>
