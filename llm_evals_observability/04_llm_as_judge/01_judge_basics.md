# 04-1 · Judge basics

> **Level:** Intermediate → Advanced · **Prerequisites:** [03-2 · Semantic & task metrics](../03_metrics/02_semantic_metrics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

Some questions no string metric can answer: *"Is this summary actually useful?"*, *"Does this answer address what was asked?"*, *"Is the tone appropriate?"* For those you need a model to read the output and grade it — **LLM-as-judge**. It's the most powerful evaluation tool and the easiest to misuse.

---

## The rubric is the whole design

A judge is only as good as its instructions. EvalKit's:

```python
RUBRIC = """You are grading an assistant's answer against a reference.

Score 1-5 using ONLY this scale:
5 - fully correct and complete
4 - correct, minor omission
3 - partially correct
2 - mostly wrong but related
1 - wrong or irrelevant

Return JSON: {"score": <1-5>, "reason": "<one sentence>"}
Judge only factual agreement with the reference. Ignore style, length and tone.
"""
```

Four deliberate choices:

- **A small discrete scale (1–5).** Ask for 0–100 and you get noise dressed as precision — models can't distinguish 73 from 76, but they *can* distinguish "correct" from "partially correct".
- **Anchored levels.** Every point on the scale has a definition. Unanchored scales drift between runs.
- **Structured output.** JSON parses reliably; free prose doesn't.
- **An explicit ignore list.** *"Ignore style, length and tone"* — otherwise judges reward verbose, confident-sounding answers regardless of correctness.

---

## Scoring

```python
verdict = judge(prediction, reference)
verdict.score        # 1..5
verdict.normalized   # 0..1, so it averages with other metrics
```

**Output (real run):**
```
score 5/5  norm 1.0     Matches the reference.            | Flask is a Python micro-framework
score 4/5  norm 0.75    Correct with a minor omission.    | Flask is a Python framework
score 3/5  norm 0.5     Partially correct.                | Flask is a web thing for Python
score 1/5  norm 0.0     Incorrect or irrelevant.          | Bananas are yellow
```

Note `normalized` — mapping 1–5 onto 0–1 lets the judge sit in the same scorecard as F1 and faithfulness, and share one threshold convention. Always ask for a **reason** too: when a score looks wrong, the reason tells you whether the judge or the answer is at fault.

---

## Pairwise beats absolute

Asking *"score this 1–5"* is hard; asking *"which of these two is better?"* is much easier — for models as for people. Pairwise comparisons are noticeably more consistent:

**Output (real run):**
```
pairwise (good vs bad):  a
pairwise (equal):        tie
```

Use pairwise when you're **comparing two candidates** — prompt A vs prompt B, model v1 vs v2. Use absolute scoring when you need a number to track over time or gate on.

> **Tip — always allow "tie".** Force a winner and the judge invents a preference, which is pure noise. An honest tie is information: it says the change didn't matter.

---

## The judge is a model, so it costs and it varies

| Property | Consequence |
|----------|-------------|
| **Costs tokens** | judging 500 cases = 500 extra LLM calls per run |
| **Slow** | seconds per case; your suite goes from 1s to minutes |
| **Non-deterministic** | same input, different score across runs |
| **Biased** | position, verbosity, self-preference ([04-2](02_rubrics_and_bias.md)) |

Practical mitigations: set **temperature 0**, use a **cheaper model** for judging than for generation where quality allows, judge a **sample** rather than every case on every run, and **cache** verdicts keyed by (prediction, reference, rubric version).

> ⚠️ **A judge whose rubric you've changed is a different instrument.** Scores from before and after a rubric edit aren't comparable — same problem as changing the dataset. Version your rubric alongside your dataset and note it in the commit; otherwise you'll "improve" your app by accidentally relaxing its grader.

---

## Recap & next

- ✅ Use a judge for what string metrics can't reach: usefulness, relevance, reasoning, tone.
- ✅ The **rubric** is the design: small anchored scale, JSON output, explicit ignore list.
- ✅ Normalize to 0–1 so the judge joins the same scorecard; always capture a **reason**.
- ✅ **Pairwise** is more reliable for comparisons — and must allow **ties**.
- ✅ Judges cost money, add latency, and vary; temperature 0, sample, cache, **version the rubric**.
- ✅ Self-check: why is a 1–5 scale better than 0–100 for a judge?

→ Next: **[04-2 · Rubrics, bias & meta-evaluation](02_rubrics_and_bias.md)**

## Exercises

1. Write a rubric for "does this support reply resolve the customer's issue?" — anchored 1–5, JSON output, with an explicit list of things to ignore.

<details>
<summary>Solution</summary>

Anchor on *resolution*, not politeness: 5 = fully resolves with correct steps; 3 = partially (addresses the issue, misses a step); 1 = doesn't address it. Ignore list: tone, length, formatting, apology presence. Without that list, judges reliably score the warmest reply highest — even when it solves nothing.
</details>
