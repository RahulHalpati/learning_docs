# 01-3 · Environment & offline models

> **Level:** Beginner · **Prerequisites:** [01-1 · Architecture & primitives](01_architecture_and_primitives.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0, litellm 1.93.0, Ollama qwen2.5:0.5b)

## Why this matters

ADK is built for Gemini/Vertex, but this course runs with **no API key**. Two models make that possible: a local **Ollama** model (via LiteLLM) for real generation, and a **fake `BaseLlm`** for deterministic tests. Set them up once here and every later lesson runs on your laptop.

---

## Install

```bash
pip install "google-adk==2.5.0" "litellm==1.93.0"
# real local generation:
ollama pull qwen2.5:0.5b        # ~400 MB, CPU-friendly
```

---

## Real generation: `LiteLlm` → Ollama

ADK reaches any non-Gemini model through **LiteLLM**. The `ollama_chat/` provider prefix points at your local Ollama server:

```python
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import LlmAgent

model = LiteLlm(model="ollama_chat/qwen2.5:0.5b")     # local, no key
agent = LlmAgent(name="a", model=model, instruction="Be concise.")
```

> ⚠️ Use `ollama_chat/`, **not** `ollama/`. The plain `ollama/` provider can cause tool-call loops and dropped context; `ollama_chat/` uses the chat-completions API and behaves correctly with ADK.

You saw this run end to end in [the introduction](../00_introduction.md) ("Hello Ada, welcome!").

---

## Deterministic tests: a fake `BaseLlm`

Local models are *real* but non-deterministic — bad for a test suite. For verified, repeatable runs, subclass `BaseLlm` to replay canned responses:

```python
# fake_model.py
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

class FakeAdkModel(BaseLlm):
    """Replays canned text responses in order — offline, deterministic."""
    responses: list = []
    counter: dict = {}                       # pydantic-friendly mutable cursor

    async def generate_content_async(self, llm_request, stream=False):
        i = self.counter.get("i", 0)
        text = self.responses[min(i, len(self.responses) - 1)]
        self.counter["i"] = i + 1
        yield LlmResponse(content=types.Content(role="model",
                                                parts=[types.Part(text=text)]))
```

Drop it in wherever a model goes:

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from fake_model import FakeAdkModel

agent = LlmAgent(name="fake_agent",
                 model=FakeAdkModel(model="fake", responses=["Deterministic hello!"]),
                 instruction="(ignored by the fake)")

async def main():
    runner = InMemoryRunner(agent=agent, app_name="d")
    s = await runner.session_service.create_session(app_name="d", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="hi")])
    async for e in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        if e.is_final_response():
            print(e.content.parts[0].text)

asyncio.run(main())
```

**Output (real run):**
```
Deterministic hello!
```

The fake ignores the prompt and returns its scripted text — so your *agent wiring* (orchestration, tools, state) is what the test verifies, independent of any model's mood. This course's tests use exactly this pattern; `qwen2.5:0.5b` is for when you want to see real generation.

> **Note:** `BaseLlm` is a Pydantic model, so we keep the response cursor in a `counter` dict field rather than a plain attribute.

---

## Picking a backend

| Model | Needs | Deterministic? | Use for |
|-------|-------|:---:|---------|
| `FakeAdkModel` | nothing | ✅ | tests / CI / learning wiring |
| `LiteLlm("ollama_chat/…")` | Ollama + a pulled model | ⚠️ | real local generation |
| `LiteLlm("gemini/…")` / Vertex | API key / GCP | ❌ | production |

---

## Recap & next

- ✅ `LiteLlm("ollama_chat/qwen2.5:0.5b")` gives real, offline generation (use `ollama_chat/`, not `ollama/`).
- ✅ A `FakeAdkModel(BaseLlm)` replays canned responses for deterministic, verified tests.
- ✅ All three backends slot into `LlmAgent(model=...)` interchangeably.
- ✅ Self-check: why do the course's *tests* use the fake model instead of Ollama?

→ Next: **[01-4 · Your first agent](04_your_first_agent.md)**

## Exercises

1. Give `FakeAdkModel` two responses and call the agent twice on the same session; confirm you get them in order.

<details>
<summary>Solution</summary>

`FakeAdkModel(model="f", responses=["first", "second"])` — the `counter` advances across calls, so the first run yields "first" and the second yields "second". (Re-create the model to reset.)
</details>
