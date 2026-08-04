# 06-1 · Runners & events

> **Level:** Intermediate · **Prerequisites:** [01-4 · Your first agent](../01_foundations/04_your_first_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

The **Runner** is the engine: it loads a session, drives the agent, coordinates the model/tools/services, and hands you a stream of **Events** — one per thing that happens. Reading events is how you observe, debug, and build UIs on top of an agent. Everything ADK does surfaces as events.

---

## The runner drives; events flow

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel        # lesson 01-3

agent = LlmAgent(name="assistant",
                 model=FakeAdkModel(model="f", responses=["Paris is the capital of France."]),
                 instruction="answer", output_key="answer")

async def main():
    runner = InMemoryRunner(agent=agent, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="Capital of France?")])
    async for event in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        print(f"author={event.author} final={event.is_final_response()} "
              f"text={event.content.parts[0].text if event.content else None}")

asyncio.run(main())
```

**Output (real run):**
```
author=assistant final=True text=Paris is the capital of France.
```

`run_async` is an **async generator** of `Event`s. Iterate it to see the run unfold in real time.

---

## Anatomy of an Event

| Field | Meaning |
|-------|---------|
| `author` | which agent produced it (routing/handoffs show up here) |
| `content` | the message parts — text, `function_call`, `function_response` |
| `is_final_response()` | True for the user-facing answer of a turn |
| `actions` | side-effects: `escalate`, `transfer_to_agent`, state deltas |
| `partial` | True for streaming chunks (06-2) |

A single tool-using turn produces several events: the model's `function_call`, the tool's `function_response`, then the final text — exactly what you saw in [03-1](../03_tools/01_function_tools.md). Filtering on `is_final_response()` gives you just the answer; reading *all* events gives you the full trace.

---

## `InMemoryRunner` vs `Runner`

- **`InMemoryRunner`** bundles in-memory session/memory/artifact services — one line, zero setup, what most lessons use.
- **`Runner`** lets you inject specific services (a durable `SessionService`, a `MemoryService`, an `ArtifactService`) — what you use in production and when wiring memory ([04-2](../04_state_sessions_memory/02_memory_service.md)).

Both drive the agent identically and yield the same events; they differ only in which services back them.

---

## Recap & next

- ✅ The `Runner` drives an agent over a session and yields `Event`s via `run_async` (async generator).
- ✅ Events carry `author`, `content` (text/tool call/tool result), `is_final_response()`, and `actions`.
- ✅ `InMemoryRunner` for quick/offline; `Runner` to inject production services.
- ✅ Self-check: how many events would a single tool-using turn produce, and what are they?

→ Next: **[06-2 · Streaming & Live](02_streaming_and_live.md)**

## Exercises

1. Give a tool-using agent (Ollama, from 03-1) a question and print *every* event's `author` and part types to see the full turn.

<details>
<summary>Solution</summary>

Iterate `run_async` without filtering on `is_final_response()`, and for each event print `event.author` and, for each part, whether it's `text`/`function_call`/`function_response`. You'll see the call → result → answer sequence.
</details>
