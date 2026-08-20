# 07-2 · Packaging & deploy

> **Level:** Intermediate → Advanced · **Prerequisites:** [07-1 · Testing MCP servers](01_testing_mcp_servers.md)
> **Time:** ~45–55 min · **Verified:** 2026-08-08 (FastMCP Client · pytest · Docker · Python 3.12)

## Why this matters

How you ship an MCP server depends entirely on its transport, and the two models are genuinely different products. A **stdio** server isn't a service at all — it's a *command the host launches* on demand, so you ship it the way you'd ship a CLI. An **HTTP** server *is* a service — many clients hit one shared process — so you ship it the way you'd ship any web app: a container. Pick the wrong distribution model and you'll try to `docker run` something that was meant to be `uvx`-ed, or expose a subprocess to the internet. Get it right and notevault drops into a host with one line of config.

---

## Two distribution models

| | **stdio server** | **HTTP server** |
|---|---|---|
| What it is | A command the host **spawns** | A long-running **web service** |
| Runs where | On the user's machine, per session | On a server, shared by many clients |
| Lifecycle | Host starts/stops it | You deploy/scale/restart it |
| Ship as | A runnable command (entry point) | A **container image** |
| Install | `uvx notevault` / `uv run` | `docker run` behind a URL |
| Config | Host's `mcpServers` JSON | Env vars at runtime |

The rule of thumb from Section 01: **one user on a laptop → stdio**; **many users on a shared endpoint → HTTP.** notevault ships *both ways* from the same code — the only difference is the transport you start.

---

## Shipping the stdio server: a runnable command

A stdio server is distributed like any Python CLI: declare an **entry point** in `pyproject.toml` so `uvx`/`pipx` can run it by name without the user cloning anything.

```toml
# pyproject.toml
[project]
name = "notevault"
version = "0.1.0"                      # versioning matters — clients pin this
requires-python = ">=3.12"
dependencies = ["fastmcp>=2"]

[project.scripts]
notevault = "notevault.server:main"    # `notevault` → calls main()
```

```python
# notevault/server.py
def main() -> None:
    # stdio is the default transport: read JSON-RPC on stdin, write on stdout.
    mcp.run()                          # equivalently: mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
```

Now anyone can run it with no install step — `uvx notevault` fetches and launches it in one shot. The **host** launches it via its config, pointing at that command:

```json
// A host's mcpServers config (Claude Desktop-style). The host owns the process.
{
  "mcpServers": {
    "notevault": {
      "command": "uvx",
      "args": ["notevault"],
      "env": { "NOTEVAULT_DB": "/home/me/notes.db" }
    }
  }
}
```

That's the whole distribution story for stdio: publish the package, and the host spawns your command over stdio. No ports, no Dockerfile, no deploy.

---

## Shipping the HTTP server: a container

The stateless HTTP server (Section 01's 2026 model) is a normal web service, so it ships as a container — and you already built this exact image in the [fastapi_complete Docker lesson](../../fastapi_complete/11_production_docker_cicd/01_docker_multistage.md). Same skills: multi-stage uv build, `python:3.12-slim` runtime, non-root user, healthcheck. Only the process at the end changes.

First, give the server a health endpoint to probe and a run entry that starts HTTP:

```python
# notevault/server.py
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# FastMCP lets you add plain HTTP routes alongside the MCP endpoint.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")

def serve_http() -> None:
    # Stateless streamable HTTP → scales behind a plain load balancer (Section 01).
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

Configure statelessness once on the server so every request stands alone:

```python
from fastmcp import FastMCP
mcp = FastMCP("notevault", stateless_http=True)   # no session to pin to one worker
```

---

## The Dockerfile

```dockerfile
# ---------- Stage 1: builder — has uv, builds the venv ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy   # precompile; copy across cache mount
WORKDIR /app

# Dependencies FIRST — this layer rebuilds only when the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Source AFTER — editing a tool never invalidates the dependency layer.
COPY notevault/ notevault/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev            # --frozen: exactly what you tested; --no-dev: no pytest

# ---------- Stage 2: runtime — slim, no uv, no cache, non-root ----------
FROM python:3.12-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app

# Only the venv and the code cross the stage boundary.
COPY --from=builder --chown=app:app /app/.venv .venv
COPY --from=builder --chown=app:app /app/notevault notevault

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1                     # logs reach stdout immediately

USER app                                   # never run as root — defense in depth
EXPOSE 8000

# slim has no curl — probe the health route with the Python that's already here.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

# Exec form: the server is PID 1 and receives SIGTERM directly (clean shutdown).
CMD ["python", "-c", "from notevault.server import serve_http; serve_http()"]
```

Everything here is the fastapi_complete pattern reused verbatim — the only MCP-specific line is the `CMD` starting the HTTP transport instead of uvicorn. (You could equally `CMD ["fastmcp", "run", "notevault/server.py:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]` — the `fastmcp` CLI does the same thing.)

---

## Secrets and env — at runtime, never in a layer

The one rule that ends careers: **config enters the container at runtime, never at build time.** A `COPY .env` bakes your token into a layer forever — `docker history` hands it to anyone who can pull the image. So keep a `.dockerignore` and inject env when you run:

```
# .dockerignore
.venv/        .git/        .env      .env.*
tests/        __pycache__/ *.pyc     .pytest_cache/
```

notevault reads its auth token and DB path from the environment (Section 06), so they arrive at `docker run` time:

```bash
docker build -t notevault .
docker images notevault                       # size — well under a slim+venv budget
docker run --rm -p 8000:8000 --env-file .env notevault   # secrets at RUNTIME
docker ps                                     # STATUS → (healthy) after ~10 s
```

---

## Verify it's actually serving

A healthcheck says the process is up; a real request says the *protocol* works. Point a FastMCP Client at the running container (this is the on-ramp to 07-3):

```bash
# In another terminal, hit the MCP endpoint over HTTP:
uv run python -c "
import asyncio
from fastmcp import Client

async def main():
    # The HTTP transport is selected by passing a URL. /mcp is the default mount.
    async with Client('http://127.0.0.1:8000/mcp') as client:
        print([t.name for t in await client.list_tools()])

asyncio.run(main())
"
```

If that prints your tool names, the container is genuinely serving MCP over HTTP — not just passing its healthcheck. That's the artifact you deploy: one image, any host with a URL can use it.

---

## Recap & next

- ✅ **Two models:** stdio ships as a **runnable command** (`uvx notevault`, an entry point) the host launches; HTTP ships as a **container**.
- ✅ stdio → one user, host owns the process, config in the host's `mcpServers` JSON. HTTP → shared service, you deploy/scale it.
- ✅ The HTTP image is the **fastapi_complete multi-stage uv build** reused: slim runtime, `--frozen --no-dev`, **non-root**, `HEALTHCHECK` on `/healthz` — only the `CMD` changes.
- ✅ **Secrets at runtime** (`--env-file`), never `COPY`'d into a layer; `.dockerignore` keeps `.env` out.
- ✅ Verify with a real Client call, not just the healthcheck.
- ✅ Self-check: why is `stateless_http=True` what lets the container sit behind an ordinary load balancer?

→ Next: **[07-3 · Consuming from agents](03_consuming_from_agents.md)**

## Exercises

1. You try to `docker run` your stdio server and it just hangs, reading nothing. Why — and what did you actually mean to ship?

<details>
<summary>Solution</summary>

A stdio server reads JSON-RPC from **stdin** and writes to **stdout** — it's a command meant to be *spawned by a host* with a pipe attached, not a service that listens on a port. Run as a bare container it sits blocked on stdin forever. Either ship it as a command (`uvx notevault`, configured in the host's `mcpServers`) so the host drives its stdio, or switch to the **HTTP** transport if you want a long-running containerized service. Same code, different transport, different distribution model.
</details>

2. A teammate adds `COPY .env .env` to the Dockerfile "so it just works." What's the concrete risk, and why doesn't a later `RUN rm .env` fix it?

<details>
<summary>Solution</summary>

The `COPY` writes your auth token into an image **layer**, and layers are permanent — `docker history` and `docker save` can extract it, so anyone who can pull the image has your secret. A later `RUN rm .env` only hides the file in the final filesystem view; the earlier layer still contains it. The only fix is never copying it: `.dockerignore` plus runtime injection (`--env-file`). Config is a runtime concern, not a build artifact.
</details>

3. Your HTTP container reports `(healthy)` but a Client connecting to `http://host:8000/mcp` gets nothing. The healthcheck hits `/healthz` and passes. What's the gap, and why is a Client call the better acceptance test?

<details>
<summary>Solution</summary>

`/healthz` only proves the process is up and can answer a trivial route — it says nothing about whether the MCP endpoint is mounted, the tools registered, or the transport wired correctly. A real `list_tools()` over HTTP exercises the actual protocol path a client uses, so it catches a mounted-but-broken server that a shallow healthcheck waves through. Keep the healthcheck for orchestration, but gate your deploy on a real Client call.
</details>
