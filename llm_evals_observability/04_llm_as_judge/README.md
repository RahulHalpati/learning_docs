# Section 04 · LLM-as-judge

> **Prerequisites:** [03 · Metrics](../03_metrics/README.md) · **Time:** ~2 h

For open-ended output, no string metric works — you need a model to grade. That's powerful and dangerous: judges are biased, inconsistent, and confidently wrong unless you control for it.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Judge basics](01_judge_basics.md) | How do I score answers with a model? |
| 04-2 | [Rubrics, bias & meta-evaluation](02_rubrics_and_bias.md) | How do I know the judge is right? |

## What you'll be able to do after this section

- Write a rubric that produces parseable, consistent scores.
- Use pairwise comparison and cancel **position bias** with a swap.
- **Validate the judge against human labels** before trusting it as a gate.

→ Start: **[04-1 · Judge basics](01_judge_basics.md)**
