"""Unit tests for individual agents, using a fake chat model (offline, deterministic)."""

from langchain_core.language_models import GenericFakeChatModel

from proposal_agent import agents
from proposal_agent.profile import load_profile, profile_to_text


def fake(text: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([text]))


def test_analyzer_returns_analysis_and_logs():
    out = agents.analyzer({"job_text": "Need a FastAPI backend"}, llm=fake("stack: FastAPI"))
    assert out["analysis"] == "stack: FastAPI"
    assert out["log"] == ["analyzer"]


def test_matcher_uses_profile():
    profile_text = profile_to_text(load_profile())
    out = agents.matcher(
        {"analysis": "needs a typed API"},
        llm=fake("HIGH fit — best project: Typed Python SDK."),
        profile_text=profile_text,
    )
    assert "HIGH fit" in out["fit"]
    assert out["log"] == ["matcher"]


def test_writer_increments_revisions():
    out = agents.writer(
        {"job_text": "j", "analysis": "a", "fit": "f", "revisions": 0},
        llm=fake("Dear client, here is my proposal..."),
        tone="confident and direct",
    )
    assert out["proposal"].startswith("Dear client")
    assert out["revisions"] == 1
    assert out["log"] == ["writer"]


def test_reviewer_detects_approval():
    approved = agents.reviewer({"job_text": "j", "proposal": "p"}, llm=fake("APPROVED"))
    assert approved["approved"] is True

    needs_work = agents.reviewer({"job_text": "j", "proposal": "p"}, llm=fake("1. Too generic."))
    assert needs_work["approved"] is False
