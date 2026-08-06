"""Minimal tracer: spans, token/cost accounting, JSON export.

This is a teaching-sized version of what Langfuse/OpenTelemetry give you. The
shape is deliberately the same — nested spans with attributes — so moving to a
real backend later is a swap, not a rewrite.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Illustrative per-1K-token prices. Real numbers change constantly — keep them
# in config, never scattered through code.
PRICES_PER_1K = {
    "demo-small": {"input": 0.0005, "output": 0.0015},
    "demo-large": {"input": 0.0100, "output": 0.0300},
}


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICES_PER_1K.get(model, {"input": 0.0, "output": 0.0})
    return round(prompt_tokens / 1000 * p["input"] + completion_tokens / 1000 * p["output"], 6)


@dataclass
class Span:
    name: str
    span_id: str
    parent_id: str | None
    start: float
    end: float | None = None
    attributes: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return round(((self.end or self.start) - self.start) * 1000, 2)


class Trace:
    """One end-to-end request: a tree of spans plus rolled-up usage."""

    def __init__(self, name: str, trace_id: str | None = None, clock=time.perf_counter):
        self.name = name
        self.trace_id = trace_id or uuid.uuid4().hex[:12]
        self.spans: list[Span] = []
        self._stack: list[str] = []
        self._clock = clock            # injectable so tests are deterministic

    @contextmanager
    def span(self, name: str, **attributes):
        s = Span(name=name, span_id=uuid.uuid4().hex[:8],
                 parent_id=self._stack[-1] if self._stack else None,
                 start=self._clock(), attributes=dict(attributes))
        self.spans.append(s)
        self._stack.append(s.span_id)
        try:
            yield s
        finally:
            s.end = self._clock()
            self._stack.pop()

    def record_llm(self, span: Span, *, model: str, prompt_tokens: int,
                   completion_tokens: int) -> None:
        """Attach usage + cost to an LLM span."""
        span.attributes.update(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd(model, prompt_tokens, completion_tokens),
        )

    # ---------------------------------------------------------------- rollups
    @property
    def total_tokens(self) -> int:
        return sum(s.attributes.get("total_tokens", 0) for s in self.spans)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(s.attributes.get("cost_usd", 0.0) for s in self.spans), 6)

    @property
    def duration_ms(self) -> float:
        if not self.spans:
            return 0.0
        return round((max(s.end or s.start for s in self.spans)
                      - min(s.start for s in self.spans)) * 1000, 2)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "spans": [asdict(s) | {"duration_ms": s.duration_ms} for s in self.spans],
        }

    def export(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path
