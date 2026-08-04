# 04-2 · JWT tokens

> **Level:** Intermediate · **Prerequisites:** [04-1 · Password hashing](01_password_hashing.md)
> **Time:** 40 min · **Verified:** 2026-07-27 (PyJWT 2.13.0)

## Why this matters

HTTP is stateless — every request must prove who's making it. A **JWT** (JSON Web Token) is a signed, self-contained credential the client sends on each request. The server can verify it *without a database lookup* (it checks the signature), which is why JWTs scale. You'll issue two: a short-lived **access** token and a long-lived **refresh** token.

---

## What a JWT is

Three base64 segments joined by dots: `header.payload.signature`. The **payload** holds claims (who, when it expires); the **signature** is an HMAC over the header+payload using your secret. Anyone can *read* a JWT (it's not encrypted), but only someone with the secret can *forge* one.

```python
# app/core/security.py (essentials)
import jwt
from datetime import datetime, timedelta, timezone

def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

```python
tok = create_access_token("42")
print("segments:", tok.count(".") + 1)
print("payload:", decode_token(tok)["sub"], decode_token(tok)["type"])
```

**Output (real run):**
```
segments: 3
payload: 42 access
```

`sub` (subject) is the user id; `type` distinguishes access vs refresh; `exp` is checked automatically by `jwt.decode` — an expired token raises, and you reject it.

> ⚠️ **The signature is the whole security model.** `jwt.decode(..., algorithms=[...])` verifies it with your `JWT_SECRET`. If the secret leaks, anyone can mint valid tokens for any user. Keep it in the environment, make it long (≥32 bytes), and rotate it if exposed. **Never** decode with `verify_signature=False` for auth.

---

## Access vs refresh — why two tokens

| Token | Lifetime | Sent when | If stolen |
|-------|----------|-----------|-----------|
| **Access** | short (e.g. 30 min) | on **every** API request | attacker has ~30 min |
| **Refresh** | long (e.g. 7 days) | only to `/auth/refresh` | worse, but sent rarely → smaller exposure |

The access token is short-lived so a leaked one expires fast. When it expires, the client trades the refresh token for a *new* access token — no re-login. This limits the blast radius of a stolen access token while keeping users logged in.

```python
def create_access_token(subject):  return _create_token(subject, "access",  timedelta(minutes=30))
def create_refresh_token(subject): return _create_token(subject, "refresh", timedelta(days=7))
```

The `type` claim matters: the refresh endpoint must **reject an access token** used as a refresh token (and vice versa), or the two-token scheme buys you nothing.

---

## Issuing and refreshing (the auth service)

```python
# app/services/auth.py (essentials)
def issue_tokens(self, user) -> TokenPair:
    return TokenPair(access_token=security.create_access_token(str(user.id)),
                     refresh_token=security.create_refresh_token(str(user.id)))

async def refresh(self, refresh_token: str) -> TokenPair:
    payload = security.decode_token(refresh_token)          # raises if invalid/expired
    if payload.get("type") != "refresh":
        raise AuthError("Not a refresh token.")             # ← enforce the type
    user = await self.users.get(int(payload["sub"]))
    return self.issue_tokens(user)
```

The test suite verifies both the happy path and that **an access token is refused at `/auth/refresh`** — the check that makes the scheme meaningful.

---

## A note on logout & revocation

Pure JWTs are **stateless** — the server doesn't track them, so it can't "log out" a token before it expires. Options: keep access tokens short (so expiry *is* your revocation), or add a server-side **denylist** / token-version in Redis for instant revocation. Short access + refresh is the common default; add a denylist when you need immediate logout.

---

## Recap & next

- ✅ A JWT is a signed, self-contained credential — verified by **signature**, no DB lookup needed.
- ✅ Issue a **short access** token (every request) + a **long refresh** token (only to `/refresh`).
- ✅ The `type` claim must be enforced so tokens aren't interchangeable.
- ✅ The secret is everything: long, in the env, never `verify_signature=False`.
- ✅ Self-check: why keep access tokens short if refresh tokens let users stay logged in anyway?

→ Next: **[04-3 · OAuth2, current user & roles](03_oauth2_current_user_roles.md)**

## Exercises

1. Decode an access token's payload *without* verifying (`jwt.decode(tok, options={"verify_signature": False})`) and read the claims. Why is this fine for inspection but a catastrophic bug for auth?

<details>
<summary>Solution</summary>

You'll see `sub`, `type`, `exp` — JWTs aren't encrypted, so reading is trivial. It's fine for debugging, but using `verify_signature=False` to *authenticate* means accepting any forged token — the attacker just writes `{"sub": "1"}` and is admin. Auth must always verify the signature.
</details>
