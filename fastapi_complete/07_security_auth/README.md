# Section 07 · Security & authentication

> **Prerequisites:** [06 · Clean architecture](../06_clean_architecture/README.md) · **Time:** ~6 h

Authentication is where a backend stops being a demo and starts being a target. This section builds the full stack of modern auth: **Argon2** password hashing (the only acceptable way to store credentials in 2026), the **OAuth2** password flow with signed **JWT** access and refresh tokens, and **RBAC** with roles and ownership checks — each control introduced alongside the concrete attack it defeats.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 07-1 | [Password hashing](01_password_hashing.md) | How do I store passwords so a database leak isn't a credential leak? |
| 07-2 | [OAuth2 login with JWT](02_oauth2_jwt_login.md) | How do users log in, and how does every request prove who's calling? |
| 07-3 | [Refresh tokens & RBAC](03_refresh_tokens_rbac.md) | How do sessions stay alive without long-lived tokens — and who may do what? |
| 07-4 | [Sessions & hardening](04_sessions_and_hardening.md) | When do cookie sessions beat JWTs, and what else must be locked down? |

## Mini-project

Add a complete auth vertical to the layered **linkbox** app from Section 06 — users register, log in, own their links, and admins moderate.

- [ ] `User` model + Alembic migration: `email` (unique, indexed), `hashed_password`, `role` enum (`member` | `admin`), `is_active`.
- [ ] `POST /auth/register` — hashes the password with Argon2 (pwdlib); the response schema never exposes `hashed_password`.
- [ ] `POST /auth/token` — `OAuth2PasswordRequestForm` login; on success returns an access JWT (~15 min) **and** a refresh JWT (~14 days); wrong email and wrong password produce the *same* generic 401.
- [ ] `POST /auth/refresh` — rotation: every use issues a new pair and invalidates the old refresh token (`jti` stored server-side); reusing a rotated token → 401 and the whole token family is revoked.
- [ ] `GET /users/me` — returns the current user via the `CurrentUser` dependency (decode → load from DB → check `is_active`).
- [ ] Links become owned: `owner_id` FK + migration; create sets the owner; update/delete enforce `owner_id == current_user.id` **in the service layer** → 403 otherwise.
- [ ] `DELETE /admin/links/{slug}` — gated by `require_role(Role.admin)`; the role is read from the DB-loaded user, never from a token claim.
- [ ] `jwt.decode` always pins `algorithms=["HS256"]` and requires `exp`; all secrets come from settings as `SecretStr`.

## Test task (gate)

**Break-then-fix audit.** Take your finished mini-project and apply the five sabotage patches below (or have someone apply them for you, then audit without peeking). Each one is a real vulnerability class seen in production codebases:

1. `jwt.decode` called without `algorithms` pinned — accepts algorithm-confusion tokens.
2. `exp` never set on tokens — a stolen token works forever.
3. Password check via `user.hashed_password == password` — plaintext comparison, hashing silently bypassed.
4. `/auth/refresh` returns a new access token but never rotates or invalidates the refresh token — one stolen refresh token = permanent access.
5. The admin check reads `role` from the client-supplied token payload and never verifies it against the DB — anyone who can mint or replay a token with `"role": "admin"` is an admin.

**Passing means all of the following, no partial credit:**

- All **five** vulnerabilities found and each **named with the attack it enables** (e.g. #1 → alg-confusion/`none` forgery, #4 → refresh-token replay).
- Each one **fixed** in code.
- A **curl or httpx transcript** proving each fix: an expired token → 401, a tampered `role` claim → 403, a reused refresh token → 401 (and the family revoked), a wrong password → generic 401, an unpinned-alg forgery now rejected.

Only move to Section 08 once the transcript shows all five rejections.

## What you'll be able to do after this section

- Store and verify passwords with Argon2id, including transparent parameter upgrades on login.
- Implement the OAuth2 password flow with PyJWT: issue, pin, verify, and expire tokens correctly.
- Run refresh-token rotation with reuse detection, and revoke tokens on logout.
- Enforce authorization at the right layers: role gates in dependencies, ownership checks in services.
- Audit an auth module for the classic JWT and password-handling vulnerabilities — and prove the fixes.

→ Start: **[07-1 · Password hashing](01_password_hashing.md)**
