# 06-2 · Passwords & Flask-Login

> **Level:** Intermediate · **Prerequisites:** [06-1 · Sessions & cookies](01_sessions_cookies.md)
> **Time:** 55 min · **Verified:** 2026-07-29 (Werkzeug 3.1.8, Flask-Login 0.6.3)

## Why this matters

Storing passwords is the highest-stakes code you'll write — one leaked database exposes credentials users reuse everywhere. The rule is absolute: **never store the password, store a slow salted hash.** Then Flask-Login handles the boring part (remembering who's logged in, protecting pages).

---

## Hashing (Werkzeug — already installed)

```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    password_hash: Mapped[str] = mapped_column(String(255))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
```

**Output (real run):**
```
hash algorithm:  scrypt:32768:8:1
verify correct:  True
verify wrong:    False
```

Werkzeug defaults to **scrypt** — deliberately slow and salted, which is what you want:

- **Salted:** each hash embeds random bytes, so identical passwords produce *different* hashes. Rainbow tables useless; you can't tell two users share a password.
- **Slow:** ~100ms per hash. Irrelevant for one login, ruinous for an attacker brute-forcing billions.

> ⚠️ **Never use MD5/SHA-256 for passwords.** They're built to be *fast* — a GPU tries billions per second. Use scrypt (Werkzeug's default), bcrypt, or argon2. Never invent your own scheme.

Also note FlaskNotes returns the *same* message for "no such email" and "wrong password" — otherwise an attacker can enumerate which emails are registered.

---

## Flask-Login

It manages the session ↔ user mapping for you.

```python
# app/extensions.py
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.login_view = "auth.login"        # where @login_required redirects
```

```python
# app/__init__.py, inside create_app()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))   # session stores the ID; this reloads the object
```

The **user loader** is the core: Flask-Login puts the user's id in the session, and calls this on each request to turn it back into a `User` object.

> ⚠️ **`login_view` needs the blueprint prefix** — `"auth.login"`, not `"login"`. Getting this wrong raises `BuildError: Could not build url for endpoint 'login'` on every `@login_required` redirect. (This exact bug appeared while building FlaskNotes; the test suite caught it — see [04-2](../04_app_structure/02_blueprints.md).)

Your model needs `UserMixin` (it supplies `is_authenticated`, `get_id()`, etc.):

```python
from flask_login import UserMixin
class User(UserMixin, db.Model): ...
```

---

## Login, logout, protect

```python
from flask_login import login_user, logout_user, login_required, current_user

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user is None or not user.check_password(password):
            flash("Incorrect email or password.", "error")     # same message either way
            return render_template("login.html"), 401
        login_user(user)                                        # ← sets the session
        return redirect(url_for("web.index"))
    return render_template("login.html")

@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@web_bp.route("/notes/new", methods=["GET", "POST"])
@login_required                       # anonymous users are redirected to login_view
def new_note():
    ...
```

**Output (real run, from the FlaskNotes test suite):**
```
GET /notes/new  (anonymous)  ->  302, Location: /login?next=...
POST /login     (bad password) ->  401
```

`current_user` is available everywhere — views *and* templates:

```jinja
{% if current_user.is_authenticated %}
  {{ current_user.email }}
{% else %}
  <a href="{{ url_for('auth.login') }}">Log in</a>
{% endif %}
```

---

## Recap & next

- ✅ Store a **salted, slow hash** (Werkzeug's scrypt); never plaintext, never MD5/SHA.
- ✅ Give the same error for unknown email and wrong password (no account enumeration).
- ✅ Flask-Login: `UserMixin` on the model, a **`@login_manager.user_loader`**, `login_user`/`logout_user`.
- ✅ `@login_required` protects views; `current_user` works in views and templates.
- ✅ `login_view` must include the **blueprint prefix**.
- ✅ Self-check: why is a *slow* hash a feature rather than a performance problem?

→ Next: **[06-3 · JWT for APIs](03_jwt_apis.md)**

## Exercises

1. Add a "remember me" checkbox that passes `remember=True` to `login_user`. What changes about the cookie?

<details>
<summary>Solution</summary>

`login_user(user, remember=True)` sets a long-lived *remember* cookie, so the session survives closing the browser (governed by `REMEMBER_COOKIE_DURATION`). Convenient — and a longer window for a stolen cookie, so pair it with `SECURE`/`HTTPONLY` flags.
</details>
