# 03-1 · Wiring & the Revision Loop

> **Level:** Beginner · **Prerequisites:** [02-5 Reviewer](../02_building_the_agents/05_reviewer.md)
> **Time:** 25 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## The full graph

```
START → analyzer → matcher → writer → reviewer ─(APPROVED or cap)─→ END
                                          └──────(needs work)───────→ writer
```

Five connections, one of which is conditional. Here's the complete `graph.py`:

```python
from __future__ import annotations

from functools import partial
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import agents
from .profile import load_profile, profile_to_text
from .providers import get_chat_model
from .state import ProposalState


def route_after_review(state: ProposalState) -> Literal["writer", "__end__"]:
    if state.get("approved") or state.get("revisions", 0) >= state.get("max_revisions", 2):
        return END
    return "writer"


def build_graph(llm: BaseChatModel | None = None, profile: dict | None = None):
    llm = llm or get_chat_model()
    profile = profile or load_profile()
    profile_text = profile_to_text(profile)
    tone = profile.get("tone", "confident and direct")

    builder = StateGraph(ProposalState)
    builder.add_node("analyzer", partial(agents.analyzer, llm=llm))
    builder.add_node("matcher", partial(agents.matcher, llm=llm, profile_text=profile_text))
    builder.add_node("writer",  partial(agents.writer,  llm=llm, tone=tone))
    builder.add_node("reviewer", partial(agents.reviewer, llm=llm))

    builder.add_edge(START, "analyzer")
    builder.add_edge("analyzer", "matcher")
    builder.add_edge("matcher", "writer")
    builder.add_edge("writer", "reviewer")
    builder.add_conditional_edges(
        "reviewer", route_after_review, {"writer": "writer", END: END}
    )

    return builder.compile(checkpointer=MemorySaver())


def generate_proposal(job_text: str, *, max_revisions: int = 2, thread_id: str = "default", **kwargs) -> dict:
    graph = build_graph(**kwargs)
    return graph.invoke(
        {"job_text": job_text, "revisions": 0, "max_revisions": max_revisions},
        config={"configurable": {"thread_id": thread_id}},
    )
```

---

## `functools.partial` — binding dependencies to nodes

LangGraph calls every node with a single argument: `state`. But the agents need `llm`,
`profile_text`, and `tone` too. How do you pass them?

`functools.partial` pre-fills arguments on a function:

```python
from functools import partial

# agents.matcher expects: (state, llm, profile_text)
# partial(...) returns a new function that only needs: (state)
node_fn = partial(agents.matcher, llm=llm, profile_text=profile_text)

# LangGraph calls: node_fn(state) ← same as agents.matcher(state, llm=llm, profile_text=...)
builder.add_node("matcher", node_fn)
```

This keeps agent functions **plain and testable** — you can call them directly in tests
with any fake LLM, without involving the graph at all.

---

## The router function

```python
def route_after_review(state: ProposalState) -> Literal["writer", "__end__"]:
    if state.get("approved") or state.get("revisions", 0) >= state.get("max_revisions", 2):
        return END      # END is the string "__end__"
    return "writer"
```

LangGraph calls this after every `reviewer` run. The return value is a key in the
edge map `{"writer": "writer", END: END}` that resolves to the next node name.

Two termination conditions:
- `approved = True` — the reviewer said yes, ship it
- `revisions >= max_revisions` — hard cap, exit with best draft so far

Without the cap, a pathologically strict reviewer (or a bad LLM) would loop forever.

---

## Integration test: the revision loop

```python
# tests/test_graph.py

from langchain_core.language_models import GenericFakeChatModel
from proposal_agent.graph import build_graph, route_after_review

def run(messages, *, max_revisions=2):
    llm = GenericFakeChatModel(messages=iter(messages))
    graph = build_graph(llm=llm)
    return graph.invoke(
        {"job_text": "Need a FastAPI backend", "revisions": 0, "max_revisions": max_revisions},
        config={"configurable": {"thread_id": "test"}},
    )


def test_happy_path_no_revision():
    final = run(["analysis", "HIGH fit — Typed SDK", "great proposal", "APPROVED"])
    assert final["log"] == ["analyzer", "matcher", "writer", "reviewer"]
    assert final["approved"] is True
    assert final["revisions"] == 1


def test_revision_loop_then_approve():
    final = run([
        "analysis", "HIGH fit — Typed SDK",
        "draft 1", "1. Too generic.",   # writer + reviewer (rejects)
        "draft 2", "APPROVED",           # writer again + reviewer (approves)
    ])
    assert final["log"] == ["analyzer", "matcher", "writer", "reviewer", "writer", "reviewer"]
    assert final["revisions"] == 2
    assert final["approved"] is True


def test_max_revisions_caps_the_loop():
    final = run(
        ["analysis", "fit", "d1", "1. fix", "d2", "2. fix", "d3", "3. fix"],
        max_revisions=2,
    )
    assert final["revisions"] == 2
    assert final["approved"] is False
```

Run all graph tests:

```bash
PROPOSAL_LLM=fake pytest tests/test_graph.py -v
```

Output:

```
tests/test_graph.py::test_happy_path_no_revision    PASSED
tests/test_graph.py::test_revision_loop_then_approve PASSED
tests/test_graph.py::test_max_revisions_caps_the_loop PASSED
tests/test_graph.py::test_router_logic               PASSED

4 passed in 1.9s
```

---

## Recap

| Concept | Code |
|---|---|
| Bind dependencies to nodes | `partial(agents.matcher, llm=llm, profile_text=...)` |
| Sequential edges | `add_edge(START, "analyzer")` etc. |
| Conditional edge | `add_conditional_edges("reviewer", route_after_review, {...})` |
| Loop termination | `approved` OR `revisions >= max_revisions` |
| Compile with memory | `builder.compile(checkpointer=MemorySaver())` |

---

## Self-check

1. Why is `functools.partial` needed when adding nodes?
2. What happens if `max_revisions=0`? Walk through the router logic.
3. `route_after_review` uses `state.get("revisions", 0)`. Why `.get()` instead of `state["revisions"]`?

<details>
<summary>Answers</summary>

1. LangGraph calls node functions with only `state`. `partial` pre-fills the extra
   arguments (`llm`, `profile_text`, `tone`) so the function signature matches.
2. With `max_revisions=0`, after the first `writer` run `revisions = 1 >= 0` is `True`,
   so the router returns `END` immediately — no review cycle at all.
3. On the very first state `{"revisions": 0, "max_revisions": 2}`, the key is present.
   But `state.get()` is a safe habit — if the key were somehow missing, it defaults
   to 0 rather than raising `KeyError`.

</details>

---

**Next → [03-2 Memory & streaming](02_memory_and_streaming.md)**
