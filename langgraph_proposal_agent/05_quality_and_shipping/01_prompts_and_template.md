# 05-1 · Prompts & the Proposal Template

> **Level:** Intermediate · **Prerequisites:** All of Section 02
> **Time:** 20 min · **Verified:** concept module

---

## What makes a proposal win

The single biggest factor in a freelance proposal isn't writing style — it's
**relevance**. The client needs to see, in the first two sentences, that you have done
this exact thing before.

The template the Writer uses enforces a structure that maximises relevance:

```
1. Hook: reference something specific from THEIR job (not a generic opener)
2. Proof: your single most relevant project, with a concrete detail
3. Plan: 2-3 sentences on HOW you'd approach their specific problem
4. CTA: one clear next step (share repo / schedule call / start Monday)
```

That's it. 120-180 words. Anything longer gets skimmed.

---

## The Writer prompt, annotated

```python
WRITER_PROMPT = ChatPromptTemplate.from_template(
    "You are an expert freelance proposal writer. Tone: {tone}. "
    # ↑ tone is injected at graph build time — default: "confident and direct"

    "Write a SHORT proposal (120-180 words) that: "
    "opens with a specific hook about THIS job, "           # forces job-specific opener
    "names the most relevant project as proof, "            # no generic "I have experience in..."
    "states a brief plan, "                                 # shows you thought about their problem
    "and ends with a clear call to action. "
    "No generic filler, no 'I am excited to apply'.\n\n"   # explicit anti-pattern ban

    "Job posting:\n{job_text}\n\n"       # full context for specificity
    "Analysis:\n{analysis}\n\n"          # structured breakdown from Agent 1
    "Best-fit project:\n{fit}\n"         # chosen project from Agent 2
    "{revision_note}\n\n"               # empty on first run; reviewer notes on revision
    "Proposal:"
)
```

The key constraints in the prompt:

| Constraint | Why |
|---|---|
| 120-180 words | Forces concision — most clients read the first 100 words and decide |
| "specific hook about THIS job" | Prevents copy-paste openers |
| "name the most relevant project" | Forces evidence, not claims |
| "no 'I am excited to apply'" | Bans the single most common generic phrase |

---

## The Reviewer prompt, annotated

```python
REVIEWER_PROMPT = ChatPromptTemplate.from_template(
    "You are a strict proposal reviewer. "
    "If the proposal is specific to the job, free of generic filler, "
    "and references concrete evidence, reply with EXACTLY 'APPROVED'. "
    "Otherwise reply with 1-3 concrete, numbered fixes (no praise).\n\n"
    "Job posting:\n{job_text}\n\nProposal:\n{proposal}\n\nReview:"
)
```

The reviewer has access to both the job and the proposal so it can check specificity.
"1-3 concrete, numbered fixes" prevents vague feedback like "be more professional".

---

## Prompt engineering principles used here

**Give the model a persona:** "You are a strict proposal reviewer" consistently
produces more critical output than "Review this proposal". The persona sets a
behavioural prior.

**Make the output format explicit:** "reply with EXACTLY 'APPROVED'" removes
ambiguity about what counts as approval. Vague instructions produce vague output.

**Ban anti-patterns explicitly:** "No generic filler, no 'I am excited to apply'"
is more effective than "be specific". LLMs are better at following prohibitions than
abstract instructions.

**Use structured inputs:** Passing `analysis` and `fit` as separate fields (not
just the raw job text) means the writer doesn't have to re-do the job of extracting
requirements. Each agent does one thing.

---

## Customising for your style

The `tone` field is your main lever. Try:

| Tone | Use case |
|---|---|
| `"confident and direct"` | Tech contracts, startup clients |
| `"warm and consultative"` | Long-term partnerships, agencies |
| `"technical and detailed"` | Senior engineering roles |
| `"brief and punchy"` | Design/creative platforms |

Set it in `profile.yaml`:

```yaml
tone: warm and consultative
```

Or per-run:

```bash
PROPOSAL_TONE="technical and detailed" python -m proposal_agent.cli job.txt
```

---

## Exercise

Rewrite the Writer prompt to also include a **question** at the end of the proposal
(asking for one detail to better scope the project). Does the Reviewer approve it
more or less often?

<details>
<summary>Hint</summary>

Add to the prompt constraints:

```
"and ends with a single scoping question that shows you're already thinking about the details."
```

Remove the generic CTA instruction. Try running with a few different job postings and
see how the reviewer responds.

</details>

---

**Next → [02 Evaluating & guardrails](02_evaluating_and_guardrails.md)**
