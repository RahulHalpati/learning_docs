"""A verified LangGraph research-assistant agent.

Combines: typed state + reducers, a tool, a self-correction loop,
a checkpointer, and a human-in-the-loop approval gate — on OpenAI
(default) or a local Ollama model.
"""
from .graph import build_graph
from .state import ResearchState

__all__ = ["build_graph", "ResearchState"]
