# 02-3 · Scriptwriter

> **Level:** Beginner · **Time:** 25 min

The scriptwriter turns the research into a **list of segments** — the structure
every downstream node depends on. This is where you learn the single most
important skill for LLM pipelines: **getting structured data out of a model and
surviving when it misbehaves.**

This is `script_writer` in [`faceless_studio/nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py).

---

## Ask for JSON

```python
def script_writer(state, *, llm) -> dict:
    system = (
        "You are a scriptwriter for short faceless YouTube videos. Write tight, "
        "spoken-word narration — no stage directions, no markdown. 5-8 segments."
    )
    human = (
        f"Hook: {state.get('hook', '')}\n"
        f"Research:\n{state.get('research', '')}\n\n"
        "Return a JSON array. Each item: "
        '{"heading": "<slide title, <=4 words>", '
        '"narration": "<1-3 spoken sentences>", '
        '"visual_hint": "<how the slide should look>"}. '
        "Return ONLY the JSON array."
    )
    raw = _ask(llm, system, human)
    segments = _parse_segments(raw, state)
    return {"segments": segments, "log": ["scriptwriter"]}
```

---

## Parse leniently — models don't always obey

A big model usually returns clean JSON. A 7B local model might wrap it in prose,
add a trailing comma, or forget a bracket. The parser must not crash the whole
video over that:

```python
import json, re

def _parse_segments(raw, state):
    # 1. grab the first [...] block even if there's surrounding text
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            segs = [
                Segment(
                    heading=str(item.get("heading", "")).strip()[:60] or "Slide",
                    narration=str(item.get("narration", "")).strip(),
                    visual_hint=str(item.get("visual_hint", "")).strip(),
                )
                for item in data
                if str(item.get("narration", "")).strip()
            ]
            if segs:
                return segs
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    # 2. fallback: build segments from plain lines of text
    lines = [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]
    segs = [Segment(heading="Intro", narration=state.get("hook", state["topic"]),
                    visual_hint="title card")]
    for i, ln in enumerate(lines[:6], start=1):
        segs.append(Segment(heading=f"Point {i}", narration=ln, visual_hint="text slide"))
    return segs
```

The **three-layer defence**:

1. **Extract** the JSON array with a regex (tolerates surrounding chatter).
2. **Validate each item** — drop segments with empty narration, clamp headings.
3. **Fall back** to line-based segments if JSON parsing fails entirely, so you
   *always* get a usable script.

> This is the pattern behind the Ollama run in
> [01-3](../01_foundations/03_environment_and_providers.md): `qwen2:7b` produced
> valid segment JSON (four chapters showed up), even though it fumbled the metadata
> format later. Structured-but-defensive wins.

---

## It's tested both ways

[`tests/test_nodes.py`](../99_project_faceless_studio/tests/test_nodes.py) has:

- `test_scriptwriter_parses_json_segments` — clean JSON → 2 segments.
- `test_scriptwriter_falls_back_on_non_json` — bullet text → still ≥1 segment,
  first one being the hook.

Both pass offline.

---

## Recap

- The scriptwriter emits the **segment list** the rest of the pipeline consumes.
- Ask for **JSON**, then parse in three layers: **extract → validate → fall back**.
- A pipeline that degrades gracefully beats one that crashes on a stray comma.

## Exercise

Add a hard cap: if the model returns more than 8 segments, keep the first 8. Then
add a *minimum* — if fewer than 3 come back, re-prompt once asking for more.
(Re-prompting inside a node is fine; just call `_ask` again.)

<details>
<summary>Hint</summary>

After `_parse_segments`, slice `segments[:8]`. For the minimum, wrap the
`_ask`+parse in a small loop that retries once with a stronger instruction like
"Return at least 5 segments." Guard the loop so it can't run forever.

</details>

---

**Next → [02-4 · Voiceover](04_voiceover.md)**
