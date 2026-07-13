# 01-2 · Environment & Providers

> **Level:** Beginner · **Prerequisites:** [01-1 Problem & architecture](01_problem_and_architecture.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## Install

```bash
cd 99_project_proposal_agent
pip install -r requirements.txt
```

`requirements.txt` — annotated:

```
langgraph==1.1.10          # the graph engine
langchain-core>=1.3.2      # shared types (BaseChatModel, etc.)
pyyaml>=6.0                # profile.yaml loading

# LLM providers — install the one you want
langchain-ollama>=1.1.0    # local Ollama (default)
langchain-anthropic>=0.3.0 # Claude
langchain-openai>=1.2.1    # OpenAI / any compatible API

# Frontends
fastapi>=0.136.1
uvicorn[standard]>=0.34.0
streamlit>=1.45.0

# Testing
pytest>=9.0.0
httpx>=0.28.0              # FastAPI TestClient dep
```

---

## The provider pattern

One of the most practical patterns in this course: the agents **never import an LLM
directly**. They receive a `BaseChatModel` from `providers.py`.

This means you swap providers by setting one environment variable, not by editing
agent code.

```
PROPOSAL_LLM=fake      → GenericFakeChatModel  (built-in, zero setup)
PROPOSAL_LLM=ollama    → ChatOllama (default)
PROPOSAL_LLM=anthropic → ChatAnthropic (needs ANTHROPIC_API_KEY)
PROPOSAL_LLM=openai    → ChatOpenAI   (needs OPENAI_API_KEY)
```

### `proposal_agent/providers.py`

```python
import os
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.language_models.chat_models import BaseChatModel

_FAKE_REPLIES = [
    "Requirements: Python, FastAPI. Budget: healthy. Timeline: ~2 weeks. "
    "Pain point: needs a clean API fast. Red flags: none.",
    "Best project: Typed Python SDK (HIGH fit) — same stack, shows you ship polished APIs.",
    "Hi — I build exactly this. I recently shipped a typed Python/FastAPI API... "
    "[draft]. Happy to start this week.",
    "APPROVED",
]


def get_chat_model(*, temperature: float = 0.3) -> BaseChatModel:
    provider = os.environ.get("PROPOSAL_LLM", "ollama").lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=os.environ.get("OLLAMA_MODEL", "qwen2:7b"),
                temperature=temperature,
            )
        except Exception:
            provider = "fake"  # falls back if Ollama not running

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                temperature=temperature,
            )
        except Exception:
            provider = "fake"

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.environ.get("OPENAI_BASE_URL"),  # optional: any compatible endpoint
                temperature=temperature,
            )
        except Exception:
            provider = "fake"

    return GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
```

### Key design decisions

**`try/except` cascade:** If a provider fails (missing package, missing key, Ollama not
running), it falls back to the next provider and ultimately to `fake`. The app always
starts — you never get a cryptic import error at boot.

**`iter(_FAKE_REPLIES)`:** `GenericFakeChatModel` consumes the iterator as it gets
called. The four fake replies cover one full agent run (analyzer → matcher → writer →
reviewer). Tests supply their own `iter([...])` so they can script any scenario.

**`BaseChatModel` return type:** Agents are typed against `BaseChatModel`, not any
specific class. LangChain's LCEL `|` operator works with any `BaseChatModel`, so you
can swap providers without touching agent code.

---

## Verify the install (offline, 5 seconds)

```bash
PROPOSAL_LLM=fake python3 -c "
from proposal_agent.providers import get_chat_model
llm = get_chat_model()
print(type(llm).__name__)
"
```

Expected output:

```
GenericFakeChatModel
```

---

## Using Claude instead of Ollama

```bash
export PROPOSAL_LLM=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python -m proposal_agent.cli data/sample_jobs/fastapi_backend.txt
```

To use a different Claude model:

```bash
export ANTHROPIC_MODEL=claude-opus-4-8
```

> **Needs key:** Claude calls are not run in this course's offline examples.
> The provider wiring is verified; the live call is yours to try.

---

## Recap

- `get_chat_model()` returns any `BaseChatModel` — agents are provider-agnostic
- `try/except` cascade: always falls back to `fake`
- Swap providers with `PROPOSAL_LLM=` — no code changes needed
- The fake model enables **fully deterministic offline testing**

---

## Self-check

1. What happens if you set `PROPOSAL_LLM=anthropic` but forget to set `ANTHROPIC_API_KEY`?
2. Why does `providers.py` use `iter(_FAKE_REPLIES)` rather than just the list?
3. Could you add a Gemini provider without changing any agent code?

<details>
<summary>Answers</summary>

1. The `try/except` catches the error and falls back to `provider = "fake"` — the app
   still runs with canned replies.
2. `GenericFakeChatModel` expects an *iterator* — it calls `next()` on each LLM call.
   A bare list would raise `TypeError`.
3. Yes. Add an `if provider == "gemini":` branch to `providers.py` that returns a
   `BaseChatModel`-compatible Gemini wrapper. Agents and the graph stay untouched.

</details>

---

**Next → [03 LangGraph refresher](03_langgraph_refresher.md)**
