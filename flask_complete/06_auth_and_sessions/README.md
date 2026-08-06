# Section 06 · Auth & sessions

> **Prerequisites:** [05 · Data layer](../05_data_layer/README.md) · **Time:** ~3 h

Who is this user, and what may they do? FlaskNotes answers it **twice** — session cookies for the browser UI, JWT tokens for the JSON API — because that's what real apps with both faces do.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Sessions & cookies](01_sessions_cookies.md) | How does Flask remember a user between requests? |
| 06-2 | [Passwords & Flask-Login](02_passwords_login.md) | How do I store passwords safely and protect pages? |
| 06-3 | [JWT for APIs](03_jwt_apis.md) | How do I authenticate API clients without cookies? |

## What you'll be able to do after this section

- Use the signed `session` cookie, and know exactly what it does and doesn't protect.
- Hash passwords with Werkzeug and wire up Flask-Login (`@login_required`, `current_user`).
- Issue and verify JWTs, and protect API routes with a decorator + ownership checks.

→ Start: **[06-1 · Sessions & cookies](01_sessions_cookies.md)**
