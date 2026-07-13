"""Node-level tests. All run offline with the fake model — no API key, no network."""

from pathlib import Path

from langchain_core.language_models import GenericFakeChatModel

from faceless_studio import nodes
from faceless_studio.state import VideoState


def _fake(replies):
    return GenericFakeChatModel(messages=iter(replies))


def test_researcher_extracts_hook():
    llm = _fake(["HOOK: This is the hook.\nANGLE: x\nPOINTS:\n- a\n- b"])
    out = nodes.topic_researcher(VideoState(topic="Big-O"), llm=llm)
    assert out["hook"] == "This is the hook."
    assert out["log"] == ["researcher"]


def test_scriptwriter_parses_json_segments():
    reply = ('[{"heading":"Intro","narration":"Hello there.","visual_hint":"card"},'
             '{"heading":"Body","narration":"Some content.","visual_hint":"text"}]')
    out = nodes.script_writer(VideoState(topic="Big-O", hook="hi"), llm=_fake([reply]))
    assert len(out["segments"]) == 2
    assert out["segments"][0]["narration"] == "Hello there."


def test_scriptwriter_falls_back_on_non_json():
    out = nodes.script_writer(
        VideoState(topic="Big-O", hook="the hook"),
        llm=_fake(["- point one\n- point two"]),
    )
    assert len(out["segments"]) >= 1
    assert out["segments"][0]["narration"] == "the hook"


def test_voiceover_and_visuals_produce_files(tmp_path: Path):
    state = VideoState(segments=[
        {"heading": "Intro", "narration": "Hello world.", "visual_hint": "card"},
    ])
    vo = nodes.voiceover(state, workdir=tmp_path)
    assert Path(vo["audio_path"]).exists()
    assert vo["segments"][0]["duration"] > 0

    state["segments"] = vo["segments"]
    vis = nodes.visuals(state, workdir=tmp_path)
    assert Path(vis["image_paths"][0]).exists()


def test_metadata_adds_chapters():
    state = VideoState(
        topic="Big-O",
        segments=[{"heading": "Intro", "narration": "hi", "duration": 3.0}],
    )
    reply = "TITLE: My Title\nDESCRIPTION: A desc.\nTAGS: a, b, c"
    out = nodes.metadata(state, llm=_fake([reply]))
    assert out["title"] == "My Title"
    assert out["tags"] == ["a", "b", "c"]
    assert "Chapters:" in out["description"]
    assert "00:00 Intro" in out["description"]
