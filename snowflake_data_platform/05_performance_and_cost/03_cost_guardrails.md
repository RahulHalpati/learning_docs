# 05-3 · Cost guardrails you actually ship

> **Level:** Intermediate · **Prerequisites:** [05-2 · Pruning, caching & query tuning](02_pruning_caching_tuning.md)
> **Time:** ~25 min · **Verified:** 2026-08-22 (Snowflake trial; Enterprise-only features flagged)

Everything so far *reported* cost. `WAREHOUSE_METERING_HISTORY` tells you what
happened yesterday; a Query Profile tells you why a query was slow. Neither one
stops anything.

This module is about the controls that **act**. There is exactly one Snowflake
feature that will halt spending without a human in the loop — the **resource
monitor** — and a short list of defaults and habits that make it rarely needed.
Ship the monitor first anyway, because the whole point is that it works when you're
asleep.

---

## Resource monitors

A resource monitor is a **credit quota plus triggers**. It watches warehouse credit
consumption over a recurring window and, at thresholds you set, notifies or
suspends. Only `ACCOUNTADMIN` can create one by default.

```sql
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE RESOURCE MONITOR dev_wh_monitor WITH
  CREDIT_QUOTA    = 20          -- credits allowed per FREQUENCY window
  FREQUENCY       = MONTHLY     -- DAILY | WEEKLY | MONTHLY | YEARLY | NEVER
  START_TIMESTAMP = IMMEDIATELY -- when the first window opens
  TRIGGERS
    ON 80  PERCENT DO NOTIFY            -- email/Snowsight alert; nothing stops
    ON 100 PERCENT DO SUSPEND           -- new queries blocked, running ones finish
    ON 110 PERCENT DO SUSPEND_IMMEDIATE;-- kill running queries too
```

Each clause earns its keep:

| Clause | Meaning | Getting it wrong |
|---|---|---|
| `CREDIT_QUOTA` | Credits allowed **per window**, not in total | Setting a monthly quota you meant as a total |
| `FREQUENCY` | Window that resets the counter. `NEVER` = one-shot budget that never resets | `MONTHLY` on a burst workload hides a bad day until the 28th |
| `START_TIMESTAMP` | When windows begin (`IMMEDIATELY` or a timestamp) | Omitting it — the monitor exists but isn't counting yet |
| `DO NOTIFY` | Alert only | Assuming it stops something. It doesn't |
| `DO SUSPEND` | Blocks **new** queries; in-flight ones complete | A 3-hour runaway query keeps burning after the trigger fires |
| `DO SUSPEND_IMMEDIATE` | Aborts running queries as well | Rolled-back work. Fine as a backstop at 110%, harsh as your only trigger |

**Always use all three tiers.** `NOTIFY` at 80 is your warning, `SUSPEND` at 100 is
the graceful stop, `SUSPEND_IMMEDIATE` at 110 is the "somebody launched a 4X-Large"
kill switch. `SUSPEND` alone can be defeated by a single long query; `NOTIFY` alone
is not a control, it's a mailing list.

> **Notifications need setup.** `DO NOTIFY` emails **account administrators whose
> email is verified and who have notifications enabled** (Snowsight → your
> profile → Notifications). A monitor whose alerts go nowhere is a monitor you'll
> learn about from the invoice.

### Assigning it: warehouse vs account

A monitor does nothing until it's attached.

```sql
-- Per warehouse: this warehouse's credits count against this monitor.
ALTER WAREHOUSE dev_wh  SET RESOURCE_MONITOR = dev_wh_monitor;
ALTER WAREHOUSE load_wh SET RESOURCE_MONITOR = dev_wh_monitor;  -- can be shared

-- Account-level: counts ALL warehouse credits in the account. The backstop.
ALTER ACCOUNT SET RESOURCE_MONITOR = account_monitor;
```

The two layers stack, and that's the intended design:

| Scope | Purpose | Quota to pick |
|---|---|---|
| **Warehouse monitor** | Blast-radius containment — a runaway ETL can't starve BI | The workload's expected credits + generous headroom |
| **Account monitor** | The last line of defence, including warehouses nobody told you about | Your actual budget |

A warehouse can be covered by both its own monitor and the account monitor;
**whichever triggers first wins**, so the account monitor catches warehouses created
later by someone who forgot the pattern. Note that a warehouse can have only **one**
monitor assigned directly, and assigning a new one replaces it.

```sql
-- Inspect and manage. USED/QUOTA is the number to look at.
SHOW RESOURCE MONITORS;

-- Raise the quota mid-window to un-suspend after a legitimate overrun:
ALTER RESOURCE MONITOR dev_wh_monitor SET CREDIT_QUOTA = 30;
ALTER WAREHOUSE dev_wh RESUME;   -- suspension by monitor is not self-healing
```

```
NAME             | CREDIT_QUOTA | USED_CREDITS | REMAINING_CREDITS | FREQUENCY | LEVEL
ACCOUNT_MONITOR  | 100          | 12.4         | 87.6              | MONTHLY   | ACCOUNT
DEV_WH_MONITOR   | 20           | 8.9          | 11.1              | MONTHLY   | WAREHOUSE
```

### The honest limitation

**Resource monitors only meter *warehouse* credits.** They do not cap
**serverless** consumption, which is billed outside any warehouse:

- Snowpipe and Snowpipe Streaming ingestion
- Automatic Clustering ([05-2](02_pruning_caching_tuning.md))
- Materialized-view maintenance (Enterprise+)
- Search Optimization Service (Enterprise+)
- Serverless tasks, Replication, Query Acceleration
- **Storage**, which no monitor has ever capped

So a monitor is a **strong cap on the biggest line item, not a total spend cap**.
Say exactly that in an interview — it's the difference between having read the docs
and having operated the platform. Serverless features are governed by *design*
choices (frequency, table size, whether you enable them at all) plus
`ACCOUNT_USAGE` views such as `AUTOMATIC_CLUSTERING_HISTORY`,
`PIPE_USAGE_HISTORY`, and `SERVERLESS_TASK_HISTORY` — and by budgets/alerts, not
by a hard stop.

Two more sharp edges: monitor checks aren't instantaneous (credits are evaluated
periodically, so a small overshoot past the quota is normal), and a
monitor-suspended warehouse **stays suspended** until the window resets or you
raise the quota — which is the correct behaviour, and worth telling your team
before it happens on a Friday.

---

## The trial-safety setup, as a recipe

Run this once on your trial account. It's ~15 lines and it removes the entire
category of "I left something running" from your life.

```sql
USE ROLE ACCOUNTADMIN;

-- 1. Account-wide backstop. $400 ≈ 120–200 credits; 100 leaves real headroom.
CREATE OR REPLACE RESOURCE MONITOR trial_guard WITH
  CREDIT_QUOTA = 100
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75  PERCENT DO NOTIFY
           ON 90  PERCENT DO SUSPEND
           ON 100 PERCENT DO SUSPEND_IMMEDIATE;
ALTER ACCOUNT SET RESOURCE_MONITOR = trial_guard;

-- 2. A daily monitor too — a MONTHLY quota can be burned in one bad afternoon.
CREATE OR REPLACE RESOURCE MONITOR trial_daily WITH
  CREDIT_QUOTA = 8 FREQUENCY = DAILY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND;
ALTER WAREHOUSE dev_wh SET RESOURCE_MONITOR = trial_daily;

-- 3. The warehouse itself: smallest size, fastest suspend, bounded statements.
ALTER WAREHOUSE dev_wh SET
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND   = 60          -- seconds; the default 600 is 10× the idle waste
  AUTO_RESUME    = TRUE        -- so suspending costs you nothing in convenience
  STATEMENT_TIMEOUT_IN_SECONDS = 600;
```

Two spellings that trip everyone up once: the object is created as
`CREATE RESOURCE MONITOR` (two words) and assigned as `SET RESOURCE_MONITOR`
(underscore), on both `ACCOUNT` and `WAREHOUSE`.

Then the two habits no DDL can give you:

```sql
-- End of every session. Auto-suspend is a safety net, not a plan.
SHOW WAREHOUSES;                                   -- check the "state" column
ALTER WAREHOUSE dev_wh SUSPEND;

-- End of every experiment. Compute stops when suspended; storage never does.
DROP DATABASE IF EXISTS scratch_db;
```

And once a day, the 05-1 morning query on `WAREHOUSE_METERING_HISTORY`. Ten
seconds, and it's the same query you'll run on a production account.

---

## RBAC is a cost control

Back in [04-2](../04_security_and_rbac/02_roles_and_grants_in_practice.md) you
granted privileges for *security* reasons. Two of them are also spending limits,
because in Snowflake **the ability to resize a warehouse is the ability to multiply
the bill by 128**.

| Privilege | Lets the grantee… | Give it to |
|---|---|---|
| `USAGE` on warehouse | Run queries on it (and auto-resume it) | Everyone who needs to query |
| `OPERATE` on warehouse | Suspend / resume it | Ops-ish roles, automation |
| **`MODIFY` on warehouse** | **Change size, auto-suspend, monitor assignment** | **Nobody but the admin role** |
| `CREATE WAREHOUSE` on account | Create new, unmonitored warehouses | `ACCOUNTADMIN`/`SYSADMIN` only |

```sql
-- Analysts get to run queries. They do not get to make dev_wh a 2X-Large.
GRANT USAGE ON WAREHOUSE dev_wh TO ROLE linkstash_analyst;
-- ...and MODIFY stays where it is. Withholding it is the control.
```

This is also why an **account-level** monitor matters more than per-warehouse ones:
anyone with `CREATE WAREHOUSE` can create a warehouse outside your per-warehouse
monitors, but nothing escapes the account monitor. Least privilege and cost control
turn out to be the same list of grants.

---

## The cost checklist

Nine items. This is the artefact — put it in your team's runbook and in your
interview answer.

| # | Control | How | Typical saving |
|---|---|---|---|
| 1 | **Right-size the warehouse** | `WAREHOUSE_SIZE` by scan volume; XS/S for BI, L+ for heavy ETL | 2–16× |
| 2 | **`AUTO_SUSPEND = 60`, `AUTO_RESUME = TRUE`** | Default 600 = ten idle minutes per burst | 2–10× |
| 3 | **Never `SELECT *`** | Name your columns; columnar store bills per column | 5–40× on wide tables |
| 4 | **Filter on bare columns so it prunes** | Ranges, not `DATE(col)`/`LOWER(col)`/`LIKE '%x%'` | 10–100× |
| 5 | **Transient tables for reloadable data** | `CREATE TRANSIENT TABLE raw.raw_clicks (...)` — no Fail-safe | ~50% of that table's storage |
| 6 | **Trim `DATA_RETENTION_TIME_IN_DAYS`** | 1 day for raw/staging, longer only where you'd truly time-travel | Big on high-churn tables |
| 7 | **One warehouse per workload** | `bi_wh`, `etl_wh`, `dev_wh` — separate sizing, isolated blast radius, attributable bill | Structural |
| 8 | **Tag every query** | `ALTER SESSION SET QUERY_TAG = 'etl:clicks_nightly'` | 0 — it buys *evidence* |
| 9 | **Monitor + alert + timeout** | Resource monitors (account **and** warehouse) + `STATEMENT_TIMEOUT_IN_SECONDS` | Caps the tail risk |

The two storage ones, concretely:

```sql
-- Raw landing data is reloadable from the stage, so pay for neither
-- Fail-safe nor a week of Time Travel on it.
CREATE OR REPLACE TRANSIENT TABLE raw.raw_clicks (
  raw_payload VARIANT,
  loaded_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) DATA_RETENTION_TIME_IN_DAYS = 1;

-- Curated tables keep real Time Travel — this one you'd actually want to rewind.
ALTER TABLE analytics.clicks SET DATA_RETENTION_TIME_IN_DAYS = 7;
```

Items 1–4 are one-line changes with multiplicative savings and no downside. If you
only ever do four things, do those four.

---

## Cost incident post-mortem

The scenario: Monday morning, the account monitor's 75% notification fired over the
weekend. Nobody was working. Here's the sequence — five queries, ten minutes, and
it doubles as the answer to "walk me through investigating a cost spike".

**Step 1 — which warehouse, and when?** Go coarse first: never start from
individual queries.

```sql
-- Credits per warehouse per hour over the weekend. The spike shows itself.
SELECT warehouse_name,
       DATE_TRUNC('hour', start_time)      AS hour,
       ROUND(SUM(credits_used_compute), 2) AS credits
FROM   snowflake.account_usage.warehouse_metering_history
WHERE  start_time >= '2026-08-15'
GROUP BY 1, 2
HAVING SUM(credits_used_compute) > 0.5
ORDER BY credits DESC
LIMIT 10;
```

```
WAREHOUSE_NAME | HOUR                | CREDITS
ETL_WH         | 2026-08-16 02:00:00 | 31.90
ETL_WH         | 2026-08-16 03:00:00 | 31.88
ETL_WH         | 2026-08-16 04:00:00 | 31.90
ETL_WH         | 2026-08-16 05:00:00 | 18.42
DEV_WH         | 2026-08-15 14:00:00 | 0.71
```

~32 credits/hour for 3+ hours = a **2X-Large** running flat out. `DEV_WH` is
irrelevant noise. **Scope established: one warehouse, one night, ~114 credits.**

**Step 2 — was it size or duration?** 32 credits/hour on a warehouse that should be
Large (8) is the whole story before you read a single query.

```sql
-- Did somebody resize it, and does it ever suspend?
SHOW WAREHOUSES LIKE 'etl_wh';   -- size, auto_suspend, state, resource_monitor
```

```
NAME   | SIZE     | AUTO_SUSPEND | STATE     | RESOURCE_MONITOR
ETL_WH | 2X-Large | 3600         | SUSPENDED | null
```

Three findings in one row: **resized to 2X-Large** (4× the intended rate),
**`AUTO_SUSPEND = 3600`** (an hour of idle billing per burst), and **no resource
monitor** attached.

**Step 3 — which queries, and whose?**

```sql
-- The actual work inside the spike window, most expensive first.
SELECT query_id,
       user_name,
       role_name,
       query_tag,
       ROUND(bytes_scanned / POWER(1024, 3), 1)  AS gb_scanned,
       ROUND(total_elapsed_time / 60000, 1)      AS minutes,
       ROUND(bytes_spilled_to_remote_storage / POWER(1024, 3), 1) AS spill_remote_gb,
       partitions_scanned, partitions_total,
       LEFT(query_text, 70)                      AS query
FROM   snowflake.account_usage.query_history
WHERE  warehouse_name = 'ETL_WH'
  AND  start_time BETWEEN '2026-08-16 02:00' AND '2026-08-16 06:00'
ORDER BY total_elapsed_time DESC
LIMIT 10;
```

```
QUERY_ID | USER_NAME | ROLE_NAME | QUERY_TAG          | GB_SCANNED | MINUTES | SPILL_REMOTE_GB | PARTITIONS_SCANNED | PARTITIONS_TOTAL | QUERY
01b2..a1 | SVC_ETL   | ETL_ROLE  | etl:clicks_nightly | 942.0      | 168.2   | 88.4            | 1284               | 1284             | INSERT INTO analytics.clicks SELECT * FROM raw.raw_clicks r JOIN
01b2..c7 | SVC_ETL   | ETL_ROLE  | etl:clicks_nightly | 0.4        | 0.6     | 0.0             | 12                 | 1284             | MERGE INTO analytics.links USING ...
```

One query, 168 minutes, 942 GB scanned, `1284/1284` partitions, 88 GB spilled to
**remote** storage. Everything from [05-2](02_pruning_caching_tuning.md) lights up
at once: no pruning, `SELECT *`, and remote spill pointing at a join that exploded.

**Step 4 — the write-up.** Separate the *cause* from the *reason it cost this much*:

- **Cause:** a backfill added a `JOIN` on a non-unique key and no date bound.
  Partition scan ratio 1.0, 88 GB remote spill ⇒ exploding join, not a data-growth
  problem.
- **Amplifiers:** the warehouse had been resized to 2X-Large "to make the backfill
  finish" and never resized back (4× rate), and `AUTO_SUSPEND = 3600` added an idle
  hour after it (~32 credits of pure nothing).
- **Why nobody was warned:** `ETL_WH` had **no resource monitor**, and the
  account-level monitor's threshold was `NOTIFY` at 75% — which fired *after* the
  spend, as designed. A `SUSPEND` trigger would have stopped it at ~3 credits.

**Step 5 — the fixes, in the order you'd land them.**

```sql
-- 1. Guardrails first: they protect you while you fix the actual query.
ALTER WAREHOUSE etl_wh SET WAREHOUSE_SIZE = 'LARGE'
                           AUTO_SUSPEND = 60
                           STATEMENT_TIMEOUT_IN_SECONDS = 7200;
CREATE OR REPLACE RESOURCE MONITOR etl_wh_monitor WITH
  CREDIT_QUOTA = 40 FREQUENCY = DAILY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND
           ON 120 PERCENT DO SUSPEND_IMMEDIATE;
ALTER WAREHOUSE etl_wh SET RESOURCE_MONITOR = etl_wh_monitor;

-- 2. Then the query: bounded window, real join key, named columns.
-- 3. Then the process: MODIFY on etl_wh revoked from ETL_ROLE, so "just size it up"
--    stops being a thing anyone can do at 2 a.m. without review.
```

Note the ordering. The guardrail goes in **before** the fix, because the guardrail
is what makes the next unknown mistake cheap. That's the whole discipline: you will
not catch every bad query, so cap what a bad query can cost.

---

## Recap & next

- ✅ **Resource monitors are the only feature that stops spend.**
  `CREDIT_QUOTA` + `FREQUENCY` + tiered triggers: `NOTIFY` 80, `SUSPEND` 100,
  `SUSPEND_IMMEDIATE` 110.
- ✅ Assign them at **both levels** — per warehouse for blast radius, on the
  **account** as the backstop that also covers warehouses created later.
- ✅ Honest limits: monitors meter **warehouse credits only** — not Snowpipe,
  Automatic Clustering, materialized views, serverless tasks, or storage. Strong
  cap, not a total one. Verify notification emails actually work.
- ✅ Trial recipe: **XS + `AUTO_SUSPEND=60` + `AUTO_RESUME=TRUE` + statement
  timeout + an account monitor + a daily monitor**, then suspend and drop what you
  created.
- ✅ **RBAC is cost control** — `USAGE` broadly, `OPERATE` narrowly, **`MODIFY`
  and `CREATE WAREHOUSE` to admins only**.
- ✅ The nine-item checklist: right-size · auto-suspend 60 · no `SELECT *` ·
  filter for pruning · transient tables · trim retention · warehouse per workload ·
  `QUERY_TAG` · monitor + alert + timeout.
- ✅ Post-mortem drill: `WAREHOUSE_METERING_HISTORY` by hour → `SHOW WAREHOUSES`
  for size/suspend → `QUERY_HISTORY` for the query, user, tag, spill and scan ratio
  → separate cause from amplifiers → **ship the guardrail before the fix**.

## Exercise

You inherit a Snowflake account with no monitors. Findings:

- `bi_wh` — **Medium**, `AUTO_SUSPEND = 600`, serves ~40 analysts 09:00–19:00 with
  small filtered dashboard queries. ~350 credits/month.
- `etl_wh` — **X-Small**, `AUTO_SUSPEND = 60`, one nightly job that takes **4 hours**
  and spills 30 GB to remote storage. ~120 credits/month.
- `ds_wh` — **X-Large**, `AUTO_SUSPEND = 600`, used by one data scientist "a couple
  of times a week" for Snowpark. ~600 credits/month.
- Nobody has `MODIFY` restricted; two analysts have `CREATE WAREHOUSE`.

Design the guardrails. Which warehouse do you fix first, and which one do you make
*bigger*?

<details>
<summary>Solution</summary>

**Day one, before touching any warehouse:** an account-level monitor at your actual
budget, with all three trigger tiers. You don't yet know what else exists in this
account, and two analysts can create warehouses your per-warehouse monitors will
never see.

**Fix first: `ds_wh` — 600 credits/month is the biggest line and the least
defensible.** An X-Large at 16 credits/hr for occasional Snowpark work, with
`AUTO_SUSPEND = 600`, is billing ~37 hours/month of which almost none is compute:
the pattern is a few interactive sessions where every 10-minute idle gap costs 2.7
credits. Drop to **Small** (2/hr, size up on demand for a real training run) and
`AUTO_SUSPEND = 60`. Expected: **600 → ~30 credits/month.** One `ALTER`, no code
touched, no user affected — the data scientist's queries were never the problem.

**Second: `bi_wh` — right-size down, keep auto-suspend moderate.** 40 analysts on
small filtered queries do not need a Medium; **Small** is likely plenty
(**350 → ~175**), and X-Small is worth a week's trial. This is the *one* place not
to slam `AUTO_SUSPEND` to 60: with continuous interactive traffic all day the
warehouse won't suspend anyway, and the warm local SSD cache genuinely helps
(05-2). Set **180–300 s** and check `QUERY_HISTORY` for queuing. If concurrency
(not slowness) is the complaint, the answer is a **multi-cluster** warehouse
(Enterprise+) with `MIN_CLUSTER_COUNT = 1`, never a bigger single one.

**Make bigger: `etl_wh`.** It is the *only* warehouse here that's undersized, and
the 30 GB remote spill is the proof. Size **X-Small → Large** and the job should
finish in roughly a quarter to an eighth of the time at similar total credits
(05-1) — with the spill gone it may cost *less* than it does now, and a 4-hour
nightly window stops threatening the morning dashboards. Check the Query Profile
first for an exploding join, though: if the spill is a join bug, sizing up just
buys a faster wrong answer.

**Guardrails and process:**

```sql
-- Account backstop + per-warehouse containment (ds_wh gets the tightest leash).
CREATE OR REPLACE RESOURCE MONITOR account_guard WITH
  CREDIT_QUOTA = 400 FREQUENCY = MONTHLY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND
           ON 110 PERCENT DO SUSPEND_IMMEDIATE;
ALTER ACCOUNT SET RESOURCE_MONITOR = account_guard;
-- ...then one monitor per warehouse, sized to its expected load, plus
ALTER WAREHOUSE ds_wh SET STATEMENT_TIMEOUT_IN_SECONDS = 3600;
```

Then **revoke `MODIFY` on all three warehouses and `CREATE WAREHOUSE` from the two
analysts** (04-2). Without that, every resize you just did can be undone by
whoever finds their query slow — and the account monitor is the only thing standing
between you and a warehouse you've never heard of.

**Net: ~1,070 → ~350 credits/month**, ETL finishing 4× faster, and a hard cap on
the tail. Total DDL: about a dozen lines, none of it clever.

</details>

**→ Next: [06 · Pipelines & data engineering](../06_pipelines_and_engineering/README.md)** —
streams, tasks, Snowpipe, Time Travel and zero-copy clones: the automation that
makes all of this run without you.
