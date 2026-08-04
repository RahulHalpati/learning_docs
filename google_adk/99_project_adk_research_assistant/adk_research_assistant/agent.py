"""The ADK research-assistant capstone.

A SequentialAgent pipeline — researcher → analyst → writer — with a LoopAgent
reviewer, function tool, and a safety callback. Mirrors the LangGraph capstone
(../../../langgraph/99_project_research_assistant/) for side-by-side comparison.

Runs offline: ADK_LLM=fake (default) uses deterministic fake models; ADK_LLM=ollama
uses a local model. Exposes `root_agent` for the `adk` CLIs.
"""
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent

from .models import get_model
from .tools import search_sources
from .callbacks import safety_guard


def build_root_agent() -> SequentialAgent:
    researcher = LlmAgent(
        name="researcher",
        model=get_model(responses=["Gathered sources on the topic."]),
        instruction="Research the topic using the search_sources tool.",
        description="Finds source material about a topic.",
        tools=[search_sources],
        output_key="research",
        before_model_callback=safety_guard,
    )

    analyst = LlmAgent(
        name="analyst",
        model=get_model(responses=["Key insight: the topic centers on stateful agents."]),
        instruction="Analyze the findings: {research}",
        description="Extracts insights from research.",
        output_key="analysis",
    )

    writer = LlmAgent(
        name="writer",
        model=get_model(responses=["Report: stateful agents, grounded in the research."]),
        instruction="Write a report from analysis: {analysis}",
        description="Writes the final report.",
        output_key="report",
    )

    # A reviewer loop: in a real build the critic escalates when quality passes.
    reviewer = LlmAgent(
        name="reviewer",
        model=get_model(responses=["Looks good."]),
        instruction="Review the report: {report}",
        description="Reviews the report for quality.",
        output_key="review",
    )
    review_loop = LoopAgent(name="review_loop", sub_agents=[reviewer], max_iterations=1)

    return SequentialAgent(
        name="research_assistant",
        sub_agents=[researcher, analyst, writer, review_loop],
    )


root_agent = build_root_agent()
