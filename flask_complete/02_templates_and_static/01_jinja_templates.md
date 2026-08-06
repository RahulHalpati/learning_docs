# 02-1 · Jinja2 templates

> **Level:** Beginner · **Prerequisites:** [01-3 · Request & response](../01_foundations/03_request_and_response.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (Flask 3.1.3, Jinja2 3.1.6)

## Why this matters

Returning HTML as Python strings gets ugly fast. **Jinja2** — Flask's built-in template engine — separates your markup from your logic, lets pages share a layout, and escapes user data by default so a comment containing `<script>` can't attack your users.

---

## Render a template

Templates live in a **`templates/`** folder next to your app:

```
app.py
templates/
├── base.html
└── page.html
```

```python
from flask import render_template

@app.get("/")
def page():
    return render_template("page.html", heading="Hi", items=["a", "b", "c"])
```

Keyword arguments become **variables** inside the template. Jinja has three delimiters:

| Syntax | Does |
|--------|------|
| `{{ ... }}` | print an expression |
| `{% ... %}` | a statement (if/for/block/extends) |
| `{# ... #}` | a comment (not sent to the browser) |

---

## Inheritance — write the layout once

`base.html` defines the skeleton with named **blocks**; pages fill them in:

```jinja
{# templates/base.html #}
<!doctype html><title>{% block title %}Site{% endblock %}</title>
<body>{% block content %}{% endblock %}</body>
```

```jinja
{# templates/page.html #}
{% extends "base.html" %}
{% block title %}{{ heading }}{% endblock %}
{% block content %}
  <h1>{{ heading }}</h1>
  <ul>{% for item in items %}<li>{{ loop.index }}. {{ item }}</li>
      {% else %}<li>none</li>{% endfor %}</ul>
  {% if items|length > 2 %}<p>many</p>{% else %}<p>few</p>{% endif %}
{% endblock %}
```

**Output (real run):**
```html
<!doctype html><title>Hi</title>
<body>
<h1>Hi</h1>
<ul><li>1. a</li><li>2. b</li><li>3. c</li></ul>
<p>many</p>
</body>
```

Three things to notice:
- **`{% extends %}`** pulled in the layout — the nav/footer/CSS links live in exactly one file.
- **`loop.index`** is the 1-based counter Jinja provides inside `for` (also `loop.index0`, `loop.first`, `loop.last`).
- **`{% else %}` inside a `for`** runs when the sequence is empty — a neat Jinja touch that saves an `{% if %}`.

---

## Filters

Filters transform a value with `|`:

```jinja
{{ price|round(2) }} — {{ name|upper }} — {{ missing|default("n/a") }}
```

**Output (real run, `price=3.14159, name="flask"`, `missing` undefined):**
```
3.14 — FLASK — n/a
```

Common ones: `length`, `upper`/`lower`/`title`, `round`, `default`, `join`, `truncate`, `tojson`. Chain them freely: `{{ items|join(", ")|upper }}`.

---

## Autoescaping — your XSS defense

Jinja escapes HTML in `{{ }}` **by default**. Given a comment of `<script>alert(1)</script>`:

**Output (real run):**
```html
<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>
```

It rendered as *visible text*, not an executing script. That default is doing real security work on every page.

> ⚠️ **`|safe` disables that protection.** `{{ comment|safe }}` injects raw HTML — if `comment` came from a user, you've just built a stored-XSS hole. Only use `|safe` on markup **you** generated, never on user input. If users must submit rich text, sanitize it server-side (e.g. with `bleach`) before storing.

---

## Recap & next

- ✅ `render_template("x.html", **context)`; templates live in `templates/`.
- ✅ `{{ }}` prints, `{% %}` controls, `{# #}` comments.
- ✅ **`{% extends %}` + `{% block %}`** = one layout, many pages; `for` supports `loop.index` and `{% else %}`.
- ✅ Filters (`|round`, `|default`, `|upper`) transform values inline.
- ✅ **Autoescaping is on by default** — `|safe` turns it off and is an XSS risk on user data.
- ✅ Self-check: a user's note title is `<b>hi</b>`. What does the browser show, and what changes if you add `|safe`?

→ Next: **[02-2 · Static files & flash messages](02_static_and_forms.md)**

## Exercises

1. Build a `base.html` with a nav block and an `index.html` that extends it and lists items, showing "No items yet" when the list is empty.

<details>
<summary>Solution</summary>

Use the `{% for %}…{% else %}…{% endfor %}` form — the `{% else %}` branch renders when the sequence is empty, so you don't need a separate `{% if items %}` wrapper. That's exactly what FlaskNotes' `index.html` does.
</details>
