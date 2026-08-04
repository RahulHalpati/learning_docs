# 02-4 · Runtime configuration

> **Level:** Intermediate · **Prerequisites:** [02-1 · Super-step model](01_super_step_model.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

State is data that *changes* during a run (messages, findings, counters). But some things are **fixed for the whole run** and shouldn't live in state: which user this is for, which model to use, what tone to write in, a request id. That's **runtime configuration** — passed in at `invoke` time and read by nodes without polluting your state schema.

---

## The modern way: `context_schema` + `Runtime`

Declare a typed context, then any node can take a second `runtime` parameter to read it:

```python
from typing import TypedDict
from dataclasses import dataclass
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

@dataclass
class Ctx:                       # the run's fixed configuration
    user_name: str
    tone: str = "formal"

class S(TypedDict):
    greeting: str

def greet(state: S, runtime: Runtime[Ctx]) -> dict:
    ctx = runtime.context                       # typed access
    hi = "Hello" if ctx.tone == "formal" else "Hey"
    return {"greeting": f"{hi}, {ctx.user_name}!"}

g = StateGraph(S, context_schema=Ctx)          # register the context type
g.add_node("greet", greet)
g.add_edge(START, "greet"); g.add_edge("greet", END)
app = g.compile()

print(app.invoke({"greeting": ""}, context=Ctx(user_name="Ada", tone="casual")))
```

**Output (real run):**
```
{'greeting': 'Hey, Ada!'}
```

Same graph, different run: pass `context=Ctx(user_name="Ada", tone="formal")` and you get `Hello, Ada!` — no state change, no code change.

> **Tip:** Use runtime context for a per-request model choice: put `model_name` in `Ctx`, and have nodes build their LLM from `runtime.context.model_name`. One graph serves "fast/cheap" and "slow/smart" tiers.

---

## The classic way: `configurable` (RunnableConfig)

Before `context_schema`, runtime values were passed under `config["configurable"]`. This still works and is what `thread_id` uses (Section 05):

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class S(TypedDict):
    greeting: str

def greet(state: S, config) -> dict:            # second param is the RunnableConfig
    name = config["configurable"].get("user_name", "friend")
    return {"greeting": f"Hi {name}"}

g = StateGraph(S); g.add_node("greet", greet)
g.add_edge(START, "greet"); g.add_edge("greet", END)

print(g.compile().invoke({"greeting": ""}, {"configurable": {"user_name": "Bob"}}))
```

**Output (real run):**
```
{'greeting': 'Hi Bob'}
```

---

## Which one?

| Use | For |
|-----|-----|
| `context_schema` + `Runtime` | your own typed, per-run settings (user, tone, model) — **preferred in 1.x** |
| `config["configurable"]` | framework keys like `thread_id`, and interop with LangChain `Runnable` config |

Both are read-only inside nodes and both are set at `invoke`/`stream` time — the difference is typing and intent. New code should reach for `context_schema`; you'll still *see* `configurable` everywhere because `thread_id` lives there.

---

## Recap & next

- ✅ Runtime config = values fixed for a whole run; keep them **out of state**.
- ✅ `context_schema=Ctx` + a `runtime: Runtime[Ctx]` node param is the typed, preferred way.
- ✅ `config["configurable"]` is the classic mechanism and carries framework keys like `thread_id`.
- ✅ Self-check: would you put `thread_id`, `user_tone`, and `message_history` in state, context, or configurable?

→ Next: **[03 · Building graphs](../03_building_graphs/README.md)**

## Exercises

1. Add a `model_tier: str` field to `Ctx` and have `greet` produce a longer greeting when `tier == "premium"`.

<details>
<summary>Solution</summary>

```python
@dataclass
class Ctx:
    user_name: str
    model_tier: str = "free"

def greet(state, runtime):
    ctx = runtime.context
    if ctx.model_tier == "premium":
        return {"greeting": f"Welcome back, {ctx.user_name}! Delighted to help today."}
    return {"greeting": f"Hi {ctx.user_name}"}
```
Runtime context lets one graph serve multiple tiers without branching its structure.
</details>
