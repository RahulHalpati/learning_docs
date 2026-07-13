# 02-1 · Shared state

> **Level:** Beginner · **Time:** 15 min

Every node reads and writes one shared object. Design it well and the nodes almost
write themselves. This is [`faceless_studio/state.py`](../99_project_faceless_studio/faceless_studio/state.py).

---

## The segment — the unit of work

A video is a list of **segments**, each a slide + the narration over it. As a
segment flows through the pipeline it *accumulates* artifacts:

```python
from typing import TypedDict

class Segment(TypedDict, total=False):
    heading: str        # short on-screen title
    narration: str      # what the voice says
    visual_hint: str    # how the slide should look
    image_path: str     # ← filled by the visuals node
    audio_path: str     # ← filled by the voiceover node
    duration: float     # ← filled by the voiceover node (seconds)
```

`total=False` means "not every key must be present" — the scriptwriter creates the
first three; later nodes add the rest.

---

## The full state

```python
import operator
from typing import Annotated, TypedDict

class VideoState(TypedDict, total=False):
    # input
    topic: str
    niche: str

    # produced in order
    research: str
    hook: str
    segments: list[Segment]
    audio_path: str
    image_paths: list[str]
    video_path: str
    title: str
    description: str
    tags: list[str]

    # human gate
    approved: bool

    # observability
    log: Annotated[list[str], operator.add]
```

---

## Two design choices worth noticing

1. **`log` uses a reducer.** `Annotated[list[str], operator.add]` makes every
   node's `{"log": ["name"]}` *append* rather than overwrite (see
   [01-4](../01_foundations/04_langgraph_refresher.md)). The result is the ordered
   pipeline path.

2. **Everything else is a plain key.** Most fields are written by exactly one node,
   so they need no reducer — a later write just replaces the (absent) earlier value.
   `segments` is written by three nodes, but each **fully replaces** the list with
   an enriched copy, which is intentional (last-writer-wins on a whole object).

> **Rule of thumb:** use a reducer only for keys that *accumulate* across nodes.
> For "produced once, read later" keys, a plain type is simpler and clearer.

---

## Recap

- The **segment** is the core structure; it gains `audio_path`, `duration`, and
  `image_path` as it flows.
- `total=False` lets keys appear as the pipeline progresses.
- Only **accumulating** keys (`log`) need a reducer; single-writer keys don't.

## Self-check

1. Why is `Segment` declared with `total=False`?
2. Which state key uses a reducer, and why only that one?

<details>
<summary>Answers</summary>

1. Because a segment doesn't have all its fields at once — `image_path`,
   `audio_path`, and `duration` are added by later nodes. `total=False` allows the
   dict to be valid before those exist.
2. `log` — it's the one key multiple nodes append to. Every other key is written by
   a single node (or fully replaced), so it needs no merge rule.

</details>

---

**Next → [02-2 · Researcher](02_researcher.md)**
