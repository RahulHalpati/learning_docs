# 08 · Choosing a production vector database

> **Level:** Intermediate · **Prerequisites:** [07 · pgvector on Postgres](07_pgvector_postgres.md)
> **Time:** ~35 min · **Verified:** 2026-08-24 (langchain-qdrant · Qdrant 1.x · market landscape as of 2026-08)

## Why this matters

This course has used three stores so far: `InMemoryVectorStore` and FAISS because they need zero setup ([02 · Vector stores](02_vector_stores.md)), and pgvector because it's the sane production default ([07 · pgvector on Postgres](07_pgvector_postgres.md)). You may have noticed that swapping between them changed **almost nothing** downstream — `add_documents`, `similarity_search`, `as_retriever` are the same three calls every time.

That's the thesis of this lesson, so let's state it plainly:

> **The vector store is the most swappable part of a RAG system.** The retriever interface is identical across engines, so the skill worth having is **choosing and justifying** a store — not memorising one vendor's SDK.

Which is convenient, because vendors change and the judgement doesn't. What an interview or a design review actually asks you is: *why this store, and what would make you move?* This lesson gives you the landscape, one hands-on dedicated engine (**Qdrant**), and the **ANN indexing vocabulary** that job specs ask for by name — because in postings at AI-native companies, **Pinecone, Weaviate, and Qdrant are the most commonly requested stores by name, and being able to explain ANN indexing (HNSW, IVF, and FAISS-style flat indexing) is frequently a stated requirement.** RAG is the primary use case driving vector-database adoption in 2026, so this is a well-trodden conversation with well-known right answers.

---

## The four categories

By mid-2026 the market has crystallised into four groups. Knowing which group a name belongs to is most of the analysis:

| Category | Examples | What it's for | The trade you're making |
|---|---|---|---|
| **"Use what you already have" extensions** | **pgvector** (Postgres), Redis, MongoDB Atlas Vector Search | vectors inside a database you already run, back up, and monitor | one system, transactional joins with your real data — at the cost of the last mile of pure-vector performance |
| **Self-hosted open-source engines** | **Qdrant**, **Milvus**, **Weaviate OSS** | purpose-built vector search you operate yourself | best filtering/scale/features and no vendor lock-in — you own the ops, upgrades, and 3am pages |
| **Fully managed SaaS** | **Pinecone**, Weaviate Cloud, **Zilliz Cloud** (managed Milvus) | someone else runs it, with SLAs and compliance certifications | zero ops and predictable support — for per-vector cost, and your corpus living in their tenancy |
| **Embedded libraries** | **Chroma**, **LanceDB**, FAISS | vectors in-process or in a local file, no server at all | trivial setup and no network hop — no concurrent writers, no independent scaling, limited operational surface |

Note what's *not* a category: "the fastest one." Every engine in the middle two rows is fast enough that your embedding model and your LLM dominate the latency budget.

---

## The decision guide

The one number that matters most is **corpus size**, and the honest headline of 2026 is that the boring answer got better:

**pgvector became the default for production RAG.** It comfortably absorbs workloads up to roughly **50M vectors**, and keeping vectors in the Postgres you already operate cuts total cost of ownership by around **40–60%** versus standing up a dedicated vector service — because the saving isn't the licence, it's the backups, monitoring, on-call, access control, and migrations you *don't* duplicate.

So start there, and move only when you can name the bottleneck:

| Situation | Store | Why |
|---|---|---|
| Under ~50M vectors and you already run Postgres | **pgvector** | one system to operate; joins vectors against your real tables |
| Outgrew it; pure-vector scale, heavy **metadata filtering**, multi-tenant isolation | **Qdrant** | Rust engine, very strong payload filtering — filters applied *with* the search, not as a post-filter |
| You want **hybrid** (keyword + vector) built in | **Weaviate** | native hybrid search and pluggable embedding modules — see [Better retrieval](../04_advanced_rag/01_better_retrieval.md) for what hybrid buys you |
| Zero ops, enterprise SLA, compliance certifications | **Pinecone** | fully managed; you write no infrastructure code |
| Massive self-hosted scale (billions), distributed | **Milvus** / **Zilliz Cloud** | built for horizontal scale-out; Zilliz is the managed flavour |
| Data residency, on-prem, or air-gapped requirements | **Milvus / Weaviate / Qdrant** | self-hostable open source — the data never leaves your network |
| Prototyping, or embedded in the application itself | **Chroma / LanceDB / FAISS** | no server to run; a file or a process, not a dependency |

> **The rule: don't migrate without a named bottleneck.** "Pinecone is faster" is not a bottleneck. These are: *p95 retrieval latency is 400ms and our budget is 100ms*; *filtered queries scan the whole table because the filter isn't index-aware*; *we're at 80M vectors and the index no longer fits in RAM*; *we need SOC 2 and nobody here wants to be on call for a database*. Each of those names a measurement, a threshold, and a store that fixes it. Without one, a migration is re-embedding your entire corpus to move a problem you haven't found yet.

And one axis this table deliberately doesn't cover: if your users' questions are about **relationships between entities** rather than similar prose, no vector store is the answer — that's [GraphRAG](../04_advanced_rag/05_graph_rag.md), a different data model entirely.

---

## Hands-on: Qdrant

Qdrant is the pick worth having actually run, because it's the common "outgrew pgvector, want pure-vector" answer and it's a single container:

```bash
uv add langchain-qdrant   # pulls in qdrant-client

# 6333 = HTTP/REST + web dashboard, 6334 = gRPC
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

export QDRANT_URL='http://localhost:6333'
```

Then open **`http://localhost:6333/dashboard`** — Qdrant ships a UI where you can browse collections and inspect individual points with their payloads. Genuinely useful while learning: it's the first time in this course you can *see* your vectors and metadata as stored rows.

Create the collection and index the same documents:

```python
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

COLLECTION = "docs"
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
client = QdrantClient(url=os.environ["QDRANT_URL"])   # URL from env, never hardcoded

# size must equal your embedding model's dimension (MiniLM = 384) and can't change later
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

store = QdrantVectorStore(client=client, collection_name=COLLECTION, embedding=embeddings)

docs: list[Document] = [
    Document(page_content="Refunds are allowed within 30 days with a receipt.", metadata={"source": "refunds"}),
    Document(page_content="Standard shipping is free over $50.", metadata={"source": "shipping"}),
    Document(page_content="Express shipping costs $14.99 and takes 1-2 days.", metadata={"source": "shipping"}),
]
store.add_documents(docs)
print(store.similarity_search("how long do I have to return something?", k=1)[0].page_content)
```

Nothing new since lesson 02 except the two lines that name a server. If you'd rather not manage the collection yourself, `QdrantVectorStore.from_documents(docs, embedding=embeddings, url=os.environ["QDRANT_URL"], collection_name=COLLECTION)` creates it and ingests in one call — handy for scripts, though in production you generally want the collection created deliberately (dimension and distance are not things to have inferred by accident).

### Filtering on metadata

This is Qdrant's headline feature. Metadata is stored as a **payload** on each point, and filters are evaluated as part of the search rather than by throwing away results afterwards — which is why filtered queries stay fast instead of degrading as the filter gets more selective:

```python
from qdrant_client import models

# The integration passes a native Qdrant Filter straight through to the engine.
# With default payload keys, LangChain metadata lands under "metadata",
# so a metadata key called "source" is addressed as "metadata.source".
only_shipping = models.Filter(
    must=[models.FieldCondition(key="metadata.source", match=models.MatchValue(value="shipping"))]
)

for doc, score in store.similarity_search_with_score("what does it cost?", k=2, filter=only_shipping):
    print(round(score, 3), doc.metadata["source"], doc.page_content)
```

The refunds document can't come back no matter how well it scores. Swap `"shipping"` for a `tenant_id` and you have the standard multi-tenant pattern: one collection, hard per-tenant isolation at query time. (Qdrant also supports **sparse + dense hybrid** retrieval in one collection — the same idea as [Better retrieval](../04_advanced_rag/01_better_retrieval.md), pushed down into the engine. Worth knowing it exists; the dense path above is what you'll use first.)

### Same interface, same chain

```python
retriever = store.as_retriever(search_kwargs={"k": 2})

# Byte-for-byte the chain from lesson 04 — only the store underneath changed.
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt | llm | StrOutputParser()
)
```

That's the whole point: a production engine, a dashboard, payload filtering — and the chain didn't notice.

---

## ANN indexing you must be able to explain

"Approximate nearest neighbour" is how a store answers in milliseconds what brute force answers in seconds. Three families cover essentially every engine, and these are the words job specs use:

| Index | How it works | Build cost | Memory | Recall / latency | Typical knobs |
|---|---|---|---|---|---|
| **Flat / brute-force** | compare the query to *every* stored vector; no index at all | none | just the vectors | **exact** (100% recall), latency grows linearly with corpus | none — only `k` |
| **IVF / IVFFlat** | cluster vectors into *lists* (k-means centroids); at query time probe only the nearest few lists | fast | low | good, tunable; misses neighbours sitting just over a cluster border | number of `lists` (partitions), `probes` (lists searched per query) |
| **HNSW** | a multi-layer "navigable small world" graph; greedily hop from a coarse top layer down to near neighbours | slow | high | **best recall at low latency** — the default in most engines | `M` (edges per node), `ef_construction` (build quality), `ef_search` (candidates per query) |

Two sentences carry the whole topic:

1. **Every ANN index trades recall for speed** — it looks at a fraction of your vectors, so it can miss a true nearest neighbour.
2. **The knobs let you choose where on that curve you sit.** Raise `ef_search` (or `probes`) for better recall and more latency; lower it for the reverse. There is no setting that gives you both, and the right point is the one your evaluation set says is good enough.

These concepts are **engine-independent**, which is exactly why they're worth learning instead of an SDK. pgvector exposes `ivfflat` and `hnsw` indexes; Qdrant is HNSW-based; Weaviate and Milvus default to HNSW; FAISS ships flat, IVF, and HNSW variants you compose yourself. Same three ideas, different spelling — and "we're on HNSW with `ef_search` tuned against our eval set" is a sentence that ends a lot of interview questions well.

> Small corpora deserve a mention: under a few tens of thousands of vectors, **flat is often the correct choice**. It's exact, needs no tuning, and the linear scan is already fast. Reaching for an approximate index on 5,000 chunks buys you a recall problem you didn't have.

---

## Migration is mostly re-embedding

Be honest about what switching stores actually costs, because it's not what people fear:

The **code** change is roughly three lines — a different import, a different constructor, the same `as_retriever()`. Everything downstream (prompt, chain, evaluation harness) is untouched. That's the part that's nearly free.

The **real** costs are elsewhere: re-embedding your whole corpus (time and, with a hosted embedding model, money), building the index on the new engine, re-tuning filters and index parameters, and re-running your evaluation set to prove retrieval didn't get worse. On a few thousand documents that's an afternoon. On tens of millions of chunks it's a project with a budget line.

Which cuts both ways. The cheap moment to choose deliberately is **before** you have 50M vectors — but if you chose wrong, you're facing a re-ingest, not a rewrite. So pick the boring default, keep your ingestion pipeline re-runnable, and spend your worry on chunking and retrieval quality, which is where the answers actually get better.

---

## Recap & next

- ✅ The store is the **most swappable** component in RAG — same `add_documents` / `similarity_search` / `as_retriever` everywhere. The skill is **choosing and justifying**, not one SDK.
- ✅ Four categories: **extensions** (pgvector, Redis, Mongo Atlas), **self-hosted engines** (Qdrant, Milvus, Weaviate OSS), **managed SaaS** (Pinecone, Weaviate Cloud, Zilliz), **embedded libraries** (Chroma, LanceDB, FAISS).
- ✅ **pgvector is the 2026 default**: fine to ~50M vectors, ~40–60% lower TCO than adding a dedicated service. Move only with a **named bottleneck**.
- ✅ Then: **Qdrant** for filtering/pure-vector scale, **Weaviate** for built-in hybrid, **Pinecone** for zero-ops + SLAs, **Milvus/Zilliz** for massive self-hosted scale, self-hosted anything for data-residency/air-gapped rules.
- ✅ **Qdrant hands-on**: one container (6333 HTTP + dashboard, 6334 gRPC), `langchain-qdrant`'s `QdrantVectorStore` over a `QdrantClient`, payload filters evaluated inside the search, `as_retriever()` into the unchanged lesson-04 chain.
- ✅ **ANN vocabulary**: flat (exact, small data), IVF/IVFFlat (`lists`/`probes`), HNSW (`M`/`ef_search`, best recall-latency). Every index trades **recall for speed**; the knobs pick your point on the curve. Engine-independent.
- ✅ Migration is ~3 lines of code plus **re-embedding** — the corpus, index build, and re-tuning are the real bill.
- ✅ Self-check: name the bottleneck that would move you off pgvector, the store you'd move to, and the index type you'd use there — and say what you'd measure before *and* after.

→ Next: **[Section 04 · Advanced RAG](../04_advanced_rag/README.md)** — hybrid retrieval, conversational RAG, evaluation, and serving.

## Exercises

1. **Pick a store for three real situations, and justify it.** (a) A 20k-document internal wiki at a company already running Postgres. (b) A 200M-vector multi-tenant product where tenants must never see each other's data. (c) A two-person startup that wants to launch without hiring anyone to run a database.

<details><summary>Solution</summary>

**(a) pgvector.** 20k documents is a handful of hundred thousand chunks — three orders of magnitude below where pgvector strains. Postgres is already backed up, monitored, and access-controlled, so the vector index inherits all of that for free, and you can join retrieval results against real tables (permissions, authorship, timestamps). Adding a dedicated engine here buys performance you cannot measure and doubles the operational surface.

**(b) Qdrant (or Milvus/Zilliz at the top end).** Two things drive this: 200M vectors is past pgvector's comfortable range, and *hard metadata isolation on every query* is precisely the filtered-search workload dedicated engines are built for — filters applied inside the search rather than as a post-filter, so a tenant filter doesn't degrade latency. Qdrant if you're happy self-hosting one strong engine; Milvus/Zilliz if you also need distributed scale-out and are heading well beyond this. Whichever you pick, the tenant filter must be enforced server-side in the query, never in application code after results come back.

**(c) Managed — Pinecone (or Weaviate Cloud / Zilliz Cloud), or an embedded store pre-launch.** With two engineers, ops time is the scarcest resource, and "zero ops with an SLA" is worth real money. Honest alternative: if you haven't launched, **Chroma or pgvector on a managed Postgres** may be cheaper still and gets you to users faster — the deciding question is whether you're already running Postgres for the rest of the product. Note that *all three* answers are defensible only with the reasoning attached; the store name alone isn't the answer.
</details>

2. **Push back on a bad migration.** A colleague says: *"we should switch from pgvector to Pinecone because it's faster."* Explain why that isn't yet a decision, and what they'd have to measure first.

<details><summary>Solution</summary>

It isn't a decision because **"faster" names no number, no threshold, and no cause.** Faster at what — p50 or p95? Under what corpus size, filter selectivity, and concurrency? And faster than *what target*: if retrieval is 40ms inside a pipeline where the embedding call is 80ms and the LLM is 3s, halving retrieval is invisible to users. Also worth naming: a benchmark of two different engines is usually also a benchmark of two different index configurations, so "faster" may just mean "someone else tuned theirs."

What to measure first:

- **p50/p95 retrieval latency in production**, separated from embedding and generation time, and the **target** it's supposed to hit.
- **Where the time actually goes** — often it's a missing or wrong index (`ivfflat` where `hnsw` belongs), an untuned `ef_search`/`probes`, a filter that isn't index-aware, or an index no longer fitting in RAM. Every one of those is fixable *without* migrating.
- **Recall against a labelled eval set** ([Better retrieval](../04_advanced_rag/01_better_retrieval.md) and the evaluation module), because a "faster" configuration that quietly returns worse chunks is a downgrade dressed as a win.
- **Corpus growth curve** — the legitimate version of this argument is "we'll cross 50M vectors in two quarters," which is a forecast, not a speed claim.
- **The full cost of moving**: re-embedding spend and time, index build, filter re-tuning, plus the recurring per-vector bill.

The reframe to offer: *"what's our latency target, what's our current p95, and what's the cheapest change that closes the gap?"* If tuning the existing index closes it, you're done for free. If it doesn't, you now have a named bottleneck — and a migration you can defend.
</details>
