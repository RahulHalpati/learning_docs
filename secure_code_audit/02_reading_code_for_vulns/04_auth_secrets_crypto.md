# 02-4 · Auth, secrets & crypto

> **Level:** Beginner · **Prerequisites:** [02-3 XSS, SSTI & output](03_xss_ssti_and_output.md)
> **Time:** 25 min · **Verified:** 2026-07-15

These bugs aren't about untrusted input flowing anywhere — they're about
**getting the security primitives wrong**. They're some of the easiest to spot in
source and among the most common in the wild.

---

## Hardcoded secrets (CWE-798)

The shape: a credential as a string literal.

```python
# samples/vulnerable_app/app.py — VULNERABLE
app.secret_key = "super-secret-key-12345"
API_TOKEN = "sk_live_51H8xExample0000000000"
```

Why it matters: anyone with the source (a leaked repo, a former employee, a
decompiled build) has the key. Git *remembers* it even after you delete the line.
Tells: assignments to names like `password`, `secret`, `api_key`, `token`, and
long random-looking string literals.

**The fix — read secrets from the environment:**

```python
import os
app.secret_key = os.environ["FLASK_SECRET_KEY"]     # set outside the code
API_TOKEN = os.environ["API_TOKEN"]
```

Keep them in a secret manager or a `.gitignore`d `.env`; never in the repo. If one
*was* committed, **rotate it** — deleting the line doesn't un-leak it from git
history.

---

## Weak cryptography (CWE-327)

The shape: broken or misused algorithms.

```python
# VULNERABLE
digest = hashlib.md5(password.encode()).hexdigest()   # MD5 for a password
```

MD5 and SHA-1 are **fast and broken** — exactly wrong for passwords (fast = easy to
brute-force; broken = collisions). Tells: `hashlib.md5`/`sha1`, `random` (not
`secrets`) for tokens, `DES`, `ECB` mode, tiny key sizes.

**The fix — the right primitive for the job:**

```python
# passwords: a slow, salted KDF
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# security tokens: a CSPRNG, not random
import secrets
token = secrets.token_urlsafe(32)
```

Passwords want **slow, salted** hashing (bcrypt/argon2/scrypt). Tokens want a
**cryptographically secure RNG** (`secrets`, never `random`).

---

## Predictable sessions & weak auth checks

Related tells while you're in the auth code:

- **Predictable session ids** — `md5(username)` or a counter as a token (an
  attacker can guess/forge). Use `secrets`.
- **`debug=True`** in production — Flask/Werkzeug's debugger is an interactive
  console = RCE if reachable. (Your tool flags this as `CA105`.)
- **Timing-unsafe comparison** — `token == expected` for secrets leaks length/prefix
  via timing; use `secrets.compare_digest`.

---

## Recap & next

- ✅ **Hardcoded secrets**: literals assigned to secret-y names → env vars /
  secret manager; **rotate** anything already committed.
- ✅ **Weak crypto**: MD5/SHA-1 for passwords, `random` for tokens → **bcrypt/argon2**
  for passwords, **`secrets`** for tokens.
- ✅ Watch for **predictable sessions**, **`debug=True`**, and **timing-unsafe
  comparisons**.

## Exercise

The app hashes passwords with `hashlib.md5`. Beyond swapping the algorithm, what
one property must a password hash have that a general-purpose hash lacks — and how
do bcrypt/argon2 provide it?

<details>
<summary>Solution</summary>

It must be **slow (deliberately expensive) and salted**. General hashes (MD5/SHA-256)
are designed to be *fast*, which helps attackers try billions of guesses per
second. bcrypt/argon2 use a tunable **work factor** (and a built-in per-hash
**salt**) so each guess is costly and precomputed rainbow tables don't work.

</details>

**→ Next: [02-5 · Traversal, SSRF & deserialization](05_traversal_ssrf_deser.md)**
