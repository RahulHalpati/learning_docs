# 04-3 · Composition & OpenAPI

> **Level:** Intermediate · **Prerequisites:** [04-2 · Robust tools: errors, limits & progress](02_robust_tools.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-08 (FastMCP · aiosqlite/asyncpg · httpx · Python 3.12)

## Why this matters

One giant `server.py` with forty tools is as unpleasant to maintain as one giant `main.py` with forty routes. FastMCP lets you build a big server out of small **sub-servers** — the same modularity your FastAPI routers gave you. And when you *already have* a FastAPI service (you built one in the [fastapi_complete course](../../fastapi_complete/README.md)), you can generate an MCP server from it directly instead of hand-writing tools that duplicate your endpoints. Both are leverage — used carelessly, both also let you expose far more surface than you should.

---

## Compose: mount vs. import

Split notevault into focused sub-servers — one per concern — then assemble them:

```python
from fastmcp import FastMCP

notes_mcp = FastMCP("notes")     # get_note, search_notes, create_note ...
admin_mcp = FastMCP("admin")     # import_notes, purge_old ...
# ... define each sub-server's tools/resources ...

app = FastMCP("notevault")       # the composed server clients actually connect to
app.mount(notes_mcp, prefix="notes")               # LIVE link
await app.import_server(admin_mcp, prefix="admin") # STATIC copy
```

Two ways to combine, and the difference matters:

- **`mount`** creates a **live link**. The parent forwards calls to the sub-server at request time, so changes to the sub-server (even added tools) show up immediately. Use it for composing servers you keep as living modules.
- **`import_server`** takes a **static copy** at import time. The sub-server's tools are flattened into the parent once; later changes to the sub-server don't propagate. Use it to snapshot a stable set of tools.

The `prefix` namespaces things so two sub-servers can each have a `list` tool without colliding — you get `notes_list` and `admin_list` (and prefixed resource URIs). 

> **API note.** FastMCP's exact signatures for `mount`/`import_server` (positional vs. keyword `prefix`, sync vs. async) have shifted across 2.x releases. The concept is stable — *live link vs. static copy, namespaced by prefix* — so check the shapes against your installed version; the pattern here is what to remember.

---

## The bigger lever: expose a service you already built

You already shipped a notevault (or taskflow) **FastAPI** app with routes, Pydantic schemas, and validation. FastMCP can turn that app into an MCP server without you re-writing any of it:

```python
from fastmcp import FastMCP
from notevault_api.main import app as fastapi_app   # your FastAPI app from fastapi_complete

# Every route becomes an MCP tool; Pydantic request/response models become the tool schemas.
mcp = FastMCP.from_fastapi(app=fastapi_app)
```

FastMCP walks the app's routes, reads their path/query/body parameters and response models straight from the existing OpenAPI metadata, and generates a tool per operation. Your `POST /notes` becomes a `create_note`-shaped tool with the same validation you already wrote. This is the pragmatic path: **don't build the same logic twice — expose the service you have.**

---

## From a raw OpenAPI spec

Same idea when the service isn't a local FastAPI object but a remote API you only have the **OpenAPI spec** for. Point FastMCP at the spec and an `httpx` client that knows the base URL and auth:

```python
import httpx
from fastmcp import FastMCP

spec = httpx.get("https://api.example.com/openapi.json").json()
client = httpx.AsyncClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer ..."},   # the API's own auth, held server-side
)
mcp = FastMCP.from_openapi(openapi_spec=spec, client=client)
```

Each operation in the spec becomes a tool; calling the tool makes the real HTTP request through your `client`. The credentials live on the *server*, never in the model — the model calls `list_widgets`, FastMCP makes the authenticated request for it.

---

## The catch: auto-generated ≠ ready

Generation gives you *coverage*, not *curation*. Two problems you must fix before shipping an auto-generated server:

- **Descriptions are usually bad.** Tools inherit their name and description from `operationId` and route docstrings, which are often terse or machine-junk (`get__notes__id_v2`). A model chooses tools by their descriptions — a vague one is an unusable tool. Rewrite names and descriptions to say *what the tool does and when to use it*.
- **Not every endpoint should be a tool.** Your API has admin routes, internal health checks, bulk deletes, and destructive operations. Exposing all of them to a model is the opposite of **least privilege**. Curate: include only what the model needs, and exclude the dangerous surface.

FastMCP supports **route mapping** to include/exclude endpoints (by path pattern, method, or tag) at generation time — the mechanism's exact shape varies by version, but the principle is fixed:

```python
# Illustrative — check your FastMCP version for the exact route-map API.
# Exclude admin + destructive routes; expose only the read/create surface a model needs.
mcp = FastMCP.from_fastapi(
    app=fastapi_app,
    route_maps=[
        exclude(path=r"^/admin/.*"),      # never expose admin routes as tools
        exclude(methods=["DELETE"]),      # no auto-generated destructive tools
    ],
)
```

Treat auto-generation as a *starting point*: generate broadly, then delete, rename, and re-describe until what's left is a small, well-labeled, least-privilege toolset. A curated server of eight good tools beats a generated one of eighty mystery tools every time.

---

## Recap & next

- ✅ Build big servers from small **sub-servers**; assemble with `mount` (**live link**) or `import_server` (**static copy**), namespaced by `prefix`.
- ✅ Turn an existing service into MCP with **`FastMCP.from_fastapi(app=...)`** — reuse the routes, schemas, and validation you already wrote in fastapi_complete.
- ✅ **`FastMCP.from_openapi(openapi_spec=..., client=...)`** does the same for a remote API from its spec; credentials stay server-side.
- ✅ Auto-generation gives coverage, not curation: **rewrite bad descriptions** and **exclude endpoints** that shouldn't be tools (least privilege).
- ✅ Exact `mount`/`import_server`/route-map signatures shift across FastMCP 2.x — hold the *concepts*, check the version.
- ✅ Self-check: you generate 80 tools from your FastAPI app in one line. Name the two things you must still do before it's safe to expose.

→ Next: **[05 · Remote servers & auth](../05_remote_and_auth/README.md)**

## Exercises

1. You have a FastAPI app with these routes: `GET /notes`, `POST /notes`, `GET /notes/{id}`, `DELETE /notes/{id}`, `POST /admin/purge-all`. Which should become MCP tools for a note-taking assistant, and which must you exclude? Justify with least privilege.

<details>
<summary>Solution</summary>

Expose the read and create surface a note assistant actually needs: `GET /notes` (→ a *paginated* search/list tool — cap the result per 04-2), `POST /notes` (create), `GET /notes/{id}` (fetch one). Exclude `POST /admin/purge-all` outright — a mass-destructive admin action has no business being model-callable. `DELETE /notes/{id}` is a judgment call: exclude it, or expose it only behind human-in-the-loop approval (Section 06). Least privilege means the default is *exclude*, and you add back only what the assistant's job requires.
</details>

2. When would you `mount` a sub-server rather than `import_server` it?

<details>
<summary>Solution</summary>

`mount` when the sub-server is a living module you'll keep changing and want those changes reflected without re-assembling the parent — a live link, evaluated at request time. `import_server` when you want a stable snapshot: copy the sub-server's tools into the parent once, and later changes to the sub-server don't leak in. Live composition vs. a frozen copy.
</details>
