# 02-2 · SequentialAgent

> **Level:** Beginner · **Prerequisites:** [02-1 · LlmAgent](01_llm_agent.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

`SequentialAgent` is the simplest orchestrator: run these sub-agents **in order**, threading a shared session state. It's ADK's answer to a fixed pipeline (research → write → review), and the workhorse of most real agents.

---

## A two-stage pipeline

Each sub-agent writes its result to state via `output_key`; the next reads it via `{key}` in its instruction:

```python
import asyncio
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel        # lesson 01-3

researcher = LlmAgent(name="researcher",
                      model=FakeAdkModel(model="f", responses=["found 3 sources"]),
                      instruction="Research the topic.", output_key="research")

writer = LlmAgent(name="writer",
                  model=FakeAdkModel(model="f", responses=["report using {research}"]),
                  instruction="Write a report using: {research}", output_key="report")

pipeline = SequentialAgent(name="pipeline", sub_agents=[researcher, writer])

async def main():
    runner = InMemoryRunner(agent=pipeline, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="research LangGraph")])
    finals = []
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        if e.is_final_response() and e.content:
            finals.append((e.author, e.content.parts[0].text))
    sess = await runner.session_service.get_session(app_name="a", user_id="u", session_id=s.id)
    print("finals:", finals)
    print("state:", dict(sess.state))

asyncio.run(main())
```

**Output (real run):**
```
finals: [('researcher', 'found 3 sources'), ('writer', 'report using {research}')]
state: {'research': 'found 3 sources', 'report': 'report using {research}'}
```

The agents ran in order and both wrote to state (`research`, then `report`). The researcher's output became available to the writer through `session.state`.

> **Note:** the writer's output shows the literal `{research}` because the **fake** model returns its canned text verbatim. With a real model (Ollama/Gemini), ADK substitutes `{research}` in the *instruction* before the call, so the writer actually sees "found 3 sources". The state-passing mechanism (`output_key` → `{key}`) is what the run verifies; the substitution is a property of the real model call.

---

## When to use it

`SequentialAgent` fits any fixed, ordered process where each step builds on the last: extract → transform → load, draft → critique → revise, plan → execute. If the *order* is known ahead of time, this is your tool. When the next step depends on a *decision*, reach for delegation ([Section 05](../05_multi_agent_systems/README.md)) or a loop.

---

## Recap & next

- ✅ `SequentialAgent(sub_agents=[...])` runs agents in order over one shared session.
- ✅ `output_key` (write) + `{key}` in the next instruction (read) thread data through.
- ✅ Use it for fixed pipelines; use delegation/loops when order depends on decisions.
- ✅ Self-check: how did the writer get the researcher's findings without you passing them explicitly?

→ Next: **[02-3 · ParallelAgent](03_parallel_agent.md)**

## Exercises

1. Add a third `reviewer` agent that reads `{report}` and writes `output_key="review"`; confirm all three keys end up in state.

<details>
<summary>Solution</summary>

Append a `reviewer = LlmAgent(..., instruction="Review: {report}", output_key="review")` to `sub_agents`. After the run, `state` has `research`, `report`, and `review`.
</details>
