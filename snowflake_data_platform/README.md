# ❄️ Snowflake — the cloud data platform, hands-on

> **What you build:** **linkstash analytics** — a real warehouse for the link-shortener app from the [AWS](../aws_localstack/) and [FastAPI](../fastapi_complete/) courses. Raw click events land as JSON, get modeled into typed tables, get queried from **Python** (connector + **Snowpark**), get locked down with **RBAC**, get tuned and cost-capped, and finally get an automated **Snowpipe → stream → task** pipeline. Real SQL, real Python, real credits.

> **Written:** 2026-08-22 · Targets a **Snowflake free trial (30 days / $400 credits)** · `snowflake-connector-python` · `snowflake-snowpark-python` (Python 3.10–3.13) · Snowsight UI. Enterprise-only features (masking, row access policies, materialized views) are **flagged as such** rather than assumed.

## ⚠️ Read this first: this course spends real money

Every other cloud course in this repo runs free — the [AWS course](../aws_localstack/) uses LocalStack, an emulator in a container. **Snowflake has no local emulator.** There is no LocalStack for Snowflake, no offline mode, no free-forever tier. You learn it on a **real account against real credits**.

That shapes the whole course:

- You start on the **30-day / $400 trial** — generous for learning, finite.
- Every lesson is **cost-aware**: X-Small warehouse, `AUTO_SUSPEND = 60`, drop what you create.
- **[05 · Performance & cost](05_performance_and_cost/)** is a first-class section, not an appendix — because "can you keep Snowflake from bankrupting us" is a real interview question and a real job responsibility.
- Set a **resource monitor** on day one ([05-3](05_performance_and_cost/03_cost_guardrails.md)). Treat teardown as part of the workflow.

Nothing here is scary — it's the same discipline any cloud spend needs. But it's honest: you cannot do this course entirely for free.

## Why learn Snowflake

It's the default cloud data platform at a large share of companies, and it shows up on backend, data-engineering, and analytics-engineering job descriptions constantly. For a Python/backend engineer it's a high-leverage adjacent skill: you already know SQL and Python — Snowflake is where the *analytical* half of a product's data lives, and "can wire an app's events into a warehouse and query them" is a genuinely marketable sentence.

It is also **not an AWS service.** Snowflake is an independent platform that *runs on* AWS, Azure, or GCP. If you know Redshift or BigQuery, this is the multi-cloud competitor — hence its own course rather than a chapter of the AWS one.

## Who this is for

You can write SQL (`SELECT`, `JOIN`, `GROUP BY`) and Python. Prior AWS/S3 familiarity helps for the external-stage and Snowpipe lessons but isn't required. **No warehouse/OLAP background assumed** — section 01 builds the architecture model from scratch.

## What you'll be able to do

- Explain the **storage / compute / services** separation and why it's the whole point of Snowflake.
- Size and schedule **virtual warehouses** without lighting credits on fire.
- Model a raw → analytics layer, load files with **stages + `COPY INTO`**, and query **semi-structured JSON** with `VARIANT` and `FLATTEN`.
- Drive Snowflake from **Python** — the connector, `write_pandas`, and **Snowpark** DataFrames that push compute into the warehouse.
- Design **RBAC** properly (access roles → functional roles, future grants) and test that denial actually works.
- Read a **Query Profile**, fix pruning, and ship **resource monitors** as guardrails.
- Automate ingestion and transformation with **Snowpipe → stream → task**, and use **Time Travel** and **zero-copy clones** like a professional.

## Course map

| # | Section | Lessons | You'll be able to… | Time |
|---|---------|---------|--------------------|------|
| 00 | [Introduction](00_introduction.md) | — | Know what this is, and what it costs | 15 min |
| 01 | [Foundations](01_foundations/) | 3 | Architecture, trial + Snowsight, warehouses & credits | ~1.2 h |
| 02 | [SQL, tables & loading data](02_sql_and_loading/) | 3 | Databases/schemas/tables, stages + `COPY INTO`, JSON/`VARIANT`/`FLATTEN` | ~1.5 h |
| 03 | [Python: connector & Snowpark](03_python_and_snowpark/) | 3 | Connector, pandas bulk I/O, Snowpark DataFrames + UDFs | ~1.5 h |
| 04 | [Security & RBAC](04_security_and_rbac/) | 3 | Roles/grants/future grants, least privilege, masking & governance | ~1.4 h |
| 05 | [Performance & cost](05_performance_and_cost/) | 3 | Billing model, pruning/caching/tuning, resource monitors | ~1.3 h |
| 06 | [Pipelines & data engineering](06_pipelines_and_engineering/) | 3 | Snowpipe, streams & tasks, Time Travel & clones | ~1.6 h |
| 99 | [Capstone: linkstash analytics](99_capstone_linkstash_analytics.md) | spec | Build the whole pipeline from a spec | ~8–12 h |

**Total:** ~9 h guided + the capstone.

## The stack (and why)

| Concern | We use | Why |
|---------|--------|-----|
| Platform | **Snowflake trial** (30 d / $400) | no emulator exists; this is the only honest way |
| UI / SQL | **Snowsight** worksheets | the modern console; query history + cost views |
| Python (SQL) | **snowflake-connector-python** | DB-API driver; `fetch_pandas_all`, `write_pandas` |
| Python (compute) | **snowflake-snowpark-python** | DataFrames that run *in* Snowflake — no data pulled local |
| Ingestion | **stages + `COPY INTO`**, then **Snowpipe** | batch first, continuous second |
| Transformation | **streams + tasks** (and dynamic tables / dbt noted) | incremental CDC pipelines |
| Security | **RBAC** (roles, future grants) | genuinely enforced — unlike the LocalStack IAM caveat |
| Cost control | **resource monitors**, right-sizing, `AUTO_SUSPEND=60` | the skill that gets you hired and keeps you employed |

## Related guides in this repo

- **[AWS Locally with LocalStack](../aws_localstack/)** — S3 (where external stages point), IAM (the model you'll compare RBAC against), Kinesis/Firehose. Free, emulated.
- **[Inventory Data Engineering](../inventory_data_engineering/)** — relational modeling, ETL, and graph modeling; complementary data-modeling depth.
- **[FastAPI — from first route to production](../fastapi_complete/)** — the app that *produces* the click events this warehouse analyzes.

→ Start here: **[00 · Introduction](00_introduction.md)**
