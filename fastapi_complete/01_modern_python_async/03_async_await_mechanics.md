# 01-3 · async/await mechanics

> **Level:** Beginner · **Prerequisites:** [01-2 · Type hints for APIs](02_type_hints_for_apis.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (Python 3.12 · asyncio · httpx)

## Why this matters

A backend spends most of its life *waiting* — for the database, for another service, for a slow client. Async is how one Python process serves thousands of concurrent requests through those waits instead of one at a time. It's also the sharpest knife in the FastAPI drawer: a single blocking call inside `async def` doesn't slow one request, it **freezes every request in the process**. Understanding the event loop is the difference between writing async code and writing sync code with extra keywords.

---

## The event loop mental model

Forget threads for a moment. Asyncio is **one thread running one loop**:

```text
Event loop (single thread):
┌─────────────────────────────────────────────────┐
│  run task A ── A awaits network ── park A       │
│  run task B ── B awaits DB      ── park B       │
│  run task C ── C awaits network ── park C       │
│  ...A's response arrived → resume A...          │
└─────────────────────────────────────────────────┘
```

The loop runs one task until that task **volunteers a pause** at an `await` on something not ready yet (a socket, a timer). The loop parks it, remembers what it's waiting for, and runs whoever *is* ready. Concurrency comes from interleaving waits, not from parallel execution — at any instant, exactly one piece of your Python code is running.

Two consequences fall straight out of this model:

- **Cooperative means voluntary.** A task that never awaits never yields. The loop cannot interrupt it — it can only wait for it to hand control back.
- **Await points are the only switching points.** Between two awaits, your code runs uninterrupted — which is also why async code needs far fewer locks than threaded code.

---

## Coroutines vs functions

`async def` changes what *calling* the function means:

```python
import asyncio

async def fetch_score() -> int:
    await asyncio.sleep(1)      # pretend network call
    return 42

fetch_score()                    # ← does NOT run the body!
                                 #   returns a coroutine object (and a warning)

score = await fetch_score()      # runs it — only valid inside another coroutine

asyncio.run(fetch_score())       # the entry point: starts a loop, runs it to completion
```

A coroutine is a *description of work* the loop can run, pause, and resume — calling `async def` just builds that description. This is the number-one beginner bug: a forgotten `await` doesn't crash, it silently does nothing (`RuntimeWarning: coroutine was never awaited`). If a result never shows up, look for a missing `await` first.

---

## Blocking vs non-blocking — the one distinction that matters

Same one-second pause, opposite behavior under the loop:

```python
import time, asyncio

async def bad() -> None:
    time.sleep(1)           # BLOCKS the thread. The loop is dead for 1 s.
                            # Every other task — every other request — waits.

async def good() -> None:
    await asyncio.sleep(1)  # PARKS this task. The loop runs others,
                            # resumes here when the timer fires.
```

`time.sleep`, `requests.get`, a sync DB driver, reading a big file with plain `open()` — these never hit an `await`, so the loop never gets control back. **Being inside `async def` does not make a call non-blocking.** The call itself must be async (an awaitable) for the loop to interleave it. This is why the async ecosystem re-implements clients: **httpx** instead of requests, **asyncpg/aiosqlite** instead of sync drivers — their I/O yields to the loop.

Scale of the failure mode: one endpoint doing a 500 ms `requests.get` under 100 concurrent requests doesn't cost 500 ms — it serializes the process. That's how "we went async for performance" services end up *slower* than the sync version they replaced.

---

## asyncio.gather — actually running things concurrently

`await` in a loop is still sequential — each iteration parks *and waits for that one task* before starting the next:

```python
import asyncio
import httpx

URLS = [f"https://example.com/{i}" for i in range(10)]

async def fetch(client: httpx.AsyncClient, url: str) -> int:
    resp = await client.get(url)
    return resp.status_code

async def main() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:   # one client, shared pool
        # Sequential — total time = SUM of latencies:
        # for url in URLS:
        #     await fetch(client, url)

        # Concurrent — total time ≈ the SLOWEST single request:
        statuses = await asyncio.gather(
            *(fetch(client, url) for url in URLS),
            return_exceptions=True,   # one failure shouldn't nuke the other 9 results
        )
    print(statuses)

asyncio.run(main())
```

`gather` hands all ten coroutines to the loop at once; the ten network waits overlap, and 10 × 300 ms becomes ~300 ms total. Notes that matter in production:

- **One `AsyncClient` for the batch**, not one per request — it owns the connection pool, exactly like the DB engine you'll meet in the data-layer section.
- **`return_exceptions=True`** turns failures into values in the result list, so you can report "URL 7 timed out" alongside nine successes instead of losing everything to one bad URL.
- Unbounded fan-out is a foot-gun at real scale — 10 000 URLs means 10 000 sockets. Cap it with `asyncio.Semaphore` when the list is big.

---

## When you must block: run_in_executor

Sometimes there's no async version — a legacy SDK, or CPU-heavy work like hashing and image resizing. Don't call it on the loop; hand it to a thread:

```python
import asyncio

def resize_image(data: bytes) -> bytes:     # sync, CPU-heavy — note: plain def
    ...

async def handle(data: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    # Runs in a worker thread; the event loop stays free to serve others.
    return await loop.run_in_executor(None, resize_image, data)
```

The loop parks `handle` at the `await` and keeps serving other tasks while the thread grinds. One caveat: for **CPU-bound** work, threads only protect the loop's responsiveness — Python's GIL means the computation itself isn't parallelized. Truly heavy CPU work (ML inference, video encoding) belongs in a `ProcessPoolExecutor` or a separate worker service. Rule: **I/O-bound → async (or threads for sync libs); CPU-bound → processes.**

---

## How FastAPI uses all of this — `async def` vs `def`

FastAPI accepts both endpoint styles and treats them very differently:

```python
@app.get("/async-endpoint")
async def a() -> dict[str, str]:
    # Runs ON the event loop. Awaited I/O interleaves with other requests.
    # A blocking call here stalls the ENTIRE process.
    ...

@app.get("/sync-endpoint")
def b() -> dict[str, str]:
    # FastAPI runs this in a THREADPOOL (via run_in_executor, same mechanism
    # as above). Blocking calls are fine — they only occupy one thread.
    ...
```

That threadpool trick is why naive FastAPI apps "work" with blocking code — until they don't: the pool has a fixed number of threads (dozens, not thousands), so `def` endpoints cap your concurrency at pool size. The decision rule:

| Your endpoint's work | Write | Why |
|---|---|---|
| Async I/O (httpx, async DB driver) | `async def` + `await` | Full event-loop concurrency — thousands of waits interleave |
| Only sync/blocking libraries | plain `def` | FastAPI's threadpool absorbs the blocking; the loop stays safe |
| CPU-heavy | `def` (or offload to a worker) | Never occupy the loop; threads/processes take the hit |

The one **unforgivable** combination is `async def` with blocking calls inside — it's slower than either correct option and stalls everyone. If you take a single rule from this lesson, take that one.

---

## Recap & next

- ✅ One thread, one loop: tasks interleave at **await points**; the loop can never interrupt code that doesn't yield.
- ✅ Calling `async def` builds a coroutine; only `await` (or `asyncio.run`) executes it — a missing `await` fails *silently*.
- ✅ `time.sleep` / `requests` / sync drivers block the loop and freeze **every** request; use `asyncio.sleep` / httpx / async drivers.
- ✅ `asyncio.gather` overlaps waits: total time ≈ slowest task, not the sum — with `return_exceptions=True` so one failure doesn't eat the batch.
- ✅ FastAPI: `async def` for async I/O, plain `def` (threadpool) for blocking libraries, never blocking code inside `async def`.
- ✅ Self-check: an `async def` endpoint calls `requests.get` and "works fine" in local testing with one user. Explain precisely what changes at 200 concurrent users — and why moving it to `def` *or* switching to httpx both fix it.

→ Next: **[Section 02 · FastAPI fundamentals & Pydantic](../02_fastapi_fundamentals_pydantic/README.md)**

## Exercises

1. Without running it, predict this program's total runtime, then verify:

```python
import asyncio, time

async def step(n: int) -> None:
    await asyncio.sleep(1)
    print(f"step {n} done")

async def main() -> None:
    start = time.perf_counter()
    for n in range(3):
        await step(n)
    await asyncio.gather(step(3), step(4), step(5))
    print(f"total: {time.perf_counter() - start:.1f}s")

asyncio.run(main())
```

<details>
<summary>Solution</summary>

**~4 seconds.** The `for` loop awaits each `step` to completion before starting the next — 3 × 1 s sequential. The `gather` starts steps 3–5 together, so their three 1 s sleeps overlap into ~1 s. Sequential awaits add; gathered awaits overlap. This is exactly the gate task's third bug in miniature.
</details>

2. Take the `gather` example from this lesson and swap `await asyncio.sleep(1)` for `time.sleep(1)` inside `fetch` (simulate with a fake fetch that just sleeps). Measure both versions with `time.perf_counter()`. Explain the numbers in terms of the event loop.

<details>
<summary>Solution</summary>

The `asyncio.sleep` version finishes in ~1 s: all ten tasks park at their await, the ten timers run concurrently, the loop resumes them as they fire. The `time.sleep` version takes ~10 s *even under gather*: each task blocks the loop's only thread for its full second, so the loop can't switch to the next task until the current one's sleep returns. `gather` schedules tasks concurrently, but concurrency only happens at await points — blocking calls remove the await points.
</details>

3. For each endpoint, choose `async def` or `def` and justify it in one sentence: (a) proxies a request to another service with httpx; (b) generates a PDF with a CPU-heavy sync library, ~2 s; (c) reads a row using a sync-only database client.

<details>
<summary>Solution</summary>

- (a) **`async def`** — httpx is async; awaiting the upstream call lets the loop serve other requests during the network wait.
- (b) **`def`** — CPU-heavy sync work would freeze the loop inside `async def`; the threadpool absorbs it (and at real volume, move it to a background worker — 2 s of CPU per request exhausts any threadpool fast).
- (c) **`def`** — the client blocks, so it must not run on the loop; threadpool it, and put "switch to an async driver" on the roadmap since pool size now caps DB concurrency.
</details>
