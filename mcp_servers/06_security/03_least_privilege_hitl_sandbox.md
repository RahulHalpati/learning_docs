# 06-3 · Least privilege, HITL & sandboxing

> **Level:** Intermediate→Advanced · **Prerequisites:** [06-2 · Prompt injection through tools](02_prompt_injection_through_tools.md)
> **Time:** ~55 min · **Verified:** 2026-08-08 (OWASP LLM Top 10 2025 · MCP spec 2026-07-28)

## Why this matters

Lesson 06-2 ended on an uncomfortable truth: a determined prompt injection eventually gets past the model's judgment. This lesson builds the layers that make that *survivable*. **Least privilege** means a hijacked `fetch_url` has no credential to delete with; a **human-in-the-loop** gate means an irreversible action stops for a person; **sandboxing** contains a tool that executes or fetches; and an **audit log** means you can reconstruct exactly what happened. These are the controls that turn "the model got fooled" into a non-event instead of a breach.

---

## Least privilege #1 — scoped tokens per tool

Section 05 issued OAuth tokens; the security move is to give **each tool its own** narrowly-scoped token instead of one god-token the whole server shares. The delete tool's token grants only delete; the fetch tool's token can't delete at all. Now a hijacked fetch path literally has no capability to invoke — the injection has nothing to reach for.

```python
import secrets

# Per-tool scoped secrets, issued in Section 05. The fetch tool's entry has
# NO delete capability — so a hijacked fetch call can't authorize a delete.
def authorize(tool: str, presented: str, expected: dict[str, str]) -> bool:
    want = expected.get(tool)
    if want is None:
        return False  # unknown tool → no token → denied
    # Constant-time compare — NEVER `==` on secrets (leaks length/prefix via timing).
    return secrets.compare_digest(presented, want)
```

The principle scales down further: don't hand a tool a broad token and trust it to use a slice. Issue the slice.

---

## Least privilege #2 — minimal DB grants and no ambient access

The credential a tool *holds* should be as narrow as the tool's job:

- **Minimal DB grants.** The note-reader tool connects as a role with `SELECT` on `notes` and nothing else — no `INSERT`, no `DELETE`, no `DROP`. Then even a hijacked read tool that's tricked into "delete everything" hits a permission error at the database, not a wiped table. Enforce it in the DB, not just app code.
- **No ambient filesystem or network.** A tool doesn't get the whole disk or the whole internet "just in case." Scope it to the one directory or the allowlisted hosts it needs (below). Ambient reach is blast radius waiting to happen.
- **Per-tenant isolation.** In a multi-user server, a tool call for user A must never be able to read or write user B's data — scope every query by tenant, don't rely on the model to pass the right id.

---

## Least privilege #3 — SSRF allowlists for any fetch/execute tool

A `fetch_url` tool is a server-side request forge waiting to happen: point it at `http://169.254.169.254/…` and it may hand back **cloud instance-metadata credentials**. This is **SSRF**, and the defense is an **allowlist** (not a blocklist — blocklists miss encodings, redirects, and DNS tricks), plus a **resolved-IP check** so a hostname can't secretly point inward:

```python
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_HOSTS = {"api.example.com", "docs.example.com"}  # allowlist, not blocklist

def check_fetch_target(url: str) -> str:
    """Return the URL if safe to fetch, else raise. Blocks SSRF to internal/metadata IPs."""
    parsed = urlparse(url)
    if parsed.scheme != "https":                     # no file://, gopher://, http://
        raise ValueError("only https allowed")
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS:                     # allowlist wins over any cleverness
        raise ValueError(f"host not allowed: {host}")
    # Re-check EVERY resolved IP — defends against a name that resolves inward
    # and against DNS rebinding. 169.254.169.254 is link-local → caught here.
    for *_, sockaddr in socket.getaddrinfo(host, 443):
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("target resolves to an internal address")
    return url
```

Note the belt-and-suspenders: the allowlist blocks unknown hosts *and* the IP check blocks an allowed host that resolves to `10.0.0.0/8`, `127.0.0.1`, or the `169.254.0.0/16` metadata range. Cloud metadata theft via SSRF is a top real-world agent breach — this is the tool that stops it.

---

## Human-in-the-loop — the ultimate backstop

Some actions are **irreversible or externally visible**: delete data, send an email, spend money, run code. For these, no automated defense should be the last word. Require an explicit human "yes" via MCP **elicitation** — the confirm/approve round-trip you built in Sections 03 and 05. Because the approval travels **out of band of the model's token stream**, a hijacked model can't fabricate the "yes" for itself.

```python
DESTRUCTIVE = {"delete_all_notes", "send_email", "run_shell", "transfer_funds"}

async def dispatch(tool: str, args: dict, ctx) -> object:
    # Any tool that deletes, sends, spends, or executes stops for a human.
    if tool in DESTRUCTIVE:
        approved = await ctx.elicit(                       # host asks the USER directly
            prompt=f"Approve {tool}({args})? This cannot be undone.",
        )
        if not approved:
            return {"status": "denied", "tool": tool}       # human said no → stop
    return await run_tool(tool, args)
```

Keep the human's decision *meaningful*: show the concrete action and its arguments (not "the agent wants to do something"), default to deny, and don't fatigue people with approvals for safe reads — gate the destructive/external set, precisely so the rare prompt actually gets read.

---

## Sandboxing & resource limits for execute/fetch tools

A tool that runs code or fetches remote content should run **contained**, so a compromise or a runaway can't take the host with it:

```python
import subprocess

def run_sandboxed(script: str) -> str:
    # Argument list (no shell), hard timeout, and — in real deployments — a
    # container / restricted user with no network and no host credentials.
    result = subprocess.run(
        ["python", "-I", "-c", script],   # -I isolated mode: ignore env & user site
        capture_output=True, text=True,
        timeout=5,                        # kill runaways / infinite loops
        shell=False,                      # never a shell on tool input
        cwd="/sandbox",                   # scoped working dir, not the host root
    )
    return result.stdout[:10_000]         # cap output size too
```

The checklist for any execute/fetch tool: **no `shell=True`** on tool input, a **timeout**, **capped** output size, a **restricted working directory**, and ideally a **container or restricted user** with no ambient network or credentials. Validate and constrain every input at the boundary before it reaches this point.

---

## Audit logging — every tool call, for detection and forensics

You cannot defend what you can't see. Log **one structured line per tool invocation** — who, what, when, with which arguments, and the outcome — so an incident is reconstructable and anomalies (a flurry of denied deletes right after a fetch) are detectable:

```python
import json
import logging
import time

audit = logging.getLogger("mcp.audit")

def log_tool_call(user: str, tool: str, args: dict, result: str) -> None:
    # One line per call. Redact secret-bearing args before logging in real code.
    audit.info(json.dumps({
        "ts": time.time(),
        "user": user,          # authenticated principal (from Section 05)
        "tool": tool,          # what ran
        "args": args,          # inputs (redacted)
        "result": result,      # "ok" | "denied" | "error"
    }))
```

Ship these to a store the tool can't rewrite. When a hijack happens, this log is how you learn *what* the injection tried, *which* layer stopped it, and whether anything got through.

---

## Defense-in-depth checklist

No single control is sufficient — that's the thesis of the whole section. Stack them so an attack must beat *all* of them:

- [ ] **Untrusted-data wrapping + provenance** on every external/user string (06-2).
- [ ] **Output scanning** for injection tells; **return the minimum** (06-2).
- [ ] **Scoped token per tool** — the fetch path can't authorize a delete.
- [ ] **Minimal DB grants**; read tools can't write; **no ambient** filesystem/network.
- [ ] **SSRF allowlist + resolved-IP check** on any fetch/execute tool (blocks `169.254.169.254`).
- [ ] **HITL elicitation** on every destructive / irreversible / external tool.
- [ ] **Sandbox + timeout + output cap**, no `shell=True` on tool input.
- [ ] **Audit log** every call (who/what/when/args/result), to a tamper-resistant store.
- [ ] **Supply chain:** pinned, reviewed, reputable servers only (06-1).

Each row is one independent layer. The delete only lands if *every* relevant layer fails at once — and that's what "production-grade" means here.

---

## Recap & next

- ✅ **Scoped token per tool** — a hijacked fetch path holds no delete capability; compare secrets with `secrets.compare_digest`.
- ✅ **Minimal DB grants, no ambient access, per-tenant isolation** — shrink what each tool *can* do to what it *must*.
- ✅ **SSRF allowlist + resolved-IP check** blocks internal and cloud-metadata endpoints (`169.254.169.254`) — a top real-world agent breach.
- ✅ **HITL via elicitation** is the ultimate backstop for destructive/irreversible/external actions — approval travels out of band, so a hijacked model can't self-approve.
- ✅ **Sandbox + limits** for execute/fetch tools; **audit-log every call** for detection and forensics.
- ✅ Self-check: your server wraps untrusted output *and* has an SSRF allowlist. Why do you still gate `delete_all_notes` behind a human?

→ Next: **[07 · Test, ship & consume](../07_test_ship_consume/README.md)**

## Exercises

1. Your `list_notes` tool connects to Postgres as a superuser "to keep things simple." Give the concrete attack this enables and the one-line fix.

<details>
<summary>Solution</summary>

A prompt injection (or a bug) that gets the read tool to run a destructive statement now executes with full rights — `DROP TABLE notes`, or worse, reading every tenant's data. Fix: connect that tool as a role granted only `SELECT` on the tables it needs; the database rejects any write or DDL regardless of what the model is tricked into asking. Enforce least privilege in the DB, not just the app.
</details>

2. Someone proposes a blocklist for `fetch_url` — reject `localhost`, `127.0.0.1`, and `169.254.169.254`. Name two ways an attacker gets past a blocklist that an allowlist + resolved-IP check would stop.

<details>
<summary>Solution</summary>

Any two: (a) an alternate encoding of the address (`0x7f.0.0.1`, `2130706433`, `[::1]`, `127.0.0.1.nip.io`) that the string blocklist misses; (b) a hostname that *resolves* to an internal IP, or **DNS rebinding** where the name resolves to a safe IP at check time and an internal IP at fetch time; (c) an HTTP redirect from an allowed page to an internal URL. An allowlist (only known-good hosts) plus re-checking **every resolved IP** at fetch time defeats all of these, because you're validating the actual destination, not pattern-matching a string.
</details>

3. Write the elicitation gate so `delete_all_notes` requires approval but `list_notes` doesn't — and justify not gating the read.

<details>
<summary>Solution</summary>

```python
DESTRUCTIVE = {"delete_all_notes", "send_email"}

async def dispatch(tool: str, args: dict, ctx):
    if tool in DESTRUCTIVE:
        if not await ctx.elicit(prompt=f"Approve {tool}({args})?"):
            return {"status": "denied"}
    return await run_tool(tool, args)
```

Reads are gated only by least privilege (a scoped read token, per-tenant queries), not by a human prompt, because (a) they're reversible and non-destructive, and (b) approval fatigue is a real failure mode — if humans must click "yes" for every harmless list, they stop reading the prompts and rubber-stamp the dangerous ones too. Gate the destructive/external set precisely so the rare, consequential approval actually gets attention.
</details>
