# 02-1 · Building eval sets

> **Level:** Intermediate · **Prerequisites:** [01-3 · Environment setup](../01_foundations/03_environment_setup.md)
> **Time:** 45 min · **Verified:** 2026-08-05 (EvalKit's dataset + real output)

## Why this matters

Your eval is only as good as its dataset. A dataset of easy happy-path questions will tell you everything is fine right up until production disagrees. Getting this right is the highest-leverage work in evaluation — and it's mostly judgement, not code.

---

## The shape of a case

EvalKit uses JSONL — one JSON object per line, appendable, diff-friendly in git:

```json
{"id": "q2", "question": "What handles database migrations in Flask?",
 "reference": "Flask-Migrate wraps Alembic for Flask",
 "relevant_docs": ["d3"], "tags": ["data"]}
```

| Field | Why it's there |
|-------|----------------|
| `id` | stable handle — you'll discuss "q2 regressed" in reviews |
| `question` | the input |
| `reference` | the known-good answer (for reference-based metrics) |
| `relevant_docs` | which documents *should* be retrieved — enables RAG metrics ([05](../05_rag_evaluation/README.md)) |
| `tags` | **the slice dimension** — this is what surfaces category failures |

> **Tip — tags earn their keep immediately.** EvalKit's overall f1 is 0.75, which sounds fine. Sliced by tag, `data` is **0.22** and `deploy` is **0.29** — two categories are broken and the average buried it. A dataset without tags can only tell you "roughly okay".

---

## What to cover

A useful dataset is deliberately unbalanced toward the things that break:

| Category | Purpose | EvalKit example |
|----------|---------|-----------------|
| **Happy path** | the core job works | "What is Flask?" |
| **Harder variants** | paraphrases, multi-hop, ambiguity | "What handles database migrations in Flask?" |
| **Out-of-scope** | must refuse, not invent | "Who won the 1998 world cup?" |
| **Adversarial** | injection, PII, jailbreaks | "Ignore previous instructions…" |
| **Regression cases** | every bug you've fixed | (added over time) |

The **out-of-scope** case is the one people forget, and it's the most valuable. EvalKit's `q6` is exactly that, and it caught a real failure:

**Output (real run):**
```
v2 answer: I don't know.
v1 answer: Flask 3 uses the application factory pattern.
```

One test case, one confident hallucination caught.

---

## How many cases?

- **20–50** to start — enough to be meaningful, small enough to actually write well.
- **100–500** for a mature system, grown mostly from production traces ([02-2](02_from_production_traces.md)).
- **Quality over volume.** Fifty carefully-referenced cases beat five hundred auto-generated ones, because a wrong reference produces a *wrong signal*, which is worse than no signal.

> ⚠️ **Beware LLM-generated datasets.** Asking a model to invent test cases is fast and produces exactly the distribution the model finds natural — which is not your users' distribution. Worse, if the same model family generates *and* answers them, you're measuring self-consistency, not correctness. Use generation to draft, then **review every reference by hand**.

---

## Writing good references

The reference defines what "correct" means, so sloppiness here poisons the whole metric. EvalKit's `q2` shows the trap:

```
reference: "Flask-Migrate wraps Alembic for Flask"
answer:    "Alembic handles database migrations."      -> f1 = 0.22
```

The answer is *true* and comes from the *right* document — it just isn't the sentence the reference wanted. Is the app wrong, or is the reference too narrow? Often it's the reference.

Practical rules:
- Keep references **short and factual** — the fewer incidental words, the less noise in string metrics.
- If several answers are correct, either store a list of acceptable references or move that case to a **judge** ([04](../04_llm_as_judge/README.md)).
- Re-read failures before "fixing" the app. **A large share of first-run failures are dataset bugs.**

---

## Versioning

Keep the dataset in git next to the code. When you change it, you've changed the measuring stick — so scores before and after aren't comparable. Note dataset changes in your commit message, and never edit a reference to make a failing test pass unless the reference was genuinely wrong.

---

## Recap & next

- ✅ A case = `id` + input + `reference` + `relevant_docs` + **`tags`**; JSONL keeps it git-friendly.
- ✅ Cover happy path, hard variants, **out-of-scope**, adversarial, and past bugs.
- ✅ 20–50 cases to start; **quality beats volume** — a wrong reference is worse than no case.
- ✅ LLM-generated sets need hand review, or you measure self-consistency.
- ✅ Version the dataset; changing it changes the measuring stick.
- ✅ Self-check: your app scores 1.0 on every case. What's the most likely explanation?

→ Next: **[02-2 · Growing it from traces](02_from_production_traces.md)**

## Exercises

1. Add two cases to `datasets/qa.jsonl`: one adversarial (a prompt-injection attempt) and one out-of-scope. Re-run `python -m evalkit.report` and see how the aggregate moves.

<details>
<summary>Solution</summary>

Both should *lower* your average — that's the dataset getting more honest, not the app getting worse. This is why you never compare scores across dataset versions: adding hard cases moves the baseline, and only a like-for-like comparison means anything.
</details>
