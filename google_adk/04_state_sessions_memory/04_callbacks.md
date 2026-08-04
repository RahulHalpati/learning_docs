# 04-4 · Callbacks

> **Level:** Intermediate · **Prerequisites:** [02-1 · LlmAgent](../02_agents_and_workflows/01_llm_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

Callbacks are hooks that fire around an agent's lifecycle — before/after the agent, the model call, and each tool call. They're where you put **guardrails** (block a disallowed request), **logging/observability**, **caching**, and **input/output rewriting** — without touching the agent's core logic. Every production ADK agent uses them.

---

## The six hooks

| Callback | Fires | Common use |
|----------|-------|-----------|
| `before_agent_callback` | before the agent runs | setup, access checks |
| `after_agent_callback` | after the agent finishes | cleanup, final logging |
| `before_model_callback` | before each LLM call | prompt guardrails, caching, logging |
| `after_model_callback` | after each LLM response | output filtering, redaction |
| `before_tool_callback` | before a tool runs | argument validation, blocking |
| `after_tool_callback` | after a tool returns | result post-processing |

The key mechanic: **return `None` to proceed normally; return a value to short-circuit** (skip the model/tool and use your value instead). That's what makes callbacks *guardrails*, not just observers.

---

## A `before_model_callback`

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel        # lesson 01-3

log = []
def before_model(callback_context, llm_request):
    log.append(f"about to call model for agent={callback_context.agent_name}")
    return None                            # None → proceed with the real model call

agent = LlmAgent(name="a", model=FakeAdkModel(model="f", responses=["hello world"]),
                 instruction="x", output_key="out",
                 before_model_callback=before_model)

async def main():
    runner = InMemoryRunner(agent=agent, app_name="app")
    s = await runner.session_service.create_session(app_name="app", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="hi")])
    async for _ in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        pass
    print(log)

asyncio.run(main())
```

**Output (real run):**
```
['about to call model for agent=a']
```

The callback fired right before the model call. Return `None` (as here) and the real call proceeds; return an `LlmResponse` instead and you **skip** the model — a cache hit, or a hard "I can't help with that" guardrail.

---

## A guardrail that blocks

```python
from google.adk.models.llm_response import LlmResponse
from google.genai import types

def block_secrets(callback_context, llm_request):
    text = str(llm_request.contents).lower()
    if "password" in text:
        return LlmResponse(content=types.Content(role="model",
                 parts=[types.Part(text="I can't help with credentials.")]))
    return None    # otherwise proceed
```

Because a non-`None` return short-circuits the model, this refuses risky prompts *before* any tokens are spent. The same pattern on `before_tool_callback` validates or blocks tool arguments.

> **Tip:** Callbacks are ADK's main **safety** surface (Section 07 builds on this) and its observability surface (log timings/tokens in before/after model). Keep them fast and side-effect-light — they run on every step.

---

## Recap & next

- ✅ Six callbacks wrap agent/model/tool, before and after each.
- ✅ Return `None` to proceed; return a value to **short-circuit** (guardrail or cache).
- ✅ Use them for guardrails, logging, caching, and I/O rewriting — no change to agent logic.
- ✅ Self-check: how would you make `before_model_callback` act as a response cache?

→ Next: **[05 · Multi-agent systems](../05_multi_agent_systems/README.md)**

## Exercises

1. Write a `before_tool_callback` that blocks a `delete` tool unless `state["confirmed"]` is true.

<details>
<summary>Solution</summary>

```python
def guard(tool, args, tool_context):
    if tool.name == "delete" and not tool_context.state.get("confirmed"):
        return {"error": "deletion not confirmed"}   # non-None → skip the tool
    return None
```
Attach as `before_tool_callback`; the tool runs only when confirmed.
</details>
