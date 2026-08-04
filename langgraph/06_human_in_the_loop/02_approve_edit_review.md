# 06-2 · Approve / edit / review

> **Level:** Intermediate · **Prerequisites:** [06-1 · Interrupt & resume](01_interrupt_and_resume.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

"Pause for a human" comes in a few standard flavors. Knowing them by name — **approve/reject**, **edit-state**, **review-tool-call**, and **static breakpoints** — means you reach for the right one instead of reinventing it. All build on `interrupt`/`Command(resume=...)` from the last lesson.

---

## Pattern 1 — approve / reject

The simplest gate: show something, resume with a yes/no. You saw it in 06-1 (`resume="approve"`). Use it before any irreversible action — sending, paying, deleting.

---

## Pattern 2 — edit state

Instead of a yes/no, the human returns *corrected data*, and the node adopts it:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

class S(TypedDict):
    draft: str

def propose(s):    return {"draft": "hello wrld"}          # note the typo
def human_edit(s):
    edited = interrupt({"draft_for_review": s["draft"]})    # show draft, await edit
    return {"draft": edited}                                # adopt the human's version

g = StateGraph(S)
g.add_node("propose", propose); g.add_node("human_edit", human_edit)
g.add_edge(START, "propose"); g.add_edge("propose", "human_edit"); g.add_edge("human_edit", END)
app = g.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "e1"}}
app.invoke({"draft": ""}, cfg)
print(app.invoke(Command(resume="hello world"), cfg))       # human fixes the typo
```

**Output (real run):**
```
{'draft': 'hello world'}
```

The human's resume value *replaced* the AI's draft. Same shape works for editing a tool's arguments before it runs, or correcting an extracted field.

---

## Pattern 3 — review a tool call

Before executing a risky tool, `interrupt` with the proposed call so a human can approve, edit the arguments, or reject. On resume, either run the (possibly edited) call or skip it. This is Pattern 1 + Pattern 2 applied to the tool node — the safety net for agents that touch the real world.

---

## Pattern 4 — static breakpoints (no code change)

Sometimes you want to pause **before** or **after** a node without editing it — for debugging or a manual gate. Compile with `interrupt_before` / `interrupt_after`:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

class S(TypedDict):
    n: int

def a(s): return {"n": s["n"] + 1}
def b(s): return {"n": s["n"] * 10}

g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile(checkpointer=InMemorySaver(), interrupt_before=["b"])   # pause before b

cfg = {"configurable": {"thread_id": "b1"}}
mid = app.invoke({"n": 0}, cfg)
print("paused, n =", mid["n"], "| next =", app.get_state(cfg).next)
print("continue:", app.invoke(None, cfg))       # resume with no input
```

**Output (real run):**
```
paused, n = 1 | next = ('b',)
continue: {'n': 10}
```

The graph stopped *before* `b` (state shows `n=1`, `next=('b',)`); invoking with `None` continued it. No `interrupt()` call inside `b` was needed — the breakpoint is set at compile time.

| | Dynamic `interrupt()` | Static `interrupt_before/after` |
|---|---|---|
| Where defined | inside the node | at `compile()` |
| Passes a payload | ✅ | ❌ (inspect state via `get_state`) |
| Edit before resume | via `Command(resume=...)` | via `update_state` (05-2) |
| Best for | product HITL flows | debugging, ad-hoc manual gates |

---

## Recap & next

- ✅ Approve/reject, edit-state, and review-tool-call are the three product HITL patterns — all on `interrupt`/`resume`.
- ✅ The resume value can be a decision *or* corrected data the node adopts.
- ✅ Static `interrupt_before`/`interrupt_after` pause without touching node code; combine with `update_state` to edit.
- ✅ Self-check: to let a human fix a tool's arguments before it runs, which pattern(s) do you combine?

→ Next: **[07 · Multi-agent](../07_multi_agent/README.md)**

## Exercises

1. Add `interrupt_after=["a"]` (instead of before `b`) and observe how `next` differs when it pauses.

<details>
<summary>Solution</summary>

`interrupt_after=["a"]` pauses at the same place logically (after `a`, before `b`), and `get_state().next` is still `('b',)`. `interrupt_before=["b"]` and `interrupt_after=["a"]` are two ways to name the same boundary here.
</details>
