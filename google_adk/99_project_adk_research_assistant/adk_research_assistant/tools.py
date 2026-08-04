"""Offline, deterministic 'search' tool for the capstone."""

_CORPUS = {
    "langgraph": "LangGraph models agents as state + nodes + edges, with checkpointers for memory.",
    "adk": "Google ADK composes LlmAgents with Sequential/Parallel/Loop workflow agents.",
}


def search_sources(topic: str) -> dict:
    """Return reference material about a topic (offline)."""
    key = next((k for k in _CORPUS if k in topic.lower()), None)
    text = _CORPUS.get(key, f"General reference material about {topic}.")
    return {"sources": text}
