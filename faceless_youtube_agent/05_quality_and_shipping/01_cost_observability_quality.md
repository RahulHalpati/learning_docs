# 05-1 · Cost, observability & quality gates

> **Level:** Beginner → Intermediate · **Time:** 20 min

Once you're producing videos regularly you want three things: to **see** what
happened in a run, to **know** what it cost, and to **auto-catch** obviously weak
drafts before they reach your review queue.

---

## Observability: you already have a trace

The `log` field is your built-in trace — every node appends its name, so the final
`log` is the exact path the run took:

```python
final["log"]  # ['researcher','scriptwriter','voiceover','visuals','assembler','metadata']
```

For richer tracing, LangGraph integrates with **LangSmith**. Set two env vars and
every node call, prompt, and latency is recorded:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls_...
```

No code change — LangChain/LangGraph pick these up automatically. You get a visual
timeline of each run, which is invaluable when a node misbehaves. (Optional and
online; the pipeline runs fine without it.)

---

## Cost: local is free, hosted is not

| Provider | Cost per video (rough) | Notes |
|---|---|---|
| `fake` | $0 | tests / demos |
| `ollama` (local) | $0 (your electricity) | default; great for drafts |
| Hosted LLM (Claude/OpenAI) | cents | 3 short calls per video; cheap but not zero |
| TTS (ElevenLabs) | per character | the real cost driver at scale |
| Video/image APIs | varies | only if you swap the offline visuals |

Two practical rules:

1. **Draft locally, polish selectively.** Generate with Ollama for free; only spend
   hosted-LLM/premium-TTS money on videos you've decided to publish.
2. **Log token usage.** For hosted models, LangChain responses carry
   `response_metadata` with token counts — sum them per run to see real cost. The
   [Claude API guide](../../langchain_rag/) and provider docs show the fields.

---

## Quality gates: auto-reject the obvious duds

Before a draft hits your review queue, cheap deterministic checks catch the
worst cases so you don't waste attention on them. Add a tiny validator after the
graph runs:

```python
def quality_check(state) -> list[str]:
    issues = []
    segs = state.get("segments", [])
    if len(segs) < 3:
        issues.append("too few segments (<3)")
    if any(len(s["narration"].split()) < 3 for s in segs):
        issues.append("a segment has near-empty narration")
    total = sum(float(s.get("duration") or 0) for s in segs)
    if total < 20:
        issues.append(f"video too short ({total:.0f}s)")
    if not state.get("title") or state["title"] == state["topic"]:
        issues.append("title fell back to the raw topic")
    return issues
```

```python
issues = quality_check(final)
if issues:
    print("⚠️ needs attention:", issues)   # route to a 'rejected' folder, or re-run
```

This is the same "degrade gracefully, but flag it" philosophy as the parsers —
except here you surface the flag to a human instead of silently continuing.

> **LLM-as-judge (next level):** for subjective quality (is the hook actually
> punchy? is the script accurate?), add a node that asks a model to score the draft
> 1–5 with reasons, and gate on the score. Keep the deterministic checks too —
> they're free and never hallucinate.

---

## Recap

- The **`log` field** is a free trace; **LangSmith** adds a full visual timeline
  with two env vars.
- **Draft locally (free), spend selectively** on hosted models/premium TTS.
- Add **cheap deterministic quality gates** to auto-flag weak drafts; layer an
  **LLM-as-judge** on top for subjective quality.

## Exercise

Turn `quality_check` into a graph node placed after `metadata` that writes an
`issues` list into the state, and have the CLI print a ⚠️ line when it's non-empty.
Bonus: move failed drafts to `out/_rejected/<slug>/`.

<details>
<summary>Hint</summary>

Add `issues: list[str]` to `VideoState`, register a `quality` node with
`add_edge("metadata", "quality")` and `add_edge("quality", END)`. In the CLI, read
`state.get("issues")` and `shutil.move` the run dir if it's non-empty.

</details>

---

**Next → [05-2 · Ethics, policy & scaling responsibly](02_ethics_policy_and_scaling.md)**
