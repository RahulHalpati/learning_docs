# 03-3 · Prebuilt agents (`create_react_agent` / `create_agent`)

> **Level:** Intermediate · **Prerequisites:** [03-2 · Tools & the ReAct loop](02_tools_and_react.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langgraph-prebuilt 1.1.0, langchain-ollama 1.1.0, Ollama qwen2.5:0.5b)

## Why this matters

You just built the ReAct loop by hand. 90% of the time you don't need to — LangGraph ships a prebuilt agent that wires `agent → tools → agent` for you, with memory, a system prompt, structured output, and hooks. Knowing it exists (and its knobs) saves you 20 lines every time; knowing *when to drop back to a custom graph* keeps you out of trouble.

---

## ⚠️ It moved in v1

The prebuilt agent has a new home in the 1.x era:

```python
# LangGraph ≤ 0.x and still-working-but-deprecated in 1.x:
from langgraph.prebuilt import create_react_agent

# LangGraph 1.x preferred location (uv pip install langchain):
from langchain.agents import create_agent
```

Importing `create_react_agent` from `langgraph.prebuilt` on 1.x prints a `LangGraphDeprecatedSinceV10` warning pointing you at `langchain.agents.create_agent`. The two share the same core idea; `create_agent` is the actively-developed one. This course verifies against `langgraph.prebuilt.create_react_agent` (no extra install needed); the API shown maps directly onto `create_agent`.

---

## The one-liner

The prebuilt agent needs a model that supports **tool calling** (`bind_tools`). `ChatOpenAI` does; this run used a local Ollama model to show it works there too:

```python
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Weather in {city}: 22C, partly cloudy"

agent = create_react_agent(
    model=ChatOllama(model="qwen2.5:0.5b", temperature=0),
    tools=[get_weather],
)

out = agent.invoke({"messages": [
    {"role": "user", "content": "What is the weather in London? Use the tool."}]})
for m in out["messages"]:
    print(m.type, "|", (m.content[:60] if m.content else ""))
```

**Output (real run, `LANGGRAPH_LLM=ollama`):**
```
human | What is the weather in London? Use the tool.
ai |
tool | Weather in London: 22C, partly cloudy
ai | The current weather in London is 22°C with partly cloudy skies.
```

That's the *entire* ReAct loop from 03-2 — model, `ToolNode`, `tools_condition`, and the edges — in three lines.

---

## The knobs that matter

`create_react_agent` / `create_agent` take far more than model + tools:

| Parameter | What it does |
|-----------|--------------|
| `prompt` | System prompt — a string, or a callable that builds messages from state |
| `checkpointer` | Adds memory (same `thread_id` story as 03-1) |
| `response_format` | A Pydantic model → the agent returns **structured** output in `state["structured_response"]` |
| `state_schema` | Use a custom state (extra fields beyond `messages`) |
| `pre_model_hook` | A node run *before* the LLM each turn — e.g. trim/summarize history ([05-4](../05_persistence_and_memory/04_message_management.md)) |
| `store` | Long-term memory across threads ([05-3](../05_persistence_and_memory/03_long_term_memory_store.md)) |

Structured output, for example:

```python
from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    summary: str

agent = create_react_agent(
    model=ChatOllama(model="qwen2.5:0.5b", temperature=0),
    tools=[get_weather],
    prompt="You are a concise weather assistant.",
    response_format=WeatherReport,     # → out["structured_response"] is a WeatherReport
)
```

> **Tip:** Structured output and reliable tool selection are where small local models struggle. If `qwen2.5:0.5b` picks the wrong tool or malforms JSON, that's the *model*, not your graph — try `qwen2:7b` or a hosted model. When in doubt, run the same graph on `gpt-4o-mini` to separate wiring bugs from model quality.

---

## Prebuilt vs custom graph

| Use the prebuilt agent | Build a custom graph |
|------------------------|----------------------|
| Standard single-agent ReAct | Multiple agents / supervisor / swarm ([07](../07_multi_agent/README.md)) |
| One tool loop | Custom routing, quality gates, self-correction ([08](../08_real_world/README.md)) |
| You want memory/structured output fast | Human-in-the-loop mid-graph, `Send` fan-out, subgraphs |

Start with the prebuilt agent; graduate to a custom graph the moment your control flow stops being "just a tool loop".

---

## Recap & next

- ✅ The prebuilt agent wires the whole ReAct loop; in v1 prefer `langchain.agents.create_agent` (the `langgraph.prebuilt` import is deprecated).
- ✅ It needs a **tool-calling** model (`bind_tools`) — `gpt-4o-mini`, or a capable local model like `qwen2.5`.
- ✅ Knobs: `prompt`, `checkpointer`, `response_format`, `state_schema`, `pre_model_hook`, `store`.
- ✅ Drop to a custom graph when control flow outgrows a single tool loop.
- ✅ Self-check: what must a model support for `create_react_agent` to work with it?

→ Next: **[03-4 · The functional API](04_functional_api.md)**

## Exercises

1. Add a `checkpointer=InMemorySaver()` and a `thread_id`, then ask a follow-up ("and tomorrow?") to confirm the prebuilt agent remembers context.

<details>
<summary>Solution</summary>

```python
from langgraph.checkpoint.memory import InMemorySaver
agent = create_react_agent(model=..., tools=[get_weather], checkpointer=InMemorySaver())
cfg = {"configurable": {"thread_id": "w1"}}
agent.invoke({"messages": [{"role": "user", "content": "Weather in London?"}]}, cfg)
agent.invoke({"messages": [{"role": "user", "content": "And tomorrow?"}]}, cfg)
```
The second turn sees the first via the checkpointer — no manual history plumbing.
</details>
