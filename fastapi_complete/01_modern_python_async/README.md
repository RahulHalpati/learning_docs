# Section 01 · Modern Python baseline

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~4 h

FastAPI is only as good as the Python underneath it. This section builds that floor: **uv** for reproducible environments and dependencies, **ruff** for lint + format, **type hints** as the runtime contract FastAPI actually reads, and **asyncio** — the event loop model that decides whether your service handles a thousand concurrent requests or chokes on ten.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 01-1 | [Tooling: uv & project setup](01_tooling_uv_project_setup.md) | How do I create a project my teammates and CI can reproduce exactly? |
| 01-2 | [Type hints for APIs](02_type_hints_for_apis.md) | Why does FastAPI care so much about type hints — and which ones matter? |
| 01-3 | [async/await mechanics](03_async_await_mechanics.md) | What is the event loop actually doing, and when do I write `async def`? |

## Mini-project

**Concurrent link checker** — a small CLI that proves you can wire all three lessons together.

Build a uv-managed project that reads a list of URLs (hard-coded list or a text file — your call), fetches them **concurrently** with `httpx.AsyncClient` + `asyncio.gather`, and prints one line per URL with its status code and latency.

Requirements checklist:

- [ ] Created with `uv init`, deps added with `uv add httpx`, runs via `uv run` — `pyproject.toml` and `uv.lock` committed.
- [ ] All URLs are fetched concurrently (`asyncio.gather` over one shared `httpx.AsyncClient`), not one-by-one.
- [ ] Per-URL output: status code (or the error) and latency in ms.
- [ ] A failing URL (timeout, DNS error) is reported — it must not crash the run or hide the other results.
- [ ] Fully type-hinted: every function signature annotated, `X | None` style, no bare `dict`/`list`.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` both pass clean.

Sanity check: 10 URLs at ~300 ms each should finish in ~0.5 s total, not ~3 s. If your total time is the sum of the latencies, you've built a sequential checker with async syntax.

## Test task (gate)

Before Section 02, pass this diagnosis-and-fix task. You're given a deliberately broken script:

```python
async def check(url: str) -> int:
    time.sleep(0.1)                    # "rate limiting"
    resp = requests.get(url)           # fetch
    return resp.status_code

async def main() -> None:
    for url in URLS:
        status = await check(url)      # one at a time
        print(url, status)
```

It's `async def` everywhere, yet 10 URLs take just as long as a plain sync script — sometimes longer. Your job:

1. **Diagnose** — identify every reason it's slow/blocking (there are three distinct problems in those nine lines).
2. **Fix** — rewrite it so the 10 URLs are actually fetched concurrently, using `httpx.AsyncClient`, `asyncio.sleep`, and `asyncio.gather`.
3. **Explain** — one paragraph: what was the event loop doing *before* your fix, and what does it do *after*?

**Passing means, exactly:**

- The fixed script completes 10 URLs **at least 5× faster** than the broken one (measure both with `time.perf_counter()` and show the numbers).
- Your paragraph **names the blocking calls by name** — `time.sleep` and `requests.get` — and states what they did to the loop: they block the single event-loop thread, so nothing else can run while they wait. It also names the third problem: `await` inside a `for` loop serializes the coroutines, so even non-blocking code runs one at a time until `gather` schedules them together.
- The fix is type-hinted and ruff-clean, same bar as the mini-project.

If any of those three is missing, it's not a pass — redo it. This gate exists because Section 02 onward assumes you can *see* blocking code on sight.

## What you'll be able to do after this section

- Spin up a reproducible Python 3.12+ project with uv and keep it lint-clean with ruff — the same commands locally and in CI.
- Read and write the type hints FastAPI is built on: `X | None`, generics, `Annotated`, and know when a `TypedDict`, dataclass, or Pydantic model is the right shape.
- Explain what an event loop is, spot a blocking call inside `async def`, and fix it.
- Run I/O-bound work concurrently with `asyncio.gather` and `httpx.AsyncClient`.
- Choose `async def` vs `def` for a FastAPI endpoint deliberately, not by superstition.

→ Start: **[01-1 · Tooling: uv & project setup](01_tooling_uv_project_setup.md)**
