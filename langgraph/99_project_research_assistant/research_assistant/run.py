"""CLI entry point for the research assistant.

Usage:
    python -m research_assistant.run "LangGraph persistence"

Uses OpenAI by default (needs OPENAI_API_KEY). Set LANGGRAPH_LLM=ollama for a local model.
The graph pauses for approval; this CLI auto-approves and prints the outcome.
"""
import sys

from langgraph.types import Command

from .graph import build_graph


def main(topic: str) -> None:
    app = build_graph()
    config = {"configurable": {"thread_id": "cli-session"}}

    initial = {
        "messages": [], "topic": topic, "sources": [],
        "draft_report": "", "quality_score": 0.0, "attempt": 0, "status": "",
    }

    # Stream until the graph pauses at the approval interrupt.
    for step in app.stream(initial, config, stream_mode="updates"):
        node = list(step)[0]
        if node != "__interrupt__":
            print(f"· {node}")

    snapshot = app.get_state(config)
    if snapshot.next:  # paused at approval
        payload = snapshot.tasks[0].interrupts[0].value
        print(f"\nDRAFT (quality {payload['quality_score']:.2f}):\n  {payload['report']}")
        print("\n[auto-approving]")
        result = app.invoke(Command(resume="approve"), config)
        print(f"\nStatus: {result['status']}")
        print(f"Sources gathered: {len(result['sources'])} over {result['attempt']} attempt(s)")


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "LangGraph persistence"
    main(topic)
