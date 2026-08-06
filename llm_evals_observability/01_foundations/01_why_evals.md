# 01-1 · Why evals

> **Level:** Intermediate · **Prerequisites:** [00 · Introduction](../00_introduction.md)
> **Time:** 40 min · **Verified:** 2026-08-05 (concepts + real EvalKit output)

## Why this matters

Every LLM project reaches the same moment: someone changes a prompt, and nobody can say whether the app got better or worse. Without evals you're steering by anecdote — "it seemed fine on the three examples I tried". Evals replace that with evidence.

---

## The four ways LLM apps break silently

Traditional bugs announce themselves — a crash, a 500, a failing test. LLM regressions don't:

1. **Prompt edits.** You reword an instruction for clarity; accuracy on a whole category drops.
2. **Model upgrades.** The provider ships a new version. It's better on benchmarks and worse on *your* task.
3. **Retrieval changes.** A new chunk size or embedding model quietly returns worse context.
4. **Drift.** Users start asking things your prompt never anticipated.

None of these throw an exception. The app keeps answering confidently — just less correctly.

---

## Why unit tests don't work

```python
assert answer == "Flask is a Python micro-framework"     # ❌ hopeless
```

This fails on `"Flask is a Python microframework."`, on `"Flask — a micro-framework for Python"`, and on every other correct phrasing. Meanwhile it *passes* if the model memorized the exact string while understanding nothing.

The fix isn't a smarter assertion — it's a different shape of test:

| Unit test | Eval |
|---|---|
| one input, one expected output | a **dataset** of many cases |
| exact equality | **scored** on several axes (0–1) |
| pass/fail per case | **aggregate** + threshold |
| deterministic | statistical — you watch the trend |

---

## Seeing it fail for real

EvalKit runs a 6-case dataset against two versions of the same app. Version `v1` has a naive retriever (it counts stopwords, so "the" makes unrelated documents look relevant):

**Output (real run):**
```
v2 out-of-scope answer: I don't know.
v1 out-of-scope answer: Flask 3 uses the application factory pattern.
```

Asked *"Who won the 1998 world cup?"*, `v1` confidently returns a fact about Flask. No error, no exception — just a wrong answer delivered with total confidence. **That** is what evals catch and unit tests don't.

Aggregated:

**Output (real run):**
```
  f1                0.7513 -> 0.5847  delta  -0.1666  REGRESSED
  judge               0.75 -> 0.5833  delta  -0.1667  REGRESSED
```

A number, a direction, a magnitude. That's a conversation you can have in a code review.

---

## The trap: one metric is not enough

From the same run:

**Output (real run):**
```
  faithfulness      0.8333 -> 1.0     delta   0.1667  ok
```

**Faithfulness went up while the app got worse.** The bad version copied text verbatim from the (wrong) document it retrieved — so its answer was perfectly grounded in its context, and perfectly useless.

> ⚠️ **Optimizing one metric will eventually break your system.** Faithfulness measures "did it stick to the context", not "was the context right" or "did it answer the question". Every metric has a blind spot; the fix is a **panel** of metrics plus per-category slicing ([03](../03_metrics/README.md)). If someone shows you a single number that went up, ask what went down.

---

## What "good" costs

**Output (real run):**
```
cost v2 $0.00264  |  v1 $0.00017
```

The *worse* version was 15× cheaper (it retrieved less context). Quality and cost trade off directly, so a scorecard that omits cost is telling you half the story — you can't decide "is this improvement worth the money" without both.

---

## Recap & next

- ✅ LLM apps degrade **silently** — prompts, model upgrades, retrieval changes, drift.
- ✅ Assertions can't express "correct"; evals score a **dataset** on several axes and compare to a baseline.
- ✅ Real example: the naive version answered an out-of-scope question with confident nonsense.
- ✅ **One metric lies** — faithfulness rose as quality fell; always use a panel, and track cost too.
- ✅ Self-check: your prompt change raises average score by 3%. What would you check before shipping it?

→ Next: **[01-2 · The eval loop & types of eval](02_eval_loop_and_types.md)**

## Exercises

1. Take an LLM app you've built. Write down five inputs where you *think* it works and two where you suspect it doesn't. That list is the seed of your first eval dataset ([02-1](../02_datasets/01_building_eval_sets.md)).

<details>
<summary>Solution</summary>

The suspicious two matter more than the confident five — they're where the signal is. Most first datasets are far too optimistic: all happy path, no edge cases, no out-of-scope questions. If everything scores 1.0 on your first run, your dataset is too easy, not your app too good.
</details>
