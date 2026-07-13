# 02-3 · Agent 2: Profile Matcher

> **Level:** Beginner · **Prerequisites:** [02-2 Analyzer](02_analyzer.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## What the Profile Matcher does

The Matcher bridges the job and the freelancer. It reads the analyzer's structured
breakdown plus a human-readable version of `profile.yaml`, then produces:

- A **fit score**: HIGH, MEDIUM, or LOW
- The **single best matching portfolio project** and why

This is what makes each proposal different. The writer always leads with the most
relevant piece of evidence.

---

## The profile file

```yaml
# profile/profile.yaml
name: Meet Patel
title: Python & AI Engineer
skills:
  - Python, FastAPI, PostgreSQL, Docker
  - LangChain, LangGraph, RAG, embeddings
  - REST API design, test-driven development

projects:
  - name: Typed Python SDK
    description: >
      Built a full Python SDK (sync + async, Pydantic v2, automatic retries,
      pagination) for the PokéAPI. Published to PyPI with GitHub Actions CI.

  - name: RAG Document Assistant
    description: >
      Built an offline-capable RAG pipeline with LangChain, InMemoryVectorStore,
      and local MiniLM embeddings. Streamlit UI. Runs without any API key.

  - name: Streaming Chat API
    description: >
      FastAPI backend with server-sent events for real-time LLM streaming.
      PostgreSQL message history, Docker Compose setup.

  - name: Multi-Agent Proposal Generator
    description: >
      LangGraph state machine with 4 agents, a conditional revision loop,
      FastAPI endpoint, and Streamlit UI. The app in this course.
```

The `profile_to_text()` function in `profile.py` converts this YAML to a readable
string that fits inside a prompt.

---

## The code

```python
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
```

### The `profile_text` argument

Unlike the other agents, `matcher` takes `profile_text` as an extra argument. This is
loaded once at graph build time (from `profile.yaml`) and bound using `functools.partial`.
See [03-1 Wiring & revision loop](../03_assembling_the_graph/01_wiring_and_revision_loop.md)
for how that binding works.

---

## Unit test

```python
from proposal_agent import agents
from proposal_agent.profile import load_profile, profile_to_text

def test_matcher_uses_profile():
    profile_text = profile_to_text(load_profile())
    llm = GenericFakeChatModel(messages=iter(["HIGH fit — best project: Typed Python SDK."]))
    out = agents.matcher(
        {"analysis": "needs a typed API"},
        llm=llm,
        profile_text=profile_text,
    )
    assert "HIGH fit" in out["fit"]
    assert out["log"] == ["matcher"]
```

```bash
PROPOSAL_LLM=fake pytest tests/test_agents.py::test_matcher_uses_profile -v
```

```
PASSED
```

---

## Personalise it

The profile is the part you **must edit** to make the agent yours. Open
`profile/profile.yaml` and replace the sample projects with your real ones.
The more specific your project descriptions, the better the matcher's output.

> **Tip:** Include numbers where possible — "delivered in 3 weeks", "80% test
> coverage", "reduced API response time by 40%". Specificity is what separates
> a good proposal from a generic one.

---

## Exercise

Add a `rate` field to `profile.yaml` and include it in the `profile_to_text()`
output. Does the matcher prompt need to change?

<details>
<summary>Hint</summary>

`profile_to_text()` is in `proposal_agent/profile.py`. Add a section like
`f"Rate: {profile.get('rate', 'negotiable')}\n"` to the returned string.
The matcher prompt doesn't need to change — it just includes the profile
text verbatim, so any new information you add automatically flows through.

</details>

---

**Next → [04 Proposal Writer](04_proposal_writer.md)**
