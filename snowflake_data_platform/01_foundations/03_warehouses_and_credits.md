# 01-3 · Virtual warehouses & credits

> **Level:** Beginner · **Prerequisites:** [01-2 Trial setup & Snowsight](02_trial_setup_and_snowsight.md)
> **Time:** 25 min · **Verified:** 2026-08-22 (Snowflake trial: 30 days / $400 credits)

A **virtual warehouse** is not a place where data lives — the name is the worst
thing about Snowflake. It's a **compute cluster**: some CPU, some RAM, and a local
SSD cache, rented by the second, completely independent of the storage layer. Data
lives in object storage whether any warehouse exists or not.

Which means warehouses are disposable. You can have six of them, drop them all,
and lose nothing but the caches. **Every dollar of Snowflake compute spend is a
decision about warehouses**, so this is the module that pays for itself.

---

## Creating one

```sql
CREATE WAREHOUSE dev_wh WITH
  WAREHOUSE_SIZE      = 'XSMALL'   -- 1 credit/hr. Smallest, and plenty for this course.
  AUTO_SUSPEND        = 60         -- Sleep after 60s idle. Default is 600 — always override.
  AUTO_RESUME         = TRUE       -- Wake automatically on the next query, no manual step.
  INITIALLY_SUSPENDED = TRUE;      -- Don't start billing the moment you press run.
```

Parameter by parameter:

- **`WAREHOUSE_SIZE`** — how much compute. Resizable later with one statement.
- **`AUTO_SUSPEND`** — idle seconds before the cluster shuts down. **This is the
  spend dial.** At 600 (the default), every session leaves a ten-minute tail of
  paid idleness behind it.
- **`AUTO_RESUME`** — wake on demand. Without it, a suspended warehouse makes
  queries *fail*, and you learn to leave warehouses running to avoid the annoyance,
  which is precisely the expensive habit.
- **`INITIALLY_SUSPENDED`** — create it asleep. Omit this and `CREATE WAREHOUSE`
  itself starts the meter for a minimum of 60 seconds.

**`AUTO_SUSPEND` and `AUTO_RESUME` are the two most important settings you will
ever configure in Snowflake.** Together they are the entire "scale to zero" promise:
suspend fast so idleness is cheap, resume automatically so cheap doesn't hurt. Set
one without the other and you get either a silent bill or a frustrated team.

---

## Sizes and the doubling curve

Each step up doubles the compute — and doubles the credits per hour:

| Size | Credits/hr | ≈ $/hr | Rough use |
|---|---|---|---|
| X-Small | 1 | ~$2–3 | learning, dev, small queries — **start here** |
| Small | 2 | ~$4–6 | light BI, small transforms |
| Medium | 4 | ~$8–12 | real ETL over tens of GB |
| Large | 8 | ~$16–24 | heavy transforms, big joins |
| X-Large | 16 | ~$32–48 | large-scale loads |
| … up to 6X-Large | 512 | — | you will not need this |

The trap is assuming bigger is wasteful. It often isn't, because **doubling the
size can halve the runtime, making the query cost the same and finish sooner**.
A query that takes 60 min on Small (2 credits) and 30 min on Medium (2 credits) is
free to speed up. But that only holds while the work parallelises: if a query takes
20 s on X-Small and 18 s on Small, you just doubled the cost for nothing. The rule
is empirical — **measure both, don't guess** — and the honest default while
learning is X-Small.

---

## The 60-second minimum

> Compute is billed **per second, with a 60-second minimum charged each time a
> warehouse starts or resumes.**

Per-second billing after the first minute is generous. The minimum is the part
that bites, and it changes how you work:

- A single 3-second query against a cold warehouse costs **60 seconds**.
- Twenty small queries, each triggering a resume because auto-suspend fired in
  between, cost **20 minutes** — for maybe a minute of actual work.

So the failure mode isn't a long query, it's a **stuttering session**: work,
suspend, work, suspend. Two consequences:

- **Don't set `AUTO_SUSPEND` below 60.** You cannot be billed less than a minute
  anyway, so suspending at 5 seconds just buys you extra resumes. 60 is the floor
  that makes sense; 60–300 is the sane range for interactive work.
- **Batch your exploring.** Run your ten ad-hoc queries in one sitting, then
  suspend — rather than one every fifteen minutes all afternoon.

The exception is queries served by the **result cache**: an identical query with
unchanged underlying data returns from the cloud services layer with **no warehouse
and no credits at all**. Re-running the same `SELECT` to show a colleague is free.

---

## Driving a warehouse

```sql
USE WAREHOUSE dev_wh;                              -- attach this session's queries to it
                                                   -- (AUTO_RESUME wakes it on the first query)

ALTER WAREHOUSE dev_wh SUSPEND;                    -- stop billing now, don't wait for the timer
ALTER WAREHOUSE dev_wh RESUME;                     -- rarely needed if AUTO_RESUME = TRUE

ALTER WAREHOUSE dev_wh SET WAREHOUSE_SIZE = 'LARGE';  -- for one heavy job...
ALTER WAREHOUSE dev_wh SET WAREHOUSE_SIZE = 'XSMALL'; -- ...and straight back down

SHOW WAREHOUSES;                                   -- the "what am I paying for" check
```

Verified (abridged):

```
name        | state     | size    | auto_suspend | auto_resume
COMPUTE_WH  | SUSPENDED | X-Small | 600          | true
DEV_WH      | STARTED   | X-Small | 60           | true
```

`DEV_WH` is `STARTED` in that output — that's a billing meter, not a status light.
Resizing is near-instant and doesn't interrupt running queries (already-running
queries finish on the old size; new ones get the new one), which is what makes
"scale up for the ETL, back down after" a practical pattern rather than a
maintenance window.

---

## Multi-cluster warehouses (Enterprise+)

A single warehouse can queue queries when too many arrive at once. A
**multi-cluster** warehouse adds more identical clusters as concurrency rises and
removes them as it falls:

```sql
ALTER WAREHOUSE bi_wh SET MIN_CLUSTER_COUNT = 1 MAX_CLUSTER_COUNT = 3;
-- Scales OUT (more concurrent users), not UP (faster single query). Enterprise+.
```

Two different problems, easily confused: **size** fixes a slow query, **cluster
count** fixes a queue. And note `MAX_CLUSTER_COUNT = 3` means the warehouse can
cost up to 3× what you assumed — worth a resource monitor.

---

## One warehouse per workload

The standard production layout, and the direct payoff of storage/compute
separation:

| Warehouse | Size | Auto-suspend | Why separate |
|---|---|---|---|
| `BI_WH` | Small, multi-cluster | 300 s | Dashboards need predictable latency and warm cache; many short concurrent queries. |
| `ETL_WH` | Medium/Large | 60 s | Scheduled bursts. Big, brief, then asleep. |
| `ADHOC_WH` | X-Small | 60 s | Analysts' experiments, capped so a runaway `SELECT *` can't hurt anyone. |

They all read **the same single copy of the data**. Merge them into one shared
warehouse and the nightly ETL job starves the morning dashboards — exactly the
contention a coupled database forces on you. Separating them also makes cost
*attributable*: `WAREHOUSE_METERING_HISTORY` then tells you what BI costs versus
what the pipeline costs, which is the number finance will eventually ask for.

---

## Where the credits went

```sql
-- Credits by warehouse and day. The starting point for every cost investigation.
SELECT warehouse_name,
       DATE_TRUNC('day', start_time)   AS day,
       ROUND(SUM(credits_used), 3)     AS credits
FROM   snowflake.account_usage.warehouse_metering_history
WHERE  start_time > DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY day DESC, credits DESC;
```

Verified:

```
WAREHOUSE_NAME | DAY        | CREDITS
DEV_WH         | 2026-08-22 | 0.417
COMPUTE_WH     | 2026-08-21 | 0.183
```

`SNOWFLAKE.ACCOUNT_USAGE` is a schema of system views covering metering, query
history, logins, and access — the audit trail for both cost and security. It lags
by up to ~45 minutes and needs `ACCOUNTADMIN` (or a granted role). Resource
monitors, credit quotas, and enforcing this properly are
[section 05](../05_performance_and_cost/README.md).

**Before you close this file:** `ALTER WAREHOUSE dev_wh SUSPEND;`

---

## Recap & next

- ✅ A warehouse is a **disposable compute cluster**, independent of storage —
  create, resize, and drop them freely.
- ✅ `AUTO_SUSPEND = 60` + `AUTO_RESUME = TRUE` + `INITIALLY_SUSPENDED = TRUE` is
  the default you should type every time. The 600-second default is billed idleness.
- ✅ Billing is **per second with a 60-second minimum per resume** — so batch your
  work, and never set auto-suspend below 60.
- ✅ Each size step **doubles credits/hr**; bigger can be cost-neutral if runtime
  halves, but measure rather than assume. Start X-Small.
- ✅ **Separate warehouses per workload** (BI / ETL / ad-hoc) for isolation and
  attributable cost; multi-cluster (Enterprise+) scales *out* for concurrency, not
  *up* for speed.
- ✅ `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` shows where credits went.

## Exercise

An analyst reports that `ADHOC_WH` (X-Small, `AUTO_SUSPEND = 30`) burned 12 credits
yesterday — twelve hours of billing — but Query History shows only about 40 minutes
of total query execution time. Explain the gap, and write the fix.

<details>
<summary>Solution</summary>

The 60-second minimum, paid over and over. `AUTO_SUSPEND = 30` means the warehouse
sleeps after 30 idle seconds, so an analyst working at human pace — think, type,
run, think — triggers a **resume for nearly every query**, and each resume is
billed a full 60 seconds no matter how short the query was. A few hundred resumes
across a day produces hours of billing out of minutes of work. Setting auto-suspend
*below* 60 cannot save money (60 s is the floor per resume) and actively costs it by
manufacturing resumes.

```sql
-- 300s keeps the warehouse warm across an interactive session, so one resume
-- covers many queries instead of one each. Also keeps the local cache alive.
ALTER WAREHOUSE adhoc_wh SET AUTO_SUSPEND = 300;
```

Confirm with `SHOW WAREHOUSES`, then re-check
`WAREHOUSE_METERING_HISTORY` tomorrow — with a warm session the same work bills
closer to the ~40 minutes of real execution plus a few idle tails.

Worth naming the second win: each resume also starts with a **cold local cache**,
so the queries themselves were slower than they needed to be. Suspending
aggressively cost money *and* time. The counter-pressure is real, though — 300 s of
idle on a Large warehouse is a different conversation, so tune auto-suspend per
warehouse and workload, not once globally.

</details>

**→ Next: [02 · SQL & loading data](../02_sql_and_loading/README.md)**
