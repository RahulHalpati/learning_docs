# 03-3 · OpenAPI tools

> **Level:** Intermediate · **Prerequisites:** [03-1 · Function tools](01_function_tools.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0; import verified, calls need a live API)

## Why this matters

Most useful APIs already have an **OpenAPI** (Swagger) spec. Instead of hand-writing a function tool per endpoint, ADK's `OpenAPIToolset` reads a spec and generates **one tool per operation** automatically. Point it at a spec and your agent can call the whole API.

---

## Generate tools from a spec

```python
from google.adk.tools.openapi_tool import OpenAPIToolset      # verified import

spec = """
openapi: 3.0.0
info: {title: Pet API, version: 1.0.0}
servers: [{url: http://localhost:8080}]
paths:
  /pets/{petId}:
    get:
      operationId: getPet
      summary: Get a pet by id
      parameters:
        - {name: petId, in: path, required: true, schema: {type: integer}}
      responses: {'200': {description: ok}}
"""

toolset = OpenAPIToolset(spec_str=spec, spec_str_type="yaml")
# agent = LlmAgent(name="pet_agent", model=..., tools=[toolset])
```

`OpenAPIToolset` parses the spec and exposes each `operationId` (here `getPet`) as a callable tool, with parameters derived from the spec. The agent's model picks the operation and fills the parameters; ADK makes the HTTP call to the `servers` URL.

> **Note:** the *import and parsing* are verified offline; actually *calling* `getPet` needs a server listening at the `servers` URL. For a fully local demo, run a tiny mock API (e.g. a FastAPI app) at `http://localhost:8080` and point the spec's `servers` at it — then the generated tool hits your mock, no external service.

---

## When to use it

- The API you're integrating already has an OpenAPI/Swagger spec.
- You'd otherwise write many near-identical function tools (one per endpoint).
- You want parameter validation and descriptions to come straight from the spec.

For one or two endpoints, a plain function tool (03-1) is simpler. For a whole API surface, `OpenAPIToolset` saves you from maintaining a wrapper per operation.

> **Tip:** Combine with auth: `OpenAPIToolset` accepts auth schemes so generated tools carry the right credentials (API key, OAuth) on each call.

---

## Recap & next

- ✅ `OpenAPIToolset(spec_str=..., spec_str_type="yaml")` turns a spec into one tool per operation.
- ✅ Parameters and descriptions come from the spec; ADK makes the HTTP calls.
- ✅ Use it for whole APIs; a function tool is simpler for one endpoint. Point `servers` at a local mock to demo offline.
- ✅ Self-check: what in the spec becomes each tool's name?

→ Next: **[03-4 · MCP tools](04_mcp_tools.md)**

## Exercises

1. Sketch (or run against a local FastAPI mock) an agent that uses a `getPet` tool generated from the spec above.

<details>
<summary>Solution</summary>

Run a FastAPI app exposing `GET /pets/{petId}` at `localhost:8080`, build the `OpenAPIToolset` above, give it to an `LlmAgent`, and ask "get pet 7". The model calls `getPet(petId=7)` and ADK hits your local mock.
</details>
