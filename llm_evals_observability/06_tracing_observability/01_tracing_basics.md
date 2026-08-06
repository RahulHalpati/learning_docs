# 06-1 · Tracing basics

> **Level:** Intermediate · **Prerequisites:** [01-3 · Environment setup](../01_foundations/03_environment_setup.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit trace output)

## Why this matters

An LLM app is a pipeline — retrieve, prompt, call, parse, maybe loop. When the output is wrong, "the answer was bad" tells you nothing about *which step* failed. A **trace** records every step with its inputs, outputs, and timing, turning debugging from guesswork into reading.

For agents this isn't optional. A 12-step agent run has twelve places to go wrong, and no way to inspect them without tracing.

---

## Spans and traces

- A **span** = one unit of work (a retrieval, an LLM call), with a name, timing, and attributes.
- A **trace** = the tree of spans for one request.

EvalKit's tracer is a context manager, so spans nest naturally:

```python
trace = Trace(name="rag.answer")

with trace.span("retrieve", query=query, version=version) as s:
    doc_ids = retrieve(query)
    s.attributes["retrieved"] = doc_ids          # record what happened

with trace.span("generate") as s:
    answer, p_tok, c_tok = generate(query, doc_ids)
    trace.record_llm(s, model="demo-large", prompt_tokens=p_tok, completion_tokens=c_tok)
```

**Output (real run, `trace.json`):**
```json
{
  "trace_id": "8f399268d560",
  "name": "rag.answer",
  "duration_ms": 0.05,
  "total_tokens": 32,
  "total_cost_usd": 0.00044,
  "spans": [
    {
      "name": "retrieve",
      "span_id": "8d2e1650",
      "parent_id": null,
      "attributes": {
        "query": "What is Flask?",
        "version": "v2",
        "retrieved": ["d1", "d3"]
      },
      "duration_ms": 0.02
    }
  ]
}
```

Everything you need to reconstruct the request: what was asked, what was retrieved, which model ran, how long it took, what it cost.

---

## What to put on a span

| Attribute | Why |
|-----------|-----|
| `input` / `query` | reproduce the failure |
| `output` | see what the step produced |
| `model`, `version` | **which** code/prompt/model produced this |
| `prompt_tokens`, `completion_tokens` | cost attribution ([06-2](02_cost_latency_tokens.md)) |
| `retrieved` doc ids | diagnose retrieval ([05-1](../05_rag_evaluation/01_retrieval_metrics.md)) |
| `error` | what went wrong |

> **Tip — record the *version* of everything.** Prompt version, model name, retriever version, dataset version. This is **traceability**, the principle the industry converged on: a score is only actionable if you can trace it back to the exact prompt/model/data that produced it. Without it you'll see quality drop and have no idea which of last week's five changes caused it.

---

## Nesting

`parent_id` builds the tree. EvalKit's test proves it:

```python
def test_spans_nest():
    t = Trace("test")
    with t.span("outer"):
        with t.span("inner"):
            pass
    outer, inner = t.spans
    assert inner.parent_id == outer.span_id and outer.parent_id is None
```

For an agent, the tree *is* the reasoning: `agent.run → plan → tool.search → tool.calculate → synthesize`. Reading it top-down shows you exactly where it went off the rails.

---

## Privacy

> ⚠️ **Traces contain raw user input — treat them as sensitive.** They're stored, searched, and shared far more casually than a database. Redact PII **before** attaching it to a span ([08](../08_guardrails/README.md)):
> ```python
> with trace.span("retrieve", query=redact_pii(query)):
> ```
> Also set a retention policy. "We keep every prompt forever" is a liability, not a feature.

---

## What this becomes in production

The shape above is deliberately the same as Langfuse/OpenTelemetry ([06-3](03_langfuse_and_otel.md)): named nested spans, key-value attributes, usage, a trace id. Moving to a real backend swaps the `Trace` class for an SDK — your instrumentation *points* don't move. That's why building it once is worth it.

---

## Recap & next

- ✅ A **span** is one step; a **trace** is the tree for one request. Nesting via `parent_id`.
- ✅ Record input, output, **model/prompt/version**, tokens, retrieved ids, errors.
- ✅ **Traceability**: every score should link back to the exact prompt/model/data — record versions.
- ✅ Traces hold raw user input — **redact and set retention**.
- ✅ The structure matches Langfuse/OTel, so migration is a swap, not a rewrite.
- ✅ Self-check: your answer quality dropped this week and you changed five things. What in the trace tells you which one?

→ Next: **[06-2 · Cost, tokens & latency](02_cost_latency_tokens.md)**

## Exercises

1. Add a `rerank` span between retrieve and generate in `evalkit/app.py`, record how many candidates it considered, and export a trace to see it nested.

<details>
<summary>Solution</summary>

Wrap the reranking work in `with trace.span("rerank", candidates=len(doc_ids)) as s:` and set `s.attributes["kept"] = kept_ids`. Export with `--trace`: the new span appears with `parent_id: null` (a sibling) — or nest it inside `retrieve` to model it as a sub-step. How you nest expresses how you think about the pipeline.
</details>
