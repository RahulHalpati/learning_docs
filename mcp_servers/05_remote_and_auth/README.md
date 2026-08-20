# Section 05 · Remote & authenticated servers

> **Prerequisites:** [04 · Tools over real systems](../04_real_backends/README.md) · **Time:** ~5 h

So far notevault has been a local stdio subprocess — one user, one laptop, no auth. This section takes it **remote**: it moves to **streamable HTTP** so many users and agents can share one deployment, adopts the **stateless spec (2026-07-28)** so the server scales horizontally behind a plain load balancer, and puts it behind **OAuth 2.1** as a resource server that *verifies* bearer tokens (it never issues them). This is the section that leans hardest on your FastAPI background — you're deploying an ASGI service, just one that speaks MCP.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 05-1 | [From stdio to streamable HTTP](01_streamable_http_and_stateless.md) | How do I serve one server to many clients — and why did 2026 make it stateless? |
| 05-2 | [OAuth 2.1 & the resource server](02_oauth2_resource_server.md) | How do I verify tokens and scope tools without becoming an auth server? |
| 05-3 | [Deployment shape & scaling](03_deploy_shape_and_infra.md) | How do I run it in production behind a load balancer? |

## Mini-project

**Take notevault remote and protect it.** Serve the notevault server you built in Section 04 over **streamable HTTP in stateless mode**, mounted inside (or behind) an ordinary ASGI app, and turn it into an **OAuth 2.1 resource server**.

Requirements checklist:

- [ ] Runs over **streamable HTTP** (not stdio), reachable at `/mcp`.
- [ ] **Stateless** — no `Mcp-Session-Id`, no server-side session store; every request is self-describing.
- [ ] **Mounted in an ASGI app** (Starlette or FastAPI) alongside a `/healthz` endpoint, so it deploys like any web service you already know.
- [ ] Acts as an OAuth 2.1 **resource server**: a `TokenVerifier` verifies incoming **bearer tokens** and returns an `AccessToken` (with scopes) or `None`. It **issues no tokens**.
- [ ] Publishes **Protected Resource Metadata** (RFC 9728) at `/.well-known/oauth-protected-resource` so clients can discover the authorization server.
- [ ] **Scopes gate tools:** read tools require `notes:read`; write tools require `notes:write`. An unauthenticated call gets **401**; a token missing the scope gets **403**.
- [ ] Works behind a **round-robin load balancer** with **no session affinity** — two consecutive requests can land on two different replicas and both succeed.
- [ ] All secrets (issuer URL, expected audience, CORS origins) come from **environment variables**, never literals.

You're proving you can ship an MCP server the same way you'd ship a FastAPI service: stateless, authenticated, horizontally scalable.

## Test task (gate)

You're handed `insecure_server.py` — an HTTP MCP server a teammate wrote in a hurry. It "works," but it has **four** security flaws. Your job: **name each flaw with the concrete attack it enables, then fix it.**

```python
# insecure_server.py — DO NOT SHIP. Four flaws to find.
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request

mcp = FastMCP("notevault")

# (A) Identity comes from a request header the caller sets themselves.
def current_user(req: Request) -> str:
    return req.headers.get("X-User", "anonymous")

# (B) There is no token verification anywhere. Anyone who can reach the
#     URL is "authenticated."

# (C) The server mints its own tokens.
@mcp.tool()
def login(username: str) -> str:
    return make_token(username)  # hand-rolled JWT, signed with a local secret

# (D) A destructive write tool with no scope check.
@mcp.tool()
def delete_all_notes() -> str:
    db.execute("DELETE FROM notes")
    return "deleted"
```

Name the flaw, the attack, and the fix for each:

1. **Header-trust identity** (`X-User`) — the caller sets their own identity, so anyone spoofs any user by sending `X-User: alice`. **Fix:** derive identity from the *verified token's* subject, never a header; drop the header entirely.
2. **No token verification** — the server never checks a bearer token, so an anonymous internet caller has full access. **Fix:** wire a `TokenVerifier`; require a valid `Authorization: Bearer …` on every request.
3. **The server issues tokens** (`login`) — an MCP server is a **resource server**, not an authorization server. Minting your own tokens means you're now a second, weaker IdP and a confused deputy waiting to happen. **Fix:** delete `login`; document that an **external IdP** issues tokens and the server only verifies them, advertising the IdP via Protected Resource Metadata (RFC 9728).
4. **Unscoped write tool** (`delete_all_notes`) — any authenticated caller, however weakly authorized, can wipe the database. **Fix:** require the `notes:write` scope; a token without it gets **403**.

**You pass when** you've named each of the four flaws with its attack *and* produced a transcript showing:

- an **unauthenticated** call (no/invalid token) → **401 Unauthorized** with a `WWW-Authenticate` header pointing at your Protected Resource Metadata, and
- an **under-scoped** call (valid token, but only `notes:read`) hitting a write tool → **403 Forbidden**.

<details>
<summary>Why "the server issues tokens" is the subtle one</summary>

The other three flaws are obviously insecure. Token issuance *feels* helpful — "I'll just let the server log people in." But it inverts the trust model: an OAuth 2.1 resource server's entire job is to **verify** tokens minted by a trusted authorization server. If the resource server also issues them, it holds signing keys, owns a user store, and becomes an attack surface no one audited. Worse, a token your notevault issued might be replayed against *another* resource server — the **confused-deputy** problem. Resource servers verify; authorization servers issue. Keep the roles separate. Section 06 goes deeper.
</details>

## What you'll be able to do

- Run a FastMCP server over **streamable HTTP** and **mount it in a FastAPI/Starlette app** next to your own routes and health checks.
- Explain the **2026-07-28 stateless model** — no handshake, no session id, self-describing requests, MRTR for server→client asks — and *why* it lets an MCP server scale like any stateless web service.
- Stand up an OAuth 2.1 **resource server**: implement a `TokenVerifier`, publish **Protected Resource Metadata**, and return correct **401 vs 403**.
- **Scope tools** so read and write require different OAuth scopes.
- Deploy the stateless server behind a **round-robin load balancer** with no session affinity, with CORS, health checks, and env-based secrets.

→ Start: **[05-1 · From stdio to streamable HTTP](01_streamable_http_and_stateless.md)**
