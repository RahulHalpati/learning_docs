"""Choose the chat model the nodes will use — without the nodes caring which.

Controlled by the ``STUDIO_LLM`` environment variable:

* ``ollama``    — a local model (no API key). The default.
* ``anthropic`` — Claude (needs ANTHROPIC_API_KEY).
* ``openai``    — OpenAI / any OpenAI-compatible endpoint (needs OPENAI_API_KEY).
* ``fake``      — a built-in canned model. Zero setup; used by the tests.

If the chosen provider can't be created (missing package/key), it falls back to
the fake model so the pipeline always runs. This is the same pattern the
LangGraph Proposal Agent course uses — learn it once, reuse it everywhere.
"""

from __future__ import annotations

import os

from langchain_core.language_models import GenericFakeChatModel
from langchain_core.language_models.chat_models import BaseChatModel

# Canned replies the fake model cycles through — enough for one full pipeline run.
# Order matters: it matches the order the nodes call the model
# (researcher → scriptwriter → metadata).
_FAKE_REPLIES = [
    # 1. researcher
    "HOOK: Ever wonder why your code slows to a crawl at scale?\n"
    "ANGLE: A calm, concrete explainer for junior devs.\n"
    "POINTS:\n- What Big-O actually measures\n- O(n^2) vs O(n log n) in real terms\n"
    "- One refactor that fixed it",
    # 2. scriptwriter (returns JSON-ish segments the node parses leniently)
    '[{"heading": "The Hook", "narration": "Ever wonder why your code slows to a '
    'crawl at scale? Let us fix that in three minutes.", "visual_hint": "bold title card"},'
    '{"heading": "What Big-O measures", "narration": "Big-O describes how work grows '
    'as your input grows, not how fast one run is.", "visual_hint": "growth curve"},'
    '{"heading": "The refactor", "narration": "Swapping a nested loop for a hash map '
    'took us from O of n squared to O of n. Same result, a hundred times faster.", '
    '"visual_hint": "before/after code"}]',
    # 3. metadata
    "TITLE: Why Your Code Slows Down (Big-O Explained in 3 Minutes)\n"
    "DESCRIPTION: A no-fluff explainer on Big-O notation for junior developers. "
    "We cover what it measures and one refactor that made real code 100x faster.\n"
    "TAGS: big o, algorithms, time complexity, coding, computer science, programming",
]


def get_chat_model(*, temperature: float = 0.4) -> BaseChatModel:
    """Return a chat model based on $STUDIO_LLM, falling back to a fake one."""
    provider = os.environ.get("STUDIO_LLM", "ollama").lower()

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
                base_url=os.environ.get("OPENAI_BASE_URL"),  # optional compatible endpoint
                temperature=temperature,
            )
        except Exception:
            provider = "fake"

    # Fallback / explicit: a canned model. No network, no key.
    return GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
