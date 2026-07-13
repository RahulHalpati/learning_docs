# 02-5 · Agent 4: Reviewer

> **Level:** Beginner · **Prerequisites:** [02-4 Proposal Writer](04_proposal_writer.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## What the Reviewer does

The Reviewer is the quality gate. It reads the job posting and the proposal draft,
then makes a binary decision:

- `"APPROVED"` — the proposal is specific, evidence-based, and ready to send
- Numbered revision notes — 1-3 concrete fixes, no praise

That verdict drives the conditional edge in the graph: approve → END, needs work →
send back to the Writer.

---

## The code

```python
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
```

### Parsing the verdict

```python
approved = review.strip().upper().startswith("APPROVED")
```

Simple and robust: if the LLM's reply starts with "APPROVED" (case-insensitive, any
leading whitespace stripped), `approved = True`. Anything else — including "APPROVED
but could be better" — is `True`. Numbered revision notes start with a digit, so they
are `False`.

This is a deliberate design choice: the prompt asks for exactly "APPROVED" or numbered
feedback. The parser trusts the prompt, not the model's creativity.

---

## Unit test

```python
def test_reviewer_detects_approval():
    approved = agents.reviewer(
        {"job_text": "j", "proposal": "p"},
        llm=GenericFakeChatModel(messages=iter(["APPROVED"]))
    )
    assert approved["approved"] is True

    needs_work = agents.reviewer(
        {"job_text": "j", "proposal": "p"},
        llm=GenericFakeChatModel(messages=iter(["1. Too generic."]))
    )
    assert needs_work["approved"] is False
```

```bash
PROPOSAL_LLM=fake pytest tests/test_agents.py::test_reviewer_detects_approval -v
```

```
PASSED
```

---

## How the graph uses `approved`

The router function in `graph.py` reads `approved` and `revisions`:

```python
def route_after_review(state: ProposalState) -> Literal["writer", "__end__"]:
    if state.get("approved") or state.get("revisions", 0) >= state.get("max_revisions", 2):
        return END
    return "writer"
```

Two conditions stop the loop:
1. `approved = True` — reviewer said yes
2. `revisions >= max_revisions` — hard cap reached, ship best draft so far

You'll wire this in the next section.

---

## Exercise

The reviewer currently returns the raw LLM text in `review`. What if you want a
structured response with both the verdict and the individual revision points as a list?

<details>
<summary>Approach</summary>

Use `JsonOutputParser` or Pydantic output parsing:

```python
from pydantic import BaseModel

class ReviewResult(BaseModel):
    approved: bool
    notes: list[str]

# Then use: REVIEWER_PROMPT | llm | JsonOutputParser(pydantic_object=ReviewResult)
```

The trade-off: structured output is more robust for downstream processing but requires
a model that reliably produces valid JSON. For simple approval detection, `startswith`
is faster and more reliable across smaller models.

</details>

---

**Next → [03-1 Wiring & the revision loop](../03_assembling_the_graph/01_wiring_and_revision_loop.md)**
