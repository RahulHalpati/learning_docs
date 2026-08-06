"""Guardrails: checks that run on live traffic, not just in the eval suite.

Evals tell you how good the system is *before* you ship. Guardrails stop a bad
input or output *while* it's happening. You need both.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\b(?:\+?\d[\d\s-]{8,}\d)\b")
CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

INJECTION_PATTERNS = [
    r"ignore (?:all |the )?(?:previous|prior|above) instructions",
    r"disregard (?:all |the )?(?:previous|prior|above)",
    r"you are now .{0,30}(?:dan|jailbroken|unrestricted)",
    r"reveal (?:your )?(?:system )?prompt",
    r"print (?:your )?(?:system )?(?:prompt|instructions)",
]


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.allowed


def redact_pii(text: str) -> str:
    """Mask PII before it reaches a model, a log, or a trace."""
    text = EMAIL.sub("[EMAIL]", text)
    text = CARD.sub("[CARD]", text)
    text = PHONE.sub("[PHONE]", text)
    return text


def check_injection(text: str) -> GuardResult:
    """Cheap prompt-injection screen for obvious override attempts."""
    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardResult(False, "possible prompt injection")
    return GuardResult(True)


def check_output_grounded(answer: str, context: list[str], threshold: float = 0.6) -> GuardResult:
    """Block answers not supported by the retrieved context (anti-hallucination)."""
    from evalkit.metrics import faithfulness
    score = faithfulness(answer, context)
    if score < threshold:
        return GuardResult(False, f"ungrounded answer (faithfulness {score} < {threshold})")
    return GuardResult(True)


def check_length(text: str, max_chars: int = 2000) -> GuardResult:
    if len(text) > max_chars:
        return GuardResult(False, f"input too long ({len(text)} > {max_chars})")
    return GuardResult(True)


def guard_input(text: str) -> tuple[str, GuardResult]:
    """Run the input pipeline: length -> injection -> redact."""
    if not (result := check_length(text)):
        return text, result
    if not (result := check_injection(text)):
        return text, result
    return redact_pii(text), GuardResult(True)
