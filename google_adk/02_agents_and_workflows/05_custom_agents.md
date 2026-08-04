# 02-5 · Custom agents

> **Level:** Intermediate · **Prerequisites:** [02-4 · LoopAgent](04_loop_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

`Sequential`/`Parallel`/`Loop` cover most orchestration, but sometimes you need logic they don't express: a deterministic gate, a custom branching rule, calling an external system as a "step", or bespoke control flow. Subclass **`BaseAgent`** and implement `_run_async_impl` — you get a first-class agent that composes with all the others.

---

## A custom logic agent

`_run_async_impl` is an async generator: read `ctx.session.state`, do work, write state, and `yield` events.

```python
import asyncio
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.genai import types

class CounterAgent(BaseAgent):
    """A deterministic (non-LLM) agent that bumps a counter in state."""
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        n = ctx.session.state.get("counter", 0) + 1
        ctx.session.state["counter"] = n                 # write state directly
        yield Event(author=self.name,
                    content=types.Content(role="model", parts=[types.Part(text=f"count={n}")]))

async def main():
    agent = CounterAgent(name="counter")
    runner = InMemoryRunner(agent=agent, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="go")])
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        if e.content:
            print(e.content.parts[0].text)

asyncio.run(main())
```

**Output (real run):**
```
count=1
```

No model was involved — a custom agent is pure Python that participates in the event/state machinery. It can also *call sub-agents* (store them on the instance and iterate their `run_async` inside `_run_async_impl`) to build orchestration the built-in workflow agents don't offer.

---

## When to write one

| Situation | Custom `BaseAgent`? |
|-----------|:---:|
| Run agents in order / parallel / loop | ❌ use the built-ins |
| Deterministic gate or branch on state | ✅ |
| Call an external system as a pipeline step | ✅ |
| Bespoke control flow (dynamic sub-agent selection) | ✅ |
| Anything an `LlmAgent` + tools already does | ❌ |

Reach for a custom agent only when the built-ins can't express your control flow — otherwise you're reinventing `Sequential`/`Parallel`/`Loop`.

> **Tip:** Custom agents are also how you insert **non-LLM logic** (validation, formatting, math) as a named step in a pipeline — the ADK analog of a plain LangGraph node.

---

## Recap & next

- ✅ Subclass `BaseAgent` and implement `_run_async_impl` (async generator of events) for custom logic.
- ✅ Read/write `ctx.session.state`; `yield` events; optionally drive sub-agents.
- ✅ Use it only when the built-in workflow agents can't express your flow.
- ✅ Self-check: what does a custom agent give you that a `SequentialAgent` of `LlmAgent`s doesn't?

→ Next: **[03 · Tools](../03_tools/README.md)**

## Exercises

1. Write a `GateAgent(BaseAgent)` that reads `state["score"]` and yields either "pass" or "fail" text (no LLM).

<details>
<summary>Solution</summary>

```python
class GateAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        ok = ctx.session.state.get("score", 0) >= 0.7
        yield Event(author=self.name,
                    content=types.Content(role="model",
                                          parts=[types.Part(text="pass" if ok else "fail")]))
```
</details>
