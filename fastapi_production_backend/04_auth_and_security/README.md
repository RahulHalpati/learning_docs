# Section 04 · Auth & security

> **Prerequisites:** [03 · Schemas & CRUD](../03_schemas_and_crud/README.md) · **Time:** ~3 h

Now lock it down. This section builds authentication from scratch: **password hashing** (never store plaintext), **JWT** access + refresh tokens, the **OAuth2** login flow, a **current-user** dependency that protects routes, and **roles/ownership** for authorization.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Password hashing](01_password_hashing.md) | How do I store passwords safely (and verify them)? |
| 04-2 | [JWT tokens](02_jwt_tokens.md) | How do access & refresh tokens work, and how do I issue them? |
| 04-3 | [OAuth2, current user & roles](03_oauth2_current_user_roles.md) | How do I protect routes and authorize by role/ownership? |

## What you'll be able to do after this section

- Hash & verify passwords with bcrypt (via pwdlib); never store plaintext.
- Issue and validate JWT **access** and **refresh** tokens.
- Wire the OAuth2 password flow and a `get_current_user` dependency.
- Enforce **authentication** (who are you) and **authorization** (roles + ownership).

→ Start: **[04-1 · Password hashing](01_password_hashing.md)**
