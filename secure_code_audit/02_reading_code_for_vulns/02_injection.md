# 02-2 · Injection: SQL, command, and code

> **Level:** Beginner · **Prerequisites:** [02-1 The review workflow](01_the_review_workflow.md)
> **Time:** 30 min · **Verified:** 2026-07-15

Injection is the archetypal vulnerability: untrusted data is interpreted as *code*
(SQL, a shell command, Python) instead of *data*. Same root cause, three flavors.
This is the "attack it" counterpart to Ethical Hacking's
[SQL injection module](../../ethical_hacking/05_web_application_security/03_sql_injection.md) —
here you find it in the source.

---

## SQL injection (CWE-89)

The shape: user data **built into** a query string.

```python
# samples/vulnerable_app/app.py  — VULNERABLE
username = request.form["username"]                       # source
cur.execute(f"SELECT * FROM users WHERE name = '{username}'")   # sink: f-string query
```

Send `username = ' OR '1'='1` and the query becomes
`... WHERE name = '' OR '1'='1'` — authentication bypassed. Any of these string
constructions is the tell:

```python
cur.execute("... WHERE id = " + user_id)        # concatenation
cur.execute("... WHERE id = %s" % user_id)       # % formatting
cur.execute("... WHERE id = {}".format(user_id)) # .format
cur.execute(f"... WHERE id = {user_id}")         # f-string
```

**The fix — parameterised queries.** Let the driver handle quoting:

```python
cur.execute("SELECT * FROM users WHERE name = ?", (username,))   # sqlite
cur.execute("SELECT * FROM users WHERE name = %s", (username,))  # psycopg/mysql
```

The `?`/`%s` is a **placeholder**, not string formatting — the value never
becomes part of the SQL text, so it can't change the query's structure.

---

## Command injection (CWE-78)

The shape: user data in a shell command.

```python
# VULNERABLE
host = request.args.get("host")
subprocess.check_output("ping -c1 " + host, shell=True)   # shell parses the whole string
os.system("logger " + host)
```

`host = 127.0.0.1; rm -rf /` → the shell runs both commands. Two tells:
**`shell=True`** and **`os.system`** with anything dynamic.

**The fix — no shell, pass an argument list:**

```python
subprocess.check_output(["ping", "-c1", host])   # host is one argument, never parsed by a shell
```

With a list and no `shell=True`, `host` can't inject extra commands — it's a
single argv element.

---

## Code injection (CWE-95)

The shape: `eval` / `exec` on input.

```python
# VULNERABLE
tmpl = request.args.get("t")
return str(eval(tmpl))     # attacker runs arbitrary Python
```

`t = __import__('os').system('id')` → remote code execution. There is essentially
**no safe way** to `eval`/`exec` untrusted input.

**The fix — don't.** Use a real parser for the thing you actually need:
`ast.literal_eval` for a Python literal, `json.loads` for JSON, a proper library
for expressions. If you think you need `eval`, you need a parser.

---

## Recap & next

- ✅ Injection = untrusted data interpreted as **code**. Same root cause for SQL,
  shell, and Python.
- ✅ Tells: **string-built queries**, **`shell=True`/`os.system`**, **`eval`/`exec`**.
- ✅ Fixes: **parameterised queries**, **argument lists (no shell)**, **a real
  parser instead of `eval`**.

## Exercises

**Exercise 1:** Find both SQL-injection sinks in `samples/vulnerable_app/app.py`
by hand, then rewrite the `/search` one to be safe.

<details>
<summary>Solution</summary>

`/login` (line ~32, f-string) and `/search` (line ~44, concatenation into
`conn.execute(query)`). Safe `/search`:

```python
term = request.args.get("q", "")
rows = conn.execute(
    "SELECT * FROM items WHERE title LIKE ?", (f"%{term}%",)
).fetchall()
```

The `%…%` wildcards live in the **value**, not the SQL text; the placeholder keeps
`term` from altering the query structure.

</details>

**Exercise 2:** Why is `subprocess.run(["ls", user_dir])` safe while
`subprocess.run("ls " + user_dir, shell=True)` is not, even though both take user
input?

<details>
<summary>Solution</summary>

Without a shell, `user_dir` is passed as a **single argument** to `ls` — shell
metacharacters (`;`, `|`, `&&`, `$()`) have no special meaning, so nothing extra
runs. With `shell=True`, the whole string is handed to `/bin/sh`, which *does*
interpret those metacharacters, so `user_dir = "; rm -rf /"` executes a second
command.

</details>

**→ Next: [02-3 · XSS, SSTI & output](03_xss_ssti_and_output.md)**
