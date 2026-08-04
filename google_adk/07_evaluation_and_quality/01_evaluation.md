# 07-1 · Evaluation

> **Level:** Intermediate · **Prerequisites:** [06-3 · API server & clients](../06_runtime_events_streaming/03_api_server_and_clients.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (google-adk 2.5.0; `AgentEvaluator` + `adk eval` present)

## Why this matters

"It seemed to work when I tried it" isn't quality assurance. ADK ships **evaluation** so you can define cases once and re-score your agent on every change — catching regressions in both *what it says* and *which tools it calls*. It's the difference between hoping and knowing.

---

## Two things ADK scores

1. **Response match** — is the final answer close enough to the expected one?
2. **Trajectory** — did the agent call the *right tools with the right arguments* in the right order?

Trajectory scoring is what makes agent eval different from plain LLM eval: an agent can give a fine answer for the *wrong* reason (skipped a tool, guessed). ADK checks the path, not just the destination.

---

## Eval sets

Test cases live in an **eval set** JSON file (`*.evalset.json`). Each case is a conversation with the expected final response and expected tool calls. Conceptually:

```jsonc
{
  "eval_set_id": "research_cases",
  "eval_cases": [
    {
      "eval_id": "capital_of_france",
      "conversation": [
        {
          "user_content": { "parts": [{ "text": "Capital of France?" }] },
          "final_response": { "parts": [{ "text": "Paris" }] },
          "intermediate_data": { "tool_uses": [] }
        }
      ]
    }
  ]
}
```

You don't hand-write these in practice — record them from real runs in `adk web` (there's a "save to eval set" button), then edit expectations.

---

## Running eval

**CLI** — point it at your agent module and eval set(s):

```bash
adk eval path/to/agent_dir path/to/cases.evalset.json
```

It runs every case, scores response-match and trajectory, and prints pass/fail per case.

**In tests** — `AgentEvaluator` runs the same scoring from pytest, so eval becomes part of CI:

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator

# await AgentEvaluator.evaluate(
#     agent_module="research_agent",
#     eval_dataset_file_path_or_dir="cases.evalset.json",
# )
```

> **Note:** `AgentEvaluator` and the `adk eval` command are verified present in `google-adk 2.5.0`. Meaningful *scores* need a capable model (response-match against a tiny local model is noisy) — but the harness, eval-set format, and CI integration are what you're learning here, and those are model-independent.

---

## Metrics & thresholds

Eval compares against thresholds you set (e.g. response-match score ≥ 0.7, tool-trajectory exact-match). Cases below threshold fail. You can also plug **custom metrics** and, for response quality, an **LLM-as-judge**. Start strict on trajectory (tools are deterministic) and looser on response text (phrasing varies).

---

## Recap & next

- ✅ ADK scores **response match** and **tool-use trajectory** — path, not just answer.
- ✅ Cases live in `*.evalset.json`; record them from `adk web`, run via `adk eval` or `AgentEvaluator`.
- ✅ Put `AgentEvaluator` in pytest to catch regressions in CI.
- ✅ Self-check: why is trajectory scoring important beyond checking the final answer?

→ Next: **[07-2 · Safety & guardrails](02_safety_and_guardrails.md)**

## Exercises

1. Sketch an eval set with two cases for a calculator agent — one requiring the `add` tool (trajectory), one a direct answer.

<details>
<summary>Solution</summary>

Case A: user "what is 2+2?", expected `final_response` "4", `tool_uses` containing an `add` call. Case B: user "hello", expected a greeting, `tool_uses` empty. Run with `adk eval` to score both response and trajectory.
</details>
