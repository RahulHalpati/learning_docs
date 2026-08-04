"""Offline tests — no network, no API key. Run: pytest -q"""
from langgraph.types import Command

from research_assistant.graph import build_graph


def _initial(topic="LangGraph persistence"):
    return {"messages": [], "topic": topic, "sources": [],
            "draft_report": "", "quality_score": 0.0, "attempt": 0, "status": ""}


def _run_to_pause(app, topic="LangGraph persistence"):
    cfg = {"configurable": {"thread_id": f"t-{topic}"}}
    app.invoke(_initial(topic), cfg)
    return cfg


def test_self_correction_loops_until_quality_bar():
    app = build_graph()
    cfg = _run_to_pause(app)
    state = app.get_state(cfg)
    # Quality bar (0.7) needs 2 sources → the loop must have run research twice.
    assert state.values["attempt"] == 2
    assert state.values["quality_score"] >= 0.7
    assert len(state.values["sources"]) == 2


def test_pauses_for_human_approval():
    app = build_graph()
    cfg = _run_to_pause(app)
    state = app.get_state(cfg)
    assert state.next == ("approval",)          # graph is parked at the HITL gate


def test_approve_finalizes():
    app = build_graph()
    cfg = _run_to_pause(app)
    result = app.invoke(Command(resume="approve"), cfg)
    assert result["status"] == "approved"


def test_reject_is_recorded():
    app = build_graph()
    cfg = _run_to_pause(app)
    result = app.invoke(Command(resume="reject"), cfg)
    assert result["status"] == "rejected"


def test_attempts_are_bounded():
    app = build_graph()
    cfg = _run_to_pause(app, topic="obscure topic with no corpus")
    state = app.get_state(cfg)
    assert state.values["attempt"] <= 3          # MAX_ATTEMPTS safety bound
