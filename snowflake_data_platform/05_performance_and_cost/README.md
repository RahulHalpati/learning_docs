# 05 · Performance & cost

In Snowflake, performance *is* cost — the same query that scans less data also
burns fewer **credits**, so tuning and FinOps are one skill, not two. This section
teaches the billing model, the one performance mechanism that matters
(**pruning**, because there are no indexes), and the guardrails — **resource
monitors** above all — that stop a mistake from becoming an invoice.

| # | Module | You'll be able to… |
|---|---|---|
| 05-1 | [How Snowflake bills you](01_credits_and_billing.md) | Break a bill into compute/storage/cloud-services, explain the 60-second minimum, right-size a warehouse, and read real spend out of `WAREHOUSE_METERING_HISTORY` |
| 05-2 | [Pruning, caching & query tuning](02_pruning_caching_tuning.md) | Write queries that prune micro-partitions, use the three caches deliberately, and read a Query Profile for spilling and bad pruning |
| 05-3 | [Cost guardrails you actually ship](03_cost_guardrails.md) | Ship resource monitors, a safe trial setup, and a cost checklist — plus run a credit-burn post-mortem from `QUERY_HISTORY` |

**Next → [05-1 · How Snowflake bills you](01_credits_and_billing.md)**
