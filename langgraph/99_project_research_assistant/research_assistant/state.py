"""The shared state of the research assistant graph."""
from typing import Annotated, TypedDict
import operator

from langgraph.graph import add_messages


class ResearchState(TypedDict):
    messages: Annotated[list, add_messages]      # conversation history (append + dedup by id)
    topic: str                                   # what to research (set once)
    sources: Annotated[list[str], operator.add]  # accumulates across research loops
    draft_report: str                            # produced by the writer node
    quality_score: float                         # 0.0–1.0 from the evaluator
    attempt: int                                 # loop counter (safety bound)
    status: str                                  # researching | writing | reviewing | approved | rejected
