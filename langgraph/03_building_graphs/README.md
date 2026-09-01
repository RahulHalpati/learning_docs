# Section 03 · Building graphs

> **Prerequisites:** [02 · Execution model](../02_execution_model/README.md) · **Time:** ~2 h

Now you build the real thing. Four escalating patterns: a memory-keeping **chatbot**, a tool-calling **ReAct agent** wired by hand, the **prebuilt** agent one-liner (and its v1 relocation), and the **functional API** — an imperative alternative to the graph builder.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Your first chatbot](01_first_chatbot.md) | How do I make a chatbot that remembers the conversation? |
| 03-2 | [Tools & the ReAct loop](02_tools_and_react.md) | How does an agent decide to call a tool, and how does `ToolNode` run it? |
| 03-3 | [Prebuilt agents](03_create_react_agent.md) | When should I use `create_react_agent` / `create_agent`, and what are its knobs? |
| 03-4 | [The functional API](04_functional_api.md) | Can I write agents as plain functions with `@entrypoint`/`@task` instead of a graph? |
| 03-5 | [MCP tools](05_mcp_tools.md) | How do I plug in tools from any MCP server instead of hand-writing every integration? |

## What you'll be able to do after this section

- Build a multi-turn chatbot with a checkpointer and `thread_id`.
- Wire a ReAct loop by hand with `ToolNode` + `tools_condition`, with a real tool-calling model.
- Use the prebuilt agent (and know it moved to `langchain.agents.create_agent` in v1), with `prompt`, `response_format`, `state_schema`, and hooks.
- Choose between the **graph API** and the **functional API**.

→ Start: **[03-1 · Your first chatbot](01_first_chatbot.md)**
