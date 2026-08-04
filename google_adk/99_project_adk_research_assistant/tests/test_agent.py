"""Offline tests — no network, no API key (ADK_LLM defaults to fake). Run: pytest -q"""
import asyncio

import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_research_assistant.agent import build_root_agent


async def _run(topic="LangGraph"):
    agent = build_root_agent()
    runner = InMemoryRunner(agent=agent, app_name="t")
    s = await runner.session_service.create_session(app_name="t", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text=f"Research: {topic}")])
    authors = []
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        authors.append(e.author)
    sess = await runner.session_service.get_session(app_name="t", user_id="u", session_id=s.id)
    return authors, dict(sess.state)


def test_pipeline_runs_all_agents():
    authors, _ = asyncio.run(_run())
    for name in ("researcher", "analyst", "writer", "reviewer"):
        assert name in authors, f"{name} did not run"


def test_state_is_threaded_through():
    _, state = asyncio.run(_run())
    # each stage wrote its output_key
    assert "research" in state
    assert "analysis" in state
    assert "report" in state
    assert "review" in state


def test_report_is_produced():
    _, state = asyncio.run(_run())
    assert state["report"].startswith("Report:")
