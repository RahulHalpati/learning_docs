# 07-3 · Refresh tokens & RBAC

> **Level:** Intermediate · **Prerequisites:** [07-2 · OAuth2 login with JWT](02_oauth2_jwt_login.md)
> **Time:** ~50 min · **Verified:** 2026-08-07 (FastAPI 0.116 · PyJWT · pwdlib/Argon2)

## Why this matters

A 15-minute access token forces a choice: log users out every 15 minutes, or find a safe way to mint new tokens. Refresh tokens with **rotation and reuse detection** solve it — and turn a stolen refresh token from permanent access into a tripwire that reveals the theft. Then authorization: **RBAC** stops **privilege escalation** (a member calling admin endpoints), and service-level ownership checks stop **IDOR** (editing someone else's resources by guessing ids).

---

## Two tokens, two lifetimes

If one token did everything, its lifetime would be a lose-lose: short = constant re-login, long = a leaked token (from a log, a proxy, browser storage) grants **months of access**. Split the job:

| | Access token | Refresh token |
|---|---|---|
| Lifetime | ~15 min | ~14 days |
| Sent | on *every* request | *only* to `/auth/refresh` |
| Server state | none (stateless) | `jti` stored → revocable |
| If stolen | blast radius: minutes | detected & revoked via rotation |

`/auth/token` now returns both. The access token stays stateless and cheap to verify; the refresh token is rare on the wire and tracked server-side.

---

## Refresh rotation

Store each refresh token's `jti` (its unique id from lesson 07-2) in the DB. **Every use of `/auth/refresh` issues a new pair and invalidates the old refresh token** — a refresh token is single-use.

```python
# app/models/auth.py — one row per issued refresh token
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    jti: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    family: Mapped[str]                    # stays constant across rotations of one login
    expires_at: Mapped[datetime]
    revoked: Mapped[bool] = mapped_column(default=False)
```

```python
# app/services/auth.py
async def refresh(db: AsyncSession, presented: str) -> TokenPair:
    payload = decode_token(presented)              # signature + exp, algorithms pinned
    row = await db.get(RefreshToken, payload["jti"])
    if row is None:
        raise InvalidRefreshError
    if row.revoked:
        # REUSE DETECTED: this token was already rotated away. Someone is replaying
        # a stolen token (or the client is broken — treat it the same). Kill the family.
        await revoke_family(db, row.family)
        raise InvalidRefreshError
    row.revoked = True                             # single-use: rotate the old one out
    return await issue_pair(db, row.user_id, family=row.family)
```

**Why reuse = theft:** after a legitimate rotation, exactly one party holds the live token. If the *old* one shows up again, two parties held it — the token leaked. You can't tell which requester is the attacker, so revoking the whole family logs both out; the real user logs in again with their password, the attacker is locked out. Without rotation, a stolen refresh token is silent, permanent access.

> Storing the raw `jti` is fine — it's an opaque uuid, not a credential (the DB row can't be replayed as a token). If you instead store a *hash of the whole token* as the lookup key, compare it with `secrets.compare_digest`, never `==` — same timing-attack rule as lesson 07-1.

---

## Logout with stateless JWTs

A signed access token is valid until `exp` — the server holds no state to delete, so "logout" needs a **server-side revocation list**: a denylist of `jti`s checked in `get_current_user`. The entry only needs to live as long as the token would have — **TTL = remaining lifetime** — so the list stays tiny.

```python
# app/services/denylist.py — the interface now; Redis implementation in Section 08
from typing import Protocol

class TokenDenylist(Protocol):
    async def add(self, jti: str, ttl_seconds: int) -> None: ...
    async def contains(self, jti: str) -> bool: ...

# Logout: denylist the access token's jti for its remaining lifetime,
# and revoke the refresh-token family in the DB.
```

Yes — this re-introduces per-request state, eroding "JWTs are stateless". That trade-off is real, and lesson 07-4 weighs it against plain sessions.

---

## RBAC: roles and the dependency factory

The `role` column (`member` | `admin`) drives coarse authorization. The gate is a **dependency factory** — a function that builds a dependency for the role you name:

```python
# app/api/deps.py
def require_role(role: Role):
    async def checker(user: CurrentUser) -> User:
        # user came from the DB in get_current_user — NEVER read the role from
        # a token claim: claims are attacker-suppliable data, and even honest
        # ones go stale (demoted admin keeps a valid token for 15 min).
        if user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

AdminUser = Annotated[User, Depends(require_role(Role.admin))]

@router.delete("/admin/links/{slug}", status_code=204)
async def admin_delete_link(slug: str, admin: AdminUser, db: DbSession) -> None:
    await link_service.admin_delete(db, slug)
```

Note the status code: **403, not 401**. The caller *is* authenticated (we know who they are); they're just not allowed. 401 means "prove who you are"; 403 means "we know, and no".

**Scopes vs roles:** roles answer "who is this user" (coarse, stored on the user, right for a handful of tiers like member/admin). OAuth2 *scopes* answer "what may this particular token do" (fine-grained, stored in the token, right when tokens are handed to third parties or limited clients — a CI token that may `links:read` but not `links:write`). A first-party app like linkbox needs roles; add scopes when you start issuing tokens to software that isn't yours.

---

## Ownership checks live in the service

Members may only mutate *their own* links. That check belongs in the **service**, not the router:

```python
# app/services/links.py
async def delete_link(db: AsyncSession, slug: str, current_user: User) -> None:
    link = await repo.get_by_slug(db, slug)
    if link is None:
        raise LinkNotFoundError(slug)
    if link.owner_id != current_user.id:      # ownership: the anti-IDOR check
        raise NotOwnerError(slug)             # handler maps it to 403
    await repo.delete(db, link)
```

Two reasons it's here and not in the router:

- **Every entry point routes through the service** — the REST router today, but also the admin CLI, a background job, the GraphQL layer someone adds next year. A router-level check guards one door and leaves the rest wide open.
- The attack it stops is **IDOR** (insecure direct object reference): an attacker takes a URL like `/links/my-slug`, substitutes someone else's slug, and mutates a resource they don't own. Authentication doesn't stop this — the attacker is a logged-in user; only the ownership comparison does.

---

## Recap & next

- ✅ Short access token (leak blast radius: minutes) + long refresh token (rare on the wire, revocable).
- ✅ Rotation: every refresh issues a new pair and revokes the old `jti`; **reuse = theft → revoke the family**.
- ✅ Logout = denylist by `jti` with TTL = remaining lifetime (interface now, Redis in Section 08).
- ✅ `require_role(...)` factory reads the role from the DB-loaded user — never from claims; 403 for authorization failures.
- ✅ Ownership (`owner_id == current_user.id`) is enforced in the service — the anti-IDOR check, on every path.
- ✅ Self-check: after a refresh-token reuse is detected, why revoke the *whole family* instead of just rejecting that one request?

→ Next: **[07-4 · Sessions & hardening](04_sessions_and_hardening.md)**

## Exercises

1. Walk the timeline: attacker steals a refresh token at 09:00; the real user's app refreshes normally at 09:30; the attacker tries their stolen token at 10:00. What happens at each step with rotation — and without it?

<details>
<summary>Solution</summary>

With rotation: 09:30 — the user's refresh succeeds, old `jti` marked revoked, user holds the new pair. 10:00 — the attacker presents the revoked `jti`; reuse detected, the family is revoked, attacker gets 401 and *stays* locked out; the user re-logs-in with their password. Without rotation: the stolen token remains valid for its full 14 days, the attacker silently mints fresh access tokens the whole time, and nothing ever signals the theft.
</details>

2. Why does the admin gate return 403 for a member but `get_current_user` returns 401 for a bad token? State the rule in one sentence.

<details>
<summary>Solution</summary>

401 = authentication failed ("I don't know who you are — present valid credentials", hence the `WWW-Authenticate` header); 403 = authentication succeeded but authorization failed ("I know exactly who you are, and you may not do this"). Conflating them confuses clients: a 401 tells an app to re-login, which won't help a member who's simply not an admin.
</details>

3. Your PM asks: "Admins can do everything anyway — why not just skip the ownership check when `role == admin`?" Where would you implement that, and what must you *not* do?

<details>
<summary>Solution</summary>

In the service, as an explicit bypass: `if link.owner_id != current_user.id and current_user.role != Role.admin: raise NotOwnerError(...)` — one line, still on every code path. What you must not do: move the check into the router (other entry points lose it), or read the role from the token payload (attacker-suppliable and stale) — the role must come from the DB-loaded `current_user`, same as the gate dependency.
</details>
