# 05-1 · How Snowflake bills you

> **Level:** Intermediate · **Prerequisites:** [04-3 · Data governance](../04_security_and_rbac/03_data_governance.md)
> **Time:** ~25 min · **Verified:** 2026-08-22 (Snowflake trial; Enterprise-only features flagged)

"Can you keep Snowflake from bankrupting us" is a real interview question because
it is a real job. Snowflake's separation of storage and compute — the thing
[01-1](../01_foundations/01_what_is_snowflake.md) sold as elegant — also means the
platform will happily give you a 128-credits-per-hour cluster for a `SELECT *` on
a 900-row table, and send an invoice that is technically correct.

Nothing in this module is exotic. The bill has three lines, one of them dominates,
and the levers are all parameters you already know how to set. What's missing on
most teams is somebody who *reads* the bill.

---

## The three billing dimensions

| Dimension | Unit | What drives it | Share of a typical bill |
|---|---|---|---|
| **Compute** | **credits**, per-second (60 s minimum per start/resume) | Warehouse size × seconds running — *not* rows returned | usually 80–95% |
| **Storage** | $/TB-month on **compressed** bytes | Table data + Time Travel + Fail-safe + stages | the rest |
| **Cloud services** | credits | Metadata, query compilation, result cache lookups, DDL | ~0 — billed only above **~10% of that day's compute credits** |

Three consequences worth internalising:

- **Compute is the bill.** Optimise warehouse *time* first, everything else second.
- **Cloud services is free in practice.** You'd have to run a workload of almost
  pure metadata operations (thousands of `SHOW`/`DESCRIBE`/result-cache hits and
  almost no warehouse time) to breach the 10% daily allowance. Don't design around it.
- **Storage is cheap but permanent.** A forgotten 200 GB table bills every month
  until someone drops it. Compute mistakes stop when the warehouse suspends;
  storage mistakes don't stop at all.

---

## Per-second billing, with a 60-second floor

A warehouse bills **per second while it is running**, with a **minimum of 60
seconds every time it starts or resumes**. That floor is the single most
misunderstood line in Snowflake pricing, and it dictates how you should shape work.

```sql
-- Three separate 2-second queries, 5 minutes apart, on a warehouse with
-- AUTO_SUSPEND = 60. Each one resumes a suspended warehouse:
--   query 1 → 60 s billed   (2 s work + 58 s of minimum/idle)
--   query 2 → 60 s billed
--   query 3 → 60 s billed
-- 6 seconds of work, 180 seconds of billing. 30× overhead.
```

Run those same three queries back to back in one session and you pay **~60
seconds total**. Same work, one third of the cost, zero tuning.

So the worst pattern in Snowflake is not the giant query — it is **many tiny cold
queries**: a dashboard polling every 5 minutes, a cron job that fires one
`INSERT` per minute, a health check that runs `SELECT 1` on a warehouse. Each
wakes a warehouse and pays the floor.

The fixes, in order of laziness:

- **Batch.** One statement, or one session, instead of N scattered ones.
- **Let the result cache serve repeats** (05-2) — a cache hit needs *no*
  warehouse, so it never pays the floor.
- **Share one warehouse** across small jobs so they land inside the same
  already-running window, instead of each waking its own.
- **Raise `AUTO_SUSPEND`** *only* for genuinely interactive traffic where the
  warehouse would be re-woken constantly anyway.

> **Careful with that last one.** Going from `AUTO_SUSPEND = 60` to `600` to avoid
> the 60-second floor usually *costs* more, not less: you replace 58 wasted seconds
> per query with 600 wasted seconds per idle period. Only raise it when queries
> arrive more often than the suspend window, and even then keep it small.

---

## The size curve: each step doubles

Warehouse sizes step up by a factor of two in both compute nodes and price:

| Size | Credits / hour | Credits / second | Relative |
|---|---|---|---|
| X-Small | 1 | 0.00028 | 1× |
| Small | 2 | 0.00056 | 2× |
| Medium | 4 | 0.0011 | 4× |
| Large | 8 | 0.0022 | 8× |
| X-Large | 16 | 0.0044 | 16× |
| 2X-Large | 32 | 0.0089 | 32× |
| 3X-Large | 64 | 0.0178 | 64× |
| 4X-Large | 128 | 0.0356 | 128× |

At ~$2–4 per credit, a 4X-Large left running over a long weekend is roughly
$20,000–$40,000. That's the number behind the interview question.

### The counter-intuitive part

Doubling the size doubles the *rate*, but a bigger warehouse also has twice the
compute to finish with. For a **single large, parallelisable scan**, total credits
are often about the same:

| Job | Warehouse | Wall clock | Credits |
|---|---|---|---|
| Aggregate 1.5 B rows | Medium (4/hr) | 16 min | ~1.07 |
| Aggregate 1.5 B rows | Large (8/hr) | 8 min | ~1.07 |
| Aggregate 1.5 B rows | X-Large (16/hr) | 4.5 min | ~1.20 |

So for big ETL, **sizing up buys speed at roughly constant cost** — until
parallelism runs out (the X-Large row above: 2× the rate for only 1.8× the speed)
or the job is too small to fill the cluster.

Now the other direction:

| Job | Warehouse | Wall clock | Credits |
|---|---|---|---|
| `SELECT COUNT(*) ... WHERE day = ...` | X-Small (1/hr) | 1.4 s → **60 s billed** | 0.017 |
| Same query | X-Large (16/hr) | 1.1 s → **60 s billed** | 0.267 |

Identical answer, 0.3 s faster, **16× the cost**. An oversized warehouse on small
queries is pure waste, and the 60-second floor makes it worse — you pay the big
rate for a full minute no matter how fast it finished.

**The rule:** size by *scan volume and query complexity*, never by importance or
by how many users are waiting. Concurrency is a different problem — solved by
multi-cluster warehouses (Enterprise+) or more warehouses, not a bigger one.

### Right-sizing by workload

Different workloads want different warehouses. This is also why you split them
(05-3): one warehouse per workload gives each its own size *and* makes the bill
attributable.

| Workload | Start at | Why | `AUTO_SUSPEND` |
|---|---|---|---|
| BI / dashboards / ad-hoc SQL | **X-Small → Small** | Small scans, well-filtered, cache-friendly | 60 s (or a few minutes if genuinely interactive) |
| Python/Snowpark development | **X-Small** | You spend most of the time typing | 60 s |
| Nightly ETL / big transforms | **Large → 2X-Large** | Sizing up is ~cost-neutral and finishes the window | 60 s |
| One-off backfill of a huge table | **size up temporarily**, then `ALTER` back | Speed at constant credits | 60 s |

For linkstash, `dev_wh` stays X-Small for the whole course. The honest reason to
ever resize it is that a specific query *spills to storage* — the signal from
[05-2](02_pruning_caching_tuning.md) — not a hunch that bigger is better.

```sql
-- Resizing is instant and online: it applies to the next query, not the running one.
-- No recreate, no reconnect, no downtime.
ALTER WAREHOUSE dev_wh SET WAREHOUSE_SIZE = 'LARGE';   -- for the backfill
ALTER WAREHOUSE dev_wh SET WAREHOUSE_SIZE = 'XSMALL';  -- ...and straight back
```

---

## Reading what you actually spent

Two views do 90% of cost work. Both live in the `SNOWFLAKE` database (you need
`ACCOUNTADMIN`, or a role granted the `GOVERNANCE_VIEWER`/`USAGE_VIEWER` database
roles — see [04-2](../04_security_and_rbac/02_roles_and_grants_in_practice.md)).

### Credits by warehouse and day

```sql
-- WAREHOUSE_METERING_HISTORY is hourly-granular credit consumption per warehouse.
-- This is the query to run every morning during the trial.
SELECT warehouse_name,
       DATE(start_time)                    AS day,
       ROUND(SUM(credits_used_compute), 3) AS compute_credits,
       ROUND(SUM(credits_used_cloud_services), 3) AS cloud_svc_credits
FROM   snowflake.account_usage.warehouse_metering_history
WHERE  start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY day DESC, compute_credits DESC;
```

```
WAREHOUSE_NAME | DAY        | COMPUTE_CREDITS | CLOUD_SVC_CREDITS
DEV_WH         | 2026-08-21 | 0.412           | 0.008
LOAD_WH        | 2026-08-21 | 0.183           | 0.004
DEV_WH         | 2026-08-20 | 1.940           | 0.011
COMPUTE_WH     | 2026-08-20 | 0.067           | 0.001
```

Note `cloud_svc_credits` is ~2% of compute here — comfortably under the 10%
allowance, so it costs nothing. And note `DEV_WH` on 08-20: 1.94 credits on an
X-Small means **~2 hours of runtime**. If you only worked for 20 minutes that day,
something didn't suspend. That gap between "time I worked" and "credits billed" is
the whole game.

### Bytes scanned per query

Credits tell you *that* you spent; `QUERY_HISTORY` tells you *what* spent it.

```sql
-- The expensive-query leaderboard. bytes_scanned is the cost driver in a
-- columnar engine; execution_time is what you feel.
SELECT LEFT(query_text, 60)                          AS query,
       warehouse_name,
       warehouse_size,
       ROUND(bytes_scanned / POWER(1024, 3), 2)      AS gb_scanned,
       ROUND(execution_time / 1000, 1)               AS exec_s,
       ROUND(percentage_scanned_from_cache * 100, 0) AS pct_from_cache,
       query_tag
FROM   snowflake.account_usage.query_history
WHERE  start_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND  warehouse_name IS NOT NULL        -- exclude free metadata-only queries
ORDER BY bytes_scanned DESC NULLS LAST
LIMIT 10;
```

```
QUERY                                    | WAREHOUSE_NAME | WAREHOUSE_SIZE | GB_SCANNED | EXEC_S | PCT_FROM_CACHE | QUERY_TAG
SELECT * FROM analytics.clicks ORDER BY  | DEV_WH         | X-Small        | 12.40      | 96.3   | 0              | NULL
INSERT INTO analytics.clicks SELECT ...  | LOAD_WH        | X-Small        | 3.11       | 22.8   | 12             | etl:clicks_nightly
SELECT link_id, COUNT(*) FROM analytics. | DEV_WH         | X-Small        | 0.42       | 3.1    | 74             | bi:top_links
```

That first row is the module in one line: a `SELECT *` with an `ORDER BY` and no
filter, 12.4 GB scanned, 96 seconds, nothing from cache. [05-2](02_pruning_caching_tuning.md)
turns it into ~0.1 GB.

> **Two `QUERY_HISTORY` views, pick deliberately.**
> `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` — ~1 year of retention, **lags minutes
> to a few hours**. Use it for trends, chargeback, post-mortems.
> `INFORMATION_SCHEMA.QUERY_HISTORY()` — table function, ~7–14 days, **near
> real-time**. Use it for "what did I just run?". Same lag/retention trade-off
> applies to most `ACCOUNT_USAGE` views.

---

## `QUERY_TAG`: making cost attributable

A shared warehouse's bill is one number. `QUERY_TAG` is a free string stamped onto
every query in your session, and it's what turns that number into a chargeback
report.

```sql
-- Set it per session, per job, per dbt run — anything you'd want a line item for.
ALTER SESSION SET QUERY_TAG = 'etl:clicks_nightly';
INSERT INTO analytics.clicks SELECT ... FROM raw.raw_clicks WHERE ...;
ALTER SESSION UNSET QUERY_TAG;
```

From Python (section 03), set it right after connecting so every statement in the
job carries it:

```python
# One line in your connection setup earns you per-job cost reporting forever.
conn.cursor().execute("ALTER SESSION SET QUERY_TAG = 'etl:clicks_nightly'")
```

Then cost per job is a `GROUP BY`:

```sql
-- Approximate credits by tag. Snowflake bills the warehouse, not the query, so
-- apportion by execution time — imperfect, but good enough to find the culprit.
SELECT COALESCE(query_tag, '(untagged)') AS job,
       COUNT(*)                          AS queries,
       ROUND(SUM(execution_time) / 3600000, 2) AS warehouse_hours,
       ROUND(SUM(bytes_scanned) / POWER(1024, 4), 3) AS tb_scanned
FROM   snowflake.account_usage.query_history
WHERE  start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
  AND  warehouse_name IS NOT NULL
GROUP BY 1
ORDER BY warehouse_hours DESC;
```

```
JOB                 | QUERIES | WAREHOUSE_HOURS | TB_SCANNED
(untagged)          | 412     | 1.86            | 0.041
etl:clicks_nightly  | 63      | 0.44            | 0.019
bi:top_links        | 190     | 0.09            | 0.003
```

`(untagged)` winning is the normal starting state. Tagging is a five-minute change
that makes the next cost conversation evidence-based instead of a guessing game.

---

## The storage side

Storage is billed on **compressed** bytes, averaged daily, and it's usually a
rounding error next to compute — right up until Time Travel on a huge table isn't.

```sql
-- ACTIVE_BYTES = current data. TIME_TRAVEL + FAILSAFE are what you also pay for.
SELECT table_name,
       ROUND(active_bytes / POWER(1024, 3), 2)          AS active_gb,
       ROUND(time_travel_bytes / POWER(1024, 3), 2)     AS time_travel_gb,
       ROUND(failsafe_bytes / POWER(1024, 3), 2)        AS failsafe_gb
FROM   snowflake.account_usage.table_storage_metrics
WHERE  table_catalog = 'LINKSTASH_ANALYTICS'
  AND  deleted = FALSE
ORDER BY active_bytes DESC;
```

```
TABLE_NAME | ACTIVE_GB | TIME_TRAVEL_GB | FAILSAFE_GB
RAW_CLICKS | 2.84      | 1.10           | 2.84
CLICKS     | 1.62      | 0.31           | 1.62
LINKS      | 0.01      | 0.00           | 0.01
```

Read that table carefully: `RAW_CLICKS` holds 2.84 GB of data and you are paying
for **6.78 GB**. Three multipliers explain it:

- **Time Travel** keeps changed/deleted data for `DATA_RETENTION_TIME_IN_DAYS`
  (1 day by default, up to 90 on Enterprise). Heavy churn ⇒ big Time Travel bytes.
- **Fail-safe** is a further **7 days**, Snowflake-managed, not configurable, not
  queryable — pure insurance you cannot switch off on a permanent table.
- **Transient tables** have **no Fail-safe** (and at most 1 day of Time Travel).
  For anything you can reload from a stage — `raw_clicks` is the textbook case —
  transient roughly halves the storage footprint. Full treatment in
  [05-3](03_cost_guardrails.md) and section 06.

Compute levers pay off daily; storage levers pay off every month forever. Both are
one-line DDL.

---

## Recap & next

- ✅ Three dimensions: **compute credits** (80–95% of the bill), **storage** on
  compressed bytes, **cloud services** (free below ~10% of daily compute).
- ✅ Compute bills **per second with a 60-second minimum per resume** — so many
  tiny cold queries is the worst pattern; batch them or let the result cache serve them.
- ✅ Each size step **doubles credits/hour**. Sizing up a big parallel job is
  roughly cost-neutral (it finishes sooner); sizing up small queries is 2ⁿ× waste.
  Size by **scan volume**, not by importance — and solve concurrency with more
  warehouses, not bigger ones.
- ✅ `WAREHOUSE_METERING_HISTORY` = credits per warehouse per hour;
  `QUERY_HISTORY` = bytes scanned per query. `ACCOUNT_USAGE` lags but retains ~1
  year; `INFORMATION_SCHEMA` is fresh but short.
- ✅ `QUERY_TAG` costs nothing and makes cost **attributable** to a job or team.
- ✅ Storage = compressed bytes **plus Time Travel plus 7 days of Fail-safe** —
  transient tables drop the Fail-safe half.

## Exercise

Your team runs a Snowsight dashboard on `analytics.clicks`. It has 8 tiles, each
its own query (~1.5 s of work), auto-refreshing every 5 minutes, on a dedicated
**Medium** warehouse (4 credits/hr) with the default `AUTO_SUSPEND = 600`, from
09:00 to 18:00 on weekdays.

Estimate the monthly credits. Then propose the two changes with the biggest effect
and re-estimate.

<details>
<summary>Solution</summary>

**As-is.** Refreshes land every 5 minutes, but `AUTO_SUSPEND = 600` is *10*
minutes — the warehouse never gets to suspend during the day. So you're not paying
per refresh at all, you're paying for **a Medium warehouse running continuously
from 09:00 to 18:10**:

9.2 hrs/day × 4 credits/hr ≈ **36.7 credits/day** → ×22 working days ≈
**~810 credits/month** (roughly $1,600–3,200).

Actual work performed: 8 tiles × 1.5 s × 12 refreshes/hr × 9 hrs ≈ 1,300 s ≈ 0.36
hrs — about **1.4 credits** of real compute. You are paying ~570× the useful work.

**Change 1 — right-size to X-Small.** These are 8 small, filtered dashboard
queries; Medium buys nothing. Same 9.2 hrs at 1 credit/hr ≈ **9.2 credits/day**,
~200/month. **4× saving from one `ALTER WAREHOUSE`.**

**Change 2 — `AUTO_SUSPEND = 60`.** Now the warehouse sleeps between refreshes.
Each refresh burns the 60-second floor (the 8 tiles run concurrently inside one
window): 12 refreshes/hr × 60 s = 12 min/hr ≈ 1.84 hrs/day at 1 credit/hr ≈
**1.84 credits/day**, ~40/month.

Combined: **~810 → ~40 credits/month, a 20× cut from two one-line `ALTER`
statements** — no query rewriting, no schema change.

**The bonus third lever:** the tiles run identical SQL every 5 minutes against a
table that only changes on the nightly load. Snowflake's **result cache** serves
identical queries for ~24 h with **no warehouse compute at all** — so most of
those refreshes should be *free*, dropping the bill to near zero until the next
load invalidates the cache. Anything that defeats the result cache (a
`CURRENT_TIMESTAMP()` in the WHERE clause, non-deterministic functions, a changed
role's masking policy) turns free refreshes back into billed ones — which is
exactly the trap [05-2](02_pruning_caching_tuning.md) opens with.

</details>

**→ Next: [05-2 · Pruning, caching & query tuning](02_pruning_caching_tuning.md)**
