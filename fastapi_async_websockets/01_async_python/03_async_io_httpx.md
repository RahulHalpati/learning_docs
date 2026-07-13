# 03: Real async I/O with httpx

> **Level:** Beginner · **Prerequisites:** [02 · async / await](02_async_await.md)
> **Time:** ~1 hour · **Verified:** 2026-06-03 (Python 3.10.12, httpx 0.28.1)

## Why this matters

So far our "slow thing" has been `asyncio.sleep` — a fake wait. Real servers wait on **the network**: calling other APIs, including the LLM. This module shows how to do network I/O the async way with **httpx**, and — critically — why the popular `requests` library will silently *break* your async server. The httpx pattern here is exactly the one you'll use to call the LLM in Section 04.

## Concept: httpx and `AsyncClient`

[`httpx`](https://www.python-httpx.org/) is a modern HTTP client for Python. It looks like the familiar `requests` library, but it also has a fully **async** mode — which is what makes it safe inside FastAPI.

The async pattern has three parts:

```python
import httpx

async def get_json(url):
    async with httpx.AsyncClient() as client:   # 1. open a client (reusable connection pool)
        response = await client.get(url)         # 2. await the request (yields during the wait)
        return response.json()                   # 3. use the response
```

- **`httpx.AsyncClient()`** manages connections and is used as an `async with` block so it's cleanly closed afterward. (`async with` is the async version of a normal `with` block.)
- **`await client.get(url)`** sends the request and **yields control while waiting** for the reply — the whole point.
- The response object has `.status_code`, `.text`, `.json()`, `.headers`, just like `requests`.

> **Reuse the client.** Creating one `AsyncClient` and reusing it for many requests is far more efficient than making a new one each time (it pools and reuses TCP connections). In FastAPI you typically create one client for the app's lifetime.

### What a real external call looks like

```python
# needs internet — illustrative; not executed in this course's sandbox
import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.github.com/repos/tiangolo/fastapi")
        data = r.json()
        print(data["full_name"], "★", data["stargazers_count"])

asyncio.run(main())
```

> This snippet is **not executed here** (the course sandbox has no open internet). Run it yourself — it prints something like `fastapi/fastapi ★ 80000`. The *mechanics* it uses (`AsyncClient`, `await client.get`, `.json()`) are exercised by the verified demo below.

## The payoff: concurrent requests, verified

Here is a **fully offline, runnable** demonstration. It starts a tiny local web server that deliberately takes **1 second** to answer each request, then fires **5 requests concurrently** with `AsyncClient` + `asyncio.gather`. If async I/O works, 5 one-second requests should finish in ~1 second, not 5.

```python
# httpx_concurrency_demo.py
import asyncio
import time
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import httpx


# --- a tiny local server that is deliberately slow (1s per request) ---
class SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(1)                       # simulate a slow backend
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):           # silence the server's request logging
        pass


def start_server():
    # ThreadingHTTPServer handles each request in its own thread,
    # so multiple slow requests can be in flight at the same time.
    ThreadingHTTPServer(("127.0.0.1", 8123), SlowHandler).serve_forever()


threading.Thread(target=start_server, daemon=True).start()
time.sleep(0.3)                              # give the server a moment to start


# --- the async client side ---
async def fetch(client, i):
    r = await client.get("http://127.0.0.1:8123/")   # yields control during the 1s wait
    return f"request {i} -> {r.text}"


async def main():
    start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        # launch all 5 at once; their waits overlap
        results = await asyncio.gather(*(fetch(client, i) for i in range(1, 6)))
    for line in results:
        print(line)
    print(f"5 requests x 1s each, concurrently, total: {time.perf_counter() - start:.1f}s")


asyncio.run(main())
```

A couple of new bits explained:

- `threading.Thread(..., daemon=True)` runs the local server in the background so the script can also act as a client. (`daemon=True` means it won't block the program from exiting.) You don't need threads for *your* async code — this is only to host a fake slow server inside one file.
- `*(fetch(client, i) for i in range(1, 6))` unpacks 5 coroutines as arguments to `gather` — a concise way to run a batch.

**Real output:**

```
request 1 -> ok
request 2 -> ok
request 3 -> ok
request 4 -> ok
request 5 -> ok
5 requests x 1s each, concurrently, total: 1.1s
```

**5 seconds of total waiting, done in ~1 second** (the extra 0.1s is HTTP overhead). Each `await client.get(...)` yielded control, so all five requests waited at the same time. This is precisely how a FastAPI server stays responsive while many users wait on slow backends.

## Concept: why `requests` and `time.sleep` break async

The `requests` library (and `time.sleep`, and most "normal" libraries) are **blocking**: they do *not* yield control. Drop one into an async function and it freezes the **entire** event loop — every other user stalls until it returns.

```python
import requests   # the classic sync library

async def handler():
    r = requests.get("https://slow-api.example/data")   # ❌ BLOCKS the whole loop
    return r.json()
```

While that `requests.get` waits, your single-threaded event loop can do **nothing else** — no other request, no other WebSocket, nothing. It looks like it works in a quick test (one user), then collapses under load. This is the most common way people accidentally destroy their async server's performance.

**The rule:**

| In async code, never use… | Use instead |
|---|---|
| `requests.get(...)` | `await client.get(...)` (httpx AsyncClient) |
| `time.sleep(n)` | `await asyncio.sleep(n)` |
| blocking DB driver | an async driver (e.g. `asyncpg`, `databases`) |
| unavoidable blocking call | `await asyncio.to_thread(blocking_func, ...)` |

`asyncio.to_thread` is the escape hatch: it runs a blocking function in a separate thread and lets you `await` it, so the loop stays free. Use it when there's no async alternative (e.g. a CPU-bound bit, or a library with no async version).

## Common mistakes

**Mistake: forgetting `await` on the request.**

```python
r = client.get(url)          # ❌ r is a coroutine, not a response
print(r.status_code)         # AttributeError: 'coroutine' object has no attribute 'status_code'
```
**Fix:** `r = await client.get(url)`.

**Mistake: a new client per request.**

```python
async def fetch(url):
    async with httpx.AsyncClient() as client:   # ❌ wasteful if called in a loop
        return await client.get(url)
```
Creating/closing a client every call throws away connection pooling. **Fix:** create one client and pass it in (as the demo does), or in FastAPI create it once for the app.

## Practice

**Exercise 1:** Take the verified concurrency demo and change `asyncio.gather(...)` so the 5 requests run **sequentially** instead (one `await` at a time, in a loop). Predict and then measure the new total time.

<details><summary>Solution</summary>

```python
async def main():
    start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        results = []
        for i in range(1, 6):
            results.append(await fetch(client, i))   # each await fully completes before the next
    for line in results:
        print(line)
    print(f"sequential total: {time.perf_counter() - start:.1f}s")
```

Now each request waits its full second before the next starts → **~5.0s** total (verified). Same five results, five times slower. This is the difference `gather` makes.
</details>

**Exercise 2:** Your teammate's async endpoint uses `time.sleep(0.5)` to "throttle" each call and complains the whole server gets sluggish under load. What's wrong and what's the one-line fix?

<details><summary>Solution</summary>

`time.sleep(0.5)` is **blocking** — it freezes the entire event loop for half a second on every call, so all concurrent users stall. Fix: `await asyncio.sleep(0.5)`, which yields control during the wait so other requests proceed.
</details>

## Recap & next

- ✅ Use **`httpx.AsyncClient`** with `async with` and `await client.get/post(...)` for async HTTP.
- ✅ Concurrent requests via `gather` overlap their waits — verified: 5×1s → 1s.
- ✅ **Never** use blocking calls (`requests`, `time.sleep`, sync DB drivers) in async code; they freeze the whole loop. Use async equivalents or `asyncio.to_thread`.
- ✅ Reuse one client; always `await` the request.
- Self-check: why does one `requests.get` inside an async handler hurt *every* connected user, not just the one making that call?

→ Next: **[Section 02 · FastAPI basics](../02_fastapi_basics/README.md)** — turn these async skills into a real web server.
