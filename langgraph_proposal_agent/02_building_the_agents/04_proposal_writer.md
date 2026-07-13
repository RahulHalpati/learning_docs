# 02-4 · Agent 3: Proposal Writer

> **Level:** Beginner · **Prerequisites:** [02-3 Profile Matcher](03_profile_matcher.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## What the Writer does

The writer's job is focused: take the structured analysis, the fit assessment, and
the reviewer's notes (if any) and produce a 120-180 word proposal. No job parsing,
no profile scoring — just prose.

It's the only agent that runs more than once. On the first run it writes a fresh
draft. On subsequent runs (triggered by the reviewer) it revises using the feedback.

---

## The code

```python
WRITER_PROMPT = ChatPromptTemplate.from_template(
    "You are an expert freelance proposal writer. Tone: {tone}. Write a SHORT proposal "
    "(120-180 words) that: opens with a specific hook about THIS job, names the most "
    "relevant project as proof, states a brief plan, and ends with a clear call to action. "
    "No generic filler, no 'I am excited to apply'.\n\n"
    "Job posting:\n{job_text}\n\nAnalysis:\n{analysis}\n\nBest-fit project:\n{fit}\n"
    "{revision_note}\n\nProposal:"
)


def writer(state: ProposalState, llm: BaseChatModel, tone: str) -> dict:
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
```

### The revision note

On the first run, `revision_note` is an empty string. On subsequent runs:

```python
# state["review"] = "1. Too generic. 2. No timeline mentioned."
# state["approved"] = False
revision_note = "\nRevise to address this feedback:\n1. Too generic. 2. No timeline mentioned."
```

The reviewer's notes are injected directly into the prompt. The writer rewrites with
full context — the original job, the analysis, the fit, and the specific critique.

### Incrementing `revisions`

```python
return {"revisions": state.get("revisions", 0) + 1, ...}
```

Using `.get("revisions", 0)` handles the first run cleanly — if `revisions` isn't in
state yet, it defaults to 0. After the first run: `revisions = 1`. After the first
revision: `revisions = 2`. The router checks this against `max_revisions`.

---

## Unit test

```python
def test_writer_increments_revisions():
    llm = GenericFakeChatModel(messages=iter(["Dear client, here is my proposal..."]))
    out = agents.writer(
        {"job_text": "j", "analysis": "a", "fit": "f", "revisions": 0},
        llm=llm,
        tone="confident and direct",
    )
    assert out["proposal"].startswith("Dear client")
    assert out["revisions"] == 1
    assert out["log"] == ["writer"]
```

```bash
PROPOSAL_LLM=fake pytest tests/test_agents.py::test_writer_increments_revisions -v
```

```
PASSED
```

---

## Customising the tone

The `tone` argument is bound at graph construction time (default: `"confident and
direct"`). To change it for the whole graph, pass it to `build_graph()`:

```python
graph = build_graph(llm=llm, tone="warm and consultative")
```

Or set the `PROPOSAL_TONE` env var (exercise below).

---

## Exercise

Add a `PROPOSAL_TONE` environment variable that lets users set the tone without
editing code. The default should be `"confident and direct"`.

<details>
<summary>Solution</summary>

In `graph.py`, change the `tone` default:

```python
import os

def build_graph(llm=None, profile=None, tone=None):
    if tone is None:
        tone = os.environ.get("PROPOSAL_TONE", "confident and direct")
    ...
```

Now users can run:

```bash
PROPOSAL_TONE="warm and conversational" python -m proposal_agent.cli job.txt
```

</details>

---

**Next → [05 Reviewer](05_reviewer.md)**
