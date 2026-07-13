"""The shared state that flows through every agent in the graph.

In LangGraph, all nodes read from and write to one shared state object. Each
agent node returns a dict of *only the keys it changes*; LangGraph merges that
into the running state. `log` uses a reducer so every node can append to it
without overwriting what previous nodes wrote.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class ProposalState(TypedDict, total=False):
    # --- input ---
    job_text: str            # the raw freelance job posting

    # --- produced by the agents, in order ---
    analysis: str            # Analyzer: requirements, budget, pain points, red flags
    fit: str                 # Matcher: best portfolio project + fit level + why
    proposal: str            # Writer: the current proposal draft
    review: str              # Reviewer: "APPROVED" or concrete revision notes
    approved: bool           # Reviewer's verdict as a bool (drives the loop)

    # --- loop control ---
    revisions: int           # how many times the writer has revised
    max_revisions: int       # hard cap so the loop always terminates

    # --- observability ---
    log: Annotated[list[str], operator.add]   # each node appends its name
