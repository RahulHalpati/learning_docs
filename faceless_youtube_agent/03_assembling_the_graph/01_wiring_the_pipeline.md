# 03-1 · Wiring the pipeline

> **Level:** Beginner · **Time:** 20 min

Time to connect the six nodes. This is [`faceless_studio/graph.py`](../99_project_faceless_studio/faceless_studio/graph.py).

---

## Binding dependencies with `partial`

Nodes have different needs: LLM nodes want an `llm`, media nodes want a `workdir`.
But LangGraph calls every node with just `state`. `functools.partial` bridges the
gap — it pre-fills the extra arguments so what LangGraph calls is a one-arg function:

```python
from functools import partial
from langgraph.graph import StateGraph, START, END
from . import nodes

def build_graph(llm=None, *, workdir="out", interrupt_before=None):
    llm = llm or get_chat_model()
    workdir = Path(workdir)

    builder = StateGraph(VideoState)
    builder.add_node("researcher",   partial(nodes.topic_researcher, llm=llm))
    builder.add_node("scriptwriter", partial(nodes.script_writer,    llm=llm))
    builder.add_node("voiceover",    partial(nodes.voiceover,   workdir=workdir))
    builder.add_node("visuals",      partial(nodes.visuals,     workdir=workdir))
    builder.add_node("assembler",    partial(nodes.assembler,   workdir=workdir))
    builder.add_node("metadata",     partial(nodes.metadata,    llm=llm))
```

This is the same dependency-injection trick the
[Proposal Agent](../../langgraph_proposal_agent/) uses — learn it once, reuse it.
It also makes nodes trivially testable: in tests you call `nodes.voiceover(state,
workdir=tmp_path)` directly.

---

## The edges: a straight line

```python
    builder.add_edge(START, "researcher")
    builder.add_edge("researcher", "scriptwriter")
    builder.add_edge("scriptwriter", "voiceover")
    builder.add_edge("voiceover", "visuals")
    builder.add_edge("visuals", "assembler")
    builder.add_edge("assembler", "metadata")
    builder.add_edge("metadata", END)

    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=interrupt_before or [],
    )
```

No conditional edges in the main path — a content pipeline is deliberately linear.
The checkpointer is attached now so the human gate in the next module is a
one-argument change.

---

## The convenience runner

```python
def produce_video(topic, *, niche="short educational explainers",
                  workdir="out", thread_id="default", **kwargs):
    run_dir = Path(workdir) / _slug(topic)      # each run gets its own folder
    graph = build_graph(workdir=run_dir, **kwargs)
    return graph.invoke(
        {"topic": topic, "niche": niche},
        config={"configurable": {"thread_id": thread_id}},
    )
```

`_slug(topic)` turns *"Why RAM is faster than a hard disk"* into
`why-ram-is-faster-than-a-hard-disk`, so runs never clobber each other's files.

---

## Run the whole thing

```python
from faceless_studio import produce_video
final = produce_video("Big-O notation for beginners")
print(final["log"])          # ['researcher','scriptwriter','voiceover','visuals','assembler','metadata']
print(final["video_path"])   # out/big-o-notation-for-beginners/video.mp4
```

`test_full_pipeline_produces_mp4` in
[`tests/test_graph.py`](../99_project_faceless_studio/tests/test_graph.py) runs
exactly this offline and asserts the `.mp4` exists — it passes.

---

## Recap

- **`functools.partial`** injects each node's dependencies so LangGraph can call
  every node with just `state`.
- The main path is a **linear chain**; the checkpointer is attached up front for
  the coming human gate.
- `produce_video` gives each run its **own output folder** via a slug.

## Self-check

1. Why use `partial(nodes.voiceover, workdir=workdir)` instead of a global variable?
2. What would you add to make the graph loop back to the scriptwriter on a failed
   review?

<details>
<summary>Answers</summary>

1. It keeps nodes **pure and testable** (no hidden globals) while satisfying
   LangGraph's "call with only state" contract — and lets you build two graphs with
   different workdirs/LLMs in the same process.
2. A `reviewer` node plus `add_conditional_edges("reviewer", router, {"scriptwriter":
   "scriptwriter", END: END})`, where the router returns `"scriptwriter"` until
   `approved` is true or a revision cap is hit.

</details>

---

**Next → [03-2 · Human-in-the-loop & checkpoints](02_human_in_the_loop.md)**
