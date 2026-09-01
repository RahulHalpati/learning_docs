# Section 03 · RAG fundamentals

> **Prerequisites:** [Section 02 · LangChain core](../02_langchain_core/README.md).
> **Time:** ~8–11 hours.

This is the heart of the course. You'll build RAG from the ground up: turn text into **embeddings**, store and search them in a **vector store**, **load and split** your documents into chunks, then assemble the **RAG chain** that retrieves relevant chunks and answers from them — with real, verified output at each step. By the end you'll have the exact pipeline the capstone uses, and you'll understand the trade-offs in **retrieval strategies**.

> Everything here runs **offline with a free local embedding model**. Answers shown were produced with a local LLM; the retrieval steps need no LLM at all.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Embeddings](01_embeddings.md) | How does a computer measure meaning/similarity of text? |
| 02 | [Vector stores](02_vector_stores.md) | How do I store and search embeddings? |
| 03 | [Loaders & splitters](03_loaders_and_splitters.md) | How do I turn my files into searchable chunks? |
| 04 | [Build a RAG chain](04_build_a_rag_chain.md) | How do I connect retrieval + LLM into an answer? |
| 05 | [Retrieval strategies](05_retrieval_strategies.md) | How do I get the *right* chunks, not just some chunks? |
| 06 | [RAG over web pages](06_web_sources.md) | How do I ground answers in a website, not just local files?  ·  ⚪ *optional / appendix* |
| 07 | [pgvector on Postgres](07_pgvector_postgres.md) | How do I run production RAG on the database I already have? |
| 08 | [Choosing a production vector DB](08_production_vector_dbs.md) | Qdrant, Pinecone, Weaviate, Milvus — which, and how do I justify it?  ·  ⚪ *optional / appendix* |

## What you'll be able to do after this section

- Explain embeddings and similarity, and compute them with a local model.
- Index documents in a vector store and search by meaning (with scores).
- Load files and split them into well-sized, overlapping chunks.
- Build a complete RAG chain in LCEL that answers grounded in your documents.
- Choose between similarity, MMR, and score-filtered retrieval.
- Scrape web pages into the same pipeline and clean the HTML noise.

→ Start: **[01 · Embeddings](01_embeddings.md)**
