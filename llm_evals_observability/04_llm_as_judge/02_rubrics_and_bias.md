# 04-2 · Rubrics, bias & meta-evaluation

> **Level:** Advanced · **Prerequisites:** [04-1 · Judge basics](01_judge_basics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

A judge produces confident numbers whether or not it's measuring anything real. If you gate releases on an unvalidated judge, you've built a quality process on an unexamined assumption. This lesson covers the known biases, how to cancel them, and — the step almost everyone skips — **checking the judge against humans**.

---

## The biases you must design around

| Bias | The judge prefers… | Fix |
|------|-------------------|-----|
| **Position** | whichever answer came first | swap and re-run |
| **Verbosity** | longer, more detailed answers | say "ignore length" in the rubric |
| **Self-preference** | text from its own model family | judge with a different model |
| **Style** | confident, well-formatted prose | anchor the rubric to *facts* |
| **Leniency drift** | scoring everything 4–5 | anchored scale + calibration examples |

Position bias is the most measurable, so let's kill it properly.

---

## Cancelling position bias

Run the comparison **both ways**. If the verdict flips, the judge wasn't deciding on merit:

```python
def judge_with_position_swap(answer_a, answer_b, reference) -> str:
    first = judge_pairwise(answer_a, answer_b, reference)
    second = judge_pairwise(answer_b, answer_a, reference)      # swapped
    flipped = {"a": "b", "b": "a", "tie": "tie"}[second]
    return first if first == flipped else "tie"                  # disagreement -> tie
```

**Output (real run):**
```
pairwise (equal):        tie
position-swap (equal):   tie
```

Two identical answers correctly produce a tie rather than an invented winner. With a real (biased) judge, the swap is what turns *"A wins!"* — an artifact of ordering — into an honest tie. It doubles your judge cost, and it's worth it for any comparison you'd act on.

---

## Meta-evaluation: is the judge any good?

This is the step that separates a real eval practice from cargo-culting. Label a sample by hand, then measure how often the judge agrees:

```python
def agreement(verdicts: list[int], human_labels: list[int]) -> float:
    matches = sum(1 for v, h in zip(verdicts, human_labels) if v == h)
    return round(matches / len(verdicts), 4)
```

**Output (real run):**
```
agreement perfect:  1.0
agreement 2/3:      0.6667
```

Procedure: hand-label **50–100** representative cases, run the judge over them, compute agreement.

| Agreement | Verdict |
|-----------|---------|
| **> 0.8** | trustworthy — use it as a gate |
| **0.6 – 0.8** | usable as a trend signal; don't block merges on it |
| **< 0.6** | your judge is measuring something else — fix the rubric |

> ⚠️ **An unvalidated judge is a vibe with a decimal point.** If you've never compared it to human judgement, you don't know whether "quality improved 8%" means anything. Measure agreement *before* the judge gets any authority over releases — and re-measure whenever you change the rubric or the judge model.

Exact agreement is strict; for a 1–5 scale, "within ±1" (adjacent agreement) is often the fairer target, since humans disagree with each other by a point routinely.

---

## Improving a weak judge

If agreement is low, in order of effect:

1. **Add calibration examples** to the rubric — one worked example per score level. Usually the single biggest improvement.
2. **Narrow the question.** "Is this good?" is unanswerable; "Does this answer contain the customer's order number?" is easy. Several narrow judges beat one vague judge.
3. **Ask for the reason first, score second** — the model commits to an analysis before the number, which reduces snap judgements.
4. **Use a stronger model** for judging (it's often worth spending more on the grader than the generator).
5. **Ensemble**: judge three times, take the median — cuts variance at 3× the cost.

---

## Humans stay in the loop

Judges scale review; they don't replace it. A healthy setup keeps a **small, regular human review** — say 20 sampled outputs a week. That's how you notice the judge drifting, catch failure modes no rubric anticipated, and keep your agreement estimate current. Teams that fully automate evaluation eventually optimize for the judge instead of the user.

---

## Recap & next

- ✅ Known biases: **position, verbosity, self-preference, style, leniency** — design the rubric against them.
- ✅ Cancel position bias with a **swap**; disagreement between orderings → report a tie.
- ✅ **Meta-evaluate**: hand-label 50–100 cases and measure agreement (>0.8 to gate on).
- ✅ Improve a weak judge with calibration examples, narrower questions, reason-before-score, a stronger model, or an ensemble.
- ✅ Keep a **human sample** in the loop permanently.
- ✅ Self-check: your judge says quality rose 8%. What do you need to know before believing it?

→ Next: **[05 · RAG evaluation](../05_rag_evaluation/README.md)**

## Exercises

1. Take 10 outputs from any LLM app, label each yourself 1–5, then score them with EvalKit's `judge()` and compute `agreement()`. Would you gate on it?

<details>
<summary>Solution</summary>

You'll likely get moderate agreement, because EvalKit's judge is an overlap heuristic — a stand-in, not a real grader. That's the lesson: the *number* only means something once you've measured it against human judgement. Try adjacent agreement (±1) as well; it's usually far higher and often the more honest target.
</details>
