# Section 01 · Foundations: what MCP is and why it won

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~3 h

Before you write a line of server code, you need the mental model. The **Model Context Protocol** is an open standard — built on **JSON-RPC 2.0** — that lets any AI host talk to any tool or data source through one wire format, killing the N×M glue problem. This section explains the host/client/server architecture, the three server primitives (resources, tools, prompts) and who controls each, and the 2026 shift to **stateless streamable HTTP** that lets an MCP server scale like any ordinary web service.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 01-1 | [What MCP is & why it won](01_what_and_why_mcp.md) | Why does a standard beat writing tool glue per app? |
| 01-2 | [The protocol & the three primitives](02_protocol_and_primitives.md) | What can a server actually expose, and who invokes it? |
| 01-3 | [Transports & the stateless spec](03_transports_and_stateless_spec.md) | stdio or HTTP — and why did 2026 make it stateless? |

## Mini-project

**Write a one-page architecture note** (no code) for a system you know — real or invented. Suggested: *"expose our internal ticketing DB to Claude."* Your note must:

- Name the system and the one job an AI host should be able to do with it.
- List each capability you'd expose and classify it as a **Resource**, a **Tool**, or a **Prompt** — with a one-line justification per item (why read-only vs. side-effecting vs. template).
- Decide **stdio or streamable HTTP**, and justify it (who runs the host? one user on a laptop, or many users hitting a shared server?).
- Flag any capability that is dangerous (writes, deletes, shells out, fetches arbitrary URLs) and note the guardrail it will need later.

One page. Prose, a table, and a rough sketch are plenty. You're proving you can *model* a system as MCP capabilities before you build one.

## Test task (gate)

A diagnostic. Given these six capabilities, classify each as **Resource**, **Tool**, or **Prompt**, and flag the dangerous ones with *why*:

1. Read a file's contents.
2. Delete a database record.
3. List all open tickets.
4. A reusable *"summarize this incident"* template the user picks from a menu.
5. Run a shell command.
6. Fetch a URL and return its body.

**You pass when** your classification is correct *and* you explicitly identify that:

- **Delete-record (2)** and **run-shell-command (5)** are the dangerous ones — they have side effects (data loss / arbitrary code execution) and must run behind **human-in-the-loop approval** and **least privilege** (scoped credentials, an allow-list, no ambient admin rights).
- **Fetch-URL (6)** returns **untrusted data** — its body can carry indirect prompt injection, so it's a tool whose *output* must never be blindly trusted as instructions.

<details>
<summary>Answer key</summary>

| # | Capability | Class | Notes |
|---|------------|-------|-------|
| 1 | Read a file | **Resource** | Read-only, URI-addressable context. No side effects. |
| 2 | Delete a record | **Tool** ⚠️ | Destructive side effect → human approval + scoped, least-privilege credentials. |
| 3 | List open tickets | **Resource** (or a read-only Tool if it takes filters) | Read-only. Safe. |
| 4 | "Summarize this incident" template | **Prompt** | User-controlled, parameterized template. |
| 5 | Run a shell command | **Tool** ⚠️ | Arbitrary code execution → the highest-risk primitive. Approval, allow-list, no ambient privilege. |
| 6 | Fetch a URL | **Tool** ⚠️ | Side effect (network egress) **and** returns untrusted data → indirect prompt-injection risk. |

If you classified 2 or 5 as "just a tool" without flagging the risk, re-read the security notes in [01-1](01_what_and_why_mcp.md) and [01-3](03_transports_and_stateless_spec.md). Full treatment is Section 06.
</details>

## What you'll be able to do after this section

- Explain the N×M integration problem and why a shared protocol (the "USB-C for AI") solves it.
- Diagram the host → client → server architecture and say precisely who decides when a capability runs.
- Classify any system's capabilities as resources, tools, or prompts — and defend the choice.
- Choose stdio vs. streamable HTTP for a given deployment, and explain why the 2026 stateless spec lets HTTP servers scale horizontally.
- Spot the two standing security flags — trusted server code and untrusted tool/resource output — before they bite you.

→ Start: **[01-1 · What MCP is & why it won](01_what_and_why_mcp.md)**
