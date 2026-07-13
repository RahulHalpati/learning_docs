"""Optional LLM triage backend for `--explain`.

Chosen by the ``CODEAUDIT_LLM`` environment variable:

* ``fake``      — a built-in, dependency-free canned model. The default, so
                  ``--explain`` runs offline with nothing installed.
* ``ollama``    — a local model (needs `pip install langchain-ollama` + Ollama).
* ``anthropic`` — Claude (needs `langchain-anthropic` + ANTHROPIC_API_KEY).
* ``openai``    — OpenAI / compatible (needs `langchain-openai` + OPENAI_API_KEY).

The core auditor is pure stdlib; LangChain is imported **lazily** and only for a
real provider. If a real provider can't load, we fall back to the fake model so
`--explain` always works. Same pattern as the LangGraph Proposal Agent course.
"""

from __future__ import annotations

import itertools
import os
from types import SimpleNamespace

# Short, generic triage lines the fake model cycles through forever.
_FAKE_REPLIES = [
    "Likely a true positive. User-controlled data reaches a dangerous sink; "
    "confirm the input is reachable from an unauthenticated route, then fix at the sink.",
    "Real risk. Replace the dangerous construct with the safe equivalent "
    "(parameterised query / safe_load / env var) and add a regression test.",
    "Worth checking. If the value is always a trusted constant it may be a false "
    "positive — but prefer the safe API regardless.",
]


class _FakeChatModel:
    """Zero-dependency stand-in with the tiny slice of the chat interface we use."""

    def __init__(self):
        self._it = itertools.cycle(_FAKE_REPLIES)

    def invoke(self, _messages):
        return SimpleNamespace(content=next(self._it))


def get_chat_model(*, temperature: float = 0.2):
    """Return something with `.invoke(messages) -> obj.content`."""
    provider = os.environ.get("CODEAUDIT_LLM", "fake").lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=os.environ.get("OLLAMA_MODEL", "qwen2:7b"),
                              temperature=temperature)
        except Exception:
            provider = "fake"
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                                 temperature=temperature)
        except Exception:
            provider = "fake"
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                              temperature=temperature)
        except Exception:
            provider = "fake"

    return _FakeChatModel()


def explain(finding, model=None) -> str:
    """Ask the model whether a finding is a real risk and how to fix it."""
    model = model or get_chat_model()
    prompt = (
        "You are a security code reviewer. In 1-2 sentences, say whether this "
        "static-analysis finding is likely a real risk and how to fix it.\n\n"
        f"Rule {finding.rule_id} ({finding.cwe}) — {finding.severity}\n"
        f"{finding.file}:{finding.line}\n"
        f"Message: {finding.message}\n"
        f"Code: {finding.snippet}"
    )
    try:
        # real langchain models accept a list of (role, content) tuples
        resp = model.invoke([("system", "You are a concise security reviewer."),
                             ("human", prompt)])
        return (getattr(resp, "content", None) or str(resp)).strip()
    except Exception:
        resp = _FakeChatModel().invoke(prompt)
        return resp.content
