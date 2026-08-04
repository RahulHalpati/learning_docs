# 01-2 · LangGraph vs Google ADK — pick your engine

> **Level:** Beginner · **Time:** 25 min

You asked to compare **LangGraph** and **Google's Agent Development Kit (ADK)**
before committing. Good instinct — the framework shapes how you think. This
module gives you an honest side-by-side, sketches the *same* video pipeline in
both, and explains why this course runs on LangGraph. Everything you learn
transfers if you later switch.

> Want to go deeper on either? There are full hands-on courses for both:
> **[LangGraph](../../langgraph/)** and **[Google ADK](../../google_adk/)** — the
> latter's [LangGraph↔ADK bridge](../../google_adk/01_foundations/02_langgraph_vs_adk.md)
> is a framework-level version of this comparison, and both ship the *same*
> offline research-assistant capstone for a true side-by-side.

---

## The two, in one sentence each

- **LangGraph** — from the LangChain team: you build an explicit **graph** of
  *state → nodes → edges*. You decide exactly what runs next. Great for
  workflows with clear stages and loops.
- **Google ADK** — Google's open-source **agent framework**: you compose
  **agents** and **workflow agents** (`Sequential`, `Parallel`, `Loop`). Tuned for
  Gemini and Vertex AI, but model-agnostic via LiteLLM.

Both are Python-first (ADK also has Java; LangGraph also has JS), both are open
source, both do multi-agent and human-in-the-loop. They overlap a lot.

---

## Side by side

| Dimension | **LangGraph** | **Google ADK** |
|---|---|---|
| Maintainer | LangChain | Google |
| Core abstraction | `StateGraph`: state + nodes + (conditional) edges | `Agent` + workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) |
| Control style | **Explicit** — you draw the graph | **Compositional** — you nest agents |
| Model support | Fully model-agnostic (any LangChain chat model) | Model-agnostic via LiteLLM, **first-class Gemini/Vertex** |
| State / memory | `TypedDict` state + pluggable **checkpointers** | Session + state services (in-memory, Vertex) |
| Human-in-the-loop | **First-class**: `interrupt_before/after`, resume from checkpoint | Supported via callbacks/tooling |
| Streaming | Token + step streaming built in | Supported |
| Deployment | LangGraph Platform / Studio, or self-host | **Vertex AI Agent Engine** (managed), or self-host |
| Ecosystem / tutorials | **Largest** in the agent space | Newer (2025), growing fast |
| Sweet spot | Explicitly-staged workflows with loops & gates | Google-Cloud-native multi-agent systems |

> Versions move fast — treat capability rows as "true at time of writing (2026)",
> not eternal. The *shapes* of the two frameworks are the durable part.

---

## The same pipeline, sketched in both

**Our pipeline is a fixed sequence with one optional gate** — research → script →
voiceover → visuals → assemble → metadata. Watch how each framework expresses
"do these in order."

### LangGraph (what this course uses)

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(VideoState)
builder.add_node("researcher", researcher)
builder.add_node("scriptwriter", scriptwriter)
builder.add_node("voiceover", voiceover)
# ...
builder.add_edge(START, "researcher")
builder.add_edge("researcher", "scriptwriter")
builder.add_edge("scriptwriter", "voiceover")
# ...
graph = builder.compile(interrupt_before=["voiceover"])   # the review gate
```

You **see the wiring**. Adding a "loop back to scriptwriter if the review fails"
is one `add_conditional_edges` call. State is an explicit `TypedDict` you control.

### Google ADK (the equivalent)

```python
from google.adk.agents import SequentialAgent, LlmAgent

researcher   = LlmAgent(name="researcher",   model="gemini-2.0-flash", instruction="...")
scriptwriter = LlmAgent(name="scriptwriter", model="gemini-2.0-flash", instruction="...")
# media steps would be custom (non-LLM) agents/tools

pipeline = SequentialAgent(
    name="faceless_studio",
    sub_agents=[researcher, scriptwriter, voiceover, visuals, assembler, metadata],
)
```

You **compose** agents; `SequentialAgent` runs them in order and threads a shared
session state. A review loop uses a `LoopAgent` with an exit condition. It's
elegant when your steps are mostly LLM agents and you're on Google Cloud.

> ⚠️ The ADK snippet is illustrative (API names shift between ADK releases) — it's
> here to show the *mental model*, not to copy-paste.

---

## Why this course picks LangGraph

Not because ADK is bad — it's genuinely good, especially on Vertex AI. For **this
project and your situation**:

1. **You're already learning LangChain.** LangGraph is the same team, the same
   chat-model objects, the same prompt style. Zero context-switch — the natural
   next step your [collection roadmap](../../README.md) already points to.
2. **A video pipeline is an explicit graph.** Fixed stages + a review loop map
   1:1 onto nodes and conditional edges. Seeing the wiring *is* the learning.
3. **The review gate is first-class.** `interrupt_before=["voiceover"]` gives you
   the "approve before rendering/publishing" pause with one argument — the single
   most important feature for doing faceless YouTube responsibly.
4. **No cloud lock-in to learn.** It runs on your laptop with Ollama or a fake
   model. ADK shines most when paired with Vertex AI, which is more to set up than
   a beginner project needs.
5. **Biggest tutorial ecosystem.** When you get stuck at 1am, there's more
   LangGraph material to search.

**When you'd reach for ADK instead:** you're building on Google Cloud, you want
managed deployment via Vertex AI Agent Engine, or you're standardising on Gemini
across a team. The concepts you learn here (shared state, sequential steps, loops,
human gates) carry straight over.

---

## Recap

- LangGraph = **explicit graph** (state/nodes/edges); ADK = **composed agents**
  (`Sequential`/`Parallel`/`Loop`). Both are capable, model-agnostic, open source.
- For a staged pipeline with a review gate, on a laptop, coming from LangChain,
  **LangGraph is the lower-friction, higher-transfer choice** — so that's what we
  use.
- The mental models overlap enough that switching later is cheap.

## Self-check

1. What is LangGraph's core abstraction, and what is ADK's?
2. Give one concrete reason a beginner coming from LangChain benefits from
   LangGraph here.
3. Name a situation where you'd genuinely prefer Google ADK.

<details>
<summary>Answers</summary>

1. LangGraph: an explicit **`StateGraph`** of state + nodes + edges. ADK:
   **agents** composed with workflow agents (`SequentialAgent`, `ParallelAgent`,
   `LoopAgent`).
2. Same team/objects as LangChain (chat models, prompts) → no context switch; and
   the graph wiring is visible, which is good for *learning* how orchestration works.
3. You're building on Google Cloud / Vertex AI, want managed agent deployment, or
   are standardising on Gemini across a team.

</details>

---

**Next → [01-3 · Environment & providers](03_environment_and_providers.md)**
