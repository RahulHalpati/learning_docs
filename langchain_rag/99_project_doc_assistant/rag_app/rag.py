"""Assemble the RAG chain: retrieve relevant chunks, then answer from them.

This is the "query" half of RAG. It's a plain LCEL chain — read the `|` pipes
left to right: build the inputs, fill the prompt, call the model, parse to text.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableParallel, RunnablePassthrough
from langchain_core.vectorstores import VectorStoreRetriever

RAG_PROMPT = ChatPromptTemplate.from_template(
    "You are a helpful assistant for the Acme company. "
    "Answer the question using ONLY the context below. "
    "If the answer is not in the context, say you don't know.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def format_docs(docs: list[Document]) -> str:
    """Join retrieved chunks into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def unique_sources(docs: list[Document]) -> list[str]:
    """The distinct source files the retrieved chunks came from, in first-seen order."""
    seen: list[str] = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        if source not in seen:
            seen.append(source)
    return seen


def build_rag_chain(retriever: VectorStoreRetriever, llm: BaseChatModel) -> Runnable:
    """Wire retriever → prompt → llm → text into one runnable chain.

    Call it with a question string: ``chain.invoke("How long are returns?")``.
    """
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )


def build_rag_chain_with_sources(
    retriever: VectorStoreRetriever, llm: BaseChatModel
) -> Runnable:
    """Like ``build_rag_chain`` but returns ``{"answer": str, "sources": [...]}``.

    Retrieval runs **once**; the same chunks feed both the answer and the list of
    source files, so the assistant can *cite where each answer came from*.
    Call it with a question string: ``chain.invoke("How long are returns?")``.
    """
    generate = RAG_PROMPT | llm | StrOutputParser()
    return RunnableParallel(
        docs=retriever, question=RunnablePassthrough()
    ) | RunnableParallel(
        answer=lambda x: generate.invoke(
            {"context": format_docs(x["docs"]), "question": x["question"]}
        ),
        sources=lambda x: unique_sources(x["docs"]),
    )
