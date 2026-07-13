"""Command-line entry point: ask the document assistant a question.

    python -m rag_app.cli "How long do I have to return something?"

With no question argument it runs a few demo questions.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .ingest import build_or_load_faiss, build_vectorstore
from .llm import get_chat_model, get_embeddings
from .rag import build_rag_chain_with_sources

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEMO_QUESTIONS = [
    "How long do I have to return something?",
    "Is shipping free?",
    "Where is the company based?",
    "What is the CEO's salary?",  # not in the docs — should say it doesn't know
]


def main(argv: list[str]) -> None:
    embeddings = get_embeddings()
    llm = get_chat_model()

    # Set DOC_ASSISTANT_INDEX_DIR to persist the index to disk (embed once, then reuse).
    index_dir = os.environ.get("DOC_ASSISTANT_INDEX_DIR")
    if index_dir:
        vectorstore = build_or_load_faiss(DATA_DIR, embeddings, index_dir)
    else:
        vectorstore = build_vectorstore(DATA_DIR, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    chain = build_rag_chain_with_sources(retriever, llm)

    questions = [" ".join(argv)] if argv else DEMO_QUESTIONS
    for question in questions:
        result = chain.invoke(question)
        print(f"\nQ: {question}")
        print(f"A: {result['answer']}")
        print(f"Sources: {', '.join(result['sources'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
