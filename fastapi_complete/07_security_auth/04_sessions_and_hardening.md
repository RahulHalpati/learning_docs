# 07-4 · Sessions & hardening

> **Level:** Intermediate · **Prerequisites:** [07-3 · Refresh tokens & RBAC](03_refresh_tokens_rbac.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · PyJWT · pwdlib/Argon2)

## Why this matters

JWTs aren't the only answer — cookie sessions are older, simpler, and for browser-first apps often *better*. But cookies change the threat model: the browser attaches them automatically, which is exactly what **CSRF** exploits, and **XSS** will happily read anything JavaScript can. This lesson covers the cookie flags, CSRF reasoning, and the header/logging/error hygiene that separates an auth module that passes review from one that pages you at 3am.

---

## Cookie sessions: the JWT alternative

Instead of a signed token, the server stores the session and hands the browser only an unguessable id:

```python
# app/api/routers/auth.py — session-cookie login (alternative to /auth/token)
import secrets
from fastapi import Response

@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()],
                db: DbSession, response: Response) -> None:
    user = await user_service.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    session_id = secrets.token_urlsafe(32)        # 256 bits — unguessable
    await session_store.set(session_id, user.id)  # server-side: id → user (Redis, Section 08)
    response.set_cookie(
        "session_id", session_id,
        httponly=True,   # JS can't read it → XSS can't exfiltrate the session
        secure=True,     # HTTPS only → can't be sniffed on open Wi-Fi
        samesite="lax",  # not sent on cross-site POSTs → blunts CSRF
        max_age=60 * 60 * 24 * 14,
    )
```

Each flag is a control against a named attack:

- **`HttpOnly`** — an XSS payload runs `document.cookie` and gets nothing; the session can't be stolen through script injection. (JWTs kept in `localStorage` have no such shield.)
- **`Secure`** — the cookie never travels over plain HTTP, so a network attacker can't sniff it.
- **`SameSite=lax`** — cross-site form POSTs and fetches don't carry the cookie; `strict` extends that to top-level navigation (safer, but breaks "arrive logged-in via external link" — pick per app).

---

## Sessions vs JWTs: when each wins

| | Cookie sessions | JWTs |
|---|---|---|
| Revocation | **instant** — delete the server record | wait for `exp`, or run a denylist |
| Server state | required (session store) | none (until you add the denylist…) |
| Multiple services / mobile | needs a shared store & cookies | any client sends a header; services share only the key |
| Browser XSS exposure | `HttpOnly` shields it | script-readable if kept in JS-accessible storage |
| CSRF exposure | yes — needs the defenses below | no (pure Bearer header) |

Rule of thumb: **browser-first app, one backend → sessions** (instant revocation, `HttpOnly`, decades of boring reliability). **Multiple services, mobile/CLI clients, third-party API consumers → JWTs.** And be honest about the classic "JWTs are stateless" argument: the moment you added a Redis denylist for logout in 07-3, you were running a session store anyway — at that point the gap narrows to "which default do you want", not "state vs no state".

---

## CSRF: why cookies need it and Bearer headers don't

**The attack:** you're logged into `linkbox.app`; you visit `evil.site`, which auto-submits a hidden form to `https://linkbox.app/links/my-slug/delete`. The browser *attaches your session cookie automatically* — the request arrives authenticated, and the server can't tell it wasn't you.

- **Cookie auth is vulnerable** because the credential travels with *every* request the browser makes, no matter which site initiated it. Defenses: `SameSite=lax/strict` (first line), plus a CSRF token (a random value the page must echo back in a header or field — `evil.site` can't read your page, so it can't supply it) for anything `SameSite` doesn't cover.
- **Pure Bearer-header JWT APIs are not** — `evil.site` can trigger requests, but it cannot set your `Authorization` header: the token lives in your app's JS memory, and cross-origin script can't reach it. No auto-attached credential, no CSRF.

The corollary that bites teams: put a JWT *in a cookie* and you've bought cookie-CSRF exposure back. The vulnerability follows the transport, not the token format.

---

## Security headers middleware

Three headers cost ten lines and each kills an attack class:

```python
# app/main.py
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # Browsers refuse plain-HTTP for your domain → stops SSL-stripping downgrades.
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # Browsers won't "sniff" a response into a different content type →
    # stops an uploaded .txt being executed as HTML/JS.
    response.headers["X-Content-Type-Options"] = "nosniff"
    # No site may embed you in an iframe → stops clickjacking
    # (invisible frame over a decoy page harvesting your users' clicks).
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response
```

---

## Rate-limiting login (preview)

Argon2 defends against *offline* cracking; **online brute force and credential stuffing** (replaying leaked email:password lists against your `/auth/token`) are defeated by rate limiting — per-IP and per-account counters with a backoff. The counters need shared state, so the real implementation lands with Redis in **Section 08**; the design decision to make now is simply that `/auth/token` *will* be rate-limited, so don't build clients that hammer it.

---

## The hardening checklist

Run down this list before calling any auth module done:

- [ ] **Secrets from the environment, typed `SecretStr`** — never a literal in code, never printable by accident:

  ```python
  class Settings(BaseSettings):
      secret_key: SecretStr          # repr → '**********'; unwrap only at sign/verify
  ```

- [ ] **Never log tokens or passwords** — a token in a log line is a credential leak with retention; log the `jti` or user id instead.
- [ ] **401 vs 403 used correctly** — 401 "authenticate" (with `WWW-Authenticate: Bearer`), 403 "authenticated but not allowed". Clients key retry/re-login behavior off this.
- [ ] **Generic login errors** — "Incorrect email or password" for both failure modes; distinct messages (or measurably different timings) let attackers enumerate registered emails.
- [ ] **`algorithms` pinned, `exp` required** on every `jwt.decode` (07-2); **`secrets.compare_digest`** for every raw secret comparison (07-1).
- [ ] **Cookie flags** on any auth cookie: `HttpOnly`, `Secure`, `SameSite`.

---

## Recap & next

- ✅ Cookie sessions: server-side state + unguessable id; `HttpOnly` (XSS), `Secure` (sniffing), `SameSite` (CSRF).
- ✅ Sessions win for browser-first apps (instant revocation); JWTs win across services and non-browser clients — and a Redis denylist erodes the "stateless" half of that argument.
- ✅ CSRF follows the *transport*: auto-attached cookies need defenses; a Bearer header can't be set cross-origin.
- ✅ HSTS, `nosniff`, and `frame-ancestors` — ten lines of middleware, three attack classes down.
- ✅ Hygiene: `SecretStr` settings, no tokens in logs, 401 vs 403, generic login errors, login rate-limiting coming in Section 08.
- ✅ Self-check: your SPA keeps its JWT in `localStorage` and sends it as a Bearer header — which of XSS and CSRF is it exposed to, and why exactly that one?

→ Next: **[Section 08 · Redis, caching & jobs](../08_redis_caching_jobs/README.md)**

## Exercises

1. A code review shows `response.set_cookie("session_id", sid, secure=True)` — `httponly` and `samesite` omitted. Name the attack each omission enables.

<details>
<summary>Solution</summary>

Without `httponly` (defaults to false), any XSS payload reads `document.cookie` and exfiltrates the session — full account takeover from one injected script. Without an explicit `samesite`, you're relying on browser defaults; a cross-site form POST may carry the cookie, enabling CSRF on every state-changing endpoint. `secure=True` alone only covers the network-sniffing case.
</details>

2. Your team moves the SPA's JWT from `localStorage` into a cookie "for security". What did they gain, what did they buy, and what must they add?

<details>
<summary>Solution</summary>

Gained: with `HttpOnly` set, XSS can no longer read the token — the main weakness of `localStorage` is closed. Bought: the browser now auto-attaches the token to cross-site requests, so the API is CSRF-exposed for the first time. Must add: `SameSite=lax/strict` on the cookie plus a CSRF token for anything SameSite doesn't cover — the protection has to move because the transport moved.
</details>

3. Curl your API and inspect the response headers. Add the security-headers middleware, curl again, and explain in one line each what changed for an attacker.

<details>
<summary>Solution</summary>

`curl -i http://localhost:8000/health` before: none of the three headers. After: `Strict-Transport-Security` — browsers pin HTTPS, so a coffee-shop MITM can't downgrade users to plain HTTP; `X-Content-Type-Options: nosniff` — a user-uploaded file served as `text/plain` can't be reinterpreted and executed as HTML/JS; `Content-Security-Policy: frame-ancestors 'none'` — no attacker page can iframe your app to steal clicks. (HSTS only takes effect over HTTPS, so verify that one against your deployed TLS endpoint.)
</details>
