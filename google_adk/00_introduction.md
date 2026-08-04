# 00 · Introduction to Google ADK

> **Level:** Beginner · **Prerequisites:** basic Python; an LLM API concept helps. LangGraph experience optional.
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0, litellm 1.93.0, Python 3.10)

Welcome to **Google's Agent Development Kit (ADK)** — an open-source, code-first Python toolkit for building, evaluating, and deploying AI agents. This course teaches ADK from scratch and, like the rest of this collection, runs **entirely offline**: a local Ollama model via LiteLLM does the thinking, no Gemini or Vertex key required.

---

## Why this matters

Google built ADK to be the framework behind its own agent products, then open-sourced it. It's model-agnostic (first-class Gemini, anything else via LiteLLM), deploys natively to Google Cloud, and ships an unusually complete toolbox — workflow agents, a tool ecosystem, sessions/memory, evaluation, and the **A2A** protocol for agents to talk to each other. If you work on Google Cloud or want a batteries-included agent framework, ADK is a first-class choice alongside LangGraph.

---

## What is ADK?

**In one sentence:** ADK lets you build an agent by **composing agents** — an `LlmAgent` that reasons and calls tools, wrapped in workflow agents (`Sequential`, `Parallel`, `Loop`) that orchestrate them — and run them through a **runtime** of sessions, events, and runners.

> **Analogy — a film crew.** An `LlmAgent` is a specialist (a researcher, a writer). A `SequentialAgent` is the shot list: do these in order. A `ParallelAgent` is a second-unit shooting simultaneously. A `LoopAgent` is "do another take until it's good". The **runner** is the director calling action and collecting the footage (events); the **session** is the continuity log.

---

## ADK vs LangGraph in one breath

If you did the [LangGraph](../langgraph/) course: LangGraph hands you a graph (`state → nodes → edges`) that you *wire*; ADK hands you agents that you *compose*. Both do multi-agent, tools, memory, and human oversight. [Section 01-2](01_foundations/02_langgraph_vs_adk.md) is a full bridge with a concept-mapping table. If you're new to both, don't worry about the comparison yet.

---

## Set up (offline, no API key)

```bash
python -m venv .venv && source .venv/bin/activate
pip install "google-adk==2.5.0" "litellm==1.93.0"
# for real local generation:
#   install Ollama (https://ollama.com), then:
ollama pull qwen2.5:0.5b
```

### Your first agent

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

agent = LlmAgent(
    name="greeter",
    model=LiteLlm(model="ollama_chat/qwen2.5:0.5b"),   # local model, no key
    instruction="You are concise. Reply in one short sentence.",
)

async def main():
    runner = InMemoryRunner(agent=agent, app_name="demo")
    session = await runner.session_service.create_session(app_name="demo", user_id="u1")
    msg = types.Content(role="user", parts=[types.Part(text="Say hello to Ada.")])
    async for event in runner.run_async(user_id="u1", session_id=session.id, new_message=msg):
        if event.is_final_response():
            print(event.content.parts[0].text)

asyncio.run(main())
```

**Output (real run, via Ollama):**
```
Hello Ada, welcome!
```

You just built an agent: defined an `LlmAgent` with a model and instruction, ran it through an `InMemoryRunner` and a session, and read the final response from the **event stream**. Every ADK program is that shape — more agents, more tools, but the same runner/session/events loop.

> **Note:** ADK is **async-first** — `run_async` yields `Event`s. We'll unpack runners and events in [Section 06](06_runtime_events_streaming/README.md); for now, "run the agent, read the final event" is enough.

---

## Key terms (one line each)

- **`LlmAgent`** (a.k.a. `Agent`) — an agent powered by an LLM, with an instruction and optional tools.
- **Workflow agent** — `SequentialAgent` / `ParallelAgent` / `LoopAgent`: orchestrate sub-agents deterministically.
- **Tool** — a capability an agent can call (a Python function, an OpenAPI op, an MCP tool).
- **Session** — one conversation; holds **state** and the event history.
- **State** — a dict on the session; agents read/write it (often via `output_key`).
- **Event** — one thing that happened in a run (a model response, a tool call/result).
- **Runner** — drives an agent over a session, yielding events.
- **A2A** — Agent-to-Agent protocol: agents (even across frameworks) calling each other.

---

## Common misconceptions

| ❌ Misconception | ✅ Reality |
|-----------------|-----------|
| "ADK is Gemini-only" | Model-agnostic via LiteLLM — this course uses local Ollama |
| "ADK needs Google Cloud" | Runs fully local; Cloud is a deployment *option* |
| "It's just LangGraph with different names" | Different model — compose agents, not wire a graph — with its own runtime, eval, and A2A |
| "Workflow agents need an LLM" | `Sequential`/`Parallel`/`Loop` are deterministic orchestrators; only `LlmAgent`s call a model |

---

## Recap & next

- ✅ ADK = **compose agents** (`LlmAgent` + workflow agents) run through a **runtime** (sessions, events, runners).
- ✅ It's model-agnostic and cloud-native, but runs offline via LiteLLM → Ollama.
- ✅ You ran a first agent and read its final response from the event stream — no API key.
- ✅ Self-check: in the first-agent code, what yields the response — the agent, the runner, or the session?

→ Next: **[01 · Foundations](01_foundations/README.md)**
