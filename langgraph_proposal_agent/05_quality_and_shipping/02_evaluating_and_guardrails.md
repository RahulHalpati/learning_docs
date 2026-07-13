# 05-2 · Evaluating & Guardrails

> **Level:** Intermediate · **Prerequisites:** [05-1 Prompts & template](01_prompts_and_template.md)
> **Time:** 20 min · **Verified:** concept module

---

## How to know if your proposals are good

The reviewer agent gives you one data point per run. For systematic evaluation,
use the **LLM-as-judge** pattern: run a set of standard job postings, collect
proposals, and have a second LLM score them against criteria.

### A simple evaluation harness

```python
# eval/run_eval.py

import json
from pathlib import Path
from proposal_agent.graph import generate_proposal
from proposal_agent.providers import get_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

JOBS = list(Path("data/sample_jobs").glob("*.txt"))

JUDGE_PROMPT = ChatPromptTemplate.from_template(
    "Score this freelance proposal on three criteria (1-5 each):\n"
    "1. Specificity: does it reference concrete details from the job?\n"
    "2. Evidence: does it cite a relevant project with specifics?\n"
    "3. Clarity: is the plan and CTA clear?\n\n"
    "Job:\n{job_text}\n\nProposal:\n{proposal}\n\n"
    "Reply with JSON: {{\"specificity\": N, \"evidence\": N, \"clarity\": N, \"total\": N, \"notes\": \"...\"}}"
)

def evaluate():
    judge = get_chat_model(temperature=0)   # low temp for consistent scoring
    judge_chain = JUDGE_PROMPT | judge | StrOutputParser()
    results = []
    for job_file in JOBS:
        job_text = job_file.read_text()
        final = generate_proposal(job_text)
        score_raw = judge_chain.invoke({"job_text": job_text, "proposal": final["proposal"]})
        try:
            score = json.loads(score_raw)
        except json.JSONDecodeError:
            score = {"error": score_raw}
        results.append({"job": job_file.name, "revisions": final["revisions"], **score})
    return results

if __name__ == "__main__":
    for r in evaluate():
        print(r)
```

---

## Guardrails: catching bad output

### Red flags to detect

| Pattern | Why it's bad | How to catch |
|---|---|---|
| "I am excited to apply" | Generic filler | `"excited to apply" in proposal.lower()` |
| Proposal < 80 words | Too short, no substance | `len(proposal.split()) < 80` |
| No numbers/dates | Missing specifics | `not re.search(r'\d', proposal)` |
| Mentions wrong tech | Hallucination | Cross-check `analysis` keywords vs `proposal` |

### A simple guardrail function

```python
import re

def guardrail_check(proposal: str, analysis: str) -> list[str]:
    """Return a list of issues; empty list means the proposal passed."""
    issues = []
    if "excited to apply" in proposal.lower():
        issues.append("Contains generic filler: 'excited to apply'")
    if len(proposal.split()) < 80:
        issues.append(f"Too short ({len(proposal.split())} words; target 120-180)")
    if not re.search(r"\d", proposal):
        issues.append("No numbers or dates — add timeline or cost specifics")
    return issues
```

You can call this after `generate_proposal()` and surface warnings to the user:

```python
final = generate_proposal(job_text)
issues = guardrail_check(final["proposal"], final["analysis"])
if issues:
    for issue in issues:
        print(f"⚠️  {issue}")
```

### Adding guardrails to the graph

A guardrail can be a fifth node in the graph:

```python
def guardrail(state: ProposalState) -> dict:
    issues = guardrail_check(state["proposal"], state["analysis"])
    if issues:
        # inject issues as review notes for the writer to address
        return {"review": "\n".join(issues), "approved": False, "log": ["guardrail"]}
    return {"log": ["guardrail"]}  # pass through unchanged
```

Wire it between writer and reviewer:

```
writer → guardrail → reviewer
```

Now bad proposals are caught by code before the LLM reviewer even sees them.

---

## What to track over time

Run evaluations weekly with a fixed set of benchmark jobs. Track:

- Average total score (target: > 12/15)
- Revision rate (how often the reviewer asks for changes)
- Guardrail hit rate (how often basic checks fail)
- Approval rate on first attempt

When you change a prompt, re-run the eval and compare before/after.

---

**Next → [03 Ship & monetise](03_ship_and_monetize.md)**
