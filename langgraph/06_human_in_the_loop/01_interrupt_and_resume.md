# 06-1 · Interrupt & resume

> **Level:** Intermediate · **Prerequisites:** [05-1 · Checkpointers](../05_persistence_and_memory/01_checkpointers.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

`interrupt()` is the one function that turns an autonomous graph into a supervised one. Call it inside a node and the graph **stops**, hands a payload to the caller, and saves a checkpoint. Later you call `Command(resume=value)` and execution continues *from that exact point* with `value` as the return of `interrupt()`. Because it's checkpoint-based, the pause can last milliseconds or days.

> **Requirement:** HITL needs a **checkpointer**. The pause is a saved checkpoint; without one there's nothing to resume from.

---

## Pause, inspect, resume

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

class S(TypedDict):
    draft: str
    status: str

def write(s):    return {"draft": "Dear customer, your refund is approved."}

def approval(s):
    decision = interrupt({"question": "Send this email?", "draft": s["draft"]})  # PAUSE here
    return {"status": "sent" if decision == "approve" else "cancelled"}

def send(s):     return {"status": f"{s['status']} (done)"}

g = StateGraph(S)
g.add_node("write", write); g.add_node("approval", approval); g.add_node("send", send)
g.add_edge(START, "write"); g.add_edge("write", "approval")
g.add_edge("approval", "send"); g.add_edge("send", END)
app = g.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "hitl-1"}}
paused = app.invoke({"draft": "", "status": ""}, cfg)     # runs until interrupt()
print("interrupt payload:", paused["__interrupt__"][0].value)

resumed = app.invoke(Command(resume="approve"), cfg)      # human approves → continue
print("resumed:", resumed)
```

**Output (real run):**
```
interrupt payload: {'question': 'Send this email?', 'draft': 'Dear customer, your refund is approved.'}
resumed: {'draft': 'Dear customer, your refund is approved.', 'status': 'sent (done)'}
```

Two invocations, one continuous run:

1. The first `invoke` runs `write`, hits `interrupt()` in `approval`, and returns — the result carries an `__interrupt__` list with the payload you passed. The graph is now parked on thread `hitl-1`.
2. `Command(resume="approve")` re-enters `approval`; `interrupt()` *returns* `"approve"`; the node finishes and the graph runs on through `send` to `END`.

> **Tip:** Whatever you pass to `Command(resume=...)` becomes the return value of `interrupt()`. That can be a string (`"approve"`), a dict of edits, anything JSON-serializable — the basis of the edit/review patterns in the next lesson.

---

## Where does the payload go?

The value you pass to `interrupt({...})` is what your UI shows the human ("here's the draft — approve?"). The value they send back via `Command(resume=...)` is what the node acts on. Your front end lives *between* the two invocations; LangGraph doesn't care whether that's a CLI prompt, a Slack button, or a web form.

---

## Recap & next

- ✅ `interrupt(payload)` pauses a node and surfaces `payload` in the result's `__interrupt__`.
- ✅ `Command(resume=value)` resumes; `value` becomes `interrupt()`'s return.
- ✅ HITL requires a checkpointer (the pause is a checkpoint) and a `thread_id`.
- ✅ Self-check: what would the run return if you resumed with `"reject"` instead of `"approve"`?

→ Next: **[06-2 · Approve / edit / review](02_approve_edit_review.md)**

## Exercises

1. Resume the graph above with `"reject"` and confirm `status` becomes `cancelled (done)`.

<details>
<summary>Solution</summary>

```python
app.invoke({"draft": "", "status": ""}, {"configurable": {"thread_id": "hitl-2"}})
print(app.invoke(Command(resume="reject"), {"configurable": {"thread_id": "hitl-2"}}))
# → status: 'cancelled (done)'
```
</details>
