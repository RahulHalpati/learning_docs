# 99 · Capstone: linkstash analytics

> **Level:** Advanced · **Prerequisites:** [Section 06 · Pipelines](06_pipelines_and_engineering/README.md) — all sections done.
> **Time:** ~8–12 h · **Format:** specification only. No walkthrough. You build it.
> **Budget:** designed to fit comfortably inside the trial's $400 / 30 days if you follow the cost rules.

Build the whole analytics platform for **linkstash** yourself, from this spec — raw ingestion through an automated, secured, cost-capped pipeline. Deliverable is a **git repo** of SQL + Python (plus a short write-up), which is what turns "I did a Snowflake course" into "I built and operated a Snowflake pipeline."

- **Everything as code.** SQL files and Python scripts in the repo — not clicks you can't reproduce. Someone should be able to run your scripts on a fresh trial and get the same platform.
- **Cost is a graded dimension.** Track what you spent and why. A cheap, well-reasoned build beats a fast, wasteful one.
- **When the spec is silent, decide and document it** in `DECISIONS.md`.

---

## The domain

`linkstash` is a link shortener. Every redirect emits a click event as JSON:

```json
{
  "slug": "abc123",
  "clicked_at": "2026-08-22T10:31:07Z",
  "geo": { "country": "IN", "city": "Surat" },
  "referrer": "https://news.example.com/post",
  "user_agent": "Mozilla/5.0 ...",
  "tags": ["campaign-a", "mobile"]
}
```

Plus a small dimension of links (`slug`, `target_url`, `owner`, `created_at`).

---

## Required build

### M0 · Account hygiene (do this first)
- [ ] `dev_wh`: **X-Small**, `AUTO_SUSPEND = 60`, `AUTO_RESUME = TRUE`, `INITIALLY_SUSPENDED = TRUE`
- [ ] A **resource monitor** with a credit quota, `NOTIFY` at 80% and `SUSPEND` at 100%, assigned to the account
- [ ] Objects created as `SYSADMIN` (not `ACCOUNTADMIN`)
- [ ] A `teardown.sql` that drops everything — written *now*, not at the end

### M1 · Layered model
- [ ] Database `linkstash_analytics` with schemas `raw` and `analytics`
- [ ] `raw.raw_clicks` — a **VARIANT** landing table (plus load metadata: filename, loaded_at)
- [ ] `analytics.links` — typed dimension
- [ ] `analytics.clicks` — typed fact, built from the raw VARIANT with explicit `::` casts
- [ ] A justified choice of **transient vs permanent** for the raw layer, written in `DECISIONS.md`

### M2 · Loading
- [ ] A named **internal stage** + a `FILE_FORMAT` for JSON
- [ ] Generate ≥100k synthetic click events (a Python script) and load them with **`COPY INTO`**
- [ ] Demonstrate **load idempotency**: re-run the same `COPY INTO` and show it skips already-loaded files; explain `FORCE=TRUE`'s danger
- [ ] Demonstrate `VALIDATION_MODE` catching a deliberately malformed file
- [ ] A `LATERAL FLATTEN` query over `tags` that returns click counts per tag

### M3 · Python
- [ ] A loader script using **snowflake-connector-python**: credentials from **env vars** (never hardcoded), parameter binding, context-managed connection
- [ ] Bulk-write a pandas DataFrame with **`write_pandas`** — and explain in the README why that beats row-by-row inserts
- [ ] One analytical query implemented **twice**: in SQL, and as a **Snowpark** DataFrame chain — with a note on which you'd ship and why
- [ ] Documented **key-pair auth** for the service user (even if you develop with password auth)

### M4 · RBAC (prove denial, don't assume it)
- [ ] **Access roles** (`linkstash_read`, `linkstash_write`) holding object grants
- [ ] **Functional roles** (`analyst`, `etl_service`) built from those, rolled up to `SYSADMIN`
- [ ] **FUTURE grants** so a newly created table is readable without re-granting — prove it: create a table *after* granting and query it as `analyst`
- [ ] A **denial transcript**: `USE ROLE analyst;` then attempt a write → rejected. Paste the error.
- [ ] Warehouse `MODIFY` restricted so `analyst` cannot resize compute (cost control via RBAC)

### M5 · Performance & cost
- [ ] A **Query Profile** screenshot/notes for one heavy query: partitions scanned vs total, and whether it spilled
- [ ] A **before/after tuning** case: kill a `SELECT *`, add a pruning-friendly filter, report the change in bytes scanned and elapsed time
- [ ] Evidence of the **result cache** (same query twice; second run's compute)
- [ ] A **cost report** from `WAREHOUSE_METERING_HISTORY` + `QUERY_HISTORY`: total credits used by the capstone, and your three biggest consumers
- [ ] `QUERY_TAG` set on the pipeline's queries for attribution

### M6 · Automated pipeline
- [ ] A **stream** on `raw.raw_clicks`
- [ ] A **task** (with `WHEN SYSTEM$STREAM_HAS_DATA(...)`) that incrementally MERGEs new raw rows into `analytics.clicks` — remembering to `ALTER TASK ... RESUME`
- [ ] A second task **`AFTER`** the first, building a daily aggregate (`analytics.daily_link_stats`)
- [ ] Proof it works: insert new raw rows → wait → show the modeled and aggregate tables updated, plus `TASK_HISTORY` output
- [ ] **Time Travel** demo: a destructive `UPDATE`, then recover the prior state via `AT (OFFSET => ...)` or `BEFORE (STATEMENT => ...)`
- [ ] A **zero-copy clone** as a pre-migration safety snapshot, with a note on why it costs (almost) no storage
- [ ] *(Optional)* Snowpipe from an S3 external stage instead of manual `COPY INTO` — or a written explanation of exactly how you'd wire it

---

## Deliverables

- **Repo layout** (suggested): `sql/` (numbered DDL + grants + pipeline), `python/` (loader, snowpark job), `teardown.sql`, `README.md`, `DECISIONS.md`, `COST_REPORT.md`
- **README**: what it is, an architecture diagram, how to run it end-to-end on a fresh trial
- **DECISIONS.md**: transient vs permanent, view vs materialized table for the modeled layer, streams+tasks vs dynamic tables, warehouse sizing
- **COST_REPORT.md**: total credits, the biggest consumers, and what you'd change to halve it

---

## Grading rubric

| Dimension | Strong looks like |
|-----------|-------------------|
| Modeling | Clear raw→analytics separation; explicit casts; no accidental full-VARIANT scans downstream |
| Loading | Idempotent, validated, reproducible from scripts |
| Python | Env-based credentials, bulk I/O not row loops, a defensible connector-vs-Snowpark choice |
| Security | Roles not users; future grants working; **a real denial transcript** |
| Cost | Right-sized, auto-suspended, monitored, measured — with a credible plan to reduce it |
| Automation | Stream+task pipeline that provably processes only new data; tasks actually resumed |
| Recoverability | Time Travel recovery demonstrated; clone used as a safety net |

---

## The interview story this earns

> "I built a Snowflake analytics platform for an app's click stream: raw JSON landing in a VARIANT table, an incremental stream-plus-task pipeline MERGEing into a typed fact table and a daily aggregate, driven from Python with the connector and Snowpark. I set up RBAC with access and functional roles plus future grants — and tested that denial actually works. On cost: X-Small warehouses with 60-second auto-suspend, a resource monitor capping spend, query tags for attribution, and I cut one query's bytes scanned by dropping `SELECT *` and adding a pruning-friendly filter. Whole build came in under X credits, and I documented what I'd change to halve it."

That paragraph answers architecture, SQL, Python, security, cost, and pipelines — and every clause is backed by a file in your repo.

---

**Before you close the account:** run `teardown.sql`, confirm the warehouse is suspended, and screenshot your final credit usage for `COST_REPORT.md`.
