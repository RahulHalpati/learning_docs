# 06-3 · Time Travel, zero-copy clones & where to go next

> **Level:** Intermediate · **Prerequisites:** [06-2 Streams & tasks](02_streams_and_tasks.md)
> **Time:** ~30 min · **Verified:** 2026-08-22 (Snowflake trial; Enterprise-only features flagged)

Micro-partitions are immutable ([02-1](../02_sql_and_loading/01_databases_schemas_tables.md)):
an `UPDATE` doesn't overwrite anything, it writes new partitions and leaves the old ones
referenced by the previous table version. Two features fall out of that one design
decision almost for free — you can **query the past**, and you can **clone a database
instantly**. Both are things a traditional database cannot do, and both have a bill
attached that's worth understanding before you rely on them.

---

## Time Travel

Every table keeps its previous versions for `DATA_RETENTION_TIME_IN_DAYS`:

```sql
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN DATABASE linkstash_analytics;

-- Settable at account, database, schema or table level; children inherit.
ALTER TABLE linkstash_analytics.analytics.clicks SET DATA_RETENTION_TIME_IN_DAYS = 7;
```

| Edition / table type | Allowed retention |
|---|---|
| Standard (and the trial) | 0 or **1** day — the default is 1 |
| **Enterprise+**, permanent tables | 0–**90** days |
| Transient / temporary tables (any edition) | 0 or 1 day |

`0` disables Time Travel for that object. On the trial you have exactly one day, which
is enough to practise everything below.

### Querying the past

Three clauses, all usable anywhere a table reference goes (including in a `CREATE TABLE
... CLONE`):

```sql
-- Relative: 10 minutes ago.
SELECT COUNT(*) FROM linkstash_analytics.analytics.clicks AT (OFFSET => -600);

-- Absolute: a timestamp.
SELECT * FROM linkstash_analytics.analytics.clicks
  AT (TIMESTAMP => '2026-08-22 09:00:00'::TIMESTAMP_NTZ);

-- Surgical: the state immediately BEFORE one statement ran.
SELECT * FROM linkstash_analytics.analytics.clicks
  BEFORE (STATEMENT => '01b7c3f4-0000-1a2b-0000-000000000abc');
```

`BEFORE (STATEMENT => ...)` is the one that saves you, because it needs no guesswork
about *when* — you find the query id of the mistake and rewind to just before it:

```sql
SELECT query_id, query_text, rows_updated, start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY      -- or INFORMATION_SCHEMA.QUERY_HISTORY, fresher
WHERE query_type = 'UPDATE'
  AND start_time > DATEADD(hour, -2, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;
```

### Recovering from the bad `UPDATE`

The framing that matters: **the mistake you just made is recoverable, for a window, and
the window costs storage.** Recover by *diffing and swapping*, not by overwriting:

```sql
-- 1. Materialise the good state as a separate table (a clone — instant, see below).
CREATE OR REPLACE TABLE linkstash_analytics.analytics.clicks_fixed
  CLONE linkstash_analytics.analytics.clicks
  BEFORE (STATEMENT => '01b7c3f4-0000-1a2b-0000-000000000abc');

-- 2. VERIFY before you touch production. This is the whole point of not overwriting.
SELECT COUNT(*) FROM linkstash_analytics.analytics.clicks_fixed;
SELECT COUNT(*) FROM linkstash_analytics.analytics.clicks;

-- 3. Atomic swap: names exchange, no window where the table is missing.
ALTER TABLE linkstash_analytics.analytics.clicks
  SWAP WITH linkstash_analytics.analytics.clicks_fixed;

-- 4. clicks_fixed now holds the BAD data. Keep it an hour, then drop it.
```

Why not `CREATE OR REPLACE TABLE clicks AS SELECT * FROM clicks BEFORE (...)`? It works,
and it **resets the table's history** — replacing the table drops the old one, so your
Time Travel for the pre-incident state goes with it. One typo in the query id and you've
destroyed both versions. Clone, verify, swap.

Rows that arrived *after* the bad statement are the honest caveat: rewinding to before
it also rewinds those. Check whether your pipeline wrote in between (`TASK_HISTORY` from
06-2), and if it did, re-run the load after the swap — which is safe, because the load
is a `MERGE`.

### `UNDROP`

```sql
DROP TABLE linkstash_analytics.analytics.clicks;
UNDROP TABLE linkstash_analytics.analytics.clicks;    -- back, instantly, within retention

UNDROP SCHEMA linkstash_analytics.analytics;          -- also works at schema level
UNDROP DATABASE linkstash_analytics;                  -- and database level
```

Dropped objects are hidden, not gone (`SHOW TABLES HISTORY` lists them with a
`dropped_on`), which also means **they keep costing storage until retention expires** —
a `DROP` is not how you stop paying. One gotcha: if you dropped `clicks` and then
created a *new* `clicks`, `UNDROP` fails on the name collision; rename the new one
first, then undrop.

### What retention actually costs

```sql
SELECT table_name,
       active_bytes/POWER(1024,3)     AS active_gb,
       time_travel_bytes/POWER(1024,3) AS time_travel_gb,
       failsafe_bytes/POWER(1024,3)   AS failsafe_gb
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
WHERE table_catalog = 'LINKSTASH_ANALYTICS' AND deleted = FALSE
ORDER BY time_travel_bytes DESC;
```

You pay for retained partitions, so the cost scales with **churn, not table size**. A
1 TB append-only table retains almost nothing extra; a 10 GB table that a task rewrites
every five minutes can retain many multiples of itself. Before setting 90 days on
anything (Enterprise), look at that column — and note that *raising* retention on a
churny table starts accruing immediately.

---

## Fail-safe, and why transient tables are cheaper

After Time Travel expires, **permanent** tables enter **Fail-safe**: 7 more days of
Snowflake-managed storage that only Snowflake Support can restore from, on a best-effort
basis, via a support ticket. You cannot query it, cannot use `AT`/`BEFORE` against it,
cannot shorten it, cannot disable it — and you pay for those bytes.

```
permanent table:  active data → Time Travel (0–90d, yours) → Fail-safe (7d, Snowflake's) → gone
transient table:  active data → Time Travel (0–1d, yours) → gone
```

That's the whole economics of the table types from
[02-1](../02_sql_and_loading/01_databases_schemas_tables.md) and the cost guardrails in
[05-3](../05_performance_and_cost/03_cost_guardrails.md): for a table you can rebuild —
`raw.raw_clicks` reloadable from staged files, `analytics.clicks` rebuildable from raw,
every staging table a pipeline recreates — a week of unusable disaster-recovery storage
is pure waste. **Transient for anything reproducible; permanent for the data that exists
nowhere else.** The pipeline you built in 06-2 is the reason `analytics.clicks` can be
transient: you can regenerate it.

---

## Zero-copy cloning

```sql
CREATE TABLE linkstash_analytics.analytics.clicks_backup
  CLONE linkstash_analytics.analytics.clicks;
```

That returns in about a second on any table size, and adds **no storage**. A clone is a
new metadata object pointing at the *same* immutable micro-partitions; only when one
side changes does Snowflake write new partitions for the changed data — copy-on-write.
You pay for divergence, and only for divergence.

Which makes three things routine:

**1. The pre-migration safety snapshot.** Combine with Time Travel and you can snapshot
a state you've already left:

```sql
-- A free, instant "before" image — even an hour after the fact.
CREATE TABLE linkstash_analytics.analytics.clicks_backup
  CLONE linkstash_analytics.analytics.clicks AT (OFFSET => -3600);
```

Take one before every schema change or backfill. It costs nothing until the tables
diverge, and it converts "restore from backup" from a ticket into a `SWAP WITH`.

**2. Full-size dev and test environments.**

```sql
CREATE DATABASE linkstash_dev CLONE linkstash_analytics;   -- every schema, table, view
```

Seconds, no extra storage, production-shaped data — and if a colleague breaks it,
`DROP DATABASE linkstash_dev` and clone again. Sit with how impossible that is on
Postgres or MySQL, where a full-size staging copy means `pg_dump`, hours, and paying for
a second full dataset. This is the feature that changes how teams work: a clone per
release branch, a clone per CI run of a dbt project, a clone as the thing you actually
test the migration against.

**3. Point-in-time investigation.** `CREATE DATABASE incident_0822 CLONE
linkstash_analytics AT (TIMESTAMP => ...)` gives you the whole warehouse as it was, to
poke at while production keeps moving.

### The honest caveats

- **Grants don't come along — mostly.** A cloned *object* does not inherit privileges granted on its source. A cloned *container* (database/schema) does keep the grants on the child objects inside it, but the new database itself starts with only the owner's access. So after cloning for a dev environment, re-grant deliberately ([04-2](../04_security_and_rbac/02_roles_and_grants_in_practice.md)) — a clone is not a permissions clone, and you may well *want* dev grants to differ.
- **Divergence costs storage.** A clone you rewrite completely costs as much as a copy. Long-lived dev clones drift into a real bill; treat them as disposable and re-clone rather than maintaining them.
- **Cloned tasks arrive suspended, and pipes need checking.** Handy — but verify before resuming anything in a cloned database, or your "dev" clone starts ingesting production files and writing to targets that now exist twice.
- **Type rules apply.** A transient table can't be cloned into a permanent one; a clone of a permanent table inside a transient database follows the container. Decide durability before the data matters.
- **Temporary/internal stage contents aren't duplicated** — a clone is a clone of table data and metadata, not of files you `PUT` somewhere.

---

## One more thing: Cortex

Since you spend your other days on GenAI work — Snowflake ships **Cortex**, LLM
functions callable straight from SQL, so inference happens where the data already lives
instead of after an export:

```sql
SELECT slug,
       SNOWFLAKE.CORTEX.SENTIMENT(feedback_text)                        AS sentiment,
       SNOWFLAKE.CORTEX.COMPLETE('claude-4-sonnet',
           'Summarise this feedback in one line: ' || feedback_text)    AS summary
FROM linkstash_analytics.analytics.link_feedback
LIMIT 10;
```

The genuinely interesting part isn't the function, it's the *architecture*: no pipeline
moving PII to an external endpoint, governance and masking policies from section 04 still
applying, and results landing in a table you can join. Model availability, regions and
pricing move fast — check the current docs before designing anything around it — but
"the LLM runs next to the warehouse" is the pattern worth filing away, along with Cortex
Search and vector types for RAG over data that never leaves Snowflake.

---

## Where to go next

You can now load, query, script, secure, tune and automate a Snowflake warehouse. The
highest-value next steps, in order:

- **dbt on Snowflake** — the single most employable adjacent skill. Take the pipeline from 06-2 and rebuild the modeling half as dbt models with tests and lineage; you'll have the artefact interviewers ask about.
- **Dynamic tables** — build the same models declaratively and compare refresh cost and freshness against your task DAG. Knowing *when each one wins* is the senior answer.
- **Snowpark depth** — UDFs, vectorised UDFs and stored procedures ([03-3](../03_python_and_snowpark/03_snowpark_dataframes.md)) push your Python into the warehouse; Snowpark ML if you want the feature-engineering-to-model path.
- **SnowPro Core certification** — cheap, well-scoped, and it maps almost exactly onto this course (architecture, loading, RBAC, performance, Time Travel/cloning). Worth it if you're job-hunting into data roles.
- **Your own capstone** — the thing that actually gets you hired. Build the whole linkstash pipeline unaided, from empty account to dashboard, with a resource monitor guarding it and a README explaining the cost choices.

Two habits to keep from this course: **watch the credits** (a warehouse left running is
the only way to actually lose money here), and **keep raw data raw** — every recovery
path in this section, from a stale stream to a bad `UPDATE`, ultimately depended on
being able to rebuild from something you never modified.

---

## Recap & next

- ✅ **Time Travel** = `DATA_RETENTION_TIME_IN_DAYS` (1 day default/max on Standard and the trial; up to 90 on Enterprise+), queried with `AT (OFFSET => -600)`, `AT (TIMESTAMP => ...)`, `BEFORE (STATEMENT => '<query_id>')`.
- ✅ Recover with **clone → verify → `SWAP WITH`**, never `CREATE OR REPLACE` (which resets the history you're relying on). `UNDROP TABLE/SCHEMA/DATABASE` within retention.
- ✅ Retention costs storage proportional to **churn**; read `TABLE_STORAGE_METRICS` before raising it, and remember dropped tables keep billing until retention expires.
- ✅ **Fail-safe** = 7 extra days, permanent tables only, Snowflake-managed, support-only, not queryable, not disableable — the reason **transient** tables are cheaper and the right default for anything reproducible.
- ✅ **Zero-copy clones** are instant metadata operations with copy-on-write storage: pre-migration snapshots (`CLONE ... AT (OFFSET => -3600)`), instant full-size dev databases, point-in-time forensic copies.
- ✅ Clone caveats: object grants don't follow (container child grants do), divergence costs real storage, cloned tasks come over suspended, transient can't become permanent.
- ✅ **Cortex** runs LLM functions inside SQL — inference where the data and its governance already are.

## Exercise

You ran this at 09:12 and realised at 09:40:

```sql
UPDATE linkstash_analytics.analytics.clicks SET country = 'US';   -- forgot the WHERE
```

Your load task has run five times since. Recover `country` without losing the clicks
that arrived after the mistake, then say which single object you should have created at
09:11 and what it would have cost.

<details>
<summary>Solution</summary>

```sql
-- 1. Find the exact statement — no guessing at timestamps.
SELECT query_id, query_text, rows_updated
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE query_type = 'UPDATE' AND database_name = 'LINKSTASH_ANALYTICS'
  AND start_time > DATEADD(hour, -2, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;

-- 2. Snapshot the pre-mistake state (instant, no storage).
CREATE OR REPLACE TABLE linkstash_analytics.analytics.clicks_pre
  CLONE linkstash_analytics.analytics.clicks BEFORE (STATEMENT => '<query_id>');

-- 3. Repair in place: take country from the snapshot, keep every current row.
--    Rows added after 09:12 don't match and keep their (correct) country.
UPDATE linkstash_analytics.analytics.clicks AS t
SET country = p.country
FROM linkstash_analytics.analytics.clicks_pre AS p
WHERE t.click_id = p.click_id;

-- 4. Verify, then clean up.
SELECT country, COUNT(*) FROM linkstash_analytics.analytics.clicks GROUP BY 1;
DROP TABLE linkstash_analytics.analytics.clicks_pre;
```

Repair-in-place beats `SWAP WITH` here **because the task kept writing**. A swap would
restore 09:12 wholesale and discard 28 minutes of legitimately loaded clicks; the
targeted `UPDATE` fixes only the column the mistake touched. (You could also swap and
then re-`MERGE`, since the load is convergent — but only if the stream hadn't already
been consumed. Prefer the repair.)

Note the two things that made this possible: an **idempotency key** (`click_id`) to join
old to new, and being inside the retention window. On the trial that window is one day —
had you noticed on Monday, the answer would have been "rebuild `analytics.clicks` from
`raw.raw_clicks`", which is available only because raw stayed raw.

What you should have created at 09:11:

```sql
CREATE TABLE linkstash_analytics.analytics.clicks_bak
  CLONE linkstash_analytics.analytics.clicks;
```

Cost: **nothing.** Zero-copy — no storage until the tables diverge, and only for the
diverged partitions. One second of typing before any hand-written `UPDATE`, `DELETE` or
migration, and recovery stops depending on retention windows or on noticing in time.

</details>

**Section complete.** → Build the whole thing yourself in the **[capstone](../99_capstone_linkstash_analytics.md)**, or back to the **[course README](../README.md)**.
