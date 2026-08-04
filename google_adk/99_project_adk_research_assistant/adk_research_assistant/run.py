"""CLI entry point for the ADK research assistant.

Usage:  python -m adk_research_assistant.run "LangGraph"
Offline by default (ADK_LLM=fake); set ADK_LLM=ollama for a local model.
"""
import asyncio
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import build_root_agent


async def run(topic: str) -> None:
    agent = build_root_agent()
    runner = InMemoryRunner(agent=agent, app_name="research")
    session = await runner.session_service.create_session(app_name="research", user_id="u1")
    msg = types.Content(role="user", parts=[types.Part(text=f"Research: {topic}")])

    async for event in runner.run_async(user_id="u1", session_id=session.id, new_message=msg):
        if event.content and event.content.parts and event.content.parts[0].text:
            print(f"· {event.author}: {event.content.parts[0].text}")

    final = await runner.session_service.get_session(
        app_name="research", user_id="u1", session_id=session.id)
    print("\nFinal report:", final.state.get("report"))


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "LangGraph"
    asyncio.run(run(topic))
