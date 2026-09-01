# 03-5 · MCP tools: connecting agents to any server

> **Level:** Intermediate · **Prerequisites:** [03-4 · The functional API](04_functional_api.md)
> **Time:** 30 min · **Verified:** 2026-08-24 (langchain-mcp-adapters · MCP spec 2026-07-28 stateless streamable HTTP)

## Why this matters

In 03-2 and 03-3 every tool was a Python function sitting in the same repo as the agent — `@tool def get_weather(...)`. That works right up until a second team wants the same capability. Then you copy-paste it, or write bespoke glue for each agent × each integration: the **N×M problem**. Ten agents and ten integrations is a hundred adapters, each with its own auth, its own drift, its own 3am page.

**MCP (Model Context Protocol)** collapses that to N+M. A tool server is written *once* and exposes a standard interface; any MCP-compatible agent can consume it. Your tools become a shared, versioned service — deployed, monitored, and owned like any other service — instead of functions duplicated across repos. `langchain-mcp-adapters` is the bridge: it turns an MCP server's tools into ordinary LangChain tools, so `create_react_agent` binds them exactly like the local ones you already wrote.

This lesson is the **consume** side. The **build** side — authoring your own server with FastMCP — is its own course here: [`mcp_servers`](../../mcp_servers/README.md).

---

## MCP in five lines

- A **client** (your agent) connects to one or more **servers** over a transport.
- A server advertises its capabilities; the client lists them and calls them.
- Transports: **stdio** (server runs as a local subprocess) or **streamable HTTP** (server runs somewhere else).
- Everything is JSON-RPC under the hood — you never write it by hand.
- Servers expose three kinds of primitive:

| Primitive | What it is | Who decides to use it |
|-----------|------------|-----------------------|
| **Tool** | An action with side effects or computation | The **model** (it emits a tool call) |
| **Resource** | Read-only data, addressed by URI | The **application** (you attach it as context) |
| **Prompt** | A reusable templated instruction | The **user** (picks it from a menu) |

We care about **tools** here — those are what an agent's ReAct loop can invoke. (The adapters package also has helpers for pulling prompts and resources; ignore them until you need them.)

---

## A local server over stdio

`MultiServerMCPClient` takes a dict mapping **server name → config**. For `"stdio"` you give it the `command` and `args` to launch — the client owns that subprocess.

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

client = MultiServerMCPClient({
    "math": {                                  # server name — namespaces nothing, but shows up in logs
        "transport": "stdio",                  # launched locally as a subprocess
        "command": "python",                   # what to run
        "args": ["/srv/mcp/math_server.py"],   # argv for it
    },
})

async def main() -> None:
    tools = await client.get_tools()           # → list[BaseTool], one per tool the server advertises
    print([t.name for t in tools])             # e.g. ['add', 'multiply']

    agent = create_react_agent(
        ChatOllama(model="qwen2.5:0.5b", temperature=0),
        tools,                                 # same slot as your hand-written @tool list
    )
    out = await agent.ainvoke({"messages": [
        {"role": "user", "content": "What is 17 * 23? Use the tool."}]})
    print(out["messages"][-1].content)

asyncio.run(main())
```

The important line is `tools = await client.get_tools()`. What comes back is a plain list of LangChain tools — the agent has no idea they live in another process. Everything you learned about `ToolNode`, `tools_condition`, and `create_react_agent` applies unchanged.

> **Note:** `get_tools()` is async because listing tools is a round-trip to each server. Use `agent.ainvoke` / `astream` from here on — mixing a sync `invoke` into an async stack is how you get a blocked event loop.

---

## A remote server over streamable HTTP

Swap the transport and the config keys change: no `command`/`args`, just a `url`. This is how you talk to a server another team runs.

```python
import os

client = MultiServerMCPClient({
    "notes": {
        "transport": "streamable_http",
        "url": "https://notes.internal.example.com/mcp/",
        "headers": {                                        # HTTP transports only
            "Authorization": f"Bearer {os.environ['NOTES_MCP_TOKEN']}",
        },
    },
})

tools = await client.get_tools()    # inside an async function
```

Two things to internalise:

- **`headers` only exist for HTTP transports** (`streamable_http` and the older `sse`). A stdio server is a child process, not an HTTP endpoint — there is no request to attach a header to. Pass secrets to a stdio server through its environment or argv instead.
- **The 2026-07-28 spec revision made the protocol core stateless.** There is no session handshake and no `Mcp-Session-Id` to pin a client to one backend; every request carries what it needs. That is why a remote MCP server sits behind an ordinary load balancer with N replicas and no sticky sessions — the deployment story of a normal HTTP service.

(`sse` still works and you will meet it in older servers. Streamable HTTP is the current transport; prefer it for anything new.)

---

## One client, many servers

This is the payoff. A single client can hold a stdio server *and* an HTTP server at once, and `get_tools()` returns **one flat list** across all of them.

```python
client = MultiServerMCPClient({
    "math": {                                    # local, ours, cheap
        "transport": "stdio",
        "command": "python",
        "args": ["/srv/mcp/math_server.py"],
    },
    "notes": {                                   # remote, another team's, authenticated
        "transport": "streamable_http",
        "url": "https://notes.internal.example.com/mcp/",
        "headers": {"Authorization": f"Bearer {os.environ['NOTES_MCP_TOKEN']}"},
    },
})

tools = await client.get_tools()                 # add + multiply + search_notes + create_note
agent = create_react_agent(ChatOllama(model="qwen2.5:0.5b", temperature=0), tools)
```

Capability composition: the notes team ships a new tool, restarts their server, and your agent picks it up on its next `get_tools()` — no change to your code, no redeploy of the agent. That is the whole argument for MCP in one sentence.

> ⚠️ Tool *names* are what the model reasons over, and they now come from servers you don't control. Two servers can ship a `search` and the model will pick badly. Keep names specific (`search_notes`, not `search`) and audit the merged list when you add a server.

---

## When not to bother

MCP is not free. You added a subprocess or a network hop, a second deploy target, and a new failure mode between the model and the work. Be honest about the ledger:

| Reach for MCP when… | Keep a plain `@tool` when… |
|---------------------|----------------------------|
| The tool is shared across several agents/teams/products | It is one private function in your own repo |
| Another team owns the tool and its release cycle | You own it and ship it with the agent anyway |
| You want it swappable/upgradable without redeploying the agent | It's three lines of Python calling one internal API |
| You're consuming somebody else's server (GitHub, Slack, an internal platform) | Latency matters and the hop buys you nothing |

Converting an internal helper into an MCP server "for consistency" is pure cost: same code, plus a transport, plus an ops surface. Don't.

**Two security facts you have to hold:**

- **Tool output is untrusted input.** A tool result is text you feed straight back into the model. Whoever controls the data the tool reads — a web page, an issue body, a customer record — can write instructions in it and try to steer your agent. That's *indirect prompt injection*, and it is not hypothetical once your tools reach the internet.
- **Remote servers need auth and least privilege.** A bearer token scoped to everything means one confused agent turn can do anything the token can. Scope narrowly, gate destructive tools behind human approval.

Depth on both — threat model, injection through tools, sandboxing, human-in-the-loop — is in [`mcp_servers/06_security`](../../mcp_servers/06_security/README.md).

---

## Recap & next

- ✅ MCP turns N×M bespoke integrations into N clients + M servers: write a tool server once, any agent consumes it.
- ✅ `MultiServerMCPClient({name: config})` → `tools = await client.get_tools()` → `create_react_agent(model, tools)`. The agent can't tell them from local tools.
- ✅ `"stdio"` uses `command` + `args` (local subprocess); `"streamable_http"` uses `url` (remote). `headers` — auth tokens — work for HTTP transports only.
- ✅ One client can mix both transports; `get_tools()` returns one flat list. That's capability composition.
- ✅ The 2026-07-28 spec made the core stateless (no session id), so remote servers scale behind a plain load balancer.
- ✅ For one private function in your own repo, `@tool` is still the right answer. MCP earns its hop when the tool is shared, externally owned, or must be swappable.
- ✅ Treat every tool result as untrusted input; scope remote credentials tightly.
- ✅ Self-check: you need to pass an API token to a tool server. Which transport lets you send it as a header, and how do you get it into the other one?

→ Next: **[04 · Control flow](../04_control_flow/README.md)**

## Exercises

1. Start from the stdio example and add a second server (an HTTP one, or a second stdio script). Print the tool names before and after, and confirm `get_tools()` returns the union — and that `create_react_agent` needs no other change.

<details>
<summary>Solution</summary>

```python
client = MultiServerMCPClient({
    "math":  {"transport": "stdio", "command": "python", "args": ["/srv/mcp/math_server.py"]},
    "notes": {"transport": "streamable_http", "url": "https://notes.internal.example.com/mcp/"},
})
tools = await client.get_tools()
print([(t.name, t.description[:40]) for t in tools])
agent = create_react_agent(model, tools)     # unchanged
```

The list is flat — nothing tells the agent which server a tool came from. Which is exactly why you check for duplicate/vague names here: if both servers exported `search`, this is where you'd notice.
</details>

2. Your codebase has `def _normalise_address(raw: str) -> Address`, used by one agent, in the same repo. A colleague suggests exposing it as an MCP server. Argue the other side.

<details>
<summary>Solution</summary>

Nothing about it is shared: one consumer, one owner, one repo, released together. Wrapping it in MCP adds a process or network hop on every call, a second thing to deploy and monitor, a serialisation boundary that flattens your `Address` type into JSON, and a new failure mode (server down = agent degraded) — in exchange for zero new capability. `@tool` on the existing function is the whole job, and it stays in the same test run and the same stack trace.

The answer flips the moment a *second* consumer appears, or another team takes ownership, or you want to ship address-parsing fixes without redeploying the agent. Then the hop is buying you decoupling, and MCP is right.
</details>
