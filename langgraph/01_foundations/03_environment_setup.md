# 01-3 · Environment setup

> **Level:** Beginner · **Prerequisites:** [01-1 · Core concepts](01_core_concepts.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0, langchain-ollama 1.1.0, Python 3.10)

## Why this matters

Every graph in this course was actually run. For that to be reproducible *for you*, we pin versions and standardise on one cheap chat model (`gpt-4o-mini`) with a free local fallback. This lesson sets up that environment and gives you one helper you'll reuse everywhere: `get_model()`.

---

## Pinned versions

Uses [uv](../../UV_GUIDE.md) as a drop-in for `venv` + `pip` (`curl -LsSf https://astral.sh/uv/install.sh | sh` if you don't have it).

```bash
uv venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
uv pip install \
  "langgraph==1.2.9" \
  "langchain-core==1.5.0" \
  "langgraph-checkpoint-sqlite==3.1.0" \
  langchain-openai                        # checkpoint-sqlite = SqliteSaver, Section 05
export OPENAI_API_KEY=sk-...              # from platform.openai.com
```

Check what you actually have if an import ever looks different:

```bash
uv pip show langgraph | grep -i version
```

---

## Two ways to get a model

This course uses two interchangeable chat models:

| Model | Needs | Cost | Use when |
|-------|-------|------|----------|
| `ChatOpenAI` (`gpt-4o-mini`) | `OPENAI_API_KEY` | cents for the whole course | **the default** — every lesson |
| `ChatOllama` (local) | Ollama + a pulled model | free (your CPU/GPU) | offline, private, no bills |

### OpenAI (default)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)   # reads OPENAI_API_KEY
print(llm.invoke("Reply with exactly: pong").content)   # → "pong"
```

`temperature=0` keeps replies as stable as an LLM gets — so the *graph*, not the model's mood, is what you're watching while you learn orchestration.

### The local model (optional, free & offline)

```bash
uv pip install langchain-ollama
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

> **Tip:** For agents that call **tools**, use a model that supports tool-calling. `qwen2.5` does; very small models sometimes don't. `gpt-4o-mini` is reliable at it — one reason it's the default.

---

## One helper to rule them all: `get_model()`

Drop this in a `providers.py` and import it in every example. It picks the model from an env var so you can flip the whole course between OpenAI and a local model with one setting:

```python
# providers.py
import os

def get_model(temperature=0):
    """Return a chat model chosen by the LANGGRAPH_LLM env var.

    LANGGRAPH_LLM=openai (default) → ChatOpenAI gpt-4o-mini (needs OPENAI_API_KEY)
    LANGGRAPH_LLM=ollama           → local ChatOllama (qwen2.5:0.5b)
    """
    if os.getenv("LANGGRAPH_LLM", "openai") == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                          temperature=temperature)
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature)
```

```python
from providers import get_model
llm = get_model()
print(llm.invoke("Capital of France? One word.").content)
```

**Output (representative):**
```
Paris
```

Run the same script with `LANGGRAPH_LLM=ollama python script.py` and it uses your local model instead — no code change.

---

## Recap & next

- ✅ Versions are pinned; `uv pip show langgraph` tells you what you actually have.
- ✅ Default to `ChatOpenAI` (`gpt-4o-mini`, `temperature=0`); flip to `ChatOllama` for free local generation.
- ✅ `get_model()` switches backends via `LANGGRAPH_LLM` — reuse it throughout.
- ✅ Self-check: why does `temperature=0` matter while you're learning orchestration?

→ Next: **[02 · Execution model](../02_execution_model/README.md)**

## Exercises

1. Write `providers.py` above, then run one script twice — once with the default (OpenAI) and once with `LANGGRAPH_LLM=ollama` (if you have Ollama) — and confirm both produce output.

<details>
<summary>Solution</summary>

```bash
python script.py                         # OpenAI (default)
LANGGRAPH_LLM=ollama python script.py    # local generation
```
Same graph, different backend — the point of the indirection.
</details>
