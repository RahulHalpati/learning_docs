# 07-1 · Password hashing

> **Level:** Intermediate · **Prerequisites:** [06 · Clean architecture](../06_clean_architecture/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · PyJWT · pwdlib/Argon2)

## Why this matters

Assume your users table *will* leak one day — a backup left on S3, a SQL injection, a stolen laptop. Password hashing decides whether that leak is an incident report or a mass credential compromise: users reuse passwords, so cracking your dump unlocks their email and bank too. The control here defends against **offline cracking** — an attacker with the dump and a GPU rig, trying guesses at hardware speed with no rate limit in the way.

---

## Why plaintext, MD5 and SHA-256 all fail

- **Plaintext** — the leak *is* the passwords. Nothing to crack.
- **Unsalted fast hash (MD5/SHA-256)** — defeated by **rainbow tables**: precomputed hash→password lookups. Every user with password `hunter2` has the *same* hash, so one lookup cracks them all.
- **Salted fast hash** — salt kills rainbow tables, but MD5 and SHA-256 are *designed to be fast*. A single consumer GPU computes tens of billions of SHA-256 hashes per second; an 8-character password falls in hours. Fast is exactly the wrong property for password storage.

What you need is a **KDF** (key derivation function): a hash that is **slow and salted by design**, with tunable cost. Argon2id — the current recommendation — is also *memory-hard*: each guess needs ~64 MB of RAM, which cripples GPU parallelism (a GPU has thousands of cores but nowhere near thousands × 64 MB of fast memory).

---

## Argon2id with pwdlib

Use **pwdlib**. (**passlib is unmaintained** — don't use it; pwdlib is its maintained successor, and `PasswordHash.recommended()` gives you Argon2id with current parameters.)

```python
# app/core/security.py
from pwdlib import PasswordHash

# Argon2id, current recommended parameters. Memory-hard → GPU-resistant.
password_hash = PasswordHash.recommended()

def hash_password(plain: str) -> str:
    # A random salt is generated per call — same password, different hash every time.
    return password_hash.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)
```

The output is self-describing:

```
$argon2id$v=19$m=65536,t=3,p=4$mFm3...$kX9c...
  └ algo    └ ver └ cost params    └ salt └ hash
```

Salt and cost parameters live *inside* the string — no separate salt column, and `verify` knows exactly how to re-derive the hash.

---

## Verify-and-rehash on login

Cost parameters that are "slow enough" today won't be in five years. The upgrade path is the **verify-and-update pattern**: login is the only moment you hold the plaintext, so it's the only moment you can re-hash with stronger parameters.

```python
# app/services/users.py (login path)
valid, new_hash = password_hash.verify_and_update(plain, user.hashed_password)
if not valid:
    return None                     # bad password
if new_hash is not None:            # hash used outdated parameters →
    user.hashed_password = new_hash # transparently upgraded, user notices nothing
return user
```

Bump the parameters once in config; the user base migrates itself, one login at a time.

---

## Timing attacks: why `==` is dangerous

`==` on strings **short-circuits** — it returns at the first differing byte. Compare a secret with `==` and the response time leaks *how many leading bytes matched*, letting an attacker recover it byte by byte over many requests.

- For passwords: `password_hash.verify()` is constant-time-ish by construction — it always derives the full hash before comparing. Use it, never compare hashes yourself.
- For **raw secret comparisons** (API keys, webhook signatures): use `secrets.compare_digest`, which examines every byte regardless of mismatches.

```python
import secrets

def check_api_key(presented: str, expected: str) -> bool:
    return secrets.compare_digest(presented, expected)   # NOT presented == expected
```

---

## Never log or return passwords

A password that lands in a log file has leaked — logs are shipped, indexed, and retained. Use Pydantic's `SecretStr` so accidental `repr`/logging shows `**********`, and keep `hashed_password` out of every response schema.

```python
# app/schemas/users.py
from pydantic import BaseModel, EmailStr, SecretStr

class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr             # logs/tracebacks show '**********'

class UserOut(BaseModel):           # response schema: no password fields, ever
    id: int
    email: EmailStr

# In the service — unwrap only at the point of hashing:
hashed = hash_password(payload.password.get_secret_value())
```

The same goes for your signing key in settings: declare it `SecretStr` so it can't wander into a log line.

---

## Recap & next

- ✅ Fast hashes (MD5/SHA-256) fail against **GPU cracking**; unsalted ones also fail against **rainbow tables**.
- ✅ Argon2id via `PasswordHash.recommended()` is slow, salted, and memory-hard — pwdlib, not the unmaintained passlib.
- ✅ `verify_and_update` on login upgrades old hashes transparently.
- ✅ `verify()` for passwords, `secrets.compare_digest` for raw secrets — never `==` (timing attack).
- ✅ `SecretStr` inputs, password-free response schemas, nothing in logs.
- ✅ Self-check: why doesn't adding a salt make SHA-256 acceptable for password storage?

→ Next: **[07-2 · OAuth2 login with JWT](02_oauth2_jwt_login.md)**

## Exercises

1. Hash the same password twice with `hash_password` and compare the outputs. Why do they differ, and how can `verify` still succeed against both?

<details>
<summary>Solution</summary>

Each call generates a fresh random salt, so the derived hashes differ. `verify` succeeds because the salt (and cost parameters) are embedded in the hash string itself — it re-derives the hash using the *stored* salt and compares.
</details>

2. Write an `x-api-key` header check for an internal endpoint, comparing against a key held in settings. What's wrong with `if header == settings.internal_api_key.get_secret_value()`?

<details>
<summary>Solution</summary>

```python
import secrets
from fastapi import Header, HTTPException

async def require_api_key(x_api_key: str = Header()) -> None:
    if not secrets.compare_digest(
        x_api_key, settings.internal_api_key.get_secret_value()
    ):
        raise HTTPException(status_code=401, detail="Invalid API key")
```

`==` short-circuits at the first differing byte, so response times leak how much of the key matched — a timing attack recovers it byte by byte. `compare_digest` takes the same time regardless of where the mismatch is.
</details>

3. Your team bumps Argon2 memory cost from 64 MB to 128 MB. Describe (no code) how every existing user's hash gets upgraded without a password-reset email.

<details>
<summary>Solution</summary>

Nothing happens at bump time — stored hashes keep their old parameters (readable from the hash string). On each user's *next login*, `verify_and_update` verifies against the old parameters, notices they're below current settings, and returns a new hash computed with the new parameters; the service stores it. The fleet migrates lazily, one successful login at a time; users who never log in keep old-parameter hashes (still salted and slow — just not upgraded).
</details>
