# 00 · Introduction

> **Level:** Beginner · **Prerequisites:** Python `async`/`await`, type hints, basic HTTP. Backend experience (or this repo's [FastAPI course](../fastapi_complete/)) strongly recommended.
> **Time:** 20 min · **Verified:** 2026-08-08 (course conventions; the stack is verified per lesson)

You have almost certainly *used* an MCP server — every time an AI assistant read your files, queried a database, or edited a ticket, an MCP server was on the other end. This course is about being the person who *builds* that server. That's a different and scarcer skill, and it's the one that turns "I use AI tools" into "I ship the integration layer enterprises are paying for."

---

## What MCP actually is (in one screen)

The **Model Context Protocol** is a standard way for an AI application (the *host* — Claude, an IDE, an agent) to reach external data and actions through small programs called *servers*. Before it, every model-to-tool connection was bespoke: M models × N tools = a combinatorial pile of glue code. MCP collapses that to "write one server, any host can use it" — the way USB-C replaced a drawer full of chargers.

A server exposes exactly three kinds of capability, and knowing which is which is the whole foundation:

| Primitive | Is like | Controlled by | Example |
|-----------|---------|---------------|---------|
| **Resource** | HTTP `GET` (read-only, no side effects) | the **app** (loads it into context) | "the text of note #42" |
| **Tool** | HTTP `POST` (an action with effects) | the **model** (decides to call it) | "create a note", "delete a record" |
| **Prompt** | a saved template | the **user** (picks it in the UI) | "summarize my notes on X" |

Get this table wrong and you build insecure servers — e.g. hiding a destructive action inside a "resource" the model can trigger without anyone noticing. Section 01 drills it.

---

## Why this is a 2026 skill, specifically

Two things changed the calculus this year:

1. **MCP won the standards war.** It's now stewarded under the Linux Foundation, spoken by every major host, and paired with A2A (agent-to-agent) as the interoperability backbone. Learning it is no longer a bet on one vendor.
2. **The 2026-07-28 spec made servers boring to operate** — in the best way. The protocol core went *stateless*: no session handshake, every request self-describing, so a server scales behind an ordinary load balancer like any web service. That removed the last excuse not to run MCP servers in real production, and demand followed.

The flip side — and the reason the *building* skill pays — is that MCP servers are a serious attack surface. A server is code the host trusts; its tool outputs flow straight into a model that can't tell instructions from data. An entire section here is defensive security, because "can build an MCP server" and "can build one you'd expose to the internet" are different job levels.

---

## One server, grown all course: notevault

You build **notevault** — an MCP server over a personal notes/knowledge base — and never throw it away:

| Section | What happens to notevault |
|---------|--------------------------|
| 02 | Born: a stdio server with `create_note` / `search_notes` over an in-memory store |
| 03 | Gains resources (`note://{id}`), a `summarize_notes` prompt, and progress callbacks |
| 04 | Backed by a real async database; robust errors, pagination, an API-enrichment tool |
| 05 | Goes remote: stateless streamable HTTP, OAuth 2.1, scaled behind a load balancer |
| 06 | Hardened: injection defenses, least privilege, SSRF allowlists, human-in-the-loop gates |
| 07 | Tested in-memory, containerized, and consumed live from an agent |

A notes app is deliberately mundane — the *engineering* (schema design, auth, injection defense, deployment) is the star, and it all transfers to whatever domain you expose next.

---

## House rules (2026 standards)

| ✅ Use | ❌ Avoid (and why) |
|-------|-------------------|
| **FastMCP** decorators + type hints | hand-rolling JSON-RPC — FastMCP generates the schema for you |
| **Stateless streamable HTTP** (2026-07-28) | the retired stateful SSE transport with session handshakes |
| OAuth 2.1 **resource server** (verify tokens) | issuing your own tokens — an MCP server verifies, never issues |
| Typed, paginated tool results | dumping 5,000 rows into the model's context window |
| Tool outputs treated as **untrusted data** | trusting fetched/returned text the model then obeys |
| Human-in-the-loop on destructive tools | letting a hijacked model delete or spend unattended |
| `uv` + `ruff`, Python 3.12+ | legacy packaging, blocking sync I/O in async tools |

---

## How to work

1. **Type the code, run every server.** The MCP Inspector (Section 02) lets you see and call your tools with no model involved — use it constantly.
2. **Keep notevault under git from Section 02.** Commit at each gate.
3. **Do the security section for real.** The injection drill in Section 06 is the one an interviewer will probe. Reproduce the attack before you fix it.
4. **Budget honestly.** The MCP-specific core (sections 01–03) is **~5 h** — see the [core track](README.md#-job-ready-core-track-5-h--mcp-is-a-12-day-skill). Sections 04–07 (~20 h) are production-service work you can do later or skip if you already know FastAPI; the capstone is 20–30 h.

---

## Where this ends

Section 99 is a **specification** for a production notevault (or your own domain): real database, OAuth, scoped tools, injection defenses, human-in-the-loop, a passing test suite, a container, and a live agent using it. No walkthrough — you build it from the spec, and the repo becomes a portfolio piece that proves you can ship the integration layer, not just call one.

→ Start: **[Section 01 · Foundations](01_foundations/README.md)**
