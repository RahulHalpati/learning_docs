# 02-2 · Researcher

> **Level:** Beginner · **Time:** 20 min

The first node turns a bare topic into a **hook + angle + key points**. The hook
matters most — on YouTube, the first line decides whether anyone stays.

This is `topic_researcher` in [`faceless_studio/nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py).

---

## The one-shot chat helper

Every LLM node uses the same tiny helper so real and fake models behave the same:

```python
from langchain_core.messages import HumanMessage, SystemMessage

def _ask(llm, system: str, human: str) -> str:
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    return (resp.content or "").strip()
```

Passing a list of messages (not a template) keeps it dead simple and works with
`ChatOllama`, `ChatAnthropic`, and the `GenericFakeChatModel` alike.

---

## The node

```python
import re

def topic_researcher(state, *, llm) -> dict:
    niche = state.get("niche", "short educational explainers")
    system = (
        "You are a YouTube content researcher for a faceless channel. "
        f"The niche is: {niche}. Be concrete and retention-focused."
    )
    human = (
        f"Topic: {state['topic']}\n\n"
        "Return exactly this shape:\n"
        "HOOK: <one punchy opening line>\n"
        "ANGLE: <the specific angle in one sentence>\n"
        "POINTS:\n- <point 1>\n- <point 2>\n- <point 3>"
    )
    research = _ask(llm, system, human)

    hook_match = re.search(r"HOOK:\s*(.+)", research)
    hook = hook_match.group(1).strip() if hook_match else state["topic"]
    return {"research": research, "hook": hook, "log": ["researcher"]}
```

Three things to note:

- **The niche steers tone.** It's part of the system prompt, so the same topic
  produces different framing for "tech explainers" vs "true crime".
- **We ask for a fixed shape** (`HOOK:` / `ANGLE:` / `POINTS:`) so the next node
  has something predictable to read.
- **We extract the hook defensively.** If the model doesn't emit `HOOK:`, we fall
  back to the topic itself. Never trust an LLM to follow format 100% of the time —
  especially a small local one.

---

## Run just this node

```python
from langchain_core.language_models import GenericFakeChatModel
from faceless_studio import nodes

llm = GenericFakeChatModel(messages=iter([
    "HOOK: Ever wonder why your code crawls at scale?\nANGLE: calm explainer\nPOINTS:\n- a\n- b"
]))
print(nodes.topic_researcher({"topic": "Big-O"}, llm=llm))
```

```
{'research': 'HOOK: Ever wonder why your code crawls at scale?\nANGLE: ...',
 'hook': 'Ever wonder why your code crawls at scale?',
 'log': ['researcher']}
```

The matching test is `test_researcher_extracts_hook` in
[`tests/test_nodes.py`](../99_project_faceless_studio/tests/test_nodes.py) — it
passes offline.

---

## Recap

- The researcher frames the video: **hook, angle, points**.
- A shared `_ask` helper makes every LLM node model-agnostic.
- Ask for a **fixed text shape** and **parse defensively** with a fallback.

## Exercise

Make the researcher also return an estimated **target length** (e.g. "60s",
"3min") based on the topic, and add it to the state. Steer the scriptwriter with
it later.

<details>
<summary>Hint</summary>

Add `LENGTH: <estimate>` to the requested shape, parse it with another
`re.search`, add a `target_length` key to `VideoState`, and include it in the
scriptwriter's prompt. Keep a sensible default if the model omits it.

</details>

---

**Next → [02-3 · Scriptwriter](03_scriptwriter.md)**
