# 01-4 · Your first agent

> **Level:** Beginner · **Prerequisites:** [01-3 · Environment & offline models](03_environment_and_offline_models.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

Time to build an `LlmAgent` deliberately and look at what comes out: the **event stream** and the **session state**. Understanding those two outputs is the key to everything else — tools, multi-agent, and debugging all show up as events and state.

---

## Build, run, inspect

We use the fake model so the output is exact and offline. `output_key="answer"` tells ADK to save the agent's final text into `session.state["answer"]`.

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel        # from lesson 01-3

agent = LlmAgent(
    name="assistant",
    model=FakeAdkModel(model="f", responses=["Paris is the capital of France."]),
    instruction="Answer the user's question.",
    output_key="answer",                   # ← save final text into session state
)

async def main():
    runner = InMemoryRunner(agent=agent, app_name="a")
    session = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="Capital of France?")])

    async for event in runner.run_async(user_id="u", session_id=session.id, new_message=msg):
        text = event.content.parts[0].text if event.content and event.content.parts else None
        print(f"event author={event.author} final={event.is_final_response()} text={text}")

    sess = await runner.session_service.get_session(app_name="a", user_id="u", session_id=session.id)
    print("session.state:", dict(sess.state))

asyncio.run(main())
```

**Output (real run):**
```
event author=assistant final=True text=Paris is the capital of France.
```
```
session.state: {'answer': 'Paris is the capital of France.'}
```

Two things to notice:

1. **Events carry an `author`** (which agent produced them) and an `is_final_response()` flag. Here there's one event — the assistant's answer. With tools or multiple agents you'd see several (a tool call, a tool result, then the final answer).
2. **`output_key` wrote to state.** Because we set `output_key="answer"`, the final text landed in `session.state["answer"]` — the primary way agents pass results to each other ([Section 04](../04_state_sessions_memory/README.md)).

---

## The three ways to run an agent

You've used the programmatic runner. ADK also ships CLIs (covered in [Section 06](../06_runtime_events_streaming/README.md)):

| How | Command / code | Use |
|-----|----------------|-----|
| Programmatic | `Runner.run_async(...)` | in your app / tests (what we use) |
| Interactive CLI | `adk run <path>` | chat with an agent in the terminal |
| Web UI | `adk web <path>` | a local chat + trace UI |
| API server | `adk api_server <path>` | expose it over HTTP |

All four run the *same* agent object — the runner is just how you drive it.

---

## Recap & next

- ✅ An `LlmAgent` needs a `name`, a `model`, and an `instruction`; `output_key` saves its result to state.
- ✅ A run yields **events** (each with an `author` and a final flag); the answer is the final event.
- ✅ Results flow between agents through **`session.state`**.
- ✅ Self-check: where did "Paris…" end up besides the event stream, and why?

→ Next: **[02 · Agents & workflows](../02_agents_and_workflows/README.md)**

## Exercises

1. Add a second `LlmAgent` and pass the first's `output_key` into the second's instruction with a `{answer}` placeholder. (Preview of state injection — full treatment in Section 04.)

<details>
<summary>Solution</summary>

Set agent 1 `output_key="answer"`; agent 2 `instruction="Rephrase this nicely: {answer}"`. When run in a `SequentialAgent`, ADK substitutes `{answer}` from `session.state` before calling agent 2's model. (With the *fake* model the substitution still happens in the request; the fake just returns canned text.)
</details>
