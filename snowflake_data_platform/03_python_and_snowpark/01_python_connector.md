# 03-1 · The Python connector

> **Level:** Intermediate · **Prerequisites:** [02-3 Semi-structured data](../02_sql_and_loading/03_semi_structured_json.md)
> **Time:** ~30 min · **Verified:** 2026-08-22 (snowflake-connector-python · snowflake-snowpark-python · Python 3.12)

`snowflake-connector-python` is a **DB-API 2.0 driver**. If you have used
`psycopg` you already know the shape: connect, get a cursor, `execute`, fetch.
Nothing exotic to learn — which is exactly why the interesting parts of this
lesson are the three things that *are* Snowflake-specific: **credentials must come
from somewhere safe**, **the session context (warehouse/role/database) is part of
the connection**, and **every query you run wakes a warehouse that bills for a
minimum of 60 seconds**. Get those right and the driver is boring.

---

## Install

```bash
uv add snowflake-connector-python
```

Nothing else is needed for SQL work. The pandas bridge is an extra
(`uv add "snowflake-connector-python[pandas]"`) — that's [03-2](02_pandas_and_bulk_io.md).

---

## Connect — and where the secrets live

Credentials never go in the file. Read them from the environment (a `.env` in dev,
real environment variables or a secret manager in production) and let the process
fail loudly if one is missing:

```python
# linkstash/db.py
import os
from contextlib import contextmanager
from collections.abc import Iterator

import snowflake.connector
from snowflake.connector import SnowflakeConnection


@contextmanager
def snowflake_conn() -> Iterator[SnowflakeConnection]:
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],      # e.g. ab12345.eu-central-1
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],    # dev only — see "Auth" below
        role="LINKSTASH_ANALYST",                     # be explicit, always
        warehouse="ADHOC_WH",
        database="LINKSTASH",
        schema="ANALYTICS",
    )
    try:
        yield conn
    finally:
        conn.close()      # returns the session; the warehouse can now auto-suspend
```

- **`os.environ[...]` not `os.getenv(...)`** — a missing variable raises `KeyError`
  at startup instead of silently sending `None` as a password and failing with a
  confusing auth error.
- **A context manager, not a bare `connect()`.** An unclosed connection holds a
  session open, which keeps the warehouse from auto-suspending — a leaked
  connection in Snowflake costs money, not just a file descriptor.
- If you already use **pydantic-settings** for your FastAPI config, put these
  fields in a `Settings` model instead and pass `settings.model_dump()`; same
  principle, one place for validation:

```python
# linkstash/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SNOWFLAKE_", env_file=".env")

    account: str
    user: str
    password: str | None = None      # dev
    private_key_file: str | None = None   # prod (see below)
    role: str = "LINKSTASH_ANALYST"
    warehouse: str = "ADHOC_WH"
    database: str = "LINKSTASH"
    schema_: str = "ANALYTICS"       # `schema` shadows a BaseSettings attr
```

> **`.env` goes in `.gitignore`.** Commit a `.env.example` with empty values so
> teammates know which variables exist without ever seeing yours.

---

## Why being explicit about the session context matters

`role`, `warehouse`, `database`, `schema` are not decoration. Every Snowflake
session has all four, and if you don't set them the connector inherits the user's
defaults — which someone can change in Snowsight next week without telling you.
Two failure modes, both real:

- **No warehouse** → `No active warehouse selected in the current session`. Your
  script dies at the first `SELECT`.
- **Wrong role** → either a permission error, or worse, a *different* warehouse
  gets billed and your `ETL_WH` cost report goes quiet while `BI_WH` mysteriously
  doubles.

Assert it once at startup if the script matters:

```python
with snowflake_conn() as conn, conn.cursor() as cur:
    cur.execute("SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
    print(cur.fetchone())   # ('LINKSTASH_ANALYST', 'ADHOC_WH', 'LINKSTASH')
```

You can also switch mid-session with `USE WAREHOUSE ETL_WH` — cheap, no reconnect.

---

## Executing queries & fetching rows

```python
with snowflake_conn() as conn, conn.cursor() as cur:
    cur.execute("SELECT slug, country, clicked_at FROM analytics.clicks LIMIT 5")

    rows = cur.fetchall()      # list[tuple] — the whole result set in memory
    one = cur.fetchone()       # next single row, or None when exhausted
    # or stream it — the cursor is an iterator, one row at a time:
    for slug, country, clicked_at in cur:
        ...
```

The choice is about **memory, not speed**:

| | Use when |
|---|---|
| `fetchone()` | you expect exactly one row (a `COUNT`, an existence check) |
| `fetchall()` | the result is small and bounded — a few thousand rows |
| iterate the cursor | the result is large or unbounded; rows arrive in chunks |
| `fetch_pandas_all()` | you want a DataFrame — much faster than `fetchall()` + `DataFrame(...)` ([03-2](02_pandas_and_bulk_io.md)) |

`cur.description` gives column names, and `cur.sfqid` gives the Snowflake query
id — paste it into Snowsight's Query History to see the profile of exactly that
execution. Log it when a query is slow; it saves an afternoon.

---

## Parameter binding — never f-string SQL

The driver's default paramstyle is `pyformat`, so `%s` placeholders with a tuple:

```python
def clicks_for_slug(conn: SnowflakeConnection, slug: str, since: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM analytics.clicks "
            "WHERE slug = %s AND clicked_at >= %s",
            (slug, since),            # values travel separately from the SQL text
        )
        return cur.fetchone()[0]
```

```python
# NEVER. `slug` came from an HTTP request.
cur.execute(f"SELECT COUNT(*) FROM analytics.clicks WHERE slug = '{slug}'")
```

Same discipline as any DB driver, same reason: an f-string makes user input part
of the *statement*, so `slug = "x' OR 1=1 --"` rewrites your query. Binding makes
it a value that can only ever be a value. Snowflake also accepts `?` placeholders
if you prefer them — set `snowflake.connector.paramstyle = "qmark"` once at import
and pass a tuple the same way.

The one thing binding **cannot** do is substitute identifiers — table names,
column names, warehouse names. If those are dynamic, validate against an
allow-list you control; never interpolate a raw string:

```python
ALLOWED_DIMENSIONS = {"country", "device", "referrer"}   # not user-controlled

if dimension not in ALLOWED_DIMENSIONS:
    raise ValueError(f"unknown dimension: {dimension}")
cur.execute(f"SELECT {dimension}, COUNT(*) FROM analytics.clicks GROUP BY 1")
```

---

## Dict rows with `DictCursor`

Tuple unpacking breaks the moment someone adds a column to the `SELECT`. For
anything you serialise (an API response, a JSON dump), ask for dicts:

```python
from snowflake.connector import DictCursor

with snowflake_conn() as conn, conn.cursor(DictCursor) as cur:
    cur.execute("SELECT slug, COUNT(*) AS clicks FROM analytics.clicks GROUP BY 1")
    for row in cur:
        print(row["SLUG"], row["CLICKS"])   # keys are UPPER-CASE — see note
```

**Keys come back upper-cased.** Snowflake folds unquoted identifiers to upper
case, so `slug` in your SQL is the column `SLUG` in the result. Either alias
explicitly (`SELECT slug AS "slug"`) or accept upper case and normalise once at
the boundary. This same casing rule bites much harder in [03-2](02_pandas_and_bulk_io.md).

---

## Transactions & autocommit

The connector runs with **autocommit on by default** — each statement commits
itself. That's usually right for analytics, where you run one big `INSERT … SELECT`
or `COPY INTO` at a time. When several statements must land together, turn it off
and own the commit:

```python
conn = snowflake.connector.connect(**params, autocommit=False)
try:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM analytics.clicks WHERE load_date = %s", (day,))
        cur.execute("INSERT INTO analytics.clicks SELECT ... WHERE load_date = %s", (day,))
    conn.commit()          # both statements, or neither
except Exception:
    conn.rollback()        # a half-reloaded day is worse than no reload
    raise
```

That delete-then-insert pair is the classic case: with autocommit on, a crash
between the two leaves the day's data *deleted and not replaced*. DDL in Snowflake
commits implicitly, so don't mix `CREATE TABLE` into a transaction you plan to
roll back.

---

## Auth: password is for dev, key-pair is for services

| Method | Use for | How |
|---|---|---|
| Password | your own laptop, throwaway scripts | `password=...` |
| **Key-pair (RSA)** | **anything non-interactive: cron, Airflow, CI, containers** | `private_key_file=...` |
| Browser SSO | humans on an SSO account | `authenticator="externalbrowser"` |
| OAuth | apps acting on a user's behalf | `authenticator="oauth"`, `token=...` |

**Key-pair is the production default, not an advanced option.** Snowflake has been
pushing programmatic access away from passwords toward MFA and key pairs, and MFA
is fundamentally incompatible with a cron job — there is nobody there to approve
the push. A key pair also gives you rotation (Snowflake accepts two public keys at
once, so you can roll without downtime) and a credential that can't be typed into
a phishing page.

Generate the pair and register the public half once:

```bash
# encrypted private key — the passphrase is itself a secret
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out linkstash_key.p8
openssl rsa -in linkstash_key.p8 -pubout -out linkstash_key.pub
# then in Snowflake, as a role that can alter the user:
#   ALTER USER linkstash_etl SET RSA_PUBLIC_KEY='MIIBIjANBgkq...';
```

Then connect with no password at all:

```python
conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"],   # path, not the key
    private_key_file_pwd=os.environ["SNOWFLAKE_PRIVATE_KEY_PWD"].encode(),
    role="LINKSTASH_ETL",
    warehouse="ETL_WH",
    database="LINKSTASH",
)
```

If your secret manager hands you PEM *bytes* rather than a file, load them and
pass DER bytes as `private_key` instead:

```python
from cryptography.hazmat.primitives import serialization

key = serialization.load_pem_private_key(
    pem_bytes,                                    # from Vault / AWS Secrets Manager
    password=os.environ["SNOWFLAKE_PRIVATE_KEY_PWD"].encode(),
)
der = key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
conn = snowflake.connector.connect(..., private_key=der)   # note: `private_key`
```

**Where the key lives:** mounted as a file from a secret manager, or fetched at
startup into memory. Never in the repository, never in the image, never in an
environment variable that gets logged. `*.p8` belongs in `.gitignore` on day one.

For interactive human use, `authenticator="externalbrowser"` pops the SSO login in
a browser and stores a short-lived token — great for a notebook, useless in a
container with no browser.

---

## The cost angle: connections are cheap, warehouses are not

A connection by itself costs nothing. **The first query on a suspended warehouse
resumes it, and a resume bills a 60-second minimum** even if your query takes 300
milliseconds. So the expensive pattern is not "long connection" — it's *many
short, scattered ones*:

```python
# BAD — a script that connects per item. 500 items = 500 resume-and-idle cycles,
# and a warehouse that never gets to auto-suspend.
for slug in slugs:
    with snowflake_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO analytics.links VALUES (%s, %s)", (slug, url))
```

```python
# GOOD — one connection, one statement, one warehouse resume.
with snowflake_conn() as conn, conn.cursor() as cur:
    cur.executemany(
        "INSERT INTO analytics.links (slug, target_url) VALUES (%s, %s)",
        [(slug, url) for slug, url in pairs],
    )
```

Three rules that follow from the 60-second minimum:

- **Batch your work into one session.** Open a connection, do everything, close it.
- **Set `AUTO_SUSPEND` low** (60 s) on dev warehouses so a forgotten script stops
  burning credits — [01-3](../01_foundations/03_warehouses_and_credits.md).
- **Close connections deterministically.** The `finally: conn.close()` above isn't
  hygiene theatre; an open session pins the warehouse awake.

And note that `executemany` is still row-by-row `INSERT`s under the hood — fine
for a few hundred rows, wrong for a hundred thousand. That's what
[`write_pandas`](02_pandas_and_bulk_io.md) and `COPY INTO` are for.

---

## Recap & next

- ✅ The connector is **DB-API 2.0** — `connect` → `cursor` → `execute` → fetch;
  wrap it in a **context manager** so sessions always close.
- ✅ **Credentials from `os.environ` / pydantic-settings**, never literals; `.env`
  in `.gitignore`, a `.env.example` in the repo.
- ✅ Set **`role`, `warehouse`, `database`, `schema` explicitly** — inherited
  defaults are someone else's setting, and a missing warehouse is a hard error.
- ✅ **Bind parameters** (`%s` / `?`); identifiers can't be bound, so validate them
  against an allow-list. `DictCursor` for dict rows — keys arrive UPPER-CASE.
- ✅ **Autocommit is on by default**; turn it off when several statements must land
  atomically (delete-then-insert).
- ✅ **Key-pair RSA auth for anything non-interactive**, password for dev only,
  `externalbrowser` for humans. Key from a secret manager or mounted file.
- ✅ **Batch work into one connection** — a query on a suspended warehouse triggers
  a 60-second minimum bill.

## Exercise

Write `top_slugs(conn, country, limit)` that returns the busiest slugs for a
country as a list of dicts. Then explain why calling it in a loop over 40
countries is worse than one query with a `GROUP BY country, slug`.

<details>
<summary>Solution</summary>

```python
from snowflake.connector import DictCursor, SnowflakeConnection


def top_slugs(conn: SnowflakeConnection, country: str, limit: int = 10) -> list[dict]:
    with conn.cursor(DictCursor) as cur:
        cur.execute(
            "SELECT slug, COUNT(*) AS clicks FROM analytics.clicks "
            "WHERE country = %s GROUP BY slug ORDER BY clicks DESC LIMIT %s",
            (country, limit),          # both values bound, including LIMIT
        )
        return cur.fetchall()          # DictCursor.fetchall() → list[dict]
```

Forty calls means forty round trips and forty full scans of `analytics.clicks`,
each one re-reading the same micro-partitions to filter a different country. One
query scans the table **once** and lets Snowflake do all forty groupings in
parallel across the warehouse's cores — the same total work compressed into one
pass, at a fraction of the warehouse-seconds. The wall-clock difference is roughly
40× the per-query latency; the billing difference is bigger, because a warehouse
kept awake by a slow drip of small queries never reaches auto-suspend.

The general rule for an OLAP store: **push the loop into the SQL.** If you find
yourself iterating in Python and querying per item, the `GROUP BY` you want
already exists.
</details>

**→ Next: [03-2 · pandas & bulk I/O](02_pandas_and_bulk_io.md)**
