"""Model selection for the ADK capstone — offline by default.

ADK_LLM=fake   (default) → deterministic FakeAdkModel (no network)
ADK_LLM=ollama           → LiteLlm(ollama_chat/qwen2.5:0.5b) local generation
"""
import os

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class FakeAdkModel(BaseLlm):
    """Replays canned responses in order — offline, deterministic (for tests/CI)."""
    responses: list = []
    counter: dict = {}

    async def generate_content_async(self, llm_request, stream=False):
        i = self.counter.get("i", 0)
        text = self.responses[min(i, len(self.responses) - 1)] if self.responses else "(fake)"
        self.counter["i"] = i + 1
        yield LlmResponse(content=types.Content(role="model",
                                                parts=[types.Part(text=text)]))


def get_model(responses=None):
    """Return a model chosen by ADK_LLM. `responses` is used only for the fake backend."""
    if os.getenv("ADK_LLM", "fake") == "ollama":
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model=os.getenv("OLLAMA_MODEL", "ollama_chat/qwen2.5:0.5b"))
    return FakeAdkModel(model="fake", responses=responses or ["(fake response)"])
