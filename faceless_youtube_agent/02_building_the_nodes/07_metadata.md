# 02-7 · Metadata & SEO

> **Level:** Beginner · **Time:** 15 min

The last node writes what YouTube actually indexes: a **title**, a **description
with chapters**, and **tags**. This is `metadata` in
[`nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py).

---

## The node

```python
def metadata(state, *, llm) -> dict:
    system = (
        "You are a YouTube SEO assistant. Write a click-worthy but honest title "
        "(<=70 chars), a 2-3 sentence description, and comma-separated tags."
    )
    human = (
        f"Topic: {state['topic']}\nResearch:\n{state.get('research', '')}\n\n"
        "Return exactly:\nTITLE: ...\nDESCRIPTION: ...\nTAGS: tag1, tag2, tag3"
    )
    raw = _ask(llm, system, human)

    title = _field(raw, "TITLE") or state["topic"]
    description = _field(raw, "DESCRIPTION") or ""
    tags = [t.strip() for t in (_field(raw, "TAGS") or "").split(",") if t.strip()]

    # auto-generate chapter markers from segment durations
    chapters, t = [], 0.0
    for seg in state.get("segments", []):
        mm, ss = divmod(int(t), 60)
        chapters.append(f"{mm:02d}:{ss:02d} {seg['heading']}")
        t += float(seg.get("duration") or 0)
    if chapters:
        description += "\n\nChapters:\n" + "\n".join(chapters)

    return {"title": title, "description": description, "tags": tags,
            "log": ["metadata"]}
```

---

## Two things worth calling out

### 1. Chapters are computed, not guessed

YouTube renders **chapter markers** if your description contains lines like
`00:00 Intro`. We don't ask the LLM for these — we *compute* them by walking the
segment durations the voiceover node measured. Deterministic data (timings) should
come from code, not a model. From the verified Ollama run:

```
Chapters:
00:00 RAM Speed
00:02 HDD Latency
00:04 Memory Retention
00:06 Cost vs. Speed
```

### 2. Every field has a fallback

`_field` returns `""` if the model didn't emit that label, and we default the
title to the topic. This is exactly the case you saw in
[01-3](../01_foundations/03_environment_and_providers.md): `qwen2:7b` didn't print
`TITLE:` in the expected shape, so the title fell back to *"Why RAM is faster than
a hard disk"* — still perfectly usable. **A pipeline that always produces valid
metadata beats one that produces perfect metadata 80% of the time.**

```python
def _field(text, key):
    m = re.search(rf"{key}:\s*(.+)", text)
    return m.group(1).strip() if m else ""
```

---

## The output is upload-ready

The CLI writes this next to the video as `metadata.json`:

```json
{
  "title": "Why Your Code Slows Down (Big-O Explained in 3 Minutes)",
  "description": "A no-fluff explainer ...\n\nChapters:\n00:00 The Hook\n...",
  "tags": ["big o", "algorithms", "time complexity", "coding", ...]
}
```

That's exactly the shape the [YouTube upload node](../04_publishing_and_serving/01_youtube_upload.md)
consumes.

---

## Recap

- Metadata is the SEO surface: **title, description + chapters, tags**.
- **Compute** deterministic data (chapter timings) in code; only ask the LLM for
  the creative text.
- **Default every field** so you always get valid, uploadable metadata.

## Exercise

Enforce YouTube's real limits: title ≤ 100 chars, description ≤ 5000 chars, ≤ 500
tags, and each tag ≤ 30 chars. Truncate/drop anything over. (The upload node also
clamps, but clamping early makes the `metadata.json` honest.)

<details>
<summary>Hint</summary>

`title[:100]`, `description[:5000]`, `[t[:30] for t in tags][:500]`. Do it right
before the `return`.

</details>

---

**Next → [03-1 · Wiring the pipeline](../03_assembling_the_graph/01_wiring_the_pipeline.md)**
