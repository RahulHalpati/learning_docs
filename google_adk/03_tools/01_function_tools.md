# 03-1 · Function tools

> **Level:** Beginner · **Prerequisites:** [02-1 · LlmAgent](../02_agents_and_workflows/01_llm_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0, litellm 1.93.0, Ollama qwen2.5:0.5b)

## Why this matters

The most common tool is a plain Python function. ADK reads its **signature and docstring** to tell the model what the tool does and how to call it — so a well-documented function *is* a tool. This is how agents reach the real world: calculators, database lookups, API calls.

---

## A function is a tool

Pass a function in `tools=[...]`; ADK auto-wraps it. The model decides when to call it (so this uses a real tool-calling model — Ollama):

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

def add(a: int, b: int) -> dict:
    """Add two integers and return the sum."""     # docstring → tool description
    return {"sum": a + b}                          # dict return → structured tool result

agent = LlmAgent(
    name="calc",
    model=LiteLlm(model="ollama_chat/qwen2.5:0.5b"),
    instruction="Use the add tool to add numbers, then state the result.",
    tools=[add],
)

async def main():
    runner = InMemoryRunner(agent=agent, app_name="a")
    s = await runner.session_service.create_session(app_name="a", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="What is 21 + 21? Use the tool.")])
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        for p in (e.content.parts if e.content else []):
            if p.function_call:     print("TOOL CALL:", p.function_call.name, dict(p.function_call.args))
            if p.function_response: print("TOOL RESULT:", p.function_response.response)
            if p.text and e.is_final_response(): print("FINAL:", p.text)

asyncio.run(main())
```

**Output (real run, via Ollama):**
```
TOOL CALL: add {'a': 21, 'b': 21}
TOOL RESULT: {'sum': 42}
FINAL: The sum of 21 + 21 is 42.
```

The event stream shows the whole tool round-trip: the model emitted a **function call**, ADK ran `add` and fed back a **function response**, and the model produced the **final** answer. That's the ADK equivalent of LangGraph's `ToolNode` loop ([langgraph 03-2](../../langgraph/03_building_graphs/02_tools_and_react.md)).

---

## Conventions that matter

- **Type hints** define the tool's parameters — always annotate them.
- **The docstring** becomes the tool's description; write it for the *model* ("Add two integers…").
- **Return a `dict`** — a structured result is clearer to the model than a bare string.

---

## `ToolContext` — reach into the run

Add a `tool_context: ToolContext` parameter and your tool can read/write **session state**, request an **escalation**, or record **artifacts**:

```python
from google.adk.tools import ToolContext

def remember(fact: str, tool_context: ToolContext) -> dict:
    """Store a fact in session state."""
    facts = tool_context.state.get("facts", [])
    tool_context.state["facts"] = facts + [fact]
    return {"stored": fact}
```

ADK injects `tool_context` automatically (the model never sees it as a parameter). This is how tools participate in state and control flow rather than being pure functions.

> **Tip:** Tool selection quality depends on the model. `qwen2.5:0.5b` handles a single clear tool well; for many tools or subtle choices, a larger/hosted model does better. Your *wiring* is verifiable regardless.

---

## Recap & next

- ✅ A typed, docstringed Python function in `tools=[...]` becomes a tool automatically.
- ✅ The tool round-trip appears in events: function call → function response → final answer.
- ✅ Add `tool_context: ToolContext` to read/write state, escalate, or save artifacts.
- ✅ Self-check: what two parts of a function does ADK use to describe the tool to the model?

→ Next: **[03-2 · Built-in & agent tools](02_builtin_and_agent_tools.md)**

## Exercises

1. Add a `multiply` tool alongside `add` and ask a question requiring both; watch two tool calls in the events.

<details>
<summary>Solution</summary>

Add `def multiply(a: int, b: int) -> dict: """Multiply two integers.""" return {"product": a*b}` to `tools`, then ask "add 2 and 3, then multiply the result by 4". The events show an `add` call, then a `multiply` call, then the final answer (model-dependent).
</details>
