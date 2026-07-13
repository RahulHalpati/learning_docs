"""End-to-end graph test — runs the whole pipeline offline and checks the .mp4."""

from pathlib import Path

from langchain_core.language_models import GenericFakeChatModel

from faceless_studio.graph import build_graph
from faceless_studio.providers import _FAKE_REPLIES
from faceless_studio.state import VideoState


def test_full_pipeline_produces_mp4(tmp_path: Path):
    llm = GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
    graph = build_graph(llm, workdir=tmp_path)

    final = graph.invoke(
        VideoState(topic="Big-O notation", niche="tech explainers"),
        config={"configurable": {"thread_id": "t1"}},
    )

    # every node ran, in order
    assert final["log"] == [
        "researcher", "scriptwriter", "voiceover", "visuals", "assembler", "metadata"
    ]
    # a real video file exists and is non-trivial
    video = Path(final["video_path"])
    assert video.exists() and video.stat().st_size > 1000
    assert final["title"]
    assert final["tags"]


def test_interrupt_before_voiceover_pauses(tmp_path: Path):
    """The human-review gate: the run stops before any media is rendered."""
    llm = GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
    graph = build_graph(llm, workdir=tmp_path, interrupt_before=["voiceover"])
    config = {"configurable": {"thread_id": "gate"}}

    graph.invoke(VideoState(topic="Big-O", niche="tech"), config=config)
    snapshot = graph.get_state(config)

    # paused with the script ready but no video yet
    assert snapshot.next == ("voiceover",)
    assert snapshot.values["segments"]
    assert "video_path" not in snapshot.values
