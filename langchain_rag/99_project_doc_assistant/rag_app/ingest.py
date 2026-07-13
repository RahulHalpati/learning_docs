"""Load the documents, split them into chunks, and index them for retrieval.

This is the "ingestion" half of RAG — it runs once, before any questions, and
turns a folder of files into a searchable vector store.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents(data_dir: str | Path) -> list[Document]:
    """Read every .md/.txt file in ``data_dir`` into a Document with a source tag."""
    data_dir = Path(data_dir)
    docs: list[Document] = []
    for path in sorted(data_dir.glob("*")):
        if path.suffix.lower() in {".md", ".txt"}:
            text = path.read_text(encoding="utf-8")
            docs.append(Document(page_content=text, metadata={"source": path.name}))
    return docs


def split_documents(docs: list[Document], *, chunk_size: int = 500, chunk_overlap: int = 50) -> list[Document]:
    """Break long documents into overlapping chunks that fit a retrieval window."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)


def build_vectorstore(data_dir: str | Path, embeddings: Embeddings) -> InMemoryVectorStore:
    """Load → split → embed → index. Returns a ready-to-query vector store.

    Uses an in-memory store, so it re-embeds every run. For a persistent index that
    survives restarts, see ``build_or_load_faiss``.
    """
    chunks = split_documents(load_documents(data_dir))
    store = InMemoryVectorStore(embeddings)
    store.add_documents(chunks)
    return store


def build_or_load_faiss(data_dir: str | Path, embeddings: Embeddings, index_dir: str | Path):
    """Persistent alternative: load a saved FAISS index, or build it once and save it.

    The first run embeds the documents and writes the index to ``index_dir``; every
    later run just loads it from disk — no re-embedding. FAISS exposes the same
    ``as_retriever`` interface as the in-memory store, so the rest of the app is
    unchanged. Needs ``pip install faiss-cpu`` (see requirements.txt).
    """
    from langchain_community.vectorstores import FAISS  # optional dep, imported lazily

    index_path = Path(index_dir)
    if index_path.exists():
        # allow_dangerous_deserialization: FAISS indexes use pickle; only load your own.
        return FAISS.load_local(
            str(index_path), embeddings, allow_dangerous_deserialization=True
        )
    chunks = split_documents(load_documents(data_dir))
    store = FAISS.from_documents(chunks, embeddings)
    store.save_local(str(index_path))
    return store
