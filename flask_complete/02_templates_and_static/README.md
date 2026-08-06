# Section 02 · Templates & static files

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~1.5 h

Flask's other half: rendering **HTML**. Jinja2 (bundled with Flask) gives you template inheritance, loops, filters, and — critically — **automatic escaping** that blocks a whole class of XSS. This is what makes Flask a great choice for server-rendered apps, not just APIs.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 02-1 | [Jinja2 templates](01_jinja_templates.md) | How do I render HTML with variables, loops, and inheritance? |
| 02-2 | [Static files & flash messages](02_static_and_forms.md) | How do I serve CSS/images and show one-off messages? |

## What you'll be able to do after this section

- Render templates with `render_template`, pass context, and use filters.
- Build a `base.html` and `{% extends %}` it — no copy-pasted layout.
- Rely on **autoescaping** (and know when `|safe` is dangerous).
- Serve static assets with `url_for('static', ...)` and flash user messages.

→ Start: **[02-1 · Jinja2 templates](01_jinja_templates.md)**
