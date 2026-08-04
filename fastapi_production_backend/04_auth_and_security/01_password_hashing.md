# 04-1 · Password hashing

> **Level:** Intermediate · **Prerequisites:** [03-1 · Pydantic schemas](../03_schemas_and_crud/01_pydantic_schemas.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (pwdlib 0.3.0 with bcrypt 5.0.0)

## Why this matters

Storing passwords is the highest-stakes thing a backend does. Get it wrong and one database leak exposes every user's password (which they've reused elsewhere). The rule is absolute: **never store the password — store a slow, salted *hash* of it.** You never "decrypt" a password; you hash the attempt and compare.

---

## Hash on the way in, verify on login

We use **pwdlib** (the modern, maintained successor to passlib) with **bcrypt**:

```python
# app/core/security.py
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

_password_hash = PasswordHash((BcryptHasher(),))

def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)
```

```python
h = hash_password("password123")
print("hash:", h[:7], "len:", len(h))
print("correct:", verify_password("password123", h))
print("wrong:  ", verify_password("nope", h))
```

**Output (real run):**
```
hash: $2b$12$ len: 60
correct: True
wrong:   False
```

The stored value is a 60-char bcrypt hash. `$2b$` is the bcrypt identifier; `12` is the **cost factor** (2¹² rounds). You verify by hashing the attempt and comparing — the plaintext is never recoverable.

---

## Why bcrypt (and why *slow* is the point)

Bcrypt is a **deliberately slow, salted** hash designed for passwords:

- **Salted:** each hash embeds a random salt, so identical passwords produce *different* hashes — rainbow tables are useless, and you can't tell two users share a password.
- **Slow (adaptive):** the cost factor makes each hash take ~100ms. Fine for one login; ruinous for an attacker brute-forcing billions of guesses. As hardware speeds up, you raise the cost.

> ⚠️ **Never use fast hashes (MD5, SHA-256) for passwords.** They're built to be *fast*, which is exactly wrong here — a GPU tries billions per second. Use bcrypt, scrypt, or **argon2** (pwdlib's `PasswordHash.recommended()` uses argon2 if you install `pwdlib[argon2]`). Never invent your own.

---

## Where it plugs in

Hashing happens in the **auth service** at registration; verification at login:

```python
# app/services/auth.py (essentials)
async def register(self, data: UserCreate) -> User:
    user = User(email=data.email,
                hashed_password=security.hash_password(data.password),   # hash here
                full_name=data.full_name)
    return await self.users.create(user)

async def authenticate(self, email: str, password: str) -> User:
    user = await self.users.get_by_email(email)
    if not user or not security.verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password.")
    return user
```

Two security details baked in:
- The DB column is `hashed_password`; the plaintext exists only for the moment of the request, never stored.
- On failure we say "**Incorrect email or password**" — never "no such email" vs "wrong password", which would let an attacker enumerate which emails are registered.

---

## Recap & next

- ✅ Never store passwords — store a **salted, slow hash** (bcrypt/argon2) and verify by re-hashing.
- ✅ pwdlib + bcrypt: `hash_password` on register, `verify_password` on login.
- ✅ Salting defeats rainbow tables; slowness defeats brute force; **never use MD5/SHA for passwords**.
- ✅ Give a generic "incorrect email or password" to avoid account enumeration.
- ✅ Self-check: why is a *slow* hash a feature, not a performance bug?

→ Next: **[04-2 · JWT tokens](02_jwt_tokens.md)**

## Exercises

1. Hash the same password twice and confirm the two hashes **differ** (salting), yet both verify. Why do they differ?

<details>
<summary>Solution</summary>

`hash_password("x") != hash_password("x")` because each embeds a fresh random salt — yet `verify_password("x", either)` is `True`, since the salt is stored *inside* the hash and reused during verification. Different hashes, same password: rainbow tables can't precompute them.
</details>
