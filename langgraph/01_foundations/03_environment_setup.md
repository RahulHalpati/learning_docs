# 01-3 · Environment setup (offline, no API key)

> **Level:** Beginner · **Prerequisites:** [01-1 · Core concepts](01_core_concepts.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0, langchain-ollama 1.1.0, Python 3.10)

## Why this matters

Every sample in this course is **verified** — actually run, with real output shown. For that to be reproducible *for you*, we pin versions and default to a model that needs no key and no network. This lesson sets up that environment and gives you one helper you'll reuse everywhere: `get_model()`.

---

## Pinned versions

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install \
  "langgraph==1.2.9" \
  "langchain-core==1.5.0" \
  "langgraph-checkpoint-sqlite==3.1.0"   # SqliteSaver, used in Section 05
```

Check what you actually have if an import ever looks different:

```bash
pip show langgraph | grep -i version
```

---

## Three ways to get a model

This course uses three interchangeable chat models, in increasing order of realism:

| Model | Needs | Deterministic? | Use when |
|-------|-------|:---:|----------|
| `FakeListChatModel` | nothing | ✅ yes | learning wiring, tests, CI — **the default** |
| `ChatOllama` (local) | Ollama + a pulled model | ⚠️ mostly | you want real generation, still offline |
| real API (OpenAI/…) | an API key | ❌ no | production |

### The fake model (default)

```python
from langchain_core.language_models.fake_chat_models import FakeListChatModel

llm = FakeListChatModel(responses=["first reply", "second reply"])
print(llm.invoke("anything").content)   # → "first reply"
print(llm.invoke("anything").content)   # → "second reply"
```

It returns your canned `responses` in order — so the *graph*, not the LLM, is what varies. That's exactly what you want while learning orchestration.

### The local model (optional, real generation)

```bash
pip install langchain-ollama
ollama pull qwen2.5:0.5b     # ~400 MB, runs on CPU
```

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(model="qwen2.5:0.5b", temperature=0)
print(llm.invoke("Reply with exactly: pong").content)
```

**Output (real run):**
```
Pong!
```

> **Tip:** For agents that call **tools**, use a model that supports tool-calling. `qwen2.5` does; very small models sometimes don't. When in doubt, the fake model lets you script exact tool calls (shown in [03-2](../03_building_graphs/02_tools_and_react.md)).

---

## One helper to rule them all: `get_model()`

Drop this in a `providers.py` and import it in every example. It picks the model from an env var so you can flip the whole course between fake and local with one setting:

```python
# providers.py
import os

def get_model(responses=None, temperature=0):
    """Return a chat model chosen by the LANGGRAPH_LLM env var.

    LANGGRAPH_LLM=fake   (default) → offline, deterministic FakeListChatModel
    LANGGRAPH_LLM=ollama           → local ChatOllama (qwen2.5:0.5b)
    """
    backend = os.getenv("LANGGRAPH_LLM", "fake")
    if backend == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                          temperature=temperature)
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    return FakeListChatModel(responses=responses or ["(fake response)"])
```

```python
from providers import get_model
llm = get_model(responses=["Paris"])
print(llm.invoke("Capital of France?").content)
```

**Output (real run, `LANGGRAPH_LLM` unset → fake):**
```
Paris
```

Run the same script with `LANGGRAPH_LLM=ollama python script.py` and it uses your local model instead — no code change.

---

## Recap & next

- ✅ Versions are pinned; `pip show langgraph` tells you what you actually have.
- ✅ Default to `FakeListChatModel` (offline, deterministic); flip to `ChatOllama` for real local generation.
- ✅ `get_model()` switches backends via `LANGGRAPH_LLM` — reuse it throughout.
- ✅ Self-check: why does a *deterministic* model make a course "verifiable"?

→ Next: **[02 · Execution model](../02_execution_model/README.md)**

## Exercises

1. Write `providers.py` above, then run one script twice — once with `LANGGRAPH_LLM=fake` and once with `LANGGRAPH_LLM=ollama` (if you have Ollama) — and confirm both produce output.

<details>
<summary>Solution</summary>

```bash
LANGGRAPH_LLM=fake   python script.py    # deterministic canned reply
LANGGRAPH_LLM=ollama python script.py    # real local generation
```
Same graph, different backend — the point of the indirection.
</details>
