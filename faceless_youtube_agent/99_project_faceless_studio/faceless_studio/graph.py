"""Wire the six nodes into a LangGraph pipeline.

    START → researcher → scriptwriter → voiceover → visuals → assembler → metadata → END

`build_graph` binds each node to its dependencies (the LLM, the working dir) with
functools.partial so every node is invoked with just `state`. A MemorySaver
checkpointer is attached so you can pause before an expensive node (voiceover) for
a human review gate — see 03_assembling_the_graph in the course.
"""

from __future__ import annotations

import re
from functools import partial
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes
from .providers import get_chat_model
from .state import VideoState


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "video"


def build_graph(
    llm: BaseChatModel | None = None,
    *,
    workdir: str | Path = "out",
    interrupt_before: list[str] | None = None,
):
    """Assemble and compile the video pipeline.

    Pass a specific `llm` (e.g. a fake model in tests); otherwise the configured
    provider is used. `interrupt_before=["voiceover"]` pauses the run after the
    script is written so a human can approve it before any media is rendered.
    """
    llm = llm or get_chat_model()
    workdir = Path(workdir)

    builder = StateGraph(VideoState)
    builder.add_node("researcher", partial(nodes.topic_researcher, llm=llm))
    builder.add_node("scriptwriter", partial(nodes.script_writer, llm=llm))
    builder.add_node("voiceover", partial(nodes.voiceover, workdir=workdir))
    builder.add_node("visuals", partial(nodes.visuals, workdir=workdir))
    builder.add_node("assembler", partial(nodes.assembler, workdir=workdir))
    builder.add_node("metadata", partial(nodes.metadata, llm=llm))

    builder.add_edge(START, "researcher")
    builder.add_edge("researcher", "scriptwriter")
    builder.add_edge("scriptwriter", "voiceover")
    builder.add_edge("voiceover", "visuals")
    builder.add_edge("visuals", "assembler")
    builder.add_edge("assembler", "metadata")
    builder.add_edge("metadata", END)

    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=interrupt_before or [],
    )


def produce_video(
    topic: str,
    *,
    niche: str = "short educational explainers",
    workdir: str | Path = "out",
    thread_id: str = "default",
    **kwargs,
) -> dict:
    """Build the graph and run one topic end to end, returning the final state.

    Each run gets its own subfolder under `workdir` so files never collide.
    """
    run_dir = Path(workdir) / _slug(topic)
    graph = build_graph(workdir=run_dir, **kwargs)
    return graph.invoke(
        {"topic": topic, "niche": niche},
        config={"configurable": {"thread_id": thread_id}},
    )
