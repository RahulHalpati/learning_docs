"""Choose the chat model the agents will use — without the agents caring which.

Controlled by the ``PROPOSAL_LLM`` environment variable:

* ``ollama``    — a local model (no API key). The default.
* ``anthropic`` — Claude (needs ANTHROPIC_API_KEY).
* ``openai``    — OpenAI / any OpenAI-compatible endpoint (needs OPENAI_API_KEY).
* ``fake``      — a built-in canned model. Zero setup; used by the tests.

If the chosen provider can't be created (missing package/key), it falls back to
the fake model so the app always runs.
"""

from __future__ import annotations

import os

from langchain_core.language_models import GenericFakeChatModel
from langchain_core.language_models.chat_models import BaseChatModel

# Canned replies the fake model cycles through (enough for one full run + a revision).
_FAKE_REPLIES = [
    "Requirements: Python, FastAPI. Budget: healthy. Timeline: ~2 weeks. "
    "Pain point: needs a clean API fast. Red flags: none.",
    "Best project: Typed Python SDK (HIGH fit) — same stack, shows you ship polished APIs.",
    "Hi — I build exactly this. I recently shipped a typed Python/FastAPI API... "
    "[draft]. Happy to start this week.",
    "APPROVED",
]


def get_chat_model(*, temperature: float = 0.3) -> BaseChatModel:
    """Return a chat model based on $PROPOSAL_LLM, falling back to a fake one."""
    provider = os.environ.get("PROPOSAL_LLM", "ollama").lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=os.environ.get("OLLAMA_MODEL", "qwen2:7b"),
                temperature=temperature,
            )
        except Exception:
            provider = "fake"

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

    # Fallback / explicit: a canned model. No network, no key.
    return GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
