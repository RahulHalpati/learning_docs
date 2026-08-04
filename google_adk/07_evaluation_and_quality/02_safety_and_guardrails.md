# 07-2 · Safety & guardrails

> **Level:** Intermediate · **Prerequisites:** [04-4 · Callbacks](../04_state_sessions_memory/04_callbacks.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

An agent that can call tools can cause harm — spend money, delete data, leak secrets. Safety in ADK is layered: **callbacks** block bad inputs/outputs and tool calls, **instructions** constrain behavior, and **human gates** (long-running tools) require approval for the risky stuff. Defense in depth, because any single layer can be bypassed.

---

## Layer 1 — callback guardrails

The primary mechanism, from [04-4](../04_state_sessions_memory/04_callbacks.md): a callback returns a non-`None` value to **short-circuit**. Block a disallowed prompt before it costs tokens:

```python
from google.adk.models.llm_response import LlmResponse
from google.genai import types

def input_guard(callback_context, llm_request):
    text = str(llm_request.contents).lower()
    if "password" in text or "ssn" in text:
        return LlmResponse(content=types.Content(role="model",
                 parts=[types.Part(text="I can't help with sensitive credentials.")]))
    return None                      # otherwise proceed
# LlmAgent(..., before_model_callback=input_guard)
```

And validate/deny tool calls with `before_tool_callback`:

```python
def tool_guard(tool, args, tool_context):
    if tool.name == "delete_record" and not tool_context.state.get("approved"):
        return {"error": "deletion requires approval"}   # non-None → tool is skipped
    return None
```

---

## Layer 2 — a dedicated safety agent

A common pattern is a cheap, fast **guard agent** (or model) that screens input/output for policy violations — either as a `before_agent_callback`, or a first step in a `SequentialAgent` that can escalate/stop. Keep it small and strict; it runs on every request.

---

## Layer 3 — human approval for irreversible actions

For anything you can't undo, don't rely on the model's judgment — require a human. A `LongRunningFunctionTool` ([03-2](../03_tools/02_builtin_and_agent_tools.md)) pauses the run until a person approves, the same role `interrupt()` plays in LangGraph. Wire *money movement, deletions, external sends* behind one.

---

## Layer 4 — least privilege & instructions

- Give each agent only the tools it needs (an agent with no `delete` tool can't delete).
- Constrain scope in the `instruction` ("only answer questions about our product; refuse others").
- Scope state with prefixes ([04-1](../04_state_sessions_memory/01_sessions_and_state.md)) so agents can't read data they shouldn't.

Instructions alone are *not* a security boundary (they can be jailbroken) — that's why callbacks and least-privilege tooling matter. Layer them.

---

## Defense in depth

| Layer | Stops |
|-------|-------|
| Callback guardrails | bad prompts, disallowed tool calls |
| Guard agent/model | policy violations in input/output |
| Human approval (long-running tool) | irreversible actions |
| Least privilege + instructions | actions the agent shouldn't be *able* to take |

No layer is sufficient alone; together they make an agent safe enough to trust with real actions.

---

## Recap & next

- ✅ Callbacks are the core guardrail: return non-`None` to block a model call or tool.
- ✅ Add a guard agent, human approval for irreversible actions, and least-privilege tooling.
- ✅ Instructions constrain but don't *secure* — layer real controls.
- ✅ Self-check: which layer protects against an irreversible action the model wrongly decides to take?

→ Next: **[08 · Deployment & A2A](../08_deployment_and_a2a/README.md)**

## Exercises

1. Add both an `input_guard` (`before_model_callback`) and a `tool_guard` (`before_tool_callback`) to an agent; test that a "password" prompt and an unapproved `delete` are both blocked.

<details>
<summary>Solution</summary>

Attach the two callbacks above. A prompt containing "password" returns the canned refusal (model skipped); a `delete_record` call without `state["approved"]` returns the error (tool skipped). Set `state["approved"]=True` to let deletion through.
</details>
