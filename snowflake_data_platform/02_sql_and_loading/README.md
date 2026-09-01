# 02 · SQL, tables & loading data

Snowflake speaks near-standard SQL, so the syntax is familiar — what's different is
everything around it: no indexes, no enforced foreign keys, files staged before they
become rows, and JSON as a first-class column type. This section builds the
**linkstash analytics** warehouse from empty account to queryable typed views.

| # | Module | You'll be able to… |
|---|---|---|
| 02-1 | [Databases, schemas & tables](01_databases_schemas_tables.md) | Lay out the account→database→schema hierarchy and pick permanent vs transient vs temporary tables |
| 02-2 | [Stages, file formats & COPY INTO](02_stages_and_copy_into.md) | Land files on a stage and bulk-load them idempotently, with error handling and dry runs |
| 02-3 | [Semi-structured data: VARIANT, JSON & FLATTEN](03_semi_structured_json.md) | Store raw JSON without a schema and query it with SQL — paths, casts, `LATERAL FLATTEN`, typed views |

**Next → [02-1 · Databases, schemas & tables](01_databases_schemas_tables.md)**
