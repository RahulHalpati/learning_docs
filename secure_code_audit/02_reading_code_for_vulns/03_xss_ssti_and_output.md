# 02-3 · XSS, SSTI & output handling

> **Level:** Beginner · **Prerequisites:** [02-2 Injection](02_injection.md)
> **Time:** 25 min · **Verified:** 2026-07-15

Injection's cousins on the *output* side: instead of data becoming code on the
server, it becomes code in the **browser** (XSS) or in the **template engine**
(SSTI). The "attack it" side is Ethical Hacking's
[XSS module](../../ethical_hacking/05_web_application_security/04_cross_site_scripting_xss.md).

---

## Cross-site scripting (XSS, CWE-79)

The shape: user data written into an HTML response **without escaping**.

```python
# VULNERABLE
name = request.args.get("name")
return f"<h1>Hello {name}</h1>"     # name is rendered as raw HTML
```

`name = <script>steal(document.cookie)</script>` → the script runs in every
visitor's browser. The tell: **user data interpolated into a string that becomes
HTML**, or explicit escaping being turned off.

**The fix — escape on output, or let the template engine do it.** Jinja2
autoescapes by default:

```python
from flask import render_template_string
return render_template_string("<h1>Hello {{ name }}</h1>", name=name)  # {{ }} is auto-escaped
```

Watch for escaping being **disabled**: `| safe` in a Jinja template,
`Markup(user_data)`, `autoescape=False`, or `flask.Markup`. Each re-opens the door.

---

## Server-side template injection (SSTI, CWE-1336)

A subtler, more dangerous variant: user input becomes **part of the template
itself**, not just a value in it.

```python
# VULNERABLE — user controls the template string
tmpl = request.args.get("t")
return render_template_string(f"<p>{tmpl}</p>")     # tmpl is compiled as a template!
```

Because Jinja templates can reach Python objects, SSTI often escalates to **remote
code execution** (the classic `{{ ''.__class__.__mro__ ... }}` payloads). The tell
is unmistakable: **user data flowing into the template *string*** passed to
`render_template_string`, not into its `**context`.

**The fix:** never build the template from user input. Keep the template static and
pass user data only as **context variables**:

```python
render_template_string("<p>{{ t }}</p>", t=tmpl)   # tmpl is data, not template code
```

---

## The principle: separate code from data at every boundary

Notice the pattern across 02-2 and 02-3 — SQL, shell, HTML, templates are all
**languages**, and every bug is user data crossing from "data" into "code" in one
of them. The universal fix is the same idea each time: a mechanism that keeps the
two apart (placeholders, argv lists, autoescaping, context variables).

| Boundary | Danger | Keep-apart mechanism |
|---|---|---|
| App → SQL | SQLi | parameterised queries |
| App → shell | command injection | argv list, no shell |
| App → browser (HTML) | XSS | output escaping / autoescape |
| App → template engine | SSTI | static template + context vars |

---

## Recap & next

- ✅ **XSS** = unescaped user data in HTML output; **SSTI** = user data in the
  *template string* itself (often RCE).
- ✅ Tells: interpolating into HTML, `| safe` / `Markup` / `autoescape=False`,
  user input reaching `render_template_string`'s template.
- ✅ Every injection family is the same story — **keep code and data apart** at
  each language boundary.

## Exercise

A template renders `{{ comment | safe }}` where `comment` is user-submitted. Is
this safe? What would you change?

<details>
<summary>Solution</summary>

**Not safe** — `| safe` disables autoescaping, so a comment containing
`<script>…</script>` executes (stored XSS). Remove `| safe` and let Jinja escape
it (`{{ comment }}`). If you must allow *some* HTML, sanitize with an allow-list
library (e.g. `bleach`) before marking it safe — never trust raw user HTML.

</details>

**→ Next: [02-4 · Auth, secrets & crypto](04_auth_secrets_crypto.md)**
