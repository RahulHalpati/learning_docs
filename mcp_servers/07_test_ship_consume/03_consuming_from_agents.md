# 07-3 · Consuming from agents

> **Level:** Intermediate → Advanced · **Prerequisites:** [07-2 · Packaging & deploy](02_packaging_and_deploy.md)
> **Time:** ~45–55 min · **Verified:** 2026-08-08 (FastMCP Client · pytest · Docker · Python 3.12)

## Why this matters

You built a server. You tested it. You containerized it. But none of that proves the thing that matters: **can a model actually use it?** This lesson closes the loop — a real client connects to notevault and lets a model call the tools you wrote, unchanged. This is the entire payoff of building on MCP instead of hand-writing tool glue: the same server drops into *any* host. The notes tools you defined are now callable from a LangGraph agent, a Google ADK agent, Claude Desktop, or a plain script — and you didn't write a line of integration code for any of them.

---

## Step 1 — a direct client against the running server

Start with the simplest consumer: a FastMCP `Client` pointed at the URL of the container from 07-2. No model yet — just prove a client can connect, discover, and call:

```python
import asyncio
from fastmcp import Client

async def main() -> None:
    # A URL selects the HTTP transport; /mcp is the default mount path.
    async with Client("http://127.0.0.1:8000/mcp") as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools])          # discover what's offered

        note = await client.call_tool(
            "create_note", {"title": "Kickoff", "body": "notevault is live."})
        print("created:", note.data)

        hits = await client.call_tool("search_notes", {"query": "live"})
        print("search:", [n["title"] for n in hits.data])

asyncio.run(main())
```

This is the same `Client` API you tested with in 07-1 — only the transport changed (a URL instead of the server object). That symmetry is the point: in-memory for tests, HTTP for the real deployment, identical calling code.

---

## Step 2 — let a model drive it (LangGraph)

A model can't speak the FastMCP `Client` API — it speaks *tool calls*. The bridge is an **MCP adapter** that fetches the server's tools and hands them to the model as bindable tools. In LangGraph, `langchain-mcp-adapters` does exactly this:

```python
# uv add langgraph langchain-mcp-adapters langchain-openai
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

async def build_agent():
    # Point the adapter at notevault's HTTP endpoint.
    mcp_client = MultiServerMCPClient({
        "notevault": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:8000/mcp",
        },
    })
    tools = await mcp_client.get_tools()        # notevault's tools → LangChain tools

    # Bind them to a model in a ReAct agent — the model now decides when to call.
    agent = create_react_agent("openai:gpt-4o", tools)
    return agent
```

```python
# Drive it: the model reads notevault's tool descriptions and calls them itself.
agent = await build_agent()
result = await agent.ainvoke(
    {"messages": [{"role": "user",
                   "content": "Save a note titled 'Retro' about shipping notevault, "
                              "then tell me what notes mention shipping."}]})
print(result["messages"][-1].content)
```

The model reads notevault's **tool descriptions**, decides `create_note` then `search_notes` are the right calls, fills the arguments, and the adapter routes each `tools/call` to your server. You wrote none of that wiring — the descriptions you authored in Section 02 are the entire interface. (LangGraph is one reader's [own course](../../langgraph/README.md); [Google ADK](../../google_adk/README.md) consumes MCP the same way through its own tool layer.)

---

## Step 3 — the destructive tool stays gated

Consuming a server does **not** dissolve its guardrails — that's the whole security model working. When the model tries the destructive `delete_note`, notevault's approval gate (Section 06's elicitation) still fires, no matter which host is driving:

```python
# The model, mid-task, decides to delete a note. Two honest outcomes:
#   1) The tool refuses without approval → the model gets an error and adapts.
#   2) The host surfaces the elicitation → a human approves/declines before it runs.
# Either way, nothing is deleted on the model's say-so alone.
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Delete the Retro note."}]})
# In a HITL-capable host this pauses for approval; in a bare client the gated
# tool returns "approval required" and no note is removed.
```

This is exactly the gate test from 07-1, now proven end-to-end with a real model in the loop. A safe call (`create_note`) succeeds; a destructive call (`delete_note`) is gated. If your capstone transcript shows both, you've passed this section's test task.

> **Why the gate holds across hosts.** Approval isn't enforced by the client — it's enforced by *your server*. So it travels with the tool into every host. A host that can't handle elicitation simply can't complete the destructive call; it can never silently bypass it.

---

## Discovery: making a server pleasant to adopt

Once notevault works, people have to *find* and *trust* it. MCP has registries and marketplaces where servers are listed; getting adopted is mostly about the boring, respectful details:

- **A clear name and description** — what it does, in one line, at the top of the listing.
- **Tool descriptions the model can act on** — these *are* the interface (Step 2 proved it). Vague descriptions mean the model picks the wrong tool or none. This is the highest-leverage documentation you'll write.
- **Versioning** — semver in `pyproject.toml` so clients can pin (`notevault>=0.1,<0.2`) and you can ship breaking changes without surprising anyone.
- **Install instructions for both models** — the `uvx notevault` command for stdio hosts, the image + URL for HTTP hosts (07-2).

You don't need a registry to be adopted — a good README and a pinned version go a long way — but the same qualities that make a server registry-ready make it pleasant for *anyone* to drop in.

---

## The loop, closed

Trace what you did across this course: modeled capabilities as primitives (01), built tools/resources/prompts (02–03), added Context and transports (03–05), secured the dangerous paths (06), and now tested, shipped, and **consumed** the result (07). The server that started as an in-memory dict is now a portable, secured, tested artifact a model uses through any host. The capstone is where you assemble the whole thing.

---

## Recap & next

- ✅ **Direct client:** point a FastMCP `Client` at the container URL — same API as your in-memory tests, only the transport differs.
- ✅ **Agent:** an **MCP adapter** (`langchain-mcp-adapters` for LangGraph) fetches your tools and binds them to a model; the model calls them using the descriptions *you* wrote.
- ✅ **Guardrails travel with the server** — the destructive tool stays gated in every host; approval is enforced by your code, not the client.
- ✅ The same server is portable across **any** MCP host — LangGraph, Google ADK, Claude Desktop, a plain script — with zero integration code.
- ✅ **Adoption** = clear name, actionable tool descriptions, semver, install instructions for both distribution models.
- ✅ Self-check: the model picks the wrong tool for a task — where's the bug most likely to be, and what do you fix?

→ Next: **[Capstone · notevault, end to end](../99_capstone_notevault.md)**

## Exercises

1. You connect the LangGraph agent and ask it to "find my notes about the Q3 launch," but the model calls `create_note` instead of `search_notes`. Nothing about the model changed. Where's the bug, and what's the fix?

<details>
<summary>Solution</summary>

The bug is almost certainly in your **tool descriptions**, not the model. The model chooses tools purely from their names and descriptions — if `search_notes` has a vague or missing description (or `create_note`'s description over-claims), the model can't tell them apart. The fix is on the *server*: write a precise description ("Search existing notes by keyword; returns matching notes. Does not create anything.") and re-run. Tool descriptions are the model-facing interface — treat them as production code.
</details>

2. Explain, in two sentences, why binding notevault to a LangGraph agent required no notevault code changes — but binding a hand-written tool would have.

<details>
<summary>Solution</summary>

notevault speaks MCP, so any MCP-aware host (via an adapter) can discover and call its tools through the same wire protocol — the adapter translates once, for every server. A hand-written tool has no standard interface, so each host needs bespoke glue to know its name, schema, and how to call it — the N×M problem MCP exists to kill (Section 01).
</details>

3. A colleague says "we tested the tools, so we don't need to test the agent consuming them." What's the one thing an end-to-end agent transcript proves that the in-memory suite can't?

<details>
<summary>Solution</summary>

The in-memory suite proves each tool *works when called correctly* — but it calls the tools itself, with hand-written arguments. An agent transcript proves a **model can actually discover, choose, and invoke** the tools from their descriptions alone, and that the destructive gate fires with a real model in the loop. It's the difference between "the tool is correct" and "the tool is usable by the thing that's supposed to use it" — and bad tool descriptions fail only the latter.
</details>
