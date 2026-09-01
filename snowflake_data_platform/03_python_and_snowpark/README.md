# 03 · Python: connector & Snowpark

Two official ways to drive Snowflake from Python, and they are not competitors.
**snowflake-connector-python** is a plain DB-API 2.0 driver — cursors, `execute`,
`fetchall` — plus a fast pandas bridge (`fetch_pandas_all`, **write_pandas**) for
bulk I/O. **Snowpark** is a DataFrame API that compiles to SQL and runs *inside*
Snowflake, so you can transform terabytes without the data ever reaching your
process.

| # | Module | You'll be able to… |
|---|---|---|
| 03-1 | [The Python connector](01_python_connector.md) | Connect safely from env vars or a key pair, run parameterised queries, and keep warehouse billing honest |
| 03-2 | [pandas & bulk I/O](02_pandas_and_bulk_io.md) | Read query results into DataFrames with Arrow and bulk-write them back with `write_pandas` instead of row inserts |
| 03-3 | [Snowpark: DataFrames & Python in Snowflake](03_snowpark_dataframes.md) | Build lazy DataFrame pipelines that execute in Snowflake, and run your own Python there with `@udf` / `@sproc` |

**Next → [03-1 · The Python connector](01_python_connector.md)**
