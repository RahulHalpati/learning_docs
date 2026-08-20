# 07-2 · OAuth2 login with JWT

> **Level:** Intermediate · **Prerequisites:** [07-1 · Password hashing](01_password_hashing.md)
> **Time:** ~50 min · **Verified:** 2026-08-07 (FastAPI 0.116 · PyJWT · pwdlib/Argon2)

## Why this matters

Hashing protects the password at rest; now the user has to *use* it — once — and then prove their identity on every request without sending it again. That's the OAuth2 password flow with a signed JWT. The signature defends against **token tampering** (edit a claim → signature breaks), the `exp` claim bounds **stolen-token replay**, and pinning the algorithm defeats the **alg-confusion/`none` forgery** attacks that gutted many JWT libraries.

---

## The flow

1. Client POSTs `username` + `password` (form-encoded) to `/auth/token`.
2. Server verifies with Argon2, signs a token, returns `{"access_token": ..., "token_type": "bearer"}`.
3. Client sends `Authorization: Bearer <token>` on every subsequent request.

FastAPI's `OAuth2PasswordBearer` handles step 3's extraction: it pulls the token from the header, returns 401 when it's missing, and tells Swagger UI where the login endpoint lives.

```python
# app/api/deps.py
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
```

---

## What a JWT actually is

Three base64url segments joined by dots: `header.payload.signature`.

```
eyJhbGciOiJIUzI1NiJ9 . eyJzdWIiOiI0MiIsImV4cCI6MTc4Nn0 . 3fK9...
└ {"alg":"HS256"}      └ {"sub":"42","exp":1786...}      └ HMAC(header.payload, key)
```

**base64url is encoding, not encryption** — anyone holding the token can decode the header and payload with two lines of Python. **Never put secrets in claims.** What the signature gives you is *integrity*: change one byte of the payload (say, `"role": "admin"`) and the HMAC no longer matches, so a server that verifies signatures rejects it. That's the entire security model — which is why the *verification* step is where all the attacks live.

---

## Signing with PyJWT

Use **PyJWT** (`import jwt`). **Never python-jose — it's unmaintained** and was the vehicle for several published JWT CVEs.

```python
# app/core/security.py
import uuid
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT

from app.core.config import settings  # settings.secret_key is a SecretStr

ACCESS_TOKEN_TTL = timedelta(minutes=15)

def create_access_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,                      # subject: whose token this is (user id)
        "iat": now,                      # issued-at: for debugging & max-age policies
        "exp": now + ACCESS_TOKEN_TTL,   # expiry: a stolen token dies in minutes
        "jti": str(uuid.uuid4()),        # unique token id: enables revocation later
    }
    return jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm="HS256")
```

| Claim | What it's for |
|-------|---------------|
| `sub` | Who the token identifies — the user id, as a string. |
| `exp` | Hard cutoff. **Always set it**: without `exp`, a leaked token works forever. |
| `iat` | When it was issued — audit trails, "tokens older than X" policies. |
| `jti` | Unique id per token — the hook for revocation and refresh rotation (next lesson). |

---

## Decoding: pin the algorithm, require exp

```python
def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=["HS256"],                 # pin exactly what YOU sign with
        options={"require": ["exp", "sub"]},  # a token without exp is invalid, full stop
    )
```

Why `algorithms=["HS256"]` is non-negotiable: the token's *header* declares its own algorithm, and historically libraries honored it. Two attacks fall out of that:

- **`alg: none`** — the attacker strips the signature and declares the token unsigned; a naive verifier accepts anything.
- **Algorithm confusion** — against RS256 services, the attacker re-signs with HS256 using the server's *public* key as the HMAC secret; a verifier that lets the header pick the algorithm validates it.

Pinning means *you* decide the algorithm, never the attacker's header. PyJWT verifies `exp` automatically when present; `options={"require": [...]}` closes the "just omit the claim" loophole.

---

## The `/auth/token` endpoint

`OAuth2PasswordRequestForm` gives you the spec-compliant form body (`username`, `password`) that Swagger's login dialog sends.

```python
# app/api/routers/auth.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> TokenOut:
    user = await user_service.authenticate(db, form.username, form.password)
    if user is None:
        # One generic error for unknown email AND wrong password —
        # distinct errors let attackers enumerate which emails have accounts.
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(sub=str(user.id)),
                    token_type="bearer")
```

---

## The `get_current_user` dependency

Every protected endpoint needs the same three steps: decode the token, load the user from the DB, check they're still active. That's one dependency.

```python
# app/api/deps.py
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    unauthorized = HTTPException(
        status_code=401, detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)     # signature + exp verified here
    except jwt.InvalidTokenError:         # expired, tampered, wrong alg, missing claims
        raise unauthorized
    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized                # banned/deleted users are cut off NOW
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
```

**Why hit the DB when the token is already verified?** The token proves who the caller was *at issue time*; the DB says who they are *now*. Loading the user is what lets `is_active = False` lock someone out immediately instead of "whenever their token expires" — and it means authorization decisions (like roles, next lesson) come from data you control, not from claims the client carries around.

Protected endpoints are now one annotation:

```python
@router.get("/users/me")
async def read_me(current_user: CurrentUser) -> UserOut:
    return current_user
```

---

## The Swagger Authorize button

Because `OAuth2PasswordBearer` declares `tokenUrl`, `/docs` grows a green **Authorize** button: click it, enter email + password, and Swagger calls `/auth/token`, stores the returned token, and attaches `Authorization: Bearer ...` to every "Try it out" request. Your interactive docs double as a login-flow test bench — no curl needed while developing.

---

## Recap & next

- ✅ OAuth2 password flow: `OAuth2PasswordRequestForm` in, Bearer token out, `OAuth2PasswordBearer` extracts it thereafter.
- ✅ A JWT is signed, **not encrypted** — never put secrets in claims; the signature only stops tampering.
- ✅ PyJWT (`import jwt`) — python-jose is unmaintained. Sign with `sub`/`iat`/`exp`/`jti`.
- ✅ `jwt.decode(..., algorithms=["HS256"], options={"require": ["exp", "sub"]})` — pinning kills alg-confusion/`none`; requiring `exp` kills eternal tokens.
- ✅ `get_current_user`: decode → load from DB → check `is_active`; alias it as `CurrentUser`.
- ✅ Self-check: why must `get_current_user` load the user from the database instead of trusting the decoded payload?

→ Next: **[07-3 · Refresh tokens & RBAC](03_refresh_tokens_rbac.md)**

## Exercises

1. Paste one of your tokens into three lines of Python — `jwt.decode(token, options={"verify_signature": False})` — and read the claims. What does this prove about where sensitive data may live?

<details>
<summary>Solution</summary>

The payload decodes without any key: base64url is readable by anyone who holds the token — the user, a proxy, a log file. Claims are *public to the bearer*. Sensitive data (password hashes, PII you wouldn't return from an endpoint) must never be a claim; the only thing the secret key protects is the token's integrity.
</details>

2. Craft an attack token: decode your token's payload, change `"sub"` to another user's id, re-encode, and send it with the original signature. What response do you get, and which line of `decode_token` rejects it?

<details>
<summary>Solution</summary>

401. The signature was computed over the *original* header.payload; after editing `sub`, the HMAC in `jwt.decode` no longer matches, so it raises `InvalidSignatureError` (a subclass of `InvalidTokenError`), which `get_current_user` maps to 401. This is the integrity guarantee working — and exactly why a server that skips or misconfigures verification is fully compromised.
</details>

3. A teammate writes `jwt.decode(token, key, algorithms=["HS256", "none"])` "to make tests easier". Explain the attack this enables in one sentence, and the correct test-friendly fix.

<details>
<summary>Solution</summary>

Accepting `"none"` means any client can strip the signature and forge arbitrary claims — instant authentication bypass for every user including admins. The fix: keep `algorithms=["HS256"]` in production code and, in tests, simply *sign* test tokens with the test settings' secret key — signing a token takes one line and needs no weakened verifier.
</details>
