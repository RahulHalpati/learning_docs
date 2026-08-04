# 02-4 · LoopAgent

> **Level:** Intermediate · **Prerequisites:** [02-2 · SequentialAgent](02_sequential_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

Some work needs repetition until a condition holds: draft → critique → revise until the critique passes; retry a flaky step; refine an answer. `LoopAgent` runs its sub-agents **repeatedly**, stopping on either a `max_iterations` cap or an explicit **escalation** signal. It's ADK's controlled cycle — the counterpart to LangGraph's bounded loop.

---

## Two ways a loop ends

1. **`max_iterations`** — a hard cap (always set one as a safety net).
2. **Escalation** — a sub-agent emits `EventActions(escalate=True)` to break out early ("good enough, stop").

Here's escalation stopping a loop *before* its cap. A custom counter agent escalates once it reaches 3, even though `max_iterations=10`:

```python
import asyncio
from typing import AsyncGenerator
from google.adk.agents import LoopAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types

class CountUntilThree(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        n = ctx.session.state.get("n", 0) + 1
        ctx.session.state["n"] = n
        yield Event(
            author=self.name,
            actions=EventActions(escalate=(n >= 3)),   # ← break the loop at 3
            content=types.Content(role="model", parts=[types.Part(text=f"iter {n}")]),
        )

async def main():
    loop = LoopAgent(name="loop", sub_agents=[CountUntilThree(name="ctr")], max_iterations=10)
    runner = InMemoryRunner(agent=loop, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="go")])
    texts = []
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        if e.content and e.content.parts and e.content.parts[0].text:
            texts.append(e.content.parts[0].text)
    print(texts)

asyncio.run(main())
```

**Output (real run):**
```
['iter 1', 'iter 2', 'iter 3']
```

The loop stopped at 3 via `escalate=True`, not the cap of 10. Flip it around — remove the escalation and set `max_iterations=3` — and you get the same three iterations, but bounded by the cap instead.

---

## The critique-revise pattern

The classic `LoopAgent` use is quality-driven revision:

```python
# LoopAgent(sub_agents=[writer, critic], max_iterations=3)
#   writer  → drafts/updates state["draft"]
#   critic  → judges it; if good, emits EventActions(escalate=True) to stop
```

The critic is where you'd escalate: if the draft passes, break; otherwise loop and let the writer revise. `max_iterations` guarantees you can't loop forever even if the critic is never satisfied — the same "cap your loops" rule as [LangGraph 09-1](../../langgraph/09_pitfalls_and_production/01_pitfalls_best_practices.md).

---

## Recap & next

- ✅ `LoopAgent` repeats its sub-agents until `max_iterations` **or** an `EventActions(escalate=True)`.
- ✅ Always set `max_iterations` as a safety net; use escalation for "good enough, stop".
- ✅ Classic use: writer + critic, critic escalates when quality passes.
- ✅ Self-check: with `max_iterations=10` and escalation at 3, how many iterations run — and why?

→ Next: **[02-5 · Custom agents](05_custom_agents.md)**

## Exercises

1. Build a `LoopAgent` of `[writer, critic]` where `critic` escalates once `state["score"] >= 0.8`; seed a rising score.

<details>
<summary>Solution</summary>

Make `critic` a `BaseAgent` that bumps `state["score"]` each pass and yields `EventActions(escalate=(score >= 0.8))`. The loop ends when the score clears the bar or `max_iterations` is hit.
</details>
