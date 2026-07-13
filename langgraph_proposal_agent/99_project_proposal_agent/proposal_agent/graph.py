"""Wire the four agents into a LangGraph state machine with a review→revise loop.

    START → analyzer → matcher → writer → reviewer ──approved/maxed──→ END
                                             └────── needs work ──────→ writer
"""

from __future__ import annotations

from functools import partial
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import agents
from .profile import load_profile, profile_to_text
from .providers import get_chat_model
from .state import ProposalState


def route_after_review(state: ProposalState) -> Literal["writer", "__end__"]:
    """Loop back to the writer unless the proposal is approved or we've hit the cap."""
    if state.get("approved") or state.get("revisions", 0) >= state.get("max_revisions", 2):
        return END
    return "writer"


def build_graph(llm: BaseChatModel | None = None, profile: dict | None = None):
    """Assemble and compile the proposal graph.

    Pass a specific ``llm`` (e.g. a fake model in tests); otherwise the configured
    provider is used. ``profile`` defaults to the bundled profile.yaml.
    """
    llm = llm or get_chat_model()
    profile = profile or load_profile()
    profile_text = profile_to_text(profile)
    tone = profile.get("tone", "confident and direct")

    builder = StateGraph(ProposalState)
    # bind the per-agent dependencies so each node is called with just `state`
    builder.add_node("analyzer", partial(agents.analyzer, llm=llm))
    builder.add_node("matcher", partial(agents.matcher, llm=llm, profile_text=profile_text))
    builder.add_node("writer", partial(agents.writer, llm=llm, tone=tone))
    builder.add_node("reviewer", partial(agents.reviewer, llm=llm))

    builder.add_edge(START, "analyzer")
    builder.add_edge("analyzer", "matcher")
    builder.add_edge("matcher", "writer")
    builder.add_edge("writer", "reviewer")
    builder.add_conditional_edges(
        "reviewer", route_after_review, {"writer": "writer", END: END}
    )

    return builder.compile(checkpointer=MemorySaver())


def generate_proposal(job_text: str, *, max_revisions: int = 2, thread_id: str = "default", **kwargs) -> dict:
    """Convenience: build the graph and run one job end to end, returning final state."""
    graph = build_graph(**kwargs)
    return graph.invoke(
        {"job_text": job_text, "revisions": 0, "max_revisions": max_revisions},
        config={"configurable": {"thread_id": thread_id}},
    )
