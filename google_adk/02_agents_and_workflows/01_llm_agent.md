# 02-1 · LlmAgent

> **Level:** Beginner · **Prerequisites:** [01-4 · Your first agent](../01_foundations/04_your_first_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

The `LlmAgent` is the only agent that thinks — it's where reasoning, tool-calling, and output shaping happen. Everything else in ADK orchestrates `LlmAgent`s. Its configuration options are the dials you'll turn most.

---

## The core fields

```python
from google.adk.agents import LlmAgent
from fake_model import FakeAdkModel        # lesson 01-3

agent = LlmAgent(
    name="researcher",                     # unique id; also the event author
    model=FakeAdkModel(model="f", responses=["..."]),   # or LiteLlm("ollama_chat/...")
    instruction="You research topics and list key facts.",  # the system prompt
    description="Finds facts about a topic.",  # used by OTHER agents to decide delegation
    output_key="research",                 # save final text into session.state["research"]
)
```

| Field | Purpose |
|-------|---------|
| `name` | unique identifier; appears as the event `author` |
| `model` | the LLM (fake / LiteLlm / Gemini) |
| `instruction` | the agent's system prompt; may reference `{state_key}` placeholders |
| `description` | a one-liner other agents read when deciding whether to delegate here |
| `output_key` | session-state key to store the agent's final response |
| `tools` | list of tools it may call ([Section 03](../03_tools/README.md)) |
| `output_schema` | a Pydantic model for **structured** output |

---

## Instruction templating

An instruction can pull values from session state with `{key}` — ADK substitutes them before calling the model:

```python
writer = LlmAgent(
    name="writer",
    model=...,
    instruction="Write a short report using these findings: {research}",
    output_key="report",
)
```

When `writer` runs after a `researcher` that set `output_key="research"`, `{research}` is replaced by the stored findings. This is how a pipeline threads data through — no manual plumbing. (You'll see it fire in [02-2](02_sequential_agent.md).)

> **Tip:** `description` matters in multi-agent systems: a coordinator's LLM reads sub-agents' descriptions to pick who handles a request ([Section 05](../05_multi_agent_systems/README.md)). Write it as "what this agent is for", not "how it works".

---

## Structured output

Set `output_schema` to a Pydantic model and the agent returns validated, typed output instead of free text — useful when a downstream step needs fields, not prose:

```python
from pydantic import BaseModel

class Facts(BaseModel):
    topic: str
    facts: list[str]

agent = LlmAgent(name="extractor", model=..., output_schema=Facts, output_key="facts")
# session.state["facts"] becomes a dict matching the Facts schema
```

> **Note:** structured output needs a model that can follow the schema. Small local models may not comply reliably — a place where Gemini or a larger model earns its keep. Your *orchestration* is still verifiable with the fake model.

---

## Recap & next

- ✅ `LlmAgent` = `name` + `model` + `instruction`, plus `output_key`, `description`, `tools`, `output_schema`.
- ✅ Instructions template session state with `{key}`; `output_key` writes results back to state.
- ✅ `description` drives delegation; `output_schema` gives structured output.
- ✅ Self-check: which field lets a coordinator decide to route a task to this agent?

→ Next: **[02-2 · SequentialAgent](02_sequential_agent.md)**

## Exercises

1. Build one `LlmAgent` with `output_key="summary"` and confirm (via `get_session`) the text lands in `session.state["summary"]`.

<details>
<summary>Solution</summary>

Same shape as [01-4](../01_foundations/04_your_first_agent.md) with `output_key="summary"`; after running, `dict(sess.state)` shows `{'summary': '<the response>'}`.
</details>
