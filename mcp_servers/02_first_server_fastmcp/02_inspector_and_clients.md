# 02-2 · The Inspector & wiring a host

> **Level:** Beginner · **Prerequisites:** [02-1 · Install & your first tool](01_install_and_first_tool.md)
> **Time:** ~35 min · **Verified:** 2026-08-08 (FastMCP · MCP Inspector · Python 3.12 · uv)

## Why this matters

Your server runs over stdio and *waits* — you can't test it by typing at it. You need a client. The one you'll reach for a hundred times is the **MCP Inspector**: the official dev UI that connects to a server, lists its tools/resources/prompts, shows you the exact generated schema, and lets you call a tool by filling in a form. It matters because it lets you debug the **contract** — the schema the model will read — *before any model is involved*. A wrong schema is cheap to catch here and expensive to catch when a model is silently skipping your tool in production.

---

## Launch the Inspector

FastMCP ships a `dev` command that boots your server and opens the Inspector against it in one step:

```bash
uv run fastmcp dev server.py
```

It prints a local URL — open it in a browser:

```
MCP Inspector running at http://127.0.0.1:6274
```

There's also a transport-agnostic launcher if you prefer it — it wraps any command that starts a stdio server:

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

Either way you get the same browser UI at roughly `http://127.0.0.1:6274`. The Inspector is the *client* here; it spoke the `initialize` handshake and `tools/list` for you the moment it connected.

---

## What the Inspector shows

The UI has a tab per primitive — **Tools**, **Resources**, **Prompts** (you've only got tools so far). Open **Tools** and you'll see:

- **`create_note`** in the list, with its **description** (your docstring) shown inline.
- Click it, and the panel renders the **input schema** as a form: a `title` field, a `body` field, an optional `tags` field — each derived from your type hints. There's a raw-schema view too, showing the exact JSON from [02-1](01_install_and_first_tool.md).

This is the single most useful habit in the section: **the Inspector is a window onto the contract.** What you see here is, byte for byte, what a model would see. If a parameter's purpose is unclear *to you* reading this form, it's unclear to the model too.

---

## Call a tool by hand

Fill the form and run it — no LLM, no chat, just you sending a `tools/call`:

- In `create_note`, type `title: Standup`, `body: Shipped 02-1`, leave `tags` empty, and hit **Run**.
- The result panel shows the response: the **structured output** — a `Note` object with a generated `id`, your `title`/`body`, and `tags: []`.
- Add a second note, then switch to `search_notes` (once you've built it) and run `query: standup` — you should get the first note back.

You just exercised the whole round trip — request in, structured result out — the same path the model takes, minus the model. When a tool misbehaves, this is where you reproduce it deterministically.

---

## Wire it into a real host

The Inspector proves the server works. To use it for real, a **host** launches it as a stdio subprocess. The canonical wiring is a JSON config with an `mcpServers` object mapping a name to a **command** and its **args**. For Claude Desktop, edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "notevault": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/to/notevault", "server.py"]
    }
  }
}
```

- **`command` + `args`** are literally the process the host spawns and pipes stdio to — the exact `uv run server.py` you ran yourself, expressed as a command and its arguments.
- **`--directory /abs/path/...`** tells `uv` which project to run in. The host launches from its own working directory, not yours, so **paths must be absolute** and you should pin the project dir — the most common "my server won't connect" bug is a relative path.
- **The name** (`notevault`) is how the server appears in the host's UI.

Restart Claude Desktop and its tool menu will list `notevault`'s tools. This same `mcpServers` shape — a name → `{command, args}` — is what **any MCP-compatible host** (IDEs, other desktop apps) uses to launch a stdio server; the keys are standard.

> **Security reminder from Section 01.** That config launches a process on your machine with your privileges. Only wire in servers whose code you trust — the host runs whatever `command` you give it.

---

## The debugging loop

Building tools is iterative, and the loop is short:

1. **Change** the tool — rename a param, rewrite the docstring, add a `Field(description=...)`.
2. **Reload** the server. In the Inspector there's a reconnect/restart control; for a host like Claude Desktop, restart the app so it re-launches the subprocess and re-reads the schema.
3. **Re-test** in the Inspector — confirm the schema now reads the way you intend, and re-run the call.

Do this loop in the **Inspector**, not in a chat with a model. Debugging against a live model is slow and non-deterministic: you can't tell whether a bad result came from your schema, the model's mood, or the prompt. The Inspector removes the model as a variable — you're testing the contract in isolation. Only once the schema and calls are right in the Inspector do you bring a model in.

---

## Recap & next

- ✅ The **MCP Inspector** is the official dev client — launch it with `uv run fastmcp dev server.py` (or `npx @modelcontextprotocol/inspector uv run server.py`) and open `http://127.0.0.1:6274`.
- ✅ It lists your tools, shows the **exact generated schema** as a form, and lets you **call a tool by hand** — no model involved.
- ✅ A host launches a stdio server via an **`mcpServers`** config: a name → `{ "command": "uv", "args": ["run", "--directory", "/abs/path", "server.py"] }`. Use **absolute paths**.
- ✅ The debugging loop is **change → reload → re-test in the Inspector** — you debug the *contract* before any model sees it.
- ✅ Self-check: why is debugging a tool's schema against a live model slower and less reliable than using the Inspector?

→ Next: **[02-3 · Tool design is contract design](03_tool_design_contract.md)**

## Exercises

1. Point Claude Desktop (or any MCP host you have) at your notevault server, restart it, and confirm the tools appear. If they don't, what are the first two things to check in the config?

<details>
<summary>Solution</summary>

First: the **path is absolute** and correct — a relative path or a typo means `uv` can't find the project, so the subprocess dies on launch and the host shows no tools. Second: `uv` is **on the host's `PATH`** (or use its absolute path as `command`) — the host spawns the process in its own environment, which may not have your shell's `PATH`. Checking the host's MCP logs usually shows the exact spawn error.
</details>

2. In the Inspector, call `create_note` with a `title` but omit `body`. What happens, and which part of the schema caused it?

<details>
<summary>Solution</summary>

The call is **rejected with a validation error** before your function runs — `body` is in the schema's `required` list (it's a non-defaulted `str`), so the client/server rejects a call that's missing it. The schema *is* the validation: `required: ["title", "body"]` is enforced, which is exactly why accurate hints matter.
</details>

3. Why does the Inspector let you catch a "the model won't call my tool" problem *even though there's no model in the Inspector*?

<details>
<summary>Solution</summary>

Because the model's only input is the **schema**, and the Inspector shows you that exact schema. If, reading the Inspector's form, *you* can't tell what a tool does or what a parameter should hold, neither can the model — it reads the same JSON. The Inspector surfaces contract problems (missing description, vague params, no output shape) directly, so you fix them without the cost and noise of a live model.
</details>
