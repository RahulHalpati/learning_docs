"""A deterministic, offline 'search' tool over a tiny built-in corpus.

Swap `search_sources` for a real retriever (Tavily, a vector store, etc.)
in production — the graph doesn't change.
"""

# A tiny offline corpus keyed by topic keyword.
_CORPUS = {
    "langgraph": [
        "LangGraph models agents as state + nodes + edges.",
        "Checkpointers give LangGraph memory, resume, and time-travel.",
        "LangGraph supports human-in-the-loop via interrupt().",
    ],
    "rag": [
        "RAG grounds answers in retrieved documents.",
        "RAG reduces hallucinations and enables citations.",
    ],
}
_DEFAULT = ["General reference material about the topic."]


def search_sources(topic: str, attempt: int) -> list[str]:
    """Return one new source for the topic on each attempt (deterministic).

    `attempt` (1-based) selects which source to return, so repeated calls in a
    self-correction loop surface *different* material instead of duplicates.
    """
    key = next((k for k in _CORPUS if k in topic.lower()), None)
    pool = _CORPUS.get(key, _DEFAULT)
    return [pool[(attempt - 1) % len(pool)]]
