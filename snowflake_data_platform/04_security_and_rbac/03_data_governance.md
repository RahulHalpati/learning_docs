# 04-3 · Governance: masking, row access & network policies

> **Level:** Intermediate · **Prerequisites:** [04-2 Roles & grants in practice](02_roles_and_grants_in_practice.md)
> **Time:** 25 min · **Verified:** 2026-08-22 (Snowflake trial; Enterprise-only features flagged)

RBAC is all-or-nothing per object: a role can read `clicks` or it cannot. Real data
isn't shaped like that. The analyst needs click volumes by hour but has no business
reason to see the visitor's email or full IP; the EU analyst shouldn't see US rows;
the auditor needs to know who read what. **Governance is the layer that answers
"which parts of this table, for whom" — and since there is no `Deny` in Snowflake
RBAC ([04-1](01_rbac_model.md)), it's the *only* way to carve an exception out of a
grant.**

If you've done anything near healthcare, fintech or EU users, you already have the
instinct: GDPR/HIPAA/PCI don't care that the column was convenient to store. What's
new is that Snowflake enforces this *in the engine*, so a mask can't be forgotten by
one query path the way an application-layer redaction can.

> ⚠️ **Edition gating, honestly:** dynamic data masking, row access policies, object
> tagging, tag-based masking and the `ACCESS_HISTORY` view are **Enterprise Edition
> or higher**. Network policies, secure views and `QUERY_HISTORY` are available on
> **Standard**. Your trial is Enterprise, so you can run all of it now — but if the
> job's account is Standard, half this page isn't available to you and the answer is
> separate tables plus separate grants. Know which is which before you promise it in
> a design review.

---

## Dynamic data masking (Enterprise+)

A **masking policy** is a function attached to a column. It runs at query time and
sees the querying role, so one physical column returns different values to different
roles — no views, no duplicated tables.

```sql
USE ROLE accountadmin;   -- or a role granted CREATE MASKING POLICY on the schema
CREATE MASKING POLICY linkstash_analytics.analytics.email_mask AS (val string)
  RETURNS string ->
  CASE
    WHEN IS_ROLE_IN_SESSION('ETL_SERVICE') THEN val        -- the pipeline needs the real value
    WHEN IS_ROLE_IN_SESSION('SYSADMIN')    THEN val
    ELSE REGEXP_REPLACE(val, '^[^@]+', '*****')            -- analysts see *****@example.com
  END;

ALTER TABLE linkstash_analytics.analytics.clicks
  MODIFY COLUMN visitor_email SET MASKING POLICY linkstash_analytics.analytics.email_mask;
```

Now `USE ROLE analyst; SELECT visitor_email FROM clicks;` returns
`*****@example.com`, and the same statement as `etl_service` returns the real address.
The policy applies everywhere the column is read — views over it, joins on it,
Snowpark DataFrames, the connector — because it lives on the column, not the query.

**Use `IS_ROLE_IN_SESSION()`, not `CURRENT_ROLE()`.** `CURRENT_ROLE()` is a single
string, so a role that *inherits* `etl_service` fails the check and gets masked data
unexpectedly; `IS_ROLE_IN_SESSION()` respects the hierarchy and secondary roles. This
is the one real footgun in masking policies.

Same idea for an IP, keeping it useful for aggregation while dropping precision:

```sql
CREATE MASKING POLICY ip_mask AS (val string) RETURNS string ->
  CASE WHEN IS_ROLE_IN_SESSION('ETL_SERVICE') THEN val
       ELSE CONCAT(SPLIT_PART(val, '.', 1), '.', SPLIT_PART(val, '.', 2), '.x.x')  -- /16 only
  END;
```

Two constraints worth knowing before you design around it: a column can carry only
**one** masking policy at a time, and the policy's argument type must match the
column's type (a `string` policy will not attach to a `VARIANT`).

---

## Row access policies (Enterprise+)

Masking hides *columns*. **Row access policies** hide *rows* — the row-level security
equivalent, evaluated per row per query.

```sql
CREATE ROW ACCESS POLICY region_rap AS (region string) RETURNS boolean ->
     IS_ROLE_IN_SESSION('ETL_SERVICE')                    -- the pipeline sees everything
  OR EXISTS (
       SELECT 1 FROM linkstash_analytics.analytics.role_regions rr
       WHERE  rr.role_name = CURRENT_ROLE()               -- a mapping table, not hardcoded roles
       AND    rr.region    = region
     );

ALTER TABLE linkstash_analytics.analytics.clicks
  ADD ROW ACCESS POLICY region_rap ON (region);           -- names the column(s) fed to the policy
```

Grant `analyst_eu` a row in `role_regions` and it sees EU clicks only — with no `WHERE`
clause in its SQL and no way to remove one. The **mapping-table pattern** shown here
is the idiomatic form: hardcoding role names in the policy body means a DDL change per
new team, whereas a mapping table means an `INSERT`.

Costs to be aware of: the policy body runs as part of every query on the table, so
keep it cheap (the mapping table should be small and, ideally, clustered/tiny enough
to cache), and a row access policy defeats some result caching. Also note a row
access policy and a masking policy compose fine on the same table — rows are filtered
first, then surviving columns masked.

---

## Object tagging + tag-based masking (Enterprise+)

Attaching policies column by column doesn't scale past one table. **Tags** invert it:
classify the data once, and let the policy follow the classification.

```sql
USE ROLE accountadmin;
CREATE TAG linkstash_analytics.analytics.pii
  ALLOWED_VALUES 'email', 'ip', 'name'                    -- a controlled vocabulary, not free text
  COMMENT = 'personal data classification';

ALTER TABLE linkstash_analytics.analytics.clicks
  MODIFY COLUMN visitor_email SET TAG linkstash_analytics.analytics.pii = 'email';

-- tag-based masking: one statement, applies to EVERY column tagged pii='email', now and future
ALTER TAG linkstash_analytics.analytics.pii
  SET MASKING POLICY linkstash_analytics.analytics.email_mask;
```

This is the same leverage `FUTURE` grants gave you in [04-2](02_roles_and_grants_in_practice.md):
a standing rule instead of a per-object chore. Tag a new table's email column `pii='email'`
and it is masked on creation — nobody has to remember the policy exists. Tags are also
inherited down the hierarchy (tag a schema, its tables carry it) and are searchable in
`SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES`, which makes "where is our PII?" an actual query
rather than a spreadsheet.

The practical workflow: tag columns as part of the DDL that creates them, and treat
"untagged column in a schema that holds user data" as a review comment.

---

## Network policies (all editions)

RBAC says *who*. A **network policy** says *from where* — an IP allowlist, the closest
thing here to a security group.

```sql
USE ROLE securityadmin;
CREATE NETWORK POLICY corp_and_ci
  ALLOWED_IP_LIST = ('203.0.113.0/24', '198.51.100.7')    -- office CIDR + the CI runner's NAT IP
  BLOCKED_IP_LIST = ();                                   -- BLOCKED wins over ALLOWED

ALTER USER linkstash_etl SET NETWORK_POLICY = corp_and_ci;  -- scope it to the service user first
-- ALTER ACCOUNT SET NETWORK_POLICY = corp_and_ci;          -- account-wide: see the warning below
```

⚠️ **You can lock yourself out of your own account with this statement.** Set it on a
single user, verify from the address you expect, and only then consider account level —
and make sure your *own* current IP is in the list when you do. Snowflake keeps an
ACCOUNTADMIN escape hatch, but recovering usually means a support ticket, which on a
30-day trial is a bad afternoon.

Newer accounts prefer **network rules** (`CREATE NETWORK RULE`) attached to a policy
via `ALLOWED_NETWORK_RULE_LIST`, which lets you reuse one rule across policies; the
`ALLOWED_IP_LIST` form above still works and is fine for a small account. A service
user pinned to the CI runner's egress IP *and* key-pair auth is a genuinely strong
posture — a leaked key is useless from anywhere else.

---

## Secure views (all editions)

A plain view is not a security boundary. Snowflake's optimizer rewrites it — pushing
predicates into the underlying tables, and surfacing details through
`GET_DDL`/`SHOW VIEWS` — so a determined user can infer rows the view was meant to
filter out, e.g. by probing which predicates error or which are fast. `CREATE SECURE
VIEW` disables those optimizations and hides the definition from anyone who isn't the
owner:

```sql
CREATE SECURE VIEW linkstash_analytics.analytics.clicks_public AS
  SELECT click_id, link_id, clicked_at, country      -- no email, no raw IP
  FROM   linkstash_analytics.analytics.clicks;

GRANT SELECT ON VIEW linkstash_analytics.analytics.clicks_public TO ROLE linkstash_read;
```

The trade is real: secure views are **slower**, because the optimizations that leak are
also the optimizations that make views fast. Rule of thumb — if the view exists for
*convenience*, plain; if it exists to *withhold* something, secure. And if it exists
to withhold something and you're on Enterprise, a masking policy on the base column is
usually the better answer, since it can't be bypassed by querying the table directly.

---

## Auditing: who read what

Two families, and the difference matters:

```sql
USE ROLE accountadmin;   -- or grant IMPORTED PRIVILEGES on the SNOWFLAKE database

-- who ran what, account-wide, ~365 days of history
SELECT user_name, role_name, query_type, start_time, LEFT(query_text, 80) AS q
FROM   SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE  start_time > DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND  database_name = 'LINKSTASH_ANALYTICS'
ORDER  BY start_time DESC LIMIT 50;

-- Enterprise+: which COLUMNS were actually touched, per query — the real audit trail
SELECT query_id, user_name, direct_objects_accessed, base_objects_accessed
FROM   SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
ORDER  BY query_start_time DESC LIMIT 20;
```

- **`SNOWFLAKE.ACCOUNT_USAGE.*`** — account-wide, long retention, **but these views
  lag by minutes to hours** depending on the view. Never build a "did that just run?"
  check on them, and never conclude "no rows, so it didn't happen" within the lag
  window. `ACCESS_HISTORY` (Enterprise+) is the column-level one — it answers "who has
  read the email column in the last 90 days", which is what a compliance question
  actually looks like.
- **`INFORMATION_SCHEMA` table functions** — e.g. `QUERY_HISTORY()`, scoped and with
  much shorter retention, but **no latency**. Use these for live debugging,
  `ACCOUNT_USAGE` for auditing and reporting.

Also useful: `LOGIN_HISTORY` (failed auth, MFA, source IP — pair it with your network
policy), and `GRANTS_TO_ROLES` / `GRANTS_TO_USERS` as the queryable version of the
`SHOW GRANTS` commands from 04-1, so "diff our access model against last week" becomes
SQL. All of these are queries, so they need a running warehouse — keep the time filter
tight on `dev_wh` rather than scanning a year of history for fun.

---

## The checklist

Your AWS/security instincts port over almost one-to-one:

| Instinct from AWS | Snowflake equivalent | Where |
|---|---|---|
| Don't use the root account | don't work in **ACCOUNTADMIN**; `USE ROLE sysadmin` | [04-1](01_rbac_model.md) |
| Least privilege, named actions on named ARNs | privileges on named objects, granted to **access roles** | [04-2](02_roles_and_grants_in_practice.md) |
| Managed policies over inline sprawl | **access roles → functional roles**, never objects to users | [04-2](02_roles_and_grants_in_practice.md) |
| No `Resource: "*"` | no `GRANT … TO ROLE PUBLIC` | [04-1](01_rbac_model.md) |
| IAM roles for services, not user keys | **`TYPE = SERVICE`** user + key-pair auth | [04-2](02_roles_and_grants_in_practice.md) |
| Security groups / IP allowlists | **network policies** | this module |
| Encrypt & redact PII | **masking policies** + **tags** (Enterprise) | this module |
| CloudTrail for "who did what" | **`ACCOUNT_USAGE.QUERY_HISTORY` / `ACCESS_HISTORY`** (lagging) | this module |
| Verify allow *and* deny | `USE ROLE x` and watch it fail — **actually enforced here** | [04-2](02_roles_and_grants_in_practice.md) |

The one item with no AWS analogue is **ownership** — and the one AWS item with no
Snowflake analogue is **`Deny`**. Those two are where ported instincts go wrong.

---

## Recap & next

- ✅ **Masking policies** (Enterprise+) return different column values per role, on
  the column itself, everywhere it's read — use **`IS_ROLE_IN_SESSION()`**, not
  `CURRENT_ROLE()`.
- ✅ **Row access policies** (Enterprise+) filter rows per role; drive them from a
  **mapping table** so new teams are an `INSERT`, not a DDL change.
- ✅ **Tags + tag-based masking** (Enterprise+) are the scalable form: classify once,
  the policy follows the tag onto future columns — the `FUTURE`-grant idea again.
- ✅ **Network policies** (all editions) restrict by IP; set them on a **user first**,
  because account-level lockout is real.
- ✅ **A plain view is not a boundary** — `CREATE SECURE VIEW` when the view exists to
  withhold something, and accept it's slower.
- ✅ Audit with **`ACCOUNT_USAGE`** (long retention, **lags minutes to hours**) and
  `INFORMATION_SCHEMA` table functions (live, short retention). `ACCESS_HISTORY` is
  Enterprise+ and column-level.
- ✅ Be **honest about edition gating** in design reviews: on Standard, column and
  row security means separate objects with separate grants.

## Exercise

Compliance asks: "analysts must never see visitor emails, and we need to prove who
has seen them in the last 90 days." You're on **Standard Edition** — no masking
policies, no tags, no `ACCESS_HISTORY`. Design it anyway, and say what you lose.

<details>
<summary>Solution</summary>

Move the control from the column into the object graph — separate the sensitive column
into its own object and grant accordingly:

```sql
USE ROLE sysadmin;
-- 1. the sensitive column lives in its own table, in its own schema
CREATE SCHEMA linkstash_analytics.sensitive;
CREATE TABLE  linkstash_analytics.sensitive.visitor_emails (click_id string, visitor_email string);

-- 2. analysts get a secure view that simply doesn't contain it
CREATE SECURE VIEW linkstash_analytics.analytics.clicks_safe AS
  SELECT click_id, link_id, clicked_at, country FROM linkstash_analytics.analytics.clicks;

USE ROLE securityadmin;
GRANT SELECT ON VIEW linkstash_analytics.analytics.clicks_safe TO ROLE linkstash_read;
-- and crucially: NO grant of USAGE on the `sensitive` schema to linkstash_read
```

Access is then enforced by the schema `USAGE` grant analysts don't have — the
four-privilege minimum working *for* you. Add a `pii_read` access role granted only to
`etl_service` for the rare legitimate read.

For the proof: `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` is available on Standard, so
query it for statements against the `sensitive` schema, remembering it **lags** and
that 90 days is inside its retention:

```sql
SELECT user_name, role_name, start_time, query_text
FROM   SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE  start_time > DATEADD(day, -90, CURRENT_TIMESTAMP())
  AND  query_text ILIKE '%sensitive.visitor_emails%';
```

**What you lose:** (1) `query_text` matching is a heuristic — a view or CTE over the
table, or a `SELECT *`, can read the column without the name appearing, which is
exactly the gap `ACCESS_HISTORY` closes with real column lineage; (2) the split table
needs a join and the ETL must maintain both halves, so it *can* drift, whereas a
masking policy cannot be forgotten; (3) any new sensitive column requires this whole
dance again — no tag to inherit. That difference is the honest business case for
Enterprise, and it's a better answer in a design review than pretending the feature is
there.

</details>

**→ Next: [05 · Performance & cost](../05_performance_and_cost/README.md)** —
where the `MODIFY` privilege you just withheld starts paying for itself.
