"""The four agents, as LangGraph node functions.

Each node takes the shared state (plus the chat model and profile text it needs)
and returns a dict of only the keys it updates. The graph (graph.py) binds the
`llm` and `profile_text` arguments so the graph calls each node with just `state`.

Keeping the agents as plain `(state, llm, ...) -> dict` functions makes them
trivial to unit-test with a fake model — no graph required.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .state import ProposalState

_parser = StrOutputParser()


# --- Agent 1: Analyzer ------------------------------------------------------
ANALYZER_PROMPT = ChatPromptTemplate.from_template(
    "You are a freelance job analyst. Read the job posting and extract, concisely:\n"
    "- Required skills / tech stack\n- Budget signal (low/healthy/unclear)\n"
    "- Timeline\n- The client's main pain point\n- Any red flags\n\n"
    "Job posting:\n{job_text}\n\nAnalysis:"
)


def analyzer(state: ProposalState, llm: BaseChatModel) -> dict:
    chain = ANALYZER_PROMPT | llm | _parser
    analysis = chain.invoke({"job_text": state["job_text"]})
    return {"analysis": analysis, "log": ["analyzer"]}


# --- Agent 2: Profile Matcher ----------------------------------------------
MATCHER_PROMPT = ChatPromptTemplate.from_template(
    "You match a freelancer to a job. Given the job analysis and the freelancer's "
    "profile, pick the SINGLE best-matching project and rate the overall fit as "
    "HIGH, MEDIUM, or LOW, with one sentence explaining why.\n\n"
    "Job analysis:\n{analysis}\n\nFreelancer profile:\n{profile}\n\n"
    "Respond as: '<HIGH|MEDIUM|LOW> fit — best project: <name>. <one sentence>.'"
)


def matcher(state: ProposalState, llm: BaseChatModel, profile_text: str) -> dict:
    chain = MATCHER_PROMPT | llm | _parser
    fit = chain.invoke({"analysis": state["analysis"], "profile": profile_text})
    return {"fit": fit, "log": ["matcher"]}


# --- Agent 3: Proposal Writer ----------------------------------------------
WRITER_PROMPT = ChatPromptTemplate.from_template(
    "You are an expert freelance proposal writer. Tone: {tone}. Write a SHORT proposal "
    "(120-180 words) that: opens with a specific hook about THIS job, names the most "
    "relevant project as proof, states a brief plan, and ends with a clear call to action. "
    "No generic filler, no 'I am excited to apply'.\n\n"
    "Job posting:\n{job_text}\n\nAnalysis:\n{analysis}\n\nBest-fit project:\n{fit}\n"
    "{revision_note}\n\nProposal:"
)


def writer(state: ProposalState, llm: BaseChatModel, tone: str) -> dict:
    # If the reviewer asked for changes, feed its notes back in.
    revision_note = ""
    if state.get("review") and not state.get("approved", False):
        revision_note = f"\nRevise to address this feedback:\n{state['review']}"
    chain = WRITER_PROMPT | llm | _parser
    proposal = chain.invoke(
        {
            "tone": tone,
            "job_text": state["job_text"],
            "analysis": state["analysis"],
            "fit": state["fit"],
            "revision_note": revision_note,
        }
    )
    return {"proposal": proposal, "revisions": state.get("revisions", 0) + 1, "log": ["writer"]}


# --- Agent 4: Reviewer ------------------------------------------------------
REVIEWER_PROMPT = ChatPromptTemplate.from_template(
    "You are a strict proposal reviewer. If the proposal is specific to the job, free of "
    "generic filler, and references concrete evidence, reply with EXACTLY 'APPROVED'. "
    "Otherwise reply with 1-3 concrete, numbered fixes (no praise).\n\n"
    "Job posting:\n{job_text}\n\nProposal:\n{proposal}\n\nReview:"
)


def reviewer(state: ProposalState, llm: BaseChatModel) -> dict:
    chain = REVIEWER_PROMPT | llm | _parser
    review = chain.invoke({"job_text": state["job_text"], "proposal": state["proposal"]})
    approved = review.strip().upper().startswith("APPROVED")
    return {"review": review, "approved": approved, "log": ["reviewer"]}
