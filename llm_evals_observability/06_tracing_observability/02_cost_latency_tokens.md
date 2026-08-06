# 06-2 · Cost, tokens & latency

> **Level:** Intermediate · **Prerequisites:** [06-1 · Tracing basics](01_tracing_basics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

LLM apps have a cost structure no other software does: **every request spends money**, proportional to text volume. A prompt tweak that adds 500 tokens of instructions raises your bill by 500 tokens *per request forever*. If you're not measuring cost alongside quality, you're optimizing blind — and the bill arrives a month later.

---

## Token accounting

Cost is a function of tokens in and tokens out, priced differently:

```python
PRICES_PER_1K = {
    "demo-small": {"input": 0.0005, "output": 0.0015},
    "demo-large": {"input": 0.0100, "output": 0.0300},
}

def cost_usd(model, prompt_tokens, completion_tokens) -> float:
    p = PRICES_PER_1K[model]
    return prompt_tokens / 1000 * p["input"] + completion_tokens / 1000 * p["output"]
```

**Output (real run, verified in the test suite):**
```
demo-large, 1000 in + 1000 out  ->  $0.04
```

Two things this makes visible immediately:

- **Output tokens cost ~3× input.** Verbose answers are disproportionately expensive — "be concise" is a cost control, not just a style preference.
- **Model choice is a 20× lever.** `demo-large` costs 20× `demo-small` per token. Routing easy requests to a smaller model is usually the single biggest saving available.

> ⚠️ **Keep prices in config, never inline.** Provider pricing changes, and a hard-coded rate scattered across your codebase silently makes every cost report wrong. EvalKit keeps one `PRICES_PER_1K` table; a real system should load it from config and stamp the *price version* onto traces.

---

## Rolling up per request

The trace aggregates automatically:

```python
trace.total_tokens      # summed across spans
trace.total_cost_usd
trace.duration_ms
```

**Output (real run):**
```
trace_id 8f399268d560 · duration 0.05 ms · total_tokens 32 · total_cost_usd 0.00044
```

Per-span attribution matters because it tells you *where* the money goes. In a RAG app the retrieval span is nearly free and the generation span is nearly all the cost — so optimization effort belongs on prompt size and output length, not on the retriever.

---

## Cost in the scorecard

EvalKit puts cost next to quality, deliberately:

**Output (real run):**
```
  judge            0.75     ███████████████
  tokens           170
  cost (usd)       0.00264
```

And the regression run shows why:

**Output (real run):**
```
cost v2 $0.00264  |  v1 $0.00017        (15× cheaper — and much worse)
```

Quality and cost move together. A scorecard with only quality invites "make it better" changes that quietly triple the bill; one with only cost invites the reverse. **You need both numbers in the same table** to have an honest conversation about a trade-off.

---

## Latency: measure percentiles, not averages

Average latency hides the experience that actually annoys users.

| Statistic | Tells you |
|-----------|-----------|
| p50 (median) | the typical request |
| **p95 / p99** | the tail — what your unluckiest users feel |
| max | the worst case (often a timeout) |

LLM latency is dominated by **output length** (tokens are generated sequentially), then model size, then everything else. Practical levers: cap `max_tokens`, **stream** the response so time-to-first-token is what users perceive, run independent steps concurrently, and cache repeated work.

---

## What to alert on in production

| Signal | Why |
|--------|-----|
| **Cost per request** trending up | prompt bloat or a model change |
| **Total daily spend** vs budget | the bill-shock alarm |
| **p95 latency** | user-visible slowness |
| **Token usage** per endpoint | which feature is expensive |
| **Error / timeout rate** | reliability |

Set a **hard budget cap** in CI too. EvalKit does:

```python
MAX_COST_USD = 0.01
def test_cost_within_budget(report):
    assert report.total_cost_usd <= MAX_COST_USD
```

That test fails the build if a change makes the eval run more expensive — catching prompt bloat before it reaches production and multiplies by your traffic.

---

## Recap & next

- ✅ Cost = tokens × per-model price; **output tokens cost ~3× input**, and model choice is a ~20× lever.
- ✅ Keep prices in **config**; attribute cost **per span** to see where it goes.
- ✅ Put **cost next to quality** in the scorecard — the worse version was 15× cheaper.
- ✅ Track **p95/p99** latency, not averages; output length dominates; stream to improve perceived speed.
- ✅ Gate cost in CI with a budget test to catch prompt bloat early.
- ✅ Self-check: your prompt grows by 500 tokens and quality rises 2%. What do you need to know before shipping it?

→ Next: **[06-3 · Langfuse & OpenTelemetry](03_langfuse_and_otel.md)**

## Exercises

1. In `evalkit/tracing.py`, switch the generate span to `demo-small` and re-run the report. How much cheaper is the run, and what happened to quality?

<details>
<summary>Solution</summary>

Cost drops ~20× while quality is unchanged — because EvalKit's "model" is a stub, the model name only affects price. With a real model you'd see quality move too, and *that* comparison — quality delta vs cost delta — is exactly the routing decision (cheap model for easy requests, expensive for hard ones) that saves real money.
</details>
