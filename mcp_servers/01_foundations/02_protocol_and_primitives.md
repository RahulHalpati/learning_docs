# 01-2 · The protocol & the three primitives

> **Level:** Beginner · **Prerequisites:** [01-1 · What MCP is & why it won](01_what_and_why_mcp.md)
> **Time:** ~30–40 min · **Verified:** 2026-08-08 (MCP spec 2026-07-28 · FastMCP · Python 3.12)

## Why this matters

A server author lives or dies by one modeling decision: **is this capability a resource, a tool, or a prompt?** Get it right and the host, the model, and the user each interact with it correctly and safely. Get it wrong — expose a destructive action as if it were harmless context, or bury a template inside a tool — and you've built something confusing at best and dangerous at worst. This lesson pins down the wire format (JSON-RPC 2.0) and the three primitives so you classify correctly every time.

---

## JSON-RPC 2.0 in one paragraph

MCP messages are **JSON-RPC 2.0**. There are exactly three message shapes. A **request** carries an `id`, a `method` name (like `tools/call`), and `params`; it expects a matching **response** carrying the same `id` and either a `result` or an `error`. A **notification** is a request with **no `id`** — fire-and-forget, no reply expected. That's the whole model: methods with params, responses correlated by id, and one-way notifications. Crucially, **JSON-RPC makes no HTTP assumptions** — it's just JSON objects, so the same messages ride over stdio pipes *or* HTTP bodies unchanged (that's the next lesson). MCP defines the method names (`resources/list`, `resources/read`, `tools/list`, `tools/call`, `prompts/list`, `prompts/get`, …); JSON-RPC defines the envelope.

---

## The three primitives

Everything a server exposes is one of these three. The single best discriminator is **who controls it** — who decides that it runs.

| Primitive | HTTP analogy | Side effects? | **Who controls it** |
|-----------|--------------|---------------|---------------------|
| **Resource** | `GET` | None (read-only) | **App** — the host loads it into context |
| **Tool** | `POST` | Yes (actions) | **Model** — it decides when to invoke |
| **Prompt** | (a saved template) | None itself | **User** — they pick it from a menu |

### Resources — app-controlled context

A **resource** is **read-only, URI-addressable data** the model can load into its context. Think `GET`: no side effects, safe to fetch, safe to fetch again. A resource is identified by a URI (`note://meeting/2026-08-10`, `file:///README.md`) and the **host application** decides when to pull it in — for example, attaching a document the user selected. Resources are *context*, not *actions*.

### Tools — model-controlled actions

A **tool** is an **executable function with side effects** that the **model** invokes. Think `POST`: it *does* something — writes a record, sends an email, runs a query that changes state. The server advertises each tool with a name, a description, and an input schema; the model reads those, decides a tool is relevant, fills in the arguments, and the host sends a `tools/call`. Because the *model* pulls the trigger, tools are where side effects and risk live — this is exactly the "the model decides when to call" point from 01-1.

### Prompts — user-controlled templates

A **prompt** is a **server-authored, parameterized template** that the **user** (or client UI) invokes deliberately — typically surfaced as a slash-command or a menu item like *"/summarize-incident"*. The server owns the wording and the parameters; the user chooses to run it and fills in the blanks. Prompts have no side effects of their own — they're reusable, curated ways to *start* an interaction, not actions.

> **The one-line test.** *Read-only data the app attaches?* Resource. *An action the model triggers?* Tool. *A template the user picks?* Prompt. If a single "capability" is really two of these, split it.

---

## One domain, all three

Take a **notes / knowledge system**. Here's each primitive for that one domain:

- **Resource** — `note://{id}` returns the read-only contents of a note so the model can reason over it. Fetching it changes nothing. *(App attaches the note the user opened.)*
- **Tool** — `create_note(title, body)` writes a new note. It has a side effect (a note now exists), so it's model-controlled and, being a write, a candidate for guardrails. *(Model calls it when the task needs it.)*
- **Prompt** — `daily_summary(date)` is a template: *"Summarize all notes from {date} into five bullets."* The user picks it from a menu; the server supplies the wording. *(User invokes it deliberately.)*

Same knowledge base, three fundamentally different interaction contracts. Model the system by asking, per capability, *who controls it and does it have side effects.*

---

## A concrete `tools/call` message

Here's the JSON-RPC request a host sends when the model decides to invoke `create_note`, and the server's response:

```json
// Request: host → server (the model chose this call)
{
  "jsonrpc": "2.0",
  "id": 42,                                  // correlates request↔response
  "method": "tools/call",
  "params": {
    "name": "create_note",
    "arguments": { "title": "Standup", "body": "Shipped 01-2." }
  }
}
```

```json
// Response: server → host (same id, a result)
{
  "jsonrpc": "2.0",
  "id": 42,                                  // matches the request
  "result": {
    "content": [{ "type": "text", "text": "Created note #128." }]
  }
}
```

Note the shape: a `method`, `params` carrying the tool `name` + `arguments`, and a `result` correlated by `id`. A failure would return an `error` object with the same `id` instead of `result`. Resources (`resources/read`) and prompts (`prompts/get`) use the same envelope with different methods.

---

## Capability negotiation in the stateless world

A host and server must agree on what each supports (does the server have tools? does the client accept a certain feature?). In older, stateful MCP this happened **once** during an `initialize` handshake, and the agreed capabilities were remembered for the session.

As of the **2026-07-28** revision the protocol core is **stateless**, so there's no long-lived session to remember anything. Instead, **capabilities are announced per request**: each message is **self-describing** — it carries the protocol version, client info, and the relevant capabilities inline, every time. The server needs no memory of a prior handshake to interpret a request correctly. *Why this matters* is a networking story we tell fully in the next lesson (it's what lets a server sit behind a plain load balancer) — for now, just know that in 2026 there's no "connect once, negotiate once" step; every request stands alone.

---

## Recap & next

- ✅ MCP rides on **JSON-RPC 2.0**: **requests** (have `id` + `method` + `params`), **responses** (same `id`, `result`/`error`), **notifications** (no `id`). No HTTP assumptions.
- ✅ **Resource** = read-only context, **app**-controlled (like `GET`). **Tool** = side-effecting action, **model**-controlled (like `POST`). **Prompt** = parameterized template, **user**-controlled.
- ✅ The discriminator is **who controls it** — plus "does it have side effects?"
- ✅ A `tools/call` request carries `name` + `arguments`; the response is correlated by `id`.
- ✅ In the stateless 2026 spec, **capabilities are announced per request** — messages are self-describing, no one-time handshake.
- ✅ Self-check: a capability "email the ticket owner a summary" — resource, tool, or prompt, and why?

→ Next: **[01-3 · Transports & the stateless spec](03_transports_and_stateless_spec.md)**

## Exercises

1. Classify each as resource / tool / prompt: (a) `GET` the current sprint's backlog as read-only text; (b) close a ticket; (c) a "/triage-bug" template the user runs; (d) fetch a config file's contents.

<details>
<summary>Solution</summary>

(a) **Resource** — read-only, URI-addressable data, app-controlled context. (b) **Tool** — it mutates state (a side effect), model-controlled. (c) **Prompt** — a user-invoked parameterized template. (d) **Resource** — read-only contents by URI. The tell is side-effect + controller: only (b) changes state, so only (b) is a tool.
</details>

2. Write the JSON-RPC **request** a host would send to read the resource `note://128`. Which `method` and `params`?

<details>
<summary>Solution</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "resources/read",
  "params": { "uri": "note://128" }
}
```

Method is `resources/read`; `params` carries the `uri`. The response comes back with `id: 7` and a `result` containing the note's contents.
</details>

3. Someone models "run this saved database query and return the rows" as a **prompt** because it feels like a canned template. Why is that the wrong primitive?

<details>
<summary>Solution</summary>

A prompt is a *text template the user invokes* — it has **no side effects and doesn't execute anything**. "Run a query and return rows" **executes** against the database (and, depending on the query, may change state or expose data). That's an **action the model can invoke**, so it's a **tool** — and if the query can write, it needs guardrails. Prompts start conversations; tools do work.
</details>
