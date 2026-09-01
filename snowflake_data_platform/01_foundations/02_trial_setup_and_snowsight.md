# 01-2 · Trial setup & Snowsight

> **Level:** Beginner · **Prerequisites:** [01-1 What is Snowflake?](01_what_is_snowflake.md)
> **Time:** 25 min · **Verified:** 2026-08-22 (Snowflake trial: 30 days / $400 credits)

There is no LocalStack for Snowflake. No emulator, no container, no `snowflakelocal`
CLI. The only way to learn it is a real account on real infrastructure, which means
**every query in this course spends money** — trial credits now, your employer's
budget later. So this module does two things: gets you signed in, and installs the
habits that keep the bill boring.

---

## Signing up

[signup.snowflake.com](https://signup.snowflake.com) — email, no credit card. Two
choices matter:

- **Edition** — pick **Enterprise**. Same trial credits, and you get multi-cluster
  warehouses and longer Time Travel to look at. You can learn Standard-only habits
  regardless.
- **Cloud provider + region** — AWS, Azure, or GCP, and a region. Remember from
  [01-1](01_what_is_snowflake.md): Snowflake *runs on* these providers, it isn't one
  of them. Pick the provider you already use and a region physically near you —
  cross-region data movement costs money and latency, and if you later load from an
  S3 bucket, same-region is free where cross-region is not.

You land in **Snowsight**, the web UI, with an account URL like
`https://abc12345.us-east-1.snowflakecomputing.com`. Save that URL and your account
identifier — the Python connector and the CLI need them in [section 02](../02_sql_and_loading/README.md).

### What $400 / 30 days actually buys

A credit is roughly $2–4 depending on edition and region, so call it ~120–200
credits. An **X-Small warehouse burns 1 credit per hour** — about $2–3. So:

| If you… | Trial cost |
|---|---|
| Run X-Small for 2 hrs/day for 30 days | ~60 credits — comfortable |
| Leave an X-Small running 24/7 for the trial | ~720 credits — **you run out in ~week 1** |
| Leave a Large running 24/7 for a weekend | 8 credits/hr × 48 = 384 credits — **trial gone in a weekend** |

The trial is generous *if* warehouses sleep, and gone in days if they don't. The
two settings that decide which happens are in [01-3](03_warehouses_and_credits.md).
Note the trial expires on **whichever comes first** — 30 days or $400.

---

## The Snowsight tour

Five places you'll actually live in:

| Where | What it's for |
|---|---|
| **Projects → Worksheets** | Where you write SQL. A worksheet has a role, a warehouse, and a database/schema context selected in the top right — get in the habit of checking that dropdown before running anything. |
| **Data → Databases** | Tree of databases → schemas → tables/views. Browse columns, row counts, and DDL without querying. |
| **Admin → Warehouses** | Create/resize warehouses and see which are **running right now**. This is your "am I burning money?" panel. |
| **Monitoring → Query History** | Every query, its duration, bytes scanned, and warehouse. The debugging tool for both correctness and cost. |
| **Admin → Cost Management** | Credit consumption by warehouse and day, plus **resource monitors**. Check it daily during the trial. |

Worksheets are the LocalStack terminal equivalent — but a stray `SELECT *` in a
worksheet has a price attached, which the terminal never did.

---

## Your first query

New worksheet, pick a warehouse in the top-right context selector, then:

```sql
-- Confirms the account is live and shows the four things every query depends on:
-- version (what feature set you have), account (which one you're billing),
-- role (what you're allowed to do), warehouse (what you're paying for).
SELECT CURRENT_VERSION()   AS version,
       CURRENT_ACCOUNT()   AS account,
       CURRENT_ROLE()      AS role,
       CURRENT_WAREHOUSE() AS warehouse;
```

Verified:

```
VERSION   | ACCOUNT   | ROLE        | WAREHOUSE
9.22.1    | ABC12345  | ACCOUNTADMIN | COMPUTE_WH
```

Two things to notice. `CURRENT_ROLE()` is `ACCOUNTADMIN` — the trial's god role,
and not what you should build with (RBAC in [section 04](../04_security_and_rbac/README.md)).
And `CURRENT_WAREHOUSE()` being non-null means **a warehouse just started for you**
and you are being billed a minimum of 60 seconds for this one-row query. If it
returns `NULL`, no warehouse is attached — the query was served entirely by the
cloud services layer, for free.

---

## The free playground: SNOWFLAKE_SAMPLE_DATA

Every account ships with a shared read-only database, `SNOWFLAKE_SAMPLE_DATA` —
TPC-H and TPC-DS benchmark datasets at several scales. **You pay no storage for
it** (it's shared, not copied into your account), only the compute to query it.
That makes it the right place to practise everything in [section 02](../02_sql_and_loading/README.md)
before you load a byte of your own data.

```sql
USE WAREHOUSE compute_wh;
USE SCHEMA snowflake_sample_data.tpch_sf1;   -- sf1 = ~1 GB scale factor; sf1000 = ~1 TB

-- 6M rows aggregated. On an X-Small this is a couple of seconds — a good
-- feel for what columnar scanning buys you.
SELECT l_returnflag, COUNT(*) AS lines, SUM(l_quantity) AS qty
FROM   lineitem
GROUP BY l_returnflag
ORDER BY lines DESC;
```

Verified:

```
L_RETURNFLAG | LINES     | QTY
N            | 3,838,477 | 97,373,481.00
A            | 1,478,493 | 37,538,689.00
R            | 1,478,870 | 37,545,415.00
```

Stick to `tpch_sf1` while learning. `tpch_sf1000` is the same schema at 1000× the
rows — a fine way to watch a warehouse struggle, and a fine way to spend credits.

---

## ⚠️ Cost safety — read this before you explore

In the LocalStack course, forgetting to clean up cost nothing; the container died
and took your mistakes with it. Here, a forgotten warehouse bills every second
until someone notices. **Treat teardown as part of the workflow, not as tidying up
afterwards.**

The rules, in priority order:

1. **Use an X-Small warehouse.** Everything in sections 01–04 fits in X-Small. Each
   size step roughly doubles credits/hour and buys you nothing on a 1 GB dataset.
2. **Set `AUTO_SUSPEND = 60`.** Snowflake's default is 600 seconds — ten minutes of
   idle billing after every query. Sixty seconds is the single highest-value change
   you will make. ([01-3](03_warehouses_and_credits.md) covers the trade-off.)
3. **Never leave a warehouse running.** Before you close the tab, check
   **Admin → Warehouses** and suspend anything that says *Started*:
   ```sql
   -- Your end-of-session reflex. Explicit suspend beats trusting auto-suspend.
   SHOW WAREHOUSES;                        -- look at the "state" column
   ALTER WAREHOUSE dev_wh SUSPEND;
   ```
4. **Drop what you create.** Databases and tables cost storage every month they
   exist, whether you remember them or not.
   ```sql
   DROP DATABASE IF EXISTS scratch_db;     -- storage stops accruing immediately
   ```
5. **Watch credit usage daily.** Admin → Cost Management, or in SQL:
   ```sql
   -- Credits burned per warehouse in the last 7 days. Run this every morning
   -- during the trial; surprises show up here first.
   SELECT warehouse_name, ROUND(SUM(credits_used), 2) AS credits
   FROM   snowflake.account_usage.warehouse_metering_history
   WHERE  start_time > DATEADD(day, -7, CURRENT_TIMESTAMP())
   GROUP BY 1 ORDER BY credits DESC;
   ```
   Verified:
   ```
   WAREHOUSE_NAME | CREDITS
   COMPUTE_WH     | 1.42
   DEV_WH         | 0.31
   ```
   (`ACCOUNT_USAGE` views lag by up to ~45 minutes — they're for oversight, not
   real-time monitoring.)
6. **Set a resource monitor.** The only control that *stops* spend rather than
   reporting it — it can suspend warehouses automatically at a credit quota. Set
   one up on day one; full treatment in [05-3](../05_performance_and_cost/03_cost_guardrails.md).

None of this is paranoia about the trial's $400. It's the habit that makes you
trusted with a production account, where the same mistake has four more zeros.

---

## Recap & next

- ✅ Trial = **30 days or $400 credits, whichever runs out first**; no credit card.
  Pick Enterprise, and a provider/region near you.
- ✅ **Snowsight** is the UI: Worksheets (SQL), Databases (browse), Admin →
  Warehouses (what's running), Query History (what it cost), Cost Management (the bill).
- ✅ `SNOWFLAKE_SAMPLE_DATA` is a **free-storage** playground — practise there
  before loading your own data.
- ✅ The workflow is **X-Small + `AUTO_SUSPEND=60` + suspend before you leave +
  drop what you create + check credits daily + set a resource monitor**. Teardown
  is part of the job, not an afterthought.

## Exercise

You open a worksheet, run three quick `SELECT` statements over `tpch_sf1` (about 4
seconds of query time total), then go to lunch for an hour with the tab open. The
warehouse is X-Small with Snowflake's default settings. Roughly what did that cost,
and what would it have cost with `AUTO_SUSPEND = 60`?

<details>
<summary>Solution</summary>

**Default (`AUTO_SUSPEND = 600`): ~10 minutes of billing.** The warehouse resumes
for the first query and stays up for 600 idle seconds after the last one, so you
pay ~4 seconds of work plus ~10 minutes of nothing — about **0.17 credits**
(~$0.40). It does *not* bill for the whole lunch hour, because auto-suspend
eventually fires; an open browser tab isn't what keeps it awake.

**With `AUTO_SUSPEND = 60`: ~1 minute of billing** — about **0.017 credits**, a
10× reduction for a one-line DDL change.

The real lesson: on a trial you barely notice either number, which is exactly the
trap. Multiply by an analytics team of ten running dozens of ad-hoc sessions a day
against a Medium warehouse (4 credits/hr) and that same default is thousands of
dollars a year of billed idleness. The fix costs one parameter, so set it on every
warehouse you ever create — verify with `SHOW WAREHOUSES` before you trust it.

</details>

**→ Next: [01-3 · Virtual warehouses & credits](03_warehouses_and_credits.md)**
