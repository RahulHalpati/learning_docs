# 03-4 · MCP tools

> **Level:** Intermediate · **Prerequisites:** [03-1 · Function tools](01_function_tools.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0, mcp 1.28.1; import verified, calls need a live MCP server)

## Why this matters

The **Model Context Protocol (MCP)** is an open standard for exposing tools (and data) to any AI agent — a growing ecosystem of servers for filesystems, databases, GitHub, and more. ADK's `MCPToolset` connects an agent to any MCP server, so you get those tools *for free* without writing wrappers.

---

## Install the extra

MCP support is optional:

```bash
pip install mcp                # ADK auto-detects it
```

Then the import is available:

```python
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams    # verified import
```

---

## Connect to an MCP server

An MCP server is launched as a subprocess (stdio) or reached over HTTP. `MCPToolset` starts/connects to it and exposes its tools to your agent:

```python
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Example: the reference filesystem MCP server (needs Node.js / npx installed)
toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/adk-demo"],
        )
    )
)
# agent = LlmAgent(name="fs_agent", model=..., tools=[toolset])
```

`MCPToolset` connects, lists the server's tools (for the filesystem server: `read_file`, `list_directory`, …), and presents them to the agent exactly like function tools. The agent's model then calls them by name.

> **Note:** the *import* is verified offline (after `pip install mcp`); actually running this needs the MCP server available (here, `npx` + Node.js to launch the reference server). Swap in any MCP server you can run locally — the ADK side is identical.

---

## Why MCP matters

- **Reuse, don't rewrite:** hundreds of MCP servers already exist; connect instead of wrapping APIs by hand.
- **Interoperable:** the same server works with any MCP-aware agent (ADK, Claude Desktop, others).
- **Two directions:** ADK can *consume* MCP tools (shown here) and also *expose* your ADK tools *as* an MCP server for others to use.

MCP is to tools what OpenAPI is to REST: a shared contract so integrations compose.

---

## Recap & next

- ✅ `pip install mcp`, then `MCPToolset(connection_params=...)` connects an agent to an MCP server's tools.
- ✅ Stdio (subprocess) or HTTP connections; the server's tools appear as normal tools.
- ✅ MCP lets you reuse a whole ecosystem of tool servers instead of writing wrappers.
- ✅ Self-check: how does an MCP tool differ, from the agent's point of view, from a function tool?

→ Next: **[04 · State, sessions & memory](../04_state_sessions_memory/README.md)**

## Exercises

1. If you have Node.js: run the filesystem MCP server against a temp dir and ask an agent (Ollama) to list its files.

<details>
<summary>Solution</summary>

Use the `MCPToolset` snippet above pointed at `/tmp/adk-demo` (create it with a file or two), give it to an `LlmAgent` on `ollama_chat/qwen2.5:0.5b`, and ask "list the files". The model calls the server's `list_directory` tool.
</details>
