"""End-to-end graph tests with a fake model — verifies wiring and the revise loop."""

from langchain_core.language_models import GenericFakeChatModel

from proposal_agent.graph import build_graph, route_after_review


def run(messages, *, max_revisions=2):
    llm = GenericFakeChatModel(messages=iter(messages))
    graph = build_graph(llm=llm)
    return graph.invoke(
        {"job_text": "Need a FastAPI backend", "revisions": 0, "max_revisions": max_revisions},
        config={"configurable": {"thread_id": "test"}},
    )


def test_happy_path_no_revision():
    # analyzer, matcher, writer, reviewer=APPROVED
    final = run(["analysis", "HIGH fit — Typed SDK", "great proposal", "APPROVED"])
    assert final["log"] == ["analyzer", "matcher", "writer", "reviewer"]
    assert final["approved"] is True
    assert final["revisions"] == 1


def test_revision_loop_then_approve():
    # reviewer rejects once, writer revises, reviewer approves
    final = run([
        "analysis", "HIGH fit — Typed SDK",
        "draft 1", "1. Too generic.",   # first writer + reject
        "draft 2", "APPROVED",            # revised writer + approve
    ])
    assert final["log"] == ["analyzer", "matcher", "writer", "reviewer", "writer", "reviewer"]
    assert final["revisions"] == 2
    assert final["approved"] is True
    assert final["proposal"] == "draft 2"


def test_max_revisions_caps_the_loop():
    # reviewer always rejects; loop must stop at max_revisions
    final = run(
        ["analysis", "fit", "d1", "1. fix", "d2", "2. fix", "d3", "3. fix"],
        max_revisions=2,
    )
    assert final["revisions"] == 2          # capped, did not loop forever
    assert final["approved"] is False


def test_router_logic():
    assert route_after_review({"approved": True, "revisions": 0, "max_revisions": 2}) == "__end__"
    assert route_after_review({"approved": False, "revisions": 0, "max_revisions": 2}) == "writer"
    assert route_after_review({"approved": False, "revisions": 2, "max_revisions": 2}) == "__end__"
