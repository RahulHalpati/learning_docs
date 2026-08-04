# Section 03 · Tools

> **Prerequisites:** [02 · Agents & workflows](../02_agents_and_workflows/README.md) · **Time:** ~90 min

Tools are how an agent *does* things beyond talking — call a function, hit an API, use another agent, reach an MCP server. This section covers all four kinds.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Function tools](01_function_tools.md) | How do I turn a Python function into a tool the agent can call? |
| 03-2 | [Built-in & agent tools](02_builtin_and_agent_tools.md) | How do I use ADK's built-in tools, and use an agent *as* a tool? |
| 03-3 | [OpenAPI tools](03_openapi_tools.md) | How do I generate tools from an OpenAPI spec? |
| 03-4 | [MCP tools](04_mcp_tools.md) | How do I connect an agent to an MCP server's tools? |

## What you'll be able to do after this section

- Write function tools (with `ToolContext`) and see an agent call them.
- Use built-in tools and wrap an `LlmAgent` as an `AgentTool`.
- Generate a toolset from an OpenAPI spec, and connect to an MCP server.

→ Start: **[03-1 · Function tools](01_function_tools.md)**
