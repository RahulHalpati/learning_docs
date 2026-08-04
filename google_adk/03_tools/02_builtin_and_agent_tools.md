# 03-2 · Built-in & agent tools

> **Level:** Intermediate · **Prerequisites:** [03-1 · Function tools](01_function_tools.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

You don't write every tool yourself. ADK ships **built-in tools** (like Google Search and code execution), lets you expose a whole **agent as a tool** (`AgentTool`), and supports **long-running tools** for slow or human-gated work. These turn agents into composable building blocks.

---

## Built-in tools

ADK provides ready-made tools you drop into `tools=[...]`:

```python
from google.adk.tools import google_search      # verified import

# agent = LlmAgent(name="searcher", model=..., tools=[google_search])
```

`google_search` (grounded web search) and the code-execution tool are the headline ones. Built-ins often require a Gemini/Vertex model and network access, so they're not part of the offline path — but the *wiring* is identical to any other tool: add it to the list.

---

## An agent as a tool: `AgentTool`

Wrap an `LlmAgent` in `AgentTool` and it becomes callable *by another agent*. This is how you reuse a specialist without giving up control to full delegation:

```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

summarizer = LlmAgent(name="summarizer", model=...,
                      instruction="Summarize the input in one sentence.")

main_agent = LlmAgent(
    name="assistant", model=...,
    instruction="Use the summarizer tool when asked to condense text.",
    tools=[AgentTool(agent=summarizer)],       # ← the summarizer is now a tool
)
```

The difference from delegation (Section 05): with `AgentTool`, the caller stays in charge and gets the sub-agent's result *as a tool response*; with sub-agent transfer, control *moves* to the other agent. Use `AgentTool` for "consult a specialist and continue".

---

## Long-running tools

Some tools don't return immediately — they kick off work that finishes later (a human approval, a batch job). `LongRunningFunctionTool` models this: the tool returns a "pending" signal, the agent run can pause, and the result is supplied when ready.

```python
from google.adk.tools import LongRunningFunctionTool

def request_approval(amount: float) -> dict:
    """Ask a human to approve a refund. Resolves later."""
    return {"status": "pending", "amount": amount}

approval_tool = LongRunningFunctionTool(func=request_approval)
```

This is ADK's primary **human-in-the-loop** mechanism: the long-running tool is the pause point, and your app supplies the outcome to resume — analogous to LangGraph's `interrupt()` ([langgraph 06-1](../../langgraph/06_human_in_the_loop/01_interrupt_and_resume.md)).

---

## Which tool type?

| Need | Use |
|------|-----|
| Call your own code | function tool (03-1) |
| Web search / code exec | built-in tool |
| Reuse a specialist agent, keep control | `AgentTool` |
| Hand control to a specialist | sub-agent transfer ([Section 05](../05_multi_agent_systems/README.md)) |
| Slow / human-gated step | `LongRunningFunctionTool` |
| An external API by spec | OpenAPI toolset (03-3) |
| A tool server | MCP toolset (03-4) |

---

## Recap & next

- ✅ Built-in tools (e.g. `google_search`) drop into `tools=[...]` like any other.
- ✅ `AgentTool(agent=...)` exposes an agent *as a tool* — caller keeps control.
- ✅ `LongRunningFunctionTool` models slow/human-gated steps — ADK's HITL pause.
- ✅ Self-check: when do you use `AgentTool` vs handing control off via transfer?

→ Next: **[03-3 · OpenAPI tools](03_openapi_tools.md)**

## Exercises

1. Wrap the `summarizer` above in an `AgentTool` and give it to a main agent; describe (in the main agent's instruction) when it should call it.

<details>
<summary>Solution</summary>

`tools=[AgentTool(agent=summarizer)]` plus an instruction like "When the user gives you long text and asks for a summary, call the summarizer tool." The main agent now consults the specialist and continues with its result.
</details>
