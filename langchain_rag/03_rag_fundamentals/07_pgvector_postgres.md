# 07 · pgvector: RAG on the Postgres you already run

> **Level:** Intermediate · **Prerequisites:** [06 · RAG over web pages](06_web_sources.md)
> **Time:** ~35 min · **Verified:** 2026-08-24 (langchain-postgres · pgvector/pgvector:pg16 · psycopg 3)

## Why this matters

Every lesson so far used `InMemoryVectorStore` or FAISS, for one reason: **zero setup**. That was the right call for learning, and it is the wrong call the moment two processes need to read the same index, or the index has to survive a deploy.

So what do you reach for in production? In 2026 the answer for most teams is **pgvector on Postgres** — and not because it wins a benchmark. It wins because it's the database your team **already runs**. You already have backups, connection pooling, monitoring, migrations, an on-call runbook, a security review, and someone who knows how to read a query plan. pgvector makes vectors a *column type* in that database instead of a second system with its own copy of all of those problems.

The industry guidance is unusually blunt about it:

> **Start with pgvector. Move to a dedicated vector database only when you can name the specific bottleneck that forced the move.**

That's a defensible engineering position, not laziness. pgvector comfortably handles workloads into the **tens of millions of vectors**, which is far more than most products ever have, and consolidating onto one system cuts total cost of ownership substantially — one thing to back up, secure, monitor, upgrade, and join against. "We added a vector database" is a sentence you should have to justify with a number.

You've already met this database elsewhere in the repo: [Section 05 of the FastAPI course](../../fastapi_complete/05_async_database_sqlalchemy_alembic/README.md) runs Postgres with SQLAlchemy and Alembic migrations. pgvector rides on **that same database** — same connection, same migration workflow, same backups. Your embeddings become just another table in an app you already know how to operate.

---

## Run it

pgvector is a **Postgres extension**, not a service. There's nothing new to deploy, nothing new to network, nothing new listening on a port — you turn it on inside a database:

```bash
uv add langchain-postgres "psycopg[binary]"

# The official image is just Postgres with the extension already compiled in.
export PGVECTOR_PASSWORD='pick-something-long'
docker run -d --name pgvector-rag \
  -e POSTGRES_PASSWORD="$PGVECTOR_PASSWORD" \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Enable the extension once per database — this is the entire "installation".
docker exec -it pgvector-rag psql -U postgres -d ragdb \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

That `CREATE EXTENSION vector;` is the whole story: it registers the `vector` column type, the distance operators, and the index types. On managed Postgres (RDS, Cloud SQL, Supabase, Neon) it's the same one line — pgvector is available on all of them, which is another reason it's the default.

> **Why this beats a new service in a code review:** a dedicated vector DB is a new deployment, a new backup story, a new auth surface, a new dashboard, and a new failure mode that wakes someone up. The extension is a `CREATE EXTENSION`.

---

## Swap the store, keep the code

Here's the payoff for all those lessons spent on the *interface* rather than on any one store. Take the RAG chain from [04 · Build a RAG chain](04_build_a_rag_chain.md) and point it at Postgres:

```python
import os
from langchain_postgres import PGVector          # NOT langchain_community.PGVector (superseded)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# postgresql+psycopg:// selects the psycopg 3 driver. Credentials from the
# environment — a connection string in source is a leaked credential.
connection: str = (
    f"postgresql+psycopg://{os.environ['PGVECTOR_USER']}:{os.environ['PGVECTOR_PASSWORD']}"
    f"@{os.environ['PGVECTOR_HOST']}:5432/{os.environ['PGVECTOR_DB']}"
)

store = PGVector(
    embeddings=embeddings,
    collection_name="support_docs",   # namespace inside the same tables
    connection=connection,
    use_jsonb=True,                   # metadata as JSONB — queryable and indexable
)

store.add_documents([
    Document(page_content="Refunds are allowed within 30 days with a receipt.",
             metadata={"source": "refunds", "tenant": "acme", "year": 2026}),
    Document(page_content="Express shipping costs $14.99 and takes 1-2 days.",
             metadata={"source": "shipping", "tenant": "acme", "year": 2026}),
])
```

Now the part worth staring at — **everything downstream is untouched**:

```python
retriever = store.as_retriever(search_kwargs={"k": 2})

# Byte-for-byte the chain from lesson 04. It does not know the store changed.
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt | llm | StrOutputParser()
)
```

`add_documents`, `similarity_search`, `similarity_search_with_score`, `as_retriever`, `delete` — the same interface you learned on `InMemoryVectorStore` in [02 · Vector stores](02_vector_stores.md). Going from a toy store to production Postgres changed **three lines**: the import, the constructor, and the connection string.

> **This is not an accident, it's the reason the course taught the interface first.** Vector store choice looks like a big architectural decision and is actually one of the cheapest decisions to reverse — as long as you never let store-specific calls leak into your chain. Keep the store behind `as_retriever()` and migration stays a config change.

---

## What the table actually looks like

`PGVector` creates two tables on first use: a **collection** table (one row per `collection_name`) and an **embedding** table holding the chunks — text, metadata, and the vector itself. In current versions they're named `langchain_pg_collection` and `langchain_pg_embedding`; check yours with `\d` rather than trusting a tutorial:

```bash
docker exec -it pgvector-rag psql -U postgres -d ragdb -c '\d langchain_pg_embedding'
```

The column that matters is the embedding, typed `vector(N)` — pgvector's own type, holding `N` float dimensions. **`N` is fixed by your embedding model**: 384 for MiniLM, 1536 for OpenAI `text-embedding-3-small`, 3072 for `-large`. Two consequences that bite people:

- **Changing embedding models means re-embedding everything.** A 384-dim vector cannot be compared to a 1536-dim one; there is no conversion. Treat the model as part of the schema.
- **Dimension mismatch fails loudly at insert**, which is the good outcome. The bad outcome is two *different* models writing into one collection — same dimension, incompatible vector spaces, silently garbage results. One collection, one model.

Everything else is ordinary Postgres: the text is a `text` column, the metadata is `jsonb` (that's `use_jsonb=True`), and `pg_dump` backs up your vectors along with the rest of your data because they *are* the rest of your data.

---

## Indexes & distance metrics

This is the part job specs ask about **by name**, so let's be precise.

### Pick the distance operator that matches your embeddings

| Metric | pgvector operator class | Use when |
|---|---|---|
| **Cosine** | `vector_cosine_ops` | The default for text embeddings — compares *direction*, ignores magnitude |
| **L2 / Euclidean** | `vector_l2_ops` | Model trained for straight-line distance in the embedding space |
| **Inner product** | `vector_ip_ops` | Model trained with a dot-product objective (fastest, magnitude matters) |

The rule: **match the metric to how the model was trained.** Most sentence-transformer and OpenAI text embeddings are normalised and trained for cosine, so cosine is the right default — but the operator class in your index must match the distance your queries use, or Postgres won't use the index at all.

### Without an index, Postgres does an exact sequential scan

Worth saying plainly because it surprises people: **a fresh pgvector table has no vector index.** Every query reads every row and computes every distance. That's an *exact* nearest-neighbour search — perfect recall — and it is completely fine for a few thousand rows. At a million rows it's a full table scan per question, and your p99 is measured in seconds.

Approximate indexes (**ANN**) trade a little recall for orders of magnitude less work. pgvector gives you two:

| | **HNSW** | **IVFFlat** |
|---|---|---|
| Structure | multi-layer proximity graph | clustered inverted lists |
| Build time | **slow** | **fast** |
| Memory | **higher** | lower |
| Recall/latency | **better** | good, needs tuning |
| Needs training data | no — build on an empty table | **yes** — needs representative rows before building |
| Tuning knobs | `m`, `ef_construction` (build) · `hnsw.ef_search` (query) | `lists` (build) · `ivfflat.probes` (query) |
| Reach for it when | you want the production default | build time or memory is the binding constraint |

**HNSW is the usual production default in 2026.** IVFFlat earns its place when you rebuild indexes often or memory is tight — but note its awkward property: it clusters based on the data present at build time, so building it on an empty or unrepresentative table gives you bad clusters and bad recall. HNSW has no such ordering requirement.

Here's the SQL — write this one from memory, an interviewer will ask you to:

```sql
-- HNSW, cosine distance, on the LangChain embedding table.
-- m = neighbours per node; ef_construction = candidate list size while building.
-- Higher = better recall, slower build, more memory.
CREATE INDEX ON langchain_pg_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- The IVFFlat alternative. Rule of thumb: lists ≈ rows / 1000 up to ~1M rows,
-- then ≈ sqrt(rows). Build this AFTER loading representative data.
CREATE INDEX ON langchain_pg_embedding
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

Note `vector_cosine_ops` appears **inside** the index definition. Index one metric, query with another, and you silently fall back to a sequential scan.

### Query-time knobs trade recall for latency

Build-time settings are baked in; these you can turn per session or per transaction:

```sql
SET hnsw.ef_search = 100;   -- HNSW: candidates inspected per search (default 40)
SET ivfflat.probes = 10;    -- IVFFlat: lists probed per search (default 1)
```

Both do the same thing conceptually: **look at more candidates, find better neighbours, spend more time.** Raise them when recall evaluation ([Section 04 · Evaluating RAG](../04_advanced_rag/03_evaluating_rag.md)) says you're missing chunks that are genuinely in the store; lower them when latency is the complaint. This is the tuning dial that a hosted vector DB hides from you and that pgvector hands you directly — which is either an advantage or a chore, depending on whether anyone on the team wants it.

---

## Metadata filtering + joins

Filtering happens **in the database**, next to the vectors:

```python
# Structured pre-filter: only this tenant's refund docs are candidates.
hits = store.similarity_search(
    "how long do I have to return something?",
    k=2,
    filter={"tenant": "acme", "source": {"$in": ["refunds", "returns"]}},
)
for doc in hits:
    print(doc.metadata["source"], "-", doc.page_content)
```

Simple equality can be written as `{"tenant": "acme"}`; richer conditions use operators like `$in`, `$ne`, `$gt`, and `$and` against the JSONB metadata. Either way Postgres applies the predicate as part of the query rather than after the fact.

And here is the thing **no dedicated vector database can do**: your vectors live in the same database as your application tables, so retrieval can `JOIN`. Permissions, tenancy, subscription tier, soft deletes, document freshness — enforced in one query against the real source of truth, not against a copy of it that a sync job hopefully updated:

```sql
-- Nearest chunks THIS user is allowed to see, in one round trip.
SELECT e.document, e.embedding <=> $1 AS distance
FROM langchain_pg_embedding e
JOIN documents d ON d.id = (e.cmetadata->>'doc_id')::uuid
JOIN acl a ON a.document_id = d.id AND a.user_id = $2
WHERE d.deleted_at IS NULL
ORDER BY distance
LIMIT 5;
```

(`<=>` is pgvector's cosine-distance operator; `<->` is L2 and `<#>` is negative inner product.) With a separate vector store, that same requirement becomes: query the vector DB, get IDs back, query Postgres to check permissions, discard what the user can't see — and now your `k=5` sometimes returns two results, and your permission logic lives in application code where it can be forgotten. **Access control is a database job.** Keeping vectors in the database keeps it one.

---

## When pgvector is the wrong call

The honest limits, because "use Postgres" is a default, not a religion:

- **Very large scale.** Past roughly the tens-of-millions-of-vectors range, purpose-built engines pull ahead on latency at a given recall — and they shard and replicate the vector workload in ways Postgres wasn't designed for.
- **Very high write throughput.** Continuous heavy inserts mean continuous index maintenance competing with your OLTP traffic on the same instance. Your product database slowing down because of the embedding pipeline is a genuinely bad afternoon.
- **Index builds are heavy.** HNSW on millions of rows costs real time, memory, and I/O. Plan for `CREATE INDEX CONCURRENTLY`, a maintenance window, or a replica.
- **You're now tuning Postgres.** `m`, `ef_construction`, `ef_search`, `maintenance_work_mem`, autovacuum on a table churning large rows. A managed vector DB sells you exactly the removal of this work.
- **You need features Postgres doesn't have**, like built-in sparse/hybrid fusion, multi-tenant vector isolation, or a managed reranking stage.

Notice all five are **named bottlenecks**. That's the test. "It'll scale better later" is not a bottleneck; "our p99 is 400 ms at 60 million vectors and index rebuilds block the write path" is. Migrate on evidence, and because you kept everything behind `as_retriever()`, migrating is a config change rather than a rewrite.

---

## Recap & next

- ✅ **pgvector is a Postgres extension** (`CREATE EXTENSION vector;`), not a service — `pgvector/pgvector:pg16` in Docker, one line on managed Postgres.
- ✅ The 2026 default for production RAG: **start with pgvector**, move to a dedicated vector DB only when you can **name the bottleneck**. One system to back up, secure, monitor, and join against.
- ✅ Use **`langchain-postgres`**' `PGVector` (it supersedes the `langchain_community` one), with `connection="postgresql+psycopg://…"` built from **env vars** and `use_jsonb=True`.
- ✅ Same interface as every other store — `add_documents` / `similarity_search` / `as_retriever` / `delete` — so swapping in Postgres changed **~3 lines** and the chain from lesson 04 didn't change at all.
- ✅ The vector column is **`vector(N)`**; `N` is fixed by your embedding model, so one collection = one model, and changing models means re-embedding.
- ✅ Match the metric to the model: **`vector_cosine_ops`** (usual default for text), `vector_l2_ops`, `vector_ip_ops` — and the operator class must match your queries or the index is ignored.
- ✅ **No index = exact sequential scan.** Fine at a few thousand rows, fatal at scale. **HNSW** = better recall/latency, slower build, more memory (the production default); **IVFFlat** = fast build, less memory, needs `lists` tuned on representative data.
- ✅ Recall-vs-latency at query time: **`hnsw.ef_search`** and **`ivfflat.probes`**.
- ✅ **Filtering and JOINs are the real win** — `filter={...}` runs in the database, and vectors sitting beside your app tables means permissions, tenancy, and freshness are enforced in one query.
- ✅ Self-check: your table has 5 million rows and queries take 3 seconds — what's almost certainly missing, what SQL fixes it, and which knob do you turn if recall is then too low?

→ Next: **[08 · Choosing a production vector database](08_production_vector_dbs.md)** — Qdrant hands-on, and how to pick between the rest.

## Exercises

1. **Add an HNSW index and read the plan.** Load a few thousand chunks into a `PGVector` collection, run `EXPLAIN ANALYZE` on a nearest-neighbour query, then create the HNSW index and run it again. What changes in the plan, and what changes in the timing?

<details><summary>Solution</summary>

```sql
EXPLAIN ANALYZE
SELECT document FROM langchain_pg_embedding
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector LIMIT 5;
```

Before the index the plan contains a **`Seq Scan on langchain_pg_embedding`** — every row read, every distance computed, then a sort. After:

```sql
CREATE INDEX ON langchain_pg_embedding
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

the plan shows an **`Index Scan using … hnsw`** and the execution time drops sharply — the gap widens with row count, because the sequential scan is O(rows) while the graph search is roughly logarithmic.

Two things to notice beyond the timing. First, the results may now differ slightly from the pre-index run: HNSW is **approximate**, so you traded exactness for speed — if a chunk you expected disappeared, raise `hnsw.ef_search` and try again. Second, if the plan *still* shows a `Seq Scan`, the usual cause is a metric mismatch: an index built with `vector_cosine_ops` cannot serve a query using `<->` (L2). The operator in the query and the operator class in the index have to agree.
</details>

2. **Filter in the query, not afterwards.** You retrieve `k=5` chunks and then drop the ones the current user isn't allowed to see. Why is a `filter={...}` (or a `JOIN`) strictly better than that post-filter — and what's the failure mode of the post-filter version?

<details><summary>Solution</summary>

Post-filtering asks for the 5 nearest chunks **from the whole corpus** and then throws some away, so `k` stops meaning what you think it means. If four of the five belong to another tenant, the LLM gets one chunk of context and answers badly — or the top 5 are all forbidden, you pass empty context, and your RAG app says "I don't know" about a document the user *does* have access to. The bug scales with how selective the filter is: the tighter the permission, the emptier the results, so it looks fine in dev with one tenant and breaks in production.

A pre-filter inverts the order: Postgres restricts the candidate set **first**, then finds the 5 nearest *within it*. You get 5 usable chunks, every time, and the ranking is computed over exactly the rows that were ever eligible.

The security point is the bigger one. Post-filtering means the database happily returned rows the user may not see and application code is trusted to discard them — one forgotten code path and that's a data leak. Expressing it as a `filter` or a `JOIN` against your real `acl` table makes the database the enforcement point, which is the whole argument for keeping vectors in the database you already run.
</details>
