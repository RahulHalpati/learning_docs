# 02-3 · ParallelAgent

> **Level:** Beginner · **Prerequisites:** [02-2 · SequentialAgent](02_sequential_agent.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

When sub-agents don't depend on each other — fetch weather *and* news, gather three independent perspectives — running them one after another wastes time. `ParallelAgent` runs them **concurrently** and merges their outputs into shared state. It's ADK's fan-out.

---

## Two agents at once

Give each parallel agent a **distinct `output_key`** so their results don't collide:

```python
import asyncio
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel

weather = LlmAgent(name="weather", model=FakeAdkModel(model="f", responses=["sunny"]),
                   instruction="Report the weather.", output_key="weather")
news = LlmAgent(name="news", model=FakeAdkModel(model="f", responses=["all quiet"]),
                instruction="Report the news.", output_key="news")

fanout = ParallelAgent(name="fanout", sub_agents=[weather, news])

async def main():
    runner = InMemoryRunner(agent=fanout, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="brief me")])
    async for _ in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        pass
    sess = await runner.session_service.get_session(app_name="a", user_id="u", session_id=s.id)
    print("state:", dict(sess.state))

asyncio.run(main())
```

**Output (real run):**
```
state: {'weather': 'sunny', 'news': 'all quiet'}
```

Both agents ran (concurrently) and each wrote its own key. A common pattern is a `ParallelAgent` (gather) followed by an `LlmAgent` (synthesize) inside a `SequentialAgent` — fan out, then fold the results together.

> ⚠️ **Distinct keys are mandatory.** If two parallel agents share an `output_key`, they race and one clobbers the other. Give each its own key and let a downstream agent combine them.

---

## Fan-out then synthesize

```python
from google.adk.agents import SequentialAgent

synthesizer = LlmAgent(name="synth", model=...,
                       instruction="Combine: weather={weather}, news={news}",
                       output_key="briefing")

pipeline = SequentialAgent(name="brief", sub_agents=[fanout, synthesizer])
# fanout runs weather+news in parallel → synth reads both from state
```

This is the ADK equivalent of LangGraph's `Send` map-reduce ([langgraph 04-3](../../langgraph/04_control_flow/03_send_map_reduce.md)): parallel workers, then a reduce step.

---

## Recap & next

- ✅ `ParallelAgent(sub_agents=[...])` runs sub-agents concurrently, merging outputs into state.
- ✅ Each parallel agent needs a **distinct `output_key`**.
- ✅ Pair with a following `LlmAgent` in a `SequentialAgent` to synthesize the gathered results.
- ✅ Self-check: what breaks if two parallel agents share an `output_key`?

→ Next: **[02-4 · LoopAgent](04_loop_agent.md)**

## Exercises

1. Add a third parallel agent `stocks` (own key), then a synthesizer that reads all three.

<details>
<summary>Solution</summary>

Add `stocks = LlmAgent(..., output_key="stocks")` to the `ParallelAgent`, and make the synthesizer's instruction reference `{weather}`, `{news}`, and `{stocks}`.
</details>
