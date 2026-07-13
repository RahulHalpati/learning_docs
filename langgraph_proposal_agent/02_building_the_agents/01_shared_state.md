# 02-1 · Shared State

> **Level:** Beginner · **Prerequisites:** [01-3 LangGraph refresher](../01_foundations/03_langgraph_refresher.md)
> **Time:** 15 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## Why a shared state?

All four agents need to communicate without calling each other directly. The solution
is a single **state dictionary** that LangGraph passes through every node. Each agent
reads what it needs and returns only the keys it updated.

Think of it as a shared whiteboard. The analyzer writes the job breakdown. The matcher
reads it and writes the fit assessment. The writer reads both and writes a draft. The
reviewer reads the draft and writes feedback. No agent stores private state.

---

## `proposal_agent/state.py`

```python
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class ProposalState(TypedDict, total=False):
    # input
    job_text: str            # the raw freelance job posting

    # produced by agents, in order
    analysis: str            # Analyzer: requirements, budget, pain points, red flags
    fit: str                 # Matcher: best portfolio project + fit level + why
    proposal: str            # Writer: the current proposal draft
    review: str              # Reviewer: "APPROVED" or concrete revision notes
    approved: bool           # Reviewer's verdict as a bool (drives the loop)

    # loop control
    revisions: int           # how many times the writer has revised
    max_revisions: int       # hard cap so the loop always terminates

    # observability
    log: Annotated[list[str], operator.add]   # each node appends its name
```

---

## Walking through the fields

### Input fields

`job_text` — the raw job posting, set once at the start and never changed.

### Agent output fields

Each agent writes exactly one key (or two):

| Agent | Writes |
|---|---|
| Analyzer | `analysis` |
| Profile Matcher | `fit` |
| Proposal Writer | `proposal`, `revisions` |
| Reviewer | `review`, `approved` |

The **order matters** — each key is only meaningful after the agent that writes it
has run. LangGraph enforces this via the edge wiring.

### Loop control fields

`revisions` — the writer increments this on every call: `state["revisions"] + 1`.  
`max_revisions` — set once at graph invocation time (default 2). The router checks
`revisions >= max_revisions` to know when to stop.

### Observability: the `log` field

```python
log: Annotated[list[str], operator.add]
```

Every agent appends its name to `log`:

```python
return {"log": ["analyzer"]}   # Analyzer
return {"log": ["matcher"]}    # Matcher
return {"log": ["writer"]}     # Writer (twice if one revision)
return {"log": ["reviewer"]}   # Reviewer (twice if one revision)
```

After a run with one revision, `log` accumulates to:

```
["analyzer", "matcher", "writer", "reviewer", "writer", "reviewer"]
```

The `operator.add` reducer appends instead of overwriting — that's what
`Annotated[list[str], operator.add]` means: "merge by concatenation".

### `total=False`

`TypedDict(total=False)` makes all keys optional at creation time. This lets you
start the graph with just `{"job_text": "...", "revisions": 0, "max_revisions": 2}`
without pre-populating `analysis`, `fit`, etc.

---

## Who reads what

```
job_text   → Analyzer ✓  Writer ✓  Reviewer ✓
analysis   →           Matcher ✓  Writer ✓
fit        →                      Writer ✓
proposal   →                               Reviewer ✓
review     →                      Writer ✓ (on revision)
approved   →                               router ✓
revisions  →                      Writer ✓  router ✓
```

---

## Verify

```python
# No LLM needed — just check the type
from proposal_agent.state import ProposalState
state: ProposalState = {
    "job_text": "Build a FastAPI backend",
    "revisions": 0,
    "max_revisions": 2,
    "log": [],
}
print(state)
```

```
{'job_text': 'Build a FastAPI backend', 'revisions': 0, 'max_revisions': 2, 'log': []}
```

---

## Self-check

1. Why is `log` typed as `Annotated[list[str], operator.add]` instead of just `list[str]`?
2. What does `total=False` do, and why is it needed?
3. The Proposal Writer both reads `review` and writes `proposal`. Which other agent also
   writes to `review`?

<details>
<summary>Answers</summary>

1. Without the reducer, each node that writes `log` would overwrite the previous list.
   `operator.add` makes LangGraph *concatenate* the new list onto the existing one.
2. `total=False` makes all keys optional at the TypedDict level. This lets the graph
   start with only `job_text`, `revisions`, and `max_revisions` — the other keys are
   populated as each agent runs.
3. The Reviewer writes `review`. The Writer reads it on its second run to incorporate
   the feedback.

</details>

---

**Next → [02 Analyzer](02_analyzer.md)**
