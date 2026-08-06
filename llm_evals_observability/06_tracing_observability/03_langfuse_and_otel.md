# 06-3 · Langfuse & OpenTelemetry

> **Level:** Intermediate → Advanced · **Prerequisites:** [06-2 · Cost, tokens & latency](02_cost_latency_tokens.md)
> **Time:** 45 min · **Verified:** 2026-08-05 (concepts; integration code marked as such)

## Why this matters

You've built a tracer to understand the mechanics. In production you want someone else to run the storage, search, dashboards, and alerting. This lesson maps what you built onto the tools the industry actually uses — so the migration is a swap, not a rewrite.

---

## Langfuse

The leading open-source LLM observability platform: traces in, dashboards and scores out, self-hostable (which matters when prompts contain customer data).

```python
# pip install langfuse   — integration shown, not run in this offline course
from langfuse import Langfuse

langfuse = Langfuse()                      # reads keys from env

trace = langfuse.trace(name="rag.answer", user_id="u_123",
                       metadata={"prompt_version": "v3"})

span = trace.span(name="retrieve", input={"query": query})
span.end(output={"retrieved": doc_ids})

gen = trace.generation(
    name="generate", model="gpt-4o-mini",
    input=messages, output=answer,
    usage={"input": p_tok, "output": c_tok},   # cost computed for you
)
gen.end()
```

Compare that to EvalKit's tracer — `trace` → `span` → attributes → usage. **The same shape**, because it's modelled on the same idea. Swapping in Langfuse means changing the tracer class; your instrumentation points stay where they are.

What you get beyond your own JSON: searchable trace history, latency/cost dashboards, **scores attached to traces** (so an eval result links to the exact run), prompt management with versioning, and user feedback capture.

---

## Scores on traces: closing the loop

The feature that ties this course together — attach an eval score to a production trace:

```python
langfuse.score(trace_id=trace.id, name="faithfulness", value=0.87)
langfuse.score(trace_id=trace.id, name="user_feedback", value=0)   # 👎
```

Now you can filter production traffic to *"traces where faithfulness < 0.6"* and feed exactly those into your dataset ([02-2](../02_datasets/02_from_production_traces.md)). That's the flywheel, running automatically.

The industry pattern the research points to: **DeepEval pre-deploy, Langfuse in production, Ragas sampling production traces hourly** and publishing scores back to Langfuse as the single source of truth.

---

## OpenTelemetry

**OTel** is the vendor-neutral standard for traces/metrics/logs, and it has emerging **GenAI semantic conventions** — agreed attribute names like `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`.

```python
# conceptual
from opentelemetry import trace as otel
tracer = otel.get_tracer(__name__)

with tracer.start_as_current_span("generate") as span:
    span.set_attribute("gen_ai.request.model", "gpt-4o-mini")
    span.set_attribute("gen_ai.usage.input_tokens", p_tok)
    span.set_attribute("gen_ai.usage.output_tokens", c_tok)
```

> **Tip — why standard attribute names matter.** If you name it `gen_ai.usage.input_tokens`, every OTel-compatible backend (Langfuse, Datadog, Grafana, Honeycomb) understands it without custom parsing — and your LLM spans sit in the *same* trace as your database and HTTP spans. One request, one timeline, end to end. If you invent your own names, every backend needs a bespoke mapping.

Emit OTel and you avoid lock-in: point it at a different backend by changing an exporter.

---

## Choosing

| Need | Use |
|------|-----|
| LLM-specific UI, prompt management, scores | **Langfuse** (or Braintrust, Phoenix, LangSmith) |
| One standard across your whole stack | **OpenTelemetry** |
| Learning / small project / air-gapped | your own tracer (what you built) |
| Best of both | instrument with **OTel**, send to an LLM-aware backend |

Most teams end up at the last row.

---

## Migrating EvalKit

You'd replace `evalkit/tracing.py` and change nothing else:

```python
# before
with trace.span("retrieve", query=query) as s:
    s.attributes["retrieved"] = doc_ids

# after (Langfuse)
span = trace.span(name="retrieve", input={"query": query})
...
span.end(output={"retrieved": doc_ids})
```

Same call sites, same nesting, same attributes. That's the payoff of learning the model rather than the SDK.

---

## Recap & next

- ✅ **Langfuse** = open-source LLM observability (traces, dashboards, scores, prompt versioning, self-hostable).
- ✅ **Attach scores to traces** to close the loop from production back into your dataset.
- ✅ **OpenTelemetry** is the vendor-neutral standard; use the `gen_ai.*` conventions to avoid lock-in and unify LLM + infra traces.
- ✅ The industry pattern: DeepEval pre-deploy · Langfuse in prod · Ragas over sampled traces.
- ✅ EvalKit's tracer mirrors these APIs, so migrating swaps the class, not the instrumentation.
- ✅ Self-check: why use `gen_ai.usage.input_tokens` instead of your own attribute name?

→ Next: **[07 · CI regression gates](../07_ci_regression/README.md)**

## Exercises

1. Map each field of EvalKit's `trace.json` onto its Langfuse and OTel equivalent (trace id, span name, model, tokens, cost).

<details>
<summary>Solution</summary>

`trace_id` → Langfuse trace id / OTel `trace_id`; `spans[].name` → span name in both; `model` → Langfuse generation `model` / OTel `gen_ai.request.model`; `prompt_tokens`/`completion_tokens` → Langfuse `usage` / OTel `gen_ai.usage.input_tokens`/`output_tokens`; `cost_usd` → computed by Langfuse from usage + model (you rarely send it). The near-1:1 mapping is the point.
</details>
