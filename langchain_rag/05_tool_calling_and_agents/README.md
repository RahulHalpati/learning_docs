# Section 05 · Tool calling & agents

> **Prerequisites:** [Section 03 · RAG fundamentals](../03_rag_fundamentals/README.md). Section 04 is helpful but not required.
> **Time:** ~4–6 hours.

Until now your RAG pipeline has been a **fixed track**: every question runs retrieve → prompt → answer, in that exact order, every time. This section adds the piece that makes modern LLM apps feel *smart*: **tool calling** — letting the model decide, on its own, to *run code* (do math, fetch a web page, **search your documents**) and use the result in its answer. Chain those decisions together and you have an **agent**.

The headline payoff for RAG: instead of *always* retrieving, the model retrieves **only when it needs to** — this is **agentic RAG**, and it's how you'd build an assistant that can search your docs, look something up on the web, *and* just say hello, all in one.

> ⚠️ **This section needs a tool-capable model.** Tool calling requires a model trained for it — a capable local model like **`qwen2`** via Ollama, or a hosted **Claude / OpenAI-compatible** model. The zero-setup **fake model can't call tools**, and small local models do it unreliably. All outputs here were produced with local **`qwen2:7b`**. If you skipped the LLM setup, revisit [01.02 · Environment setup](../01_foundations/02_environment_setup.md).

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [What is tool calling?](01_what_is_tool_calling.md) | How does an LLM run my code, and who actually runs it? |
| 02 | [Building useful tools](02_building_useful_tools.md) | How do I write good tools (incl. a web-search tool)? |
| 03 | [Agentic RAG](03_agentic_rag.md) | How do I make retrieval a tool the model *chooses* to use? |

## What you'll be able to do after this section

- Explain what tool calling is and why the **model never runs the tool — your code does**.
- Turn any Python function into a tool with `@tool` and expose it with `bind_tools`.
- Run the full **call → execute → respond** loop by hand, and understand what an agent automates.
- Build **agentic RAG**: retrieval as a tool, so the model searches only when a question needs it.
- Judge **when an agent is worth it** versus a plain, predictable RAG chain.

→ Start: **[01 · What is tool calling?](01_what_is_tool_calling.md)**
