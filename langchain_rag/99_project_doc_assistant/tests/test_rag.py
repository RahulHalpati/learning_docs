"""Tests for the document assistant.

Ingestion/retrieval tests use a deterministic *fake* embedding model, so they run
instantly offline. The two end-to-end RAG tests call the real chat model (OpenAI)
and real local embeddings; they are skipped unless ``OPENAI_API_KEY`` is set.
"""

import os
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_openai import ChatOpenAI

from rag_app.ingest import build_vectorstore, load_documents, split_documents
from rag_app.llm import get_embeddings
from rag_app.rag import (
    build_rag_chain,
    build_rag_chain_with_sources,
    format_docs,
    unique_sources,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

needs_openai = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="set OPENAI_API_KEY to run live-LLM tests"
)


def test_load_documents_reads_all_files():
    docs = load_documents(DATA_DIR)
    sources = {d.metadata["source"] for d in docs}
    assert sources == {"refunds.md", "shipping.md", "company.md"}
    assert all(isinstance(d, Document) and d.page_content for d in docs)


def test_split_documents_produces_chunks():
    docs = load_documents(DATA_DIR)
    chunks = split_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) >= len(docs)            # splitting only adds pieces
    assert all(len(c.page_content) <= 200 for c in chunks)
    # chunks keep their source metadata
    assert all("source" in c.metadata for c in chunks)


def test_format_docs_joins_content():
    docs = [Document(page_content="alpha"), Document(page_content="beta")]
    assert format_docs(docs) == "alpha\n\nbeta"


def test_retriever_returns_k_documents():
    store = build_vectorstore(DATA_DIR, DeterministicFakeEmbedding(size=384))
    hits = store.as_retriever(search_kwargs={"k": 2}).invoke("any question")
    assert len(hits) == 2
    assert all(isinstance(h, Document) for h in hits)


@needs_openai
def test_rag_chain_end_to_end():
    store = build_vectorstore(DATA_DIR, get_embeddings())
    retriever = store.as_retriever(search_kwargs={"k": 2})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = build_rag_chain(retriever, llm)

    answer = chain.invoke("How long are returns?")
    assert "30" in answer          # grounded in refunds.md


def test_unique_sources_dedupes_and_preserves_order():
    docs = [
        Document(page_content="a", metadata={"source": "refunds.md"}),
        Document(page_content="b", metadata={"source": "shipping.md"}),
        Document(page_content="c", metadata={"source": "refunds.md"}),
    ]
    assert unique_sources(docs) == ["refunds.md", "shipping.md"]


@needs_openai
def test_rag_chain_with_sources_returns_answer_and_sources():
    store = build_vectorstore(DATA_DIR, get_embeddings())
    retriever = store.as_retriever(search_kwargs={"k": 2})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = build_rag_chain_with_sources(retriever, llm)

    result = chain.invoke("How long are returns?")
    assert "30" in result["answer"]
    # sources are a de-duplicated list of the real capstone files that were retrieved
    assert isinstance(result["sources"], list) and result["sources"]
    assert set(result["sources"]) <= {"refunds.md", "shipping.md", "company.md"}
