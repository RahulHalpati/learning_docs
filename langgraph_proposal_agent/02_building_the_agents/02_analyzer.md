# 02-2 · Agent 1: Analyzer

> **Level:** Beginner · **Prerequisites:** [02-1 Shared state](01_shared_state.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## What the Analyzer does

The Analyzer reads the raw job posting and extracts a structured breakdown:

- Required skills / tech stack
- Budget signal (low / healthy / unclear)
- Timeline
- The client's main pain point
- Any red flags

This structured output is what makes the downstream agents work well. The
writer gets *data*, not a wall of text.

---

## The code

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .state import ProposalState

_parser = StrOutputParser()

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
```

### How it works

1. Build an LCEL chain: `prompt | llm | StrOutputParser()`
2. Call `.invoke()` with the job text
3. Return only the two keys this node writes: `analysis` and `log`

The `|` operator is LangChain's **pipe syntax** (LCEL). It passes the output of each
step as input to the next: the prompt formats the text → the LLM generates a reply →
`StrOutputParser` strips it down to a plain string.

---

## Unit test

```python
# tests/test_agents.py

from langchain_core.language_models import GenericFakeChatModel
from proposal_agent import agents

def test_analyzer_returns_analysis_and_logs():
    llm = GenericFakeChatModel(messages=iter(["stack: FastAPI"]))
    out = agents.analyzer({"job_text": "Need a FastAPI backend"}, llm=llm)

    assert out["analysis"] == "stack: FastAPI"
    assert out["log"] == ["analyzer"]
```

Run it:

```bash
PROPOSAL_LLM=fake pytest tests/test_agents.py::test_analyzer_returns_analysis_and_logs -v
```

Output:

```
PASSED                                                                   [100%]
```

### Why this test pattern works

`GenericFakeChatModel(messages=iter(["stack: FastAPI"]))` returns the string
`"stack: FastAPI"` the first time the LLM is called — no network, no API key, 100%
deterministic.

Because the agent is a plain function `(state, llm) -> dict`, the test passes a
fake LLM directly. No graph, no fixtures, no mocking framework.

---

## Exercise

**Add a second assertion:** check that `analyzer` raises a `KeyError` if `job_text`
is missing from the state. Call `analyzer({}, llm=llm)`.

<details>
<summary>Solution</summary>

```python
import pytest
from langchain_core.language_models import GenericFakeChatModel
from proposal_agent import agents

def test_analyzer_missing_job_text():
    llm = GenericFakeChatModel(messages=iter(["...any reply..."]))
    with pytest.raises(KeyError):
        agents.analyzer({}, llm=llm)
```

`state["job_text"]` raises `KeyError` when the key isn't present — Python dict
behaviour, no special LangGraph handling needed.

</details>

---

**Next → [03 Profile Matcher](03_profile_matcher.md)**
