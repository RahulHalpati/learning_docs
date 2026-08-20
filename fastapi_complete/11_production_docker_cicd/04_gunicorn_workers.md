# 11-4 · Gunicorn: process manager & worker model

> **Level:** Intermediate→Advanced · **Prerequisites:** [11-2 · Compose & runtime](02_compose_and_runtime.md)
> **Time:** ~35–45 min · **Verified:** 2026-08-07 (Gunicorn · uvicorn workers · Nginx)

## Why this matters

11-2 called `gunicorn -k uvicorn.workers.UvicornWorker` the "legacy pattern" — and it is, for a k8s deploy. But it's also on half the job descriptions you'll read, and the interview question behind it ("why can't Gunicorn just run FastAPI?") separates people who *deployed* Python from people who copied a command. Get this lesson right and you can explain WSGI vs ASGI, worker classes, and worker-count math on the spot — the four things every Gunicorn JD actually tests.

---

## The one correction: Gunicorn can't run FastAPI (directly)

Gunicorn is a **WSGI** server. WSGI is a *synchronous* contract — one callable, one request in, one response out, the worker blocks until it returns. Flask and Django speak it.

FastAPI speaks **ASGI** — the *async* contract, built around an event loop so one process juggles thousands of concurrent connections without a thread per request. These two protocols are not interchangeable. Hand your FastAPI `app` to Gunicorn's default worker and it crashes: the sync worker tries to call an async ASGI app as if it were a plain WSGI function.

So you don't run FastAPI *on* Gunicorn. You run Gunicorn as a **process manager** for **Uvicorn worker processes**:

```bash
uv add gunicorn uvicorn

# Gunicorn is the master; each worker is a full Uvicorn ASGI server.
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
```

The division of labor is the whole point:

- **Gunicorn (master process):** binds the socket, forks and supervises workers, monitors their health, restarts crashed ones, handles signals, orchestrates graceful reloads. It never touches a single HTTP request itself.
- **Uvicorn worker (`-k uvicorn.workers.UvicornWorker`):** *is* an ASGI server running your event loop. It accepts connections on the shared socket and serves your async FastAPI app.

> **Interview one-liner:** "Gunicorn is a WSGI process manager; the `UvicornWorker` class adapts each worker into an ASGI server, so Gunicorn supervises processes while Uvicorn runs the async app." That sentence is the answer to the #1 Gunicorn gotcha.

---

## What Gunicorn buys you over bare `uvicorn --workers`

11-2 showed `uvicorn app.main:app --workers 4` — Uvicorn forking its own workers. That works. So why does the Gunicorn pattern survive? Because Gunicorn's master is a **battle-tested supervisor** with features Uvicorn's forker doesn't fully match:

- **Health monitoring + auto-restart.** A worker that hangs past `timeout` or dies is reaped and replaced automatically. The master keeps the socket open, so no requests are refused during the swap.
- **Graceful reload on `SIGHUP`.** Reload config/code with zero dropped connections (next section) — no `docker restart`, no blip.
- **Worker recycling** via `--max-requests` / `--max-requests-jitter`: retire a worker after N requests to cap the blast radius of a slow memory leak in a dependency.
- **Richer signal + timeout handling:** `--graceful-timeout`, per-signal semantics, `TTIN`/`TTOU` to scale workers live.

Be honest about the trade, though: **Uvicorn's `--workers` has matured** and is perfectly fine for many single-host deploys — and on an orchestrator (11-2) you often want *one process per container* and none of Gunicorn's supervision at all. Gunicorn+UvicornWorker is the **traditional, ops-friendly choice on a VM or single host**, not a universal upgrade.

---

## Worker classes: pick the right `-k`

`-k` (`--worker-class`) is where people go wrong. The class decides how a worker handles concurrency:

| Class | Model | Use for |
|-------|-------|---------|
| `sync` (default) | One request at a time, blocks | Traditional WSGI (Flask/Django) — **wrong for FastAPI** |
| `gthread` (`--threads N`) | Sync worker, thread pool per worker | WSGI apps that do blocking I/O |
| `uvicorn.workers.UvicornWorker` | **ASGI event loop** (uvloop + httptools) | **FastAPI / any ASGI app** |
| `uvicorn.workers.UvicornH11Worker` | ASGI event loop, pure-Python `h11` HTTP | ASGI where uvloop/httptools can't build |

For FastAPI the answer is `UvicornWorker`. The `H11` variant is the fallback when the C-accelerated stack (uvloop, httptools) won't install — slower, but pure Python. The default `sync` class is the trap: run it against FastAPI and every async endpoint breaks.

---

## Worker count: async is NOT `(2 × cores) + 1`

The famous Gunicorn rule of thumb — **`(2 × CPU cores) + 1`** — is for **sync** workers. A sync worker is blocked for the entire duration of one request, so you provision extra workers to keep the CPU busy while others wait on I/O. On a 4-core box: `2×4 + 1 = 9` sync workers.

**That number is wrong for async workers.** A `UvicornWorker` runs an event loop: while one request awaits the database, the same worker is already serving hundreds of others. It is *not* blocked per-request, so you don't need to oversubscribe to hide I/O waits. The rule flips:

- **Async (UvicornWorker): ~1 worker per core** (sometimes cores × 1–2 under heavy CPU work). On 4 cores → **4 workers**, not 9.
- Each async worker is a full Python process (~100–200 MB with your deps loaded). Applying `2N+1` to async workers just **doubles your memory bill** to serve the same concurrency the event loop already handled.

```bash
# 4-core host, async app:
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4   # ✅ ~1 per core
# gunicorn ... -w 9   # ❌ that's the SYNC formula — wasted RAM, no throughput gain
```

> **The mental model:** sync scales concurrency with *processes* (so you need many); async scales concurrency *inside* each process on the event loop (so you need few). Reciting `2N+1` for a FastAPI app is a tell that someone hasn't internalized this.

---

## Configuration: `gunicorn.conf.py`

Flags don't scale; put the config in a file Gunicorn auto-loads. Every line here is a decision:

```python
# gunicorn.conf.py — auto-discovered when you run `gunicorn app.main:app`
import multiprocessing

bind = "0.0.0.0:8000"                         # or "unix:/run/linkbox.sock" behind Nginx (see below)
worker_class = "uvicorn.workers.UvicornWorker"  # ASGI — the whole reason Gunicorn can serve FastAPI
workers = multiprocessing.cpu_count()         # ~1 per core for ASGI, NOT (2*cores)+1

timeout = 30              # kill+replace a worker silent for 30s (a hung request, not a slow one)
graceful_timeout = 30     # on reload/shutdown, give in-flight requests 30s to finish before SIGKILL
keepalive = 5             # hold idle keep-alive conns 5s; behind Nginx this can be higher

# Recycle workers to bound slow memory leaks in deps. Jitter staggers restarts
# so all workers don't recycle on the same request and drop capacity at once.
max_requests = 1000
max_requests_jitter = 100   # actual limit = 1000..1100, randomized per worker

accesslog = "-"          # "-" = stdout, so Docker/journald collects logs (12-factor)
errorlog = "-"           # "-" = stderr
loglevel = "info"

preload_app = False      # see the trade-off below
```

**`preload_app`** deserves its own note. `True` imports your app **once in the master**, then forks — workers share that memory copy-on-write (lower RAM, faster boot). The cost: anything created at import time is now **shared across forks**, which breaks per-worker resources (a DB pool or async event loop created before fork misbehaves after it) and disables graceful code reload. For an async app with connection pools, keep it **`False`** unless you've measured a memory win and confirmed nothing global is created at import.

---

## Graceful reload & worker recycling

This is Gunicorn's headline feature and a common interview probe. Two signals to the *master*:

```bash
kill -HUP  $(cat /run/linkbox.pid)   # graceful reload: re-read config, roll workers, ZERO downtime
kill -TERM $(cat /run/linkbox.pid)   # graceful shutdown: drain in-flight, then exit
```

On **`SIGHUP`** the master starts new workers with the fresh code/config, lets old workers **finish their in-flight requests** (up to `graceful_timeout`), then retires them. The listening socket never closes, so no connection is refused across the swap. That's how you reload a VM deploy without a load-balancer blip.

**Worker recycling** (`max_requests`) is the same graceful-swap, triggered by request count instead of a signal: after ~1000 requests a worker finishes its current request, exits, and the master forks a replacement. It's a pragmatic seatbelt — it won't fix a leak, but it stops one in a third-party lib from OOM-killing the box overnight. The jitter matters: without it, workers that started together hit 1000 together and all recycle at once, dropping capacity in a synchronized dip.

---

## Behind Nginx: the standard topology

Gunicorn is an app server, not an edge server. In production it sits **behind Nginx**, which owns everything you don't want async workers spending cycles on:

- **TLS termination** — Nginx does the HTTPS handshake; Gunicorn speaks plain HTTP on a private socket.
- **Static files** — served straight from disk by Nginx, never touching a Python worker.
- **Request/response buffering** — Nginx absorbs slow clients. A slowloris client dribbling one byte a second ties up *Nginx*, not a precious event-loop worker. This alone is why you don't expose Gunicorn directly.
- **`X-Forwarded-For` / `X-Forwarded-Proto`** — the real client IP and scheme, since Gunicorn only sees Nginx's address.
- **Load-balancing** across multiple Gunicorn hosts/sockets.

Gunicorn binds a **unix socket** (or `127.0.0.1:8000`); only Nginx is public:

```nginx
# /etc/nginx/sites-enabled/linkbox
upstream linkbox { server unix:/run/linkbox.sock; }   # Gunicorn's bind target

server {
    listen 443 ssl;
    server_name linkbox.example.com;
    # ssl_certificate / ssl_certificate_key here — TLS ends at Nginx

    location /static/ { alias /srv/linkbox/static/; }  # bypass Python entirely

    location / {
        proxy_pass http://linkbox;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;     # so FastAPI knows it's HTTPS
    }
}
```

> **Ties back to rate-limiting (Section 10):** your app reads the client IP from `X-Forwarded-For`. Only trust that header when the request came through **your own** Nginx — a client can forge it otherwise. Configure the ASGI/Uvicorn proxy-headers trust (`--forwarded-allow-ips`) to accept it *only* from the Nginx address, or an attacker spoofs their way past your per-IP limits.

---

## In Docker (and the 2026 reality)

In a container, Gunicorn is the `CMD` — **exec-form**, so Gunicorn is PID 1 and receives `SIGTERM` directly (same lesson as 11-1/11-2: shell-form swallows the signal):

```dockerfile
# exec-form → gunicorn is PID 1 → gets SIGTERM → drains workers gracefully
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

On `SIGTERM` the Gunicorn master stops accepting, drains in-flight requests up to `graceful_timeout`, then exits — the graceful-shutdown chain from 11-2, with Gunicorn's master as the drain coordinator.

But know **when this pattern earns its keep in 2026**:

- **Single VM / single host:** Gunicorn's multi-worker supervision is genuinely useful — one container, N workers, auto-restart, `SIGHUP` reload. This is where it shines.
- **Kubernetes / cloud-native:** the modern default flips to **one process per container, scale by replicas**. The orchestrator already does health checks, restarts, rolling deploys, and load-balancing — so Gunicorn's master duplicates the platform. Many k8s FastAPI images run a single Uvicorn process and let the Deployment own concurrency. Multi-worker-per-pod also blurs the orchestrator's per-unit accounting (CPU/memory requests, probes).

Neither is "correct" everywhere — matching the tool to the host is the point. On a box, Gunicorn. On k8s, replicas.

---

## Recap & next

- ✅ **Gunicorn is WSGI (sync); FastAPI is ASGI (async)** — you can't run FastAPI on Gunicorn directly. Run Gunicorn as a **process manager** for **Uvicorn workers**: `-k uvicorn.workers.UvicornWorker`.
- ✅ Gunicorn's master gives you **health-monitored auto-restart, `SIGHUP` graceful reload, and `--max-requests` worker recycling** over bare `uvicorn --workers` — the ops-friendly choice on a VM. On k8s, one-process-per-container often wins.
- ✅ **Worker count: sync = `(2×cores)+1`, async ≈ 1 per core.** Async workers aren't blocked per-request, so `2N+1` just wastes RAM. Set with `-w`.
- ✅ **Worker classes:** `sync` (WSGI default, wrong for FastAPI), `gthread`, and `UvicornWorker`/`UvicornH11Worker` for ASGI. Use `UvicornWorker`.
- ✅ **Nginx in front** terminates TLS, serves static, buffers slow clients, and sets `X-Forwarded-*` — Gunicorn binds a private unix socket. Only trust forwarded headers from your own proxy.
- ✅ Self-check: you're handed a FastAPI service on a 8-core VM configured with `-w 17` sync workers and getting OOM-killed. What two things are wrong, and what do you change them to?

→ Next: **[Capstone · DevBoard](../99_capstone_devboard.md)**

## Exercises

1. A teammate deploys FastAPI with `gunicorn app.main:app -w 4` (no `-k`) and every request 500s with an error about the app not being callable in the expected way. What's wrong, and what's the one-flag fix?

<details>
<summary>Solution</summary>

No `-k` means the **default `sync` worker class**, which expects a WSGI callable. FastAPI is an ASGI app — the sync worker can't invoke it correctly, so every request errors. The fix is one flag: `-k uvicorn.workers.UvicornWorker`, which makes each worker an ASGI (Uvicorn) server. This is the WSGI-vs-ASGI gotcha in the wild: Gunicorn *supervises* the process, but the worker class is what actually speaks the app's protocol.
</details>

2. You're sizing workers for a mostly-I/O-bound FastAPI app (calls Postgres and an upstream API) on a 4-core box with 2 GB RAM. Someone proposes the classic `(2×4)+1 = 9` workers. Why is that the wrong formula here, and what would you set instead?

<details>
<summary>Solution</summary>

`(2×cores)+1` is the **sync**-worker rule — it exists to hide per-request blocking by running many processes. An async `UvicornWorker` isn't blocked per request; its event loop already serves hundreds of concurrent I/O-bound requests per process, so extra workers add memory (~100–200 MB each) without adding throughput. Nine workers on 2 GB is a straight path to OOM. Set **~1 per core → 4 workers** (`-w 4`), and scale further with replicas/hosts, not more workers-per-box. If profiling later showed CPU saturation you might try cores×1.5–2, but you'd measure first.
</details>

3. Explain, signal by signal, how `SIGHUP` to a running Gunicorn master gives a zero-downtime code reload — and one reason you'd still prefer rolling replicas behind a load balancer on Kubernetes.

<details>
<summary>Solution</summary>

`SIGHUP` tells the **master** (not the workers) to reload: it re-reads the config, spawns **new** workers running the fresh code, and signals old workers to stop accepting new requests while **finishing their in-flight ones** (up to `graceful_timeout`), then retires them. The listening socket stays open on the master the whole time, so no connection is ever refused — that's the zero-downtime part. On Kubernetes you'd still prefer rolling replicas because the orchestrator can shift **traffic** away from a pod before touching it, roll pod-by-pod across nodes, and automatically roll *back* on a failed health check — cluster-level guarantees a single host's in-place `SIGHUP` can't provide (if that one box dies mid-reload, everything on it is gone).
</details>
