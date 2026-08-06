# 06-3 · JWT for APIs

> **Level:** Intermediate → Advanced · **Prerequisites:** [06-2 · Passwords & Flask-Login](02_passwords_login.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (PyJWT 2.13.0)

## Why this matters

Session cookies are great for browsers and wrong for API clients — mobile apps and other services don't want cookie jars, and cookies bring CSRF concerns. The standard answer is a **JWT**: a signed token the client sends in an `Authorization` header. FlaskNotes runs both — sessions for the web UI, JWT for `/api/v1`.

---

## What a JWT is

Three base64 segments — `header.payload.signature`. The payload holds claims; the signature is an HMAC over it using your secret.

**Output (real run):**
```
segments: 3
payload decoded WITHOUT the secret: {'sub': '1', 'exp': 1785950857}
```

> ⚠️ **A JWT is signed, not encrypted — anyone holding it can read the payload.** (Same rule as the session cookie.) Put an id and an expiry in it; never a password, card number, or anything private. The signature only proves it wasn't *tampered with*.

---

## Issuing a token

```python
import jwt
from datetime import datetime, timedelta, timezone

def issue_token(user) -> str:
    payload = {
        "sub": str(user.id),                                    # subject: who
        "exp": datetime.now(timezone.utc)                        # expiry: enforced on decode
              + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")

@api_bp.post("/auth/token")
def get_token():
    data = request.get_json(silent=True) or {}
    user = db.session.scalar(db.select(User).filter_by(email=(data.get("email") or "").lower()))
    if user is None or not user.check_password(data.get("password") or ""):
        raise ApiError("Incorrect email or password", 401)
    return jsonify(access_token=issue_token(user), token_type="bearer")
```

The client trades credentials **once** for a token, then sends the token on every request.

---

## Verifying it: a decorator

```python
from functools import wraps
from flask import g

def token_required(view):
    @wraps(view)                                  # keeps the view's name (Flask needs it)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ApiError("Missing or malformed Authorization header", 401)
        try:
            payload = jwt.decode(header[7:], current_app.config["JWT_SECRET"],
                                 algorithms=["HS256"])          # verifies signature AND exp
        except jwt.PyJWTError:
            raise ApiError("Invalid or expired token", 401)
        user = db.session.get(User, int(payload["sub"]))
        if user is None:
            raise ApiError("User no longer exists", 401)
        g.current_user = user                     # request-scoped, like current_user
        return view(*args, **kwargs)
    return wrapper

@api_bp.get("/notes")
@token_required
def list_notes():
    ...  # g.current_user is available
```

`jwt.decode` does the security work — verified against real failures:

**Output (real run):**
```
correct secret   ->  sub = 1
wrong secret     ->  InvalidSignatureError
expired token    ->  ExpiredSignatureError
```

Both become a clean **401** via the `except jwt.PyJWTError` catch (their common base class).

> ⚠️ **Never `jwt.decode(..., options={"verify_signature": False})` for auth.** That accepts forged tokens — an attacker just writes `{"sub": "1"}` and is you. Always pass `algorithms=[...]` too, which prevents the classic `alg: none` attack.

---

## Authorization ≠ authentication

A valid token says *who* you are, not *what you may do*. FlaskNotes checks ownership on every note:

```python
def _owned_note(note_id: int) -> Note:
    note = db.session.get(Note, note_id)
    if note is None:
        raise ApiError("Note not found", 404)
    if note.user_id != g.current_user.id:
        raise ApiError("You do not have access to this note", 403)   # 403, not 401
    return note
```

**Output (real run, from the test suite — user B requesting user A's note):**
```
GET /api/v1/notes/<A's id>   as B  ->  403
GET /api/v1/notes            as B  ->  total: 0     (sees none of A's)
```

That test is the most important one in the suite: it proves users can't read each other's data.

---

## Logout & revocation

Pure JWTs are **stateless** — the server keeps no record, so it can't invalidate one early. Options: keep expiry short (so expiry *is* revocation), or keep a denylist / token-version in Redis for instant logout. Short-lived tokens plus a refresh token is the usual compromise.

> **Tip — `Flask-JWT-Extended`** wraps all of this (refresh tokens, denylists, cookie mode, `@jwt_required()`) and is the standard choice for bigger Flask APIs. Building it by hand once, as here, means you'll actually understand what it does.

---

## Recap & next

- ✅ JWT = signed token in `Authorization: Bearer …`; **readable by anyone**, so no secrets inside.
- ✅ Issue on login (`sub` + `exp`); verify with `jwt.decode(..., algorithms=["HS256"])` — it checks signature *and* expiry.
- ✅ A `@token_required` decorator + `g.current_user` protects routes; catch `jwt.PyJWTError` → 401.
- ✅ **Authorization is separate**: check ownership and return **403** (not 401).
- ✅ Stateless means no instant logout — use short expiry or a denylist.
- ✅ Self-check: what's the difference between the 401 and the 403 in this lesson?

→ Next: **[07 · Errors, logging & CORS](../07_errors_logging_cors/README.md)**

## Exercises

1. Add a `/api/v1/auth/refresh` that accepts a valid token and issues a fresh one. What stops an *expired* token being refreshed forever?

<details>
<summary>Solution</summary>

Decode the incoming token (it must still be valid) and issue a new one. An expired token raises `ExpiredSignatureError` → 401, so the chain breaks once a user is inactive past the window — which is exactly the property you want. Production systems use a separate longer-lived *refresh* token so access tokens can be very short.
</details>
