# 02-6 · Access control & IDOR

> **Level:** Beginner · **Prerequisites:** [02-5 Traversal, SSRF & deserialization](05_traversal_ssrf_deser.md)
> **Time:** 20 min · **Verified:** 2026-07-15

The hardest class to find — and #1 on the OWASP Top 10. Broken access control is a
bug of **omission**: the dangerous thing is a check that *isn't there*. No scanner
finds it reliably, which makes it the purest test of a human auditor. The "attack
it" side is Ethical Hacking's
[IDOR module](../../ethical_hacking/05_web_application_security/06_idor_and_access_control.md).

---

## IDOR: the missing ownership check

The shape: a route acts on an object identified by a user-supplied id, without
checking the user is *allowed* that object.

```python
# VULNERABLE
@app.route("/user/<int:uid>/profile")
def profile(uid):
    return db.get_user(uid)          # returns ANY user's profile
```

Logged in as user 7, request `/user/8/profile` → you read user 8's data. The id is
a **direct object reference**, and it's **insecure** because nothing ties `uid` to
the current user. Nothing here is "tainted into a sink" — the code is missing a
line.

**The fix — check ownership (or role) on every access:**

```python
@app.route("/user/<int:uid>/profile")
@login_required
def profile(uid):
    if uid != current_user.id and not current_user.is_admin:
        abort(403)
    return db.get_user(uid)
```

---

## Why tools miss it

A scanner can flag "a route takes an id and hits the DB," but it **can't know**
whether the check that *should* exist is missing — that requires understanding your
app's authorization model (who owns what, which roles exist). This is why access
control is a **human review** item and why it dominates real breach reports.

The most a tool can do is *remind* you to look — e.g. list every route that takes
an id parameter so you can eyeball each for a check. (A nice extension exercise for
your auditor in [Section 03](../03_static_analysis_with_ast/03_writing_detection_rules.md).)

---

## A checklist for access-control review

Walk every endpoint and ask:

- **Authentication** — is the user logged in? (`@login_required` or equivalent)
- **Authorization** — may *this* user perform *this* action on *this* object?
- **Function-level** — are admin routes actually restricted to admins, or just
  hidden from the menu?
- **Mass assignment** — can the user set fields they shouldn't (e.g. `is_admin`)
  by adding them to the request body?
- **Consistency** — is the check on *every* path to the resource (API + web + batch),
  not just the obvious one?

---

## Recap & next

- ✅ **IDOR / broken access control** = a **missing** ownership/role check — a bug
  of omission.
- ✅ Scanners **can't** find it reliably; it needs a human who knows the authz
  model. It's OWASP #1 for a reason.
- ✅ Review **every endpoint** against the authn/authz checklist; verify the check
  is on *every* path to the object.

## Exercise

The sample app has no `/user/<id>` route, on purpose — access control needs app
context to judge. Sketch (in words) how you'd extend your `codeaudit` tool to at
least *flag routes worth reviewing* for IDOR, and why it can only "flag for review"
rather than "confirm a bug."

<details>
<summary>Solution</summary>

Add a rule that finds function defs decorated with `@app.route` whose path contains
a `<...>` parameter **and** whose body calls a data-access function (`db.get_*`,
`.query`, `.execute`) using that parameter — emit an *informational* "review for
access control" finding. It can only flag, not confirm, because deciding whether a
check is *missing* requires knowing the app's ownership/role rules, which aren't in
the syntax — a correct check might also live in a decorator or middleware the rule
can't evaluate.

</details>

**→ Next: [03-1 · How SAST works](../03_static_analysis_with_ast/01_how_sast_works.md)**
