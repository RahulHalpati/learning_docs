# 03-2 · pandas & bulk I/O

> **Level:** Intermediate · **Prerequisites:** [03-1 The Python connector](01_python_connector.md)
> **Time:** ~25 min · **Verified:** 2026-08-22 (snowflake-connector-python · snowflake-snowpark-python · Python 3.12)

You know pandas. The interesting question is how data crosses the boundary between
Snowflake and a DataFrame, because the obvious way is the slow way in both
directions. Reading with `fetchall()` and building a DataFrame from tuples throws
away Snowflake's columnar wire format; writing with `INSERT` statements throws away
everything a warehouse is good at. Two functions fix both: **`fetch_pandas_all()`**
and **`write_pandas()`**.

---

## Install the extra

```bash
uv add "snowflake-connector-python[pandas]"
```

The `[pandas]` extra pulls in **pyarrow**. That's the whole point: Snowflake sends
results over the wire as Arrow record batches — a columnar binary format — and
pyarrow turns them into a DataFrame with almost no conversion work. Without the
extra, `fetch_pandas_all()` raises `NotSupportedError`.

---

## Reading: `fetch_pandas_all()` vs the naive way

```python
# NAIVE — rows arrive as Arrow, get materialised into Python tuples, then pandas
# re-boxes every value into a column. Two pointless conversions per cell.
cur.execute("SELECT slug, country, clicked_at FROM analytics.clicks")
df = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
```

```python
# FAST — Arrow batches go straight into pandas columns, dtypes and all.
import pandas as pd

with snowflake_conn() as conn, conn.cursor() as cur:
    cur.execute("""
        SELECT slug, country, COUNT(*) AS clicks
        FROM analytics.clicks
        WHERE clicked_at >= %s
        GROUP BY slug, country
    """, (since,))
    df: pd.DataFrame = cur.fetch_pandas_all()   # requires the [pandas] extra
```

The naive version is typically several times slower on a wide result and uses far
more peak memory, because every value exists as a Python object at least once.
Note the query still does the aggregation — you are pulling *results*, not raw
rows. The size of the DataFrame is your choice, made in SQL.

### `fetch_pandas_batches()` for results bigger than RAM

`fetch_pandas_all()` builds one DataFrame — so the whole result must fit in memory.
When it won't, stream:

```python
cur.execute("SELECT * FROM analytics.clicks WHERE clicked_at >= %s", (since,))

totals: dict[str, int] = {}
for batch in cur.fetch_pandas_batches():      # one DataFrame per Arrow batch
    for country, n in batch.groupby("COUNTRY").size().items():
        totals[country] = totals.get(country, 0) + n   # fold, don't accumulate
```

This works, and it is also a smell: you just wrote a `GROUP BY` in Python. If your
answer is an aggregate, aggregate in SQL and fetch the small result. Batches are
for when you genuinely need every row locally — feeding a model, writing files,
calling an external API per row. If you need row-level work at scale *without*
pulling it down, that's [Snowpark](03_snowpark_dataframes.md).

---

## Writing: `write_pandas`

```python
from snowflake.connector.pandas_tools import write_pandas

with snowflake_conn() as conn:
    success, n_chunks, n_rows, _ = write_pandas(
        conn,
        df,                            # column names must match the table's
        table_name="LINKS",            # existing table
        database="LINKSTASH",
        schema="ANALYTICS",
        quote_identifiers=False,       # see the casing trap below
        chunk_size=100_000,            # rows per staged file
    )
    print(f"{n_rows} rows in {n_chunks} chunk(s), ok={success}")
```

### What it actually does — and why that makes it fast

`write_pandas` does not generate `INSERT` statements. Under the hood it:

1. writes your DataFrame to **Parquet** files locally (one per chunk),
2. `PUT`s them to a **temporary internal stage**,
3. runs **`COPY INTO <table>`** to load them in parallel,
4. drops the stage.

```mermaid
flowchart LR
    DF[pandas DataFrame] -->|to_parquet| F[Parquet chunks]
    F -->|PUT| S[(Temporary<br/>internal stage)]
    S -->|COPY INTO<br/>parallel load| T[(ANALYTICS.LINKS)]
```

That is the same bulk-load path you built by hand in
[02-2](../02_sql_and_loading/02_stages_and_copy_into.md), just wrapped in one call.
It's fast for one structural reason: **`COPY INTO` is a parallel, columnar bulk
load; `INSERT` is a transaction per statement.** A warehouse loads staged files
across all its cores at once, while `executemany` walks rows through the query
compiler one batch at a time.

> **The honest rule: single-row `INSERT`s into an analytics warehouse are an
> anti-pattern.** Snowflake stores data in immutable ~16 MB micro-partitions, so a
> one-row insert writes a whole tiny partition. Do it a million times and you have
> a million miserable partitions, a shredded table, and a bill dominated by
> overhead. Batch to files and `COPY`, or stage and `COPY` on a schedule
> (Snowpipe — [section 06](../06_pipelines_and_engineering/README.md)). If you truly
> need per-row writes with low latency, that workload belongs in Postgres.

---

## The casing trap

This is the single most common `write_pandas` bug, so it gets its own section.

Snowflake **folds unquoted identifiers to upper case**. `CREATE TABLE links (slug
STRING, clicked_at TIMESTAMP)` actually creates columns named `SLUG` and
`CLICKED_AT`. Meanwhile your DataFrame has lower-case columns from
`pd.read_csv`. And `write_pandas` defaults to **`quote_identifiers=True`**, which
wraps your DataFrame's column names in double quotes — making them
case-*sensitive*:

```sql
-- what write_pandas generates with quote_identifiers=True and lower-case columns
COPY INTO "LINKS" ("slug", "clicked_at") FROM ...
-- error: invalid identifier '"clicked_at"' … there is no column "clicked_at",
-- only CLICKED_AT
```

Two fixes, pick one and be consistent:

```python
# Fix A — normalise the DataFrame to Snowflake's own convention (recommended).
df.columns = df.columns.str.upper()
write_pandas(conn, df, "LINKS")          # keeps default quote_identifiers=True

# Fix B — let Snowflake fold the names for you.
write_pandas(conn, df, "LINKS", quote_identifiers=False)
```

Fix A is safer: with `quote_identifiers=False`, a column name containing a space or
a reserved word produces broken SQL. And the mirror image applies on reads — a
DataFrame from `fetch_pandas_all()` has UPPER-CASE columns, which is why round
trips work naturally if you standardise on upper case everywhere and lower-case
only at your API boundary.

Other gotchas in the same family:

- **`table_name` is also case-folded.** Pass `"LINKS"`, not `"links"`, unless the
  table was genuinely created as `"links"` in quotes.
- **dtypes:** pandas `object` columns land as `VARIANT` or `STRING` depending on
  content; `datetime64[ns]` maps to `TIMESTAMP_NTZ` (no timezone). If you care
  about timezones, use `datetime64[ns, UTC]` and a `TIMESTAMP_TZ` column, or store
  UTC and be explicit about it. `NaN` becomes `NULL`; an all-`NaN` float column
  still lands as `FLOAT`, not the type you meant.
- **Nothing validates your schema for you.** `write_pandas` will happily load a
  column of strings into a `NUMBER` column and fail mid-`COPY`, or silently drop
  DataFrame columns the table doesn't have.

---

## `auto_create_table` — convenient, and usually wrong

```python
write_pandas(conn, df, "CLICKS_STAGING", auto_create_table=True)   # infers the DDL
```

It works, and it's genuinely useful for a scratch table in a notebook. Why you
don't want it in a pipeline:

- The **types are inferred from this batch**. A column that happens to hold only
  integers today becomes `NUMBER`, then breaks when tomorrow's file has a decimal
  or a null-turned-string.
- Everything wide becomes `VARCHAR(16777216)` — no constraints, no clustering
  choices, no comments, no idea what the table is supposed to contain.
- Your table's schema now lives in whatever DataFrame ran first, not in version
  control. Nobody can review it.

Create tables deliberately in SQL (or migrations), and let `write_pandas` only
ever *load* into a table whose shape you decided on purpose. `overwrite=True`
exists too — it replaces the table's contents, which is fine for a
rebuild-from-scratch dimension table and dangerous for anything else.

---

## Chunking large DataFrames

`chunk_size` controls rows per staged file, and the default (100k) is a reasonable
starting point. Snowflake's own guidance for bulk loading is files of roughly
**100–250 MB compressed** — that's big enough to amortise per-file overhead and
small enough that the warehouse can load several in parallel.

```python
# A 20M-row DataFrame: 200 files, loaded in parallel by the warehouse.
write_pandas(conn, big_df, "CLICKS", chunk_size=100_000)
```

Rules of thumb:

- **Too small** (thousands of tiny files) → per-file overhead dominates; the load
  is slower than a bigger warehouse can fix.
- **Too large** (one 5 GB file) → no parallelism; one thread does everything.
- If a 20M-row DataFrame doesn't fit in *your* RAM in the first place, don't build
  it — write Parquet from your source in a loop, `PUT` to a stage, and `COPY INTO`.
  Or use Snowpark and never materialise it locally at all.

---

## Which tool when

| Tool | Use when | Data flows |
|---|---|---|
| **connector + SQL** | DDL, one-off queries, small results, anything a `GROUP BY` answers | Snowflake does the work; a few rows come back |
| **`fetch_pandas_all()`** | you need an *aggregated* result in pandas — charts, a model's features, an API response | small/medium result → your process |
| **`write_pandas()`** | pushing a DataFrame you already have in memory into a table | your process → stage → table (Parquet + `COPY`) |
| **`COPY INTO` from a stage** | files already in S3/GCS/Azure, or produced by another system; the largest loads | cloud storage → table, your process never touches the rows |
| **Snowpark** | transformations over data too big for local RAM, expressed in Python | nothing moves; the plan runs in Snowflake ([03-3](03_snowpark_dataframes.md)) |
| `executemany` INSERT | a few hundred rows of config/lookup data, nothing more | row-by-row — accept the cost knowingly |

The decision collapses to one question: **does the data need to be in your process
at all?** If the answer is no — you're filtering, joining, aggregating, or writing
results back — keep it in Snowflake. pandas is for the last mile, once the result
is small enough to be interesting to a human or a model.

---

## Recap & next

- ✅ Install `[pandas]` for the **pyarrow** bridge; `fetch_pandas_all()` turns Arrow
  batches straight into a DataFrame, far cheaper than `fetchall()` + `DataFrame(...)`.
- ✅ **`fetch_pandas_batches()`** streams results bigger than RAM — but if you're
  folding batches into an aggregate, write the aggregate in SQL instead.
- ✅ **`write_pandas` stages Parquet + runs `COPY INTO`** — that's why it beats
  `INSERT`. Single-row inserts into an analytics warehouse are an anti-pattern
  (one tiny micro-partition per row).
- ✅ **Casing:** Snowflake upper-cases unquoted identifiers; `quote_identifiers`
  defaults to `True`, so upper-case your DataFrame columns (or pass `False`).
- ✅ **Create tables deliberately** — `auto_create_table` infers types from one
  batch and hides your schema from code review.
- ✅ `chunk_size` for parallel loading (aim ~100–250 MB compressed per file).
- ✅ Ask **"does this data need to be in my process?"** — if not, keep the work in
  Snowflake.

## Exercise

You have a 12M-row `clicks.csv` on disk and an empty `ANALYTICS.CLICKS` table.
Write the loader, then say what you'd do differently if the file were 200 GB.

<details>
<summary>Solution</summary>

```python
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas

with snowflake_conn() as conn:                      # ONE connection, one resume
    for chunk in pd.read_csv("clicks.csv", chunksize=1_000_000):
        chunk.columns = chunk.columns.str.upper()   # SLUG, CLICKED_AT, COUNTRY…
        chunk["CLICKED_AT"] = pd.to_datetime(chunk["CLICKED_AT"], utc=True)
        write_pandas(conn, chunk, "CLICKS", chunk_size=250_000)
```

`pd.read_csv(chunksize=...)` keeps peak memory bounded — you never hold 12M rows
at once — and each `write_pandas` call stages a handful of Parquet files that the
warehouse loads in parallel. The `str.upper()` line is what stops the
`invalid identifier` error; the explicit `to_datetime(utc=True)` stops pandas from
guessing and landing your timestamps as strings.

**At 200 GB, don't use pandas at all.** Nothing about this problem needs the rows
in a Python process:

1. Upload the raw file(s) to a stage (`PUT`, or an external stage over
   S3/GCS/Azure — better still, split into ~150 MB gzipped parts).
2. `COPY INTO ANALYTICS.CLICKS FROM @stage FILE_FORMAT = (TYPE = CSV …)` on a
   larger warehouse for the duration of the load, then resize back down.

That path never serialises through your machine, uses the warehouse's full
parallelism, and gets `COPY`'s load metadata for free — re-running skips files it
has already loaded, so the load is idempotent. Pandas would be a bottleneck
standing between two systems that can talk to each other directly.
</details>

**→ Next: [03-3 · Snowpark: DataFrames & Python in Snowflake](03_snowpark_dataframes.md)**
