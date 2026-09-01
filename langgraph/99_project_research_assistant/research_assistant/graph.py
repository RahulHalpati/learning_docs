"""The research-assistant graph.

Flow:  research → write → evaluate ──(score < 0.7 and attempt < 3)──▶ research
                                   └─(good enough)─▶ approval (HITL) ─▶ finalize ─▶ END

Every concept from the course appears: typed state + reducers, a tool, a
conditional self-correction loop, a checkpointer, and a human approval gate.
"""
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from langchain_core.messages import AIMessage

from .state import ResearchState
from .providers import get_model
from .tools import search_sources

MAX_ATTEMPTS = 3
QUALITY_BAR = 0.7


def research(state: ResearchState) -> dict:
    attempt = state.get("attempt", 0) + 1
    found = search_sources(state["topic"], attempt)
    return {"sources": found, "attempt": attempt, "status": "researching"}


def write(state: ResearchState) -> dict:
    prompt = (f"Write a two-sentence report on '{state['topic']}' using ONLY these sources:\n"
              + "\n".join(f"- {s}" for s in state["sources"]))
    report = get_model().invoke(prompt).content
    return {"draft_report": report, "status": "writing",
            "messages": [AIMessage(content="Drafted a report.")]}


def evaluate(state: ResearchState) -> dict:
    # Deterministic proxy for an LLM-judge: quality grows with how many sources we gathered.
    score = min(len(state["sources"]) / 2, 1.0)
    return {"quality_score": score, "status": "reviewing"}


def quality_gate(state: ResearchState) -> Literal["research", "approval"]:
    if state["quality_score"] >= QUALITY_BAR or state["attempt"] >= MAX_ATTEMPTS:
        return "approval"
    return "research"


def approval(state: ResearchState) -> dict:
    decision = interrupt({                       # PAUSE for a human
        "report": state["draft_report"],
        "quality_score": state["quality_score"],
        "question": "Approve this report?",
    })
    return {"status": "approved" if decision == "approve" else "rejected"}


def finalize(state: ResearchState) -> dict:
    return {"messages": [AIMessage(content=f"Report {state['status']}.")]}


def build_graph(checkpointer=None):
    """Build and compile the research-assistant graph.

    Pass a checkpointer (required for the HITL approval pause). Defaults to
    InMemorySaver so the capstone runs with zero setup.
    """
    b = StateGraph(ResearchState)
    b.add_node("research", research)
    b.add_node("write", write)
    b.add_node("evaluate", evaluate)
    b.add_node("approval", approval)
    b.add_node("finalize", finalize)

    b.add_edge(START, "research")
    b.add_edge("research", "write")
    b.add_edge("write", "evaluate")
    b.add_conditional_edges("evaluate", quality_gate,
                            {"research": "research", "approval": "approval"})
    b.add_edge("approval", "finalize")
    b.add_edge("finalize", END)

    return b.compile(checkpointer=checkpointer or InMemorySaver())
