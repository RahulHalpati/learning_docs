"""Evaluation metrics — deterministic first, so results are reproducible.

Every metric returns a float in [0, 1] (higher is better) so they can be
averaged, thresholded, and compared across runs uniformly.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


# ------------------------------------------------------------ string metrics
def exact_match(prediction: str, reference: str) -> float:
    """1.0 only if the normalized strings are identical."""
    return float(prediction.strip().lower() == reference.strip().lower())


def contains_answer(prediction: str, reference: str) -> float:
    """Did the answer include the expected span? Forgiving of extra prose."""
    return float(reference.strip().lower() in prediction.strip().lower())


def f1_overlap(prediction: str, reference: str) -> float:
    """Token-level F1 — the standard QA metric; partial credit for partial answers."""
    pred, ref = _tokens(prediction), _tokens(reference)
    if not pred or not ref:
        return float(pred == ref)
    common = set(pred) & set(ref)
    if not common:
        return 0.0
    precision = len(common) / len(set(pred))
    recall = len(common) / len(set(ref))
    return round(2 * precision * recall / (precision + recall), 4)


def jaccard(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta and not tb:
        return 1.0
    return round(len(ta & tb) / len(ta | tb), 4) if (ta | tb) else 0.0


# --------------------------------------------------------------- RAG metrics
def context_precision(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    """Of what we retrieved, how much was actually relevant? (precision)"""
    if not retrieved:
        return 0.0
    hits = sum(1 for doc in retrieved if doc in relevant)
    return round(hits / len(retrieved), 4)


def context_recall(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    """Of what was relevant, how much did we retrieve? (recall)"""
    if not relevant:
        return 1.0
    hits = sum(1 for doc in relevant if doc in retrieved)
    return round(hits / len(relevant), 4)


def hit_rate_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int = 3) -> float:
    """Did ANY relevant doc make the top-k? The blunt 'did retrieval work' check."""
    return float(any(doc in relevant for doc in list(retrieved)[:k]))


def faithfulness(answer: str, context: Sequence[str]) -> float:
    """Fraction of the answer's content words that are supported by the context.

    A cheap, deterministic groundedness proxy: unsupported words suggest the
    model invented something. Real tools (Ragas) use an LLM to decompose the
    answer into claims and verify each — same idea, better resolution.
    """
    answer_tokens = [t for t in _tokens(answer) if len(t) > 3]
    if not answer_tokens:
        return 1.0
    context_tokens = set()
    for doc in context:
        context_tokens.update(_tokens(doc))
    supported = sum(1 for t in answer_tokens if t in context_tokens)
    return round(supported / len(answer_tokens), 4)
