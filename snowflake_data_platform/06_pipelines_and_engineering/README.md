# 06 · Pipelines & data engineering

Everything so far you ran by hand. A data platform earns its name when files land
and rows appear without you: **Snowpipe** ingests continuously off cloud storage
events, **streams** capture what changed, and **tasks** transform it on a schedule —
the raw → staged → modeled pipeline that every warehouse eventually grows. Then the
two features that make Snowflake feel unlike a traditional database: Time Travel and
**zero-copy clones**, an instant full-size dev environment for free.

| # | Module | You'll be able to… |
|---|---|---|
| 06-1 | [Continuous ingestion with Snowpipe](01_snowpipe_ingestion.md) | Choose batch `COPY INTO` vs auto-ingest Snowpipe, wire an S3 event notification to a pipe, and monitor it with `SYSTEM$PIPE_STATUS` and `COPY_HISTORY` |
| 06-2 | [Streams & tasks: the transformation pipeline](02_streams_and_tasks.md) | Build raw → stream → task → modeled table end to end, reason about transactional stream consumption, and say when dynamic tables or dbt beat hand-written tasks |
| 06-3 | [Time Travel, zero-copy clones & where to go next](03_time_travel_clones_and_next.md) | Recover a bad `UPDATE` from history, clone a whole database in seconds, explain Fail-safe's cost, and pick your next step |

**Next → [06-1 · Continuous ingestion with Snowpipe](01_snowpipe_ingestion.md)**
